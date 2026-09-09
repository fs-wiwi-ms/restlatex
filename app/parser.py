import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ParsedError:
    error_type: str
    line_number: Optional[int]
    context_line: str
    raw_block: str

    def format_raw(self) -> str:
        parts = [f"! {self.error_type}"]
        if self.line_number is not None:
            parts.append(f"Line: {self.line_number}")
        if self.context_line:
            parts.append(f"Context: {self.context_line}")
        parts.append("--- Details ---")
        parts.append(self.raw_block.strip())
        return "\n".join(parts)


def parse_tex_log(log_content: str, stderr_fallback: str = "") -> str:
    if not log_content and not stderr_fallback:
        return "Compilation failed: No error log generated."

    lines = log_content.splitlines() if log_content else []
    errors: List[ParsedError] = []

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if line.startswith("!"):
            raw_lines = [line]
            error_type = line[1:].strip()
            line_number: Optional[int] = None
            context_parts: List[str] = []

            i += 1
            while i < n:
                curr_line = lines[i]
                if curr_line.startswith("!"):
                    break

                raw_lines.append(curr_line)
                pkg_cont = re.match(r"^\(([a-zA-Z0-9_\-]+)\)\s+(.*)", curr_line)
                if pkg_cont and not line_number:
                    error_type += " " + pkg_cont.group(2).strip()

                l_match = re.match(r"^l\.(\d+)\s*(.*)", curr_line)
                if l_match:
                    line_number = int(l_match.group(1))
                    first_ctx = l_match.group(2).strip()
                    if first_ctx:
                        context_parts.append(first_ctx)

                    if i + 1 < n and not lines[i + 1].startswith("!"):
                        next_line = lines[i + 1]
                        if next_line.startswith(" ") or next_line.startswith("\t"):
                            raw_lines.append(next_line)
                            second_ctx = next_line.strip()
                            if second_ctx:
                                context_parts.append(second_ctx)
                            i += 1
                    i += 1
                    break

                i += 1

            full_context = " ".join(context_parts).strip()
            if error_type.endswith("."):
                error_type = error_type[:-1]

            raw_block = "\n".join(raw_lines).strip()
            errors.append(
                ParsedError(
                    error_type=error_type,
                    line_number=line_number,
                    context_line=full_context,
                    raw_block=raw_block,
                )
            )
        else:
            i += 1

    for idx in range(len(errors) - 1):
        if errors[idx].line_number is None and errors[idx + 1].error_type.startswith("Emergency stop"):
            if errors[idx + 1].line_number is not None:
                errors[idx].line_number = errors[idx + 1].line_number
                if not errors[idx].context_line:
                    errors[idx].context_line = errors[idx + 1].context_line

    if errors:
        specific_errors = [
            e
            for e in errors
            if not e.error_type.startswith("Emergency stop")
            and not e.error_type.startswith("==> Fatal error")
            and "no output PDF file produced" not in e.error_type
        ]
        errors_to_report = specific_errors if specific_errors else errors

        output_blocks = []
        for idx, err in enumerate(errors_to_report, 1):
            header = f"=== LaTeX Error {idx} ==="
            output_blocks.append(f"{header}\n{err.format_raw()}")
        return "\n\n".join(output_blocks)

    if stderr_fallback:
        return f"Compilation process error:\n{stderr_fallback.strip()}"

    last_lines = [l for l in lines if l.strip()][-20:]
    return "Compilation failed without explicit error marker:\n" + "\n".join(last_lines)
