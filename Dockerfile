FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        texlive-full \
        bubblewrap \
        python3 \
        python3-pip \
        python3-venv \
        procps \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY texmf.cnf /etc/texmf/web2c/texmf.cnf
RUN mktexlsr 2>/dev/null || true

RUN groupadd -g 10001 appuser && \
    useradd -u 10001 -g 10001 -m -s /bin/false appuser

RUN python3 -m venv /opt/venv
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm -f /tmp/requirements.txt

WORKDIR /app
COPY . /app

RUN python3 -m compileall /app /opt/venv && \
    chown -R root:root /app && \
    chmod -R 755 /app

USER 10001:10001
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
