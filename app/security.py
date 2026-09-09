import errno
import os
import resource
import tempfile
from pathlib import Path
from typing import List, Optional
from app.config import settings

_SECCOMP_BPF_BYTES: Optional[bytes] = None


def get_seccomp_bpf_bytes() -> Optional[bytes]:
    global _SECCOMP_BPF_BYTES
    if _SECCOMP_BPF_BYTES is None:
        try:
            import seccomp

            f = seccomp.SyscallFilter(defaction=seccomp.ALLOW)
            for sc in [
                "socket",
                "connect",
                "bind",
                "accept",
                "accept4",
                "sendto",
                "recvfrom",
                "sendmsg",
                "recvmsg",
            ]:
                try:
                    f.add_rule(seccomp.ERRNO(errno.EPERM), sc)
                except Exception:
                    pass
            with tempfile.NamedTemporaryFile() as tmp:
                f.export_bpf(tmp)
                tmp.seek(0)
                _SECCOMP_BPF_BYTES = tmp.read()
        except Exception:
            return None
    return _SECCOMP_BPF_BYTES


def get_verified_ro_binds() -> List[str]:
    forbidden_prefixes = [
        str(Path(settings.APP_DIR).resolve()),
        "/root",
        "/home",
    ]

    verified = []
    for cand in settings.CANDIDATE_RO_BINDS:
        p = Path(cand)
        if p.exists() and not p.is_symlink():
            resolved = str(p.resolve())
            if any(resolved == f or resolved.startswith(f + "/") for f in forbidden_prefixes):
                continue
            verified.append(str(p))
    return verified


def build_bwrap_command(
    job_dir: Path,
    tex_filename: str = "input.tex",
    seccomp_fd: Optional[int] = None,
) -> List[str]:
    cmd = [
        settings.BWRAP_PATH,
        "--unshare-user",
        "--unshare-ipc",
        "--unshare-pid",
        "--unshare-uts",
        "--die-with-parent",
        "--dev", "/dev",
    ]

    if seccomp_fd is not None:
        cmd.extend(["--seccomp", str(seccomp_fd)])

    if Path("/usr").exists():
        cmd.extend(["--ro-bind", "/usr", "/usr"])

    for sym_candidate in ["/bin", "/lib", "/lib64", "/sbin"]:
        p = Path(sym_candidate)
        if p.is_symlink():
            cmd.extend(["--symlink", os.readlink(str(p)), sym_candidate])
        elif p.is_dir():
            cmd.extend(["--ro-bind", sym_candidate, sym_candidate])

    for ro_path in get_verified_ro_binds():
        if ro_path not in ["/usr", "/bin", "/lib", "/lib64", "/sbin"]:
            cmd.extend(["--ro-bind", ro_path, ro_path])

    cmd.extend(["--dir", "/tmp"])

    job_dir_str = str(job_dir.resolve())
    cmd.extend(["--bind", job_dir_str, job_dir_str])
    cmd.extend(["--chdir", job_dir_str])

    cmd.extend([
        "--setenv", "PATH", "/usr/bin:/bin",
        "--setenv", "HOME", job_dir_str,
        "--setenv", "TMPDIR", job_dir_str,
        "--setenv", "TEXMFOUTPUT", job_dir_str,
        "--setenv", "LC_ALL", "C.UTF-8",
    ])

    cmd.extend([
        settings.LATEXMK_PATH,
        "-pdf",
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-no-shell-escape",
        tex_filename
    ])

    return cmd


def set_child_resource_limits():
    try:
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    except Exception:
        pass

    if settings.MAX_MEMORY_MB > 0:
        mem_bytes = settings.MAX_MEMORY_MB * 1024 * 1024
        try:
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        except Exception:
            pass

    if settings.MAX_FILE_SIZE_MB > 0:
        fsize_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        try:
            resource.setrlimit(resource.RLIMIT_FSIZE, (fsize_bytes, fsize_bytes))
        except Exception:
            pass
