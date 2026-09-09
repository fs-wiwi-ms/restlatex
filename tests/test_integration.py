import io
import pytest
from httpx import AsyncClient, ASGITransport
from pypdf import PdfReader
from app.main import app


@pytest.mark.asyncio
async def test_basic_compilation():
    tex = r"""
\documentclass{article}
\begin{document}
Hello Secure LaTeX Compiler!
\end{document}
"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/compile",
            content=tex,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert 'filename="document.pdf"' in response.headers.get("content-disposition", "")
        assert response.content.startswith(b"%PDF-1.")


@pytest.mark.asyncio
async def test_multipass_lastpage():
    tex = r"""
\documentclass{article}
\usepackage{lastpage}
\usepackage{fancyhdr}
\pagestyle{fancy}
\fancyhf{}
\rfoot{Page \thepage\ of \pageref{LastPage}}
\begin{document}
Page One Content
\newpage
Page Two Content
\end{document}
"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/compile",
            content=tex,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        assert response.content.startswith(b"%PDF-1.")

        reader = PdfReader(io.BytesIO(response.content))
        assert len(reader.pages) == 2
        extracted_text = "".join([page.extract_text() or "" for page in reader.pages])
        assert "??" not in extracted_text
        assert "Page 1 of 2" in extracted_text or "Page 2 of 2" in extracted_text or "of 2" in extracted_text


@pytest.mark.asyncio
async def test_exam_package():
    tex = r"""
\documentclass{exam}
\begin{document}
\begin{questions}
\question What is $2 + 2$?
\begin{choices}
\choice 3
\choice 4
\choice 5
\end{choices}
\end{questions}
\end{document}
"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/compile", content=tex)
        assert response.status_code == 200
        assert response.content.startswith(b"%PDF-1.")


@pytest.mark.asyncio
async def test_amsmath_package():
    tex = r"""
\documentclass{article}
\usepackage{amsmath}
\begin{document}
\begin{equation}
f(x) = \int_{0}^{\infty} e^{-t} t^{x-1} dt
\end{equation}
\end{document}
"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/compile", content=tex)
        assert response.status_code == 200
        assert response.content.startswith(b"%PDF-1.")


@pytest.mark.asyncio
async def test_tikz_package():
    tex = r"""
\documentclass{article}
\usepackage{tikz}
\begin{document}
\begin{tikzpicture}
\draw[thick, rounded corners=8pt] (0,0) -- (0,2) -- (1,3.25) -- (2,2) -- (2,0) -- (0,2) -- (2,2) -- (0,0) -- (2,0);
\end{tikzpicture}
\end{document}
"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/compile", content=tex)
        assert response.status_code == 200
        assert response.content.startswith(b"%PDF-1.")


@pytest.mark.asyncio
async def test_circuitikz_package():
    tex = r"""
\documentclass{article}
\usepackage{circuitikz}
\begin{document}
\begin{circuitikz}
\draw (0,0) to[R] (2,0);
\end{circuitikz}
\end{document}
"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/compile", content=tex)
        assert response.status_code == 200
        assert response.content.startswith(b"%PDF-1.")


@pytest.mark.asyncio
async def test_listings_package():
    tex = r"""
\documentclass{article}
\usepackage{listings}
\begin{document}
\begin{lstlisting}[language=Python]
def test():
    return True
\end{lstlisting}
\end{document}
"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/compile", content=tex)
        assert response.status_code == 200
        assert response.content.startswith(b"%PDF-1.")
