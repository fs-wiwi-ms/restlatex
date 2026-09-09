# RestLatex

A stateless, hardened HTTP microservice to securely compile untrusted LaTeX documents into PDFs.

## Security Architecture

RestLatex isolates untrusted LaTeX execution through a two-tier sandboxing architecture:

- **OCI Container Hardening:**
  - Read-only root filesystem (`--read-only`).
  - Unprivileged execution (`appuser`, UID 10001, GID 10001).
  - Volatile in-memory temporary storage (`tmpfs /tmp:rw,noexec,nosuid,size=512m`).
  - Privilege escalation prevented (`no-new-privileges:true`).

- **Bubblewrap (bwrap) Process Sandboxing:**
  - Full namespace isolation: `--unshare-user`, `--unshare-net` (no network access), `--unshare-pid`, `--unshare-ipc`, `--unshare-uts`.
  - Minimal read-only mounts: Only `/usr` and necessary TeX system paths are mounted read-only.
  - Backend application directory (`/app`) and sensitive system files (`/etc/passwd`, `/root`) are completely excluded from the sandbox.
  - Only the request-specific ephemeral directory `/tmp/compile_<uuid>` is mounted read-write.
  - Resource limits enforced via `RLIMIT_AS` (memory limit) and process tree termination (`SIGKILL`) on timeout.

- **TeX Engine Hardening (`texmf.cnf`):**
  - `openin_any = p`: Blocks parent directory traversal (`../`) and unauthorized file access.
  - `openout_any = p`: Blocks writing files outside the job directory.
  - `shell_escape = f`: Fully disables shell execution (`\write18`).

- **Deterministic Cleanup:**
  - Ephemeral directories (`/tmp/compile_<uuid>`) are strictly removed in a `try...finally` block across all scenarios (success, compilation error, timeout, or unexpected exception).
  - The generated PDF is read into memory before directory removal, guaranteeing zero leaked disk space.

---

## API Specification

### Endpoints

#### 1. `POST /api/compile`

Compiles a LaTeX document and returns the generated PDF.

##### Request Parameters

- **Query Parameters (optional):**
  - `timeout` (integer): Per-request timeout in seconds (default: `30`).
- **Headers (optional):**
  - `Content-Type`: `application/json` or `text/plain`.
  - `X-Compile-Timeout`: Alternative way to set per-request timeout.

##### Request Formats

The endpoint accepts either:
1. **Raw TeX source** (recommended for direct file streaming).
2. **JSON payload** (`{"tex": "\\documentclass{article}..."}`).

##### Response Formats

| Status Code | Content-Type | Description |
| :--- | :--- | :--- |
| **`200 OK`** | `application/pdf` | Binary PDF stream. Header: `Content-Disposition: inline; filename="document.pdf"` |
| **`422 Unprocessable Entity`** | `text/plain; charset=utf-8` | Raw filtered log with error type, line number, and context. |
| **`504 Gateway Timeout`** | `application/json` | JSON error explaining timeout termination. |

#### 2. `GET /health`

Health check endpoint returning `{"status": "healthy"}` (`200 OK`).

---

## API Usage Examples

### Using cURL

#### 1. Compile Raw TeX File to PDF
```bash
curl -s -X POST http://localhost:8000/api/compile \
  --data-binary @document.tex \
  --output document.pdf
```

#### 2. Compile via JSON Payload
```bash
curl -s -X POST http://localhost:8000/api/compile \
  -H "Content-Type: application/json" \
  -d '{"tex": "\\documentclass{article}\\begin{document}Hello World!\\end{document}"}' \
  --output document.pdf
```

#### 3. Set a Custom Compilation Timeout (e.g., 10 seconds)
```bash
curl -s -X POST "http://localhost:8000/api/compile?timeout=10" \
  --data-binary @document.tex \
  --output document.pdf
```

#### 4. Handling Errors in Bash
```bash
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST http://localhost:8000/api/compile --data-binary @document.tex -o /tmp/result.bin)
HTTP_STATUS=$(echo "$RESPONSE" | tail -n 1)

if [ "$HTTP_STATUS" -eq 200 ]; then
  mv /tmp/result.bin document.pdf
  echo "PDF successfully created."
elif [ "$HTTP_STATUS" -eq 422 ]; then
  echo "LaTeX compilation error:"
  cat /tmp/result.bin
elif [ "$HTTP_STATUS" -eq 504 ]; then
  echo "Compilation timed out:"
  cat /tmp/result.bin
fi
```

---

### Using Python (`httpx` / `requests`)

```python
import httpx

latex_code = r"""
\documentclass{article}
\begin{document}
Hello from Python!
\end{document}
"""

response = httpx.post(
    "http://localhost:8000/api/compile",
    content=latex_code,
    headers={"Content-Type": "text/plain"},
    params={"timeout": 30}
)

if response.status_code == 200:
    with open("output.pdf", "wb") as f:
        f.write(response.content)
    print("PDF saved.")
elif response.status_code == 422:
    print("Compilation Error:\n", response.text)
elif response.status_code == 504:
    print("Timeout:", response.json())
```

---

### Using JavaScript / TypeScript (`fetch`)

```javascript
const latexCode = `
\\documentclass{article}
\\begin{document}
Hello from JavaScript!
\\end{document}
`;

const response = await fetch("http://localhost:8000/api/compile", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ tex: latexCode })
});

if (response.ok) {
  const pdfBlob = await response.blob();
  const pdfBuffer = Buffer.from(await pdfBlob.arrayBuffer());
  // Save or stream pdfBuffer
} else if (response.status === 422) {
  const errorLog = await response.text();
  console.error("LaTeX Error:\n", errorLog);
} else if (response.status === 504) {
  const timeoutInfo = await response.json();
  console.error("Timeout:\n", timeoutInfo);
}
```

---

## Configuration

The service can be configured via environment variables:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `RESTLATEX_TIMEOUT_SECONDS` | `30` | Default timeout for compilation in seconds. |
| `RESTLATEX_MAX_MEMORY_MB` | `512` | Address space memory limit per compilation process. |
| `RESTLATEX_MAX_FILE_SIZE_MB`| `50` | Maximum generated file size limit. |
| `RESTLATEX_BWRAP_PATH` | `/usr/bin/bwrap` | Path to the bubblewrap executable. |
| `RESTLATEX_LATEXMK_PATH` | `/usr/bin/latexmk` | Path to the latexmk executable. |

---

## Quickstart

### Using Docker Compose

```bash
docker compose up -d
```

### Using Docker Directly

```bash
docker run -d \
  --name restlatex \
  -p 8000:8000 \
  --user 10001:10001 \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=512m \
  --security-opt=no-new-privileges:true \
  --security-opt seccomp=unconfined \
  --cap-add=SYS_ADMIN \
  ghcr.io/fs-wiwi-ms/restlatex:latest
```

---

## Running Tests

Execute the test suite inside the hardened container:

```bash
docker run --rm \
  --user 10001:10001 \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=512m \
  --security-opt=no-new-privileges:true \
  --security-opt seccomp=unconfined \
  --cap-add=SYS_ADMIN \
  restlatex:latest \
  pytest -v -o cache_dir=/tmp/.pytest_cache
```
