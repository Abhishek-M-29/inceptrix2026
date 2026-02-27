# docker_mcp/Dockerfile
# ─────────────────────────────────────────────────────────────────────────
# Builds the Inceptrix MCP server on top of the pentest-toolbox image.
# All pentest binaries (nmap, sqlmap, nikto …) are already present in the
# base image; we only add the Python MCP server layer here.
#
# Build:
#   docker build -f docker_mcp/Dockerfile -t inceptrix-mcp:latest .
#
# Run (or just use start_server.ps1 from the project root):
#   docker run --rm -p 8090:8090 -p 8091:8091 inceptrix-mcp:latest
#     8090 → REST API  /  8091 → MCP HTTP
# ─────────────────────────────────────────────────────────────────────────

FROM pentest-toolbox:latest

# ── System dependencies for Python packaging + pentest tools ────────────
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3-venv python3-pip build-essential \
        httpx-toolkit dirb wordlists git curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# ── Node.js 20 LTS via NodeSource ────────────────────────────────────────
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# ── Create and activate a clean Python venv for the MCP server ───────────
ENV VENV=/opt/mcp_venv
RUN python3 -m venv "${VENV}"
ENV PATH="${VENV}/bin:${PATH}"

# ── Install Python dependencies ───────────────────────────────────────────
WORKDIR /opt/inceptrix_mcp
COPY docker_mcp/requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Copy source ───────────────────────────────────────────────────────────
COPY docker_mcp/ .

# ── Runtime environment variables (override with -e or compose) ──────────
ENV MCP_PORT=8090 \
    API_PORT=8091 \
    LOG_LEVEL=INFO \
    LOG_FORMAT=json \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# ── Smoke test — verify the Python environment is sane ────────────────────
RUN python3 -c "import fastmcp, fastapi, uvicorn, pydantic; print('Python deps OK')"
RUN chmod +x start_services.sh

# 8090 — MCP HTTP  (mcp_server.py)
# 8091 — REST API  (api_server.py)
# 3000-3010 — sandbox dev servers
EXPOSE ${MCP_PORT} ${API_PORT} 3000 3001 3002 3003 3004 3005 3006 3007 3008 3009 3010

# ── Health check ─────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:${API_PORT}/health')" \
    || exit 1

ENTRYPOINT ["bash", "start_services.sh"]
