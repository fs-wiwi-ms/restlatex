import os
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_cleanup_after_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        before_entries = set(os.listdir("/tmp"))
        tex = r"""
\documentclass{article}
\begin{document}
Cleanup test: Success path.
\end{document}
"""
        response = await client.post("/api/compile", content=tex)
        assert response.status_code == 200

        after_entries = set(os.listdir("/tmp"))
        diff = after_entries - before_entries
        assert len(diff) == 0, f"Leaked files in /tmp: {diff}"
        assert len(after_entries) == len(before_entries)


@pytest.mark.asyncio
async def test_cleanup_after_compilation_error():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        before_entries = set(os.listdir("/tmp"))
        tex = r"""
\documentclass{article}
\begin{document}
\invalidSyntaxHere%%%
\end{document}
"""
        response = await client.post("/api/compile", content=tex)
        assert response.status_code == 422

        after_entries = set(os.listdir("/tmp"))
        diff = after_entries - before_entries
        assert len(diff) == 0, f"Leaked files in /tmp: {diff}"
        assert len(after_entries) == len(before_entries)


@pytest.mark.asyncio
async def test_cleanup_after_timeout():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        before_entries = set(os.listdir("/tmp"))
        tex = r"""
\documentclass{article}
\begin{document}
\def\loopit{\loopit}\loopit
\end{document}
"""
        response = await client.post("/api/compile?timeout=2", content=tex)
        assert response.status_code == 504

        after_entries = set(os.listdir("/tmp"))
        diff = after_entries - before_entries
        assert len(diff) == 0, f"Leaked files in /tmp: {diff}"
        assert len(after_entries) == len(before_entries)
