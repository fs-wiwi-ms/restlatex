import pytest
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_arbitrary_file_read_etc_passwd():
    tex = r"""
\documentclass{article}
\begin{document}
\input{/etc/passwd}
\end{document}
"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/compile", content=tex)
        assert response.status_code == 422
        error_text = response.text
        assert "not found" in error_text or "Emergency stop" in error_text
        assert "root:x:0:0" not in error_text


@pytest.mark.asyncio
async def test_arbitrary_file_read_app_source():
    tex = r"""
\documentclass{article}
\begin{document}
\input{/app/main.py}
\end{document}
"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/compile", content=tex)
        assert response.status_code == 422
        error_text = response.text
        assert "not found" in error_text or "Emergency stop" in error_text
        assert "compile_endpoint" not in error_text


@pytest.mark.asyncio
async def test_rce_shell_escape():
    hacked_file = Path("/tmp/hacked.txt")
    if hacked_file.exists():
        hacked_file.unlink()

    tex = r"""
\documentclass{article}
\begin{document}
\immediate\write18{id > /tmp/hacked.txt}
\immediate\write18{touch /tmp/hacked.txt}
RCE Test
\end{document}
"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/compile", content=tex)
        assert not hacked_file.exists()


@pytest.mark.asyncio
async def test_path_traversal_escape():
    tex = r"""
\documentclass{article}
\begin{document}
\input{../../../../etc/shadow}
\end{document}
"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/compile", content=tex)
        assert response.status_code == 422
        assert "shadow" not in response.text or "not found" in response.text


@pytest.mark.asyncio
async def test_dos_infinite_loop_timeout():
    tex = r"""
\documentclass{article}
\begin{document}
\def\loopit{\loopit}\loopit
\end{document}
"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/compile?timeout=3", content=tex)
        assert response.status_code == 504
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert data.get("error") == "Compilation timeout"
        assert data.get("timeout_seconds") == 3


@pytest.mark.asyncio
async def test_dos_memory_exhaustion():
    tex = r"""
\documentclass{article}
\begin{document}
\newcount\i
\i=0
\def\eat#1{}
\def\recurse{\advance\i by 1 \edef\foo{\foo \foo A}\recurse}
\def\foo{AAAAAAAAAAAAAAAAAAAAAAAAAAAA}
\recurse
\end{document}
"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/compile?timeout=5", content=tex)
        assert response.status_code in [422, 504]
        health_resp = await client.get("/health")
        assert health_resp.status_code == 200
        assert health_resp.json() == {"status": "healthy"}
