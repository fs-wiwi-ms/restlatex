import json
import asyncio
from typing import Optional
from fastapi import FastAPI, Request, Response, Query
from fastapi.responses import JSONResponse

from app.config import settings
from app.compiler import compile_latex, CompilationError, CompilationTimeoutError

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/api/compile")
async def compile_endpoint(request: Request, timeout: Optional[int] = Query(None)):
    effective_timeout = timeout
    if effective_timeout is None:
        header_timeout = request.headers.get("X-Compile-Timeout")
        if header_timeout and header_timeout.isdigit():
            effective_timeout = int(header_timeout)
        else:
            effective_timeout = settings.TIMEOUT_SECONDS

    raw_body_bytes = await request.body()
    if not raw_body_bytes or not raw_body_bytes.strip():
        return Response(
            content="Empty request body. Please provide LaTeX source code.",
            status_code=422,
            media_type="text/plain; charset=utf-8",
        )

    content_type = request.headers.get("content-type", "").lower()
    if "application/json" in content_type:
        try:
            parsed_json = json.loads(raw_body_bytes.decode("utf-8"))
            if isinstance(parsed_json, dict):
                tex_source = (
                    parsed_json.get("tex")
                    or parsed_json.get("latex")
                    or parsed_json.get("code")
                    or parsed_json.get("content")
                    or parsed_json.get("source")
                    or parsed_json.get("document")
                    or ""
                )
            elif isinstance(parsed_json, str):
                tex_source = parsed_json
            else:
                tex_source = raw_body_bytes.decode("utf-8", errors="replace")
        except Exception:
            tex_source = raw_body_bytes.decode("utf-8", errors="replace")
    else:
        tex_source = raw_body_bytes.decode("utf-8", errors="replace")

    if not tex_source.strip():
        return Response(
            content="No valid LaTeX source code found in request payload.",
            status_code=422,
            media_type="text/plain; charset=utf-8",
        )

    try:
        pdf_bytes = await asyncio.to_thread(compile_latex, tex_source, effective_timeout)
        return Response(
            content=pdf_bytes,
            status_code=200,
            media_type="application/pdf",
            headers={"Content-Disposition": 'inline; filename="document.pdf"'},
        )
    except CompilationError as e:
        return Response(
            content=e.message,
            status_code=422,
            media_type="text/plain; charset=utf-8",
        )
    except CompilationTimeoutError as e:
        return JSONResponse(
            content={
                "error": "Compilation timeout",
                "detail": e.message,
                "timeout_seconds": e.timeout_seconds,
            },
            status_code=504,
        )
    except Exception as e:
        return JSONResponse(
            content={"error": "Internal server error", "detail": str(e)},
            status_code=500,
        )
