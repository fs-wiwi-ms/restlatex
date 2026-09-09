import os
import signal
import shutil
import uuid
import subprocess
from pathlib import Path

from app.config import settings
from app.security import build_bwrap_command, set_child_resource_limits
from app.parser import parse_tex_log


class CompilationError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class CompilationTimeoutError(Exception):
    def __init__(self, timeout_seconds: int, message: str = ""):
        msg = message or f"Compilation timed out after {timeout_seconds} seconds"
        super().__init__(msg)
        self.timeout_seconds = timeout_seconds
        self.message = msg


def compile_latex(tex_source: str, timeout_seconds: int = None) -> bytes:
    if timeout_seconds is None:
        timeout_seconds = settings.TIMEOUT_SECONDS

    job_uuid = uuid.uuid4().hex
    job_dir = Path(settings.TEMP_DIR) / f"{settings.JOB_PREFIX}{job_uuid}"
    job_dir.mkdir(parents=True, mode=0o700, exist_ok=False)

    tex_filename = "input.tex"
    pdf_filename = "input.pdf"
    log_filename = "input.log"

    try:
        tex_path = job_dir / tex_filename
        tex_path.write_text(tex_source, encoding="utf-8")

        bwrap_cmd = build_bwrap_command(job_dir, tex_filename)
        proc = subprocess.Popen(
            bwrap_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
            preexec_fn=set_child_resource_limits,
        )

        try:
            stdout, stderr = proc.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                try:
                    proc.kill()
                except Exception:
                    pass
            try:
                proc.communicate(timeout=2)
            except Exception:
                pass
            raise CompilationTimeoutError(timeout_seconds=timeout_seconds)

        pdf_path = job_dir / pdf_filename
        log_path = job_dir / log_filename

        if proc.returncode != 0 or not pdf_path.exists() or pdf_path.stat().st_size == 0:
            log_content = ""
            if log_path.exists():
                try:
                    log_content = log_path.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    pass

            parsed_error = parse_tex_log(log_content, stderr_fallback=stderr or stdout)
            raise CompilationError(parsed_error)

        return pdf_path.read_bytes()

    finally:
        shutil.rmtree(job_dir, ignore_errors=True)
