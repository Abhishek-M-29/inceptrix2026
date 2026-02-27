"""
Inceptrix — MCP Server
======================
Pure FastMCP HTTP server exposing every pentest tool via the
Model Context Protocol (Streamable-HTTP transport).

Connect any MCP client, agent, or Claude Desktop to:
    http://<host>:<MCP_PORT>/

Port: MCP_PORT  (default 8090)
"""

from __future__ import annotations

import logging
import os
import socket
import sys

import uvicorn
from fastmcp import FastMCP

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from logging_config import setup_logging  # noqa: E402

setup_logging()
log = logging.getLogger("inceptrix.mcp")

from tools import register_all  # noqa: E402

_MCP_PORT = int(os.environ.get("MCP_PORT", 8090))

# ---------------------------------------------------------------------------
# FastMCP instance
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="Inceptrix-MCP",
    instructions=(
        "You are an expert penetration tester operating inside an isolated Kali "
        "Linux environment. Each tool is fully installed and ready. "
        "Use the tools to assist in authorised security assessments — "
        "always confirm scope and authorisation before running active scans."
    ),
)

register_all(mcp)
log.info("All tools registered onto FastMCP instance")

# ASGI app for uvicorn
app = mcp.http_app(path="/")


# ---------------------------------------------------------------------------
# Helpers / entrypoint
# ---------------------------------------------------------------------------

def _get_host_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "0.0.0.0"


if __name__ == "__main__":
    ip = _get_host_ip()
    print(f"\n  MCP endpoint  :  http://{ip}:{_MCP_PORT}/\n", flush=True)
    uvicorn.run("mcp_server:app", host="0.0.0.0", port=_MCP_PORT,
                log_level=os.environ.get("LOG_LEVEL", "info").lower(), access_log=False)
