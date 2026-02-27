"""
Inceptrix MCP Server
====================
FastAPI application that mounts a FastMCP instance exposing every pentest
tool installed in the pentest-toolbox Docker image.

Layout
------
  GET  /               — basic info
  GET  /health         — liveness probe
  GET  /tools          — list of registered tools with metadata
  POST /tools/{name}   — invoke a tool via plain JSON (FastAPI layer)
  *    /mcp/*          — MCP protocol endpoint (SSE + HTTP transport)

Transport is HTTP (Streamable-HTTP / SSE) so any MCP client, agent
framework, or Claude Desktop can connect at  http://<host>:<port>/mcp
"""

from __future__ import annotations

import asyncio
import logging
import os
import socket
import sys
import threading
import tempfile
import time
import traceback
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Bootstrap logging before any other import
# ---------------------------------------------------------------------------
# Add docker_mcp root to sys.path so relative imports work
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from logging_config import setup_logging, correlation_id  # noqa: E402

setup_logging()
log = logging.getLogger("inceptrix.mcp.server")

# ---------------------------------------------------------------------------
# Import tool modules  (after logging is configured)
# ---------------------------------------------------------------------------
from executor import run_tool  # noqa: E402
from models import (  # noqa: E402
    DalfoxInput,
    FfufInput,
    HealthResponse,
    HttpxInput,
    JwtToolInput,
    NiktoInput,
    NmapInput,
    NucleiInput,
    ShellInput,
    SqlmapInput,
    ToolMeta,
    ToolResponse,
    ToolStatus,
    ToolsListResponse,
    WfuzzInput,
    WhatWebInput,
)
from tools import register_all  # noqa: E402

# Every tool module exposes META dict for documentation
import tools.nmap as _nmap
import tools.nikto as _nikto
import tools.whatweb as _whatweb
import tools.sqlmap as _sqlmap
import tools.wfuzz as _wfuzz
import tools.ffuf as _ffuf
import tools.nuclei as _nuclei
import tools.httpx_tool as _httpx
import tools.dalfox as _dalfox
import tools.jwt_tool as _jwt
import tools.shell as _shell

_ALL_META = [
    _nmap.META, _nikto.META, _whatweb.META, _sqlmap.META,
    _wfuzz.META, _ffuf.META, _nuclei.META, _httpx.META,
    _dalfox.META, _jwt.META, _shell.META,
]


# ---------------------------------------------------------------------------
# Build the FastMCP instance
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

# Register every tool onto the MCP instance
register_all(mcp)
log.info("All tools registered onto FastMCP instance")

# Ports
_API_PORT = int(os.environ.get("MCP_PORT", 8090))
_MCP_PORT = int(os.environ.get("MCP_STANDALONE_PORT", 8091))

# Standalone uvicorn Server instance — kept at module scope so lifespan can stop it
_standalone_server: Optional[uvicorn.Server] = None

# Build the MCP ASGI app once; shared between the FastAPI mount and the
# standalone uvicorn server so both serve the same tool registry.
mcp_asgi = mcp.http_app(path="/")


# ---------------------------------------------------------------------------
# FastAPI lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global _standalone_server
    host_ip = _get_host_ip()

    # ── Standalone MCP HTTP server (pure MCP, no FastAPI wrapper) ──────────
    # Clients that speak the MCP Streamable-HTTP protocol can connect directly
    # to http://<host>:MCP_STANDALONE_PORT/ without going through FastAPI.
    mcp_config = uvicorn.Config(
        mcp_asgi,
        host="0.0.0.0",
        port=_MCP_PORT,
        log_level=os.environ.get("LOG_LEVEL", "info").lower(),
        access_log=False,
    )
    _standalone_server = uvicorn.Server(mcp_config)
    t = threading.Thread(
        target=_standalone_server.run,
        name="mcp-standalone",
        daemon=True,
    )
    t.start()
    log.info(
        "Standalone MCP HTTP server started",
        extra={"host": host_ip, "mcp_port": _MCP_PORT},
    )

    _print_banner(host_ip, _API_PORT, _MCP_PORT)
    log.info(
        "Server starting",
        extra={"host": host_ip, "api_port": _API_PORT, "mcp_port": _MCP_PORT, "tools": len(_ALL_META)},
    )
    yield

    # ── Graceful stop of standalone MCP server ──────────────────────────────
    if _standalone_server:
        log.info("Stopping standalone MCP HTTP server...")
        _standalone_server.should_exit = True
        t.join(timeout=5)
    log.info("Server shutting down")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Inceptrix MCP — Pentest Toolbox",
    description=(
        "FastAPI + FastMCP gateway exposing nmap, sqlmap, nikto, whatweb, "
        "wfuzz, ffuf, nuclei, httpx, dalfox, and jwt_tool as MCP tools.\n\n"
        "Connect your MCP client to **`/mcp`** for the full protocol."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / response tracing middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def _trace_requests(request: Request, call_next):
    """Assign a correlation ID to every in-coming HTTP request."""
    cid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    token = correlation_id.set(cid)
    start = time.monotonic()

    log.info(
        "HTTP request received",
        extra={
            "method": request.method,
            "path": str(request.url.path),
            "cid": cid,
            "client": request.client.host if request.client else "unknown",
        },
    )

    try:
        response = await call_next(request)
    except Exception as exc:
        log.exception(
            "Unhandled exception in request",
            extra={"cid": cid, "path": str(request.url.path)},
        )
        correlation_id.reset(token)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "cid": cid},
        )

    duration = (time.monotonic() - start) * 1000
    log.info(
        "HTTP request completed",
        extra={
            "method": request.method,
            "path": str(request.url.path),
            "status_code": response.status_code,
            "duration_ms": round(duration, 1),
            "cid": cid,
        },
    )
    response.headers["X-Request-ID"] = cid
    correlation_id.reset(token)
    return response


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(HTTPException)
async def _http_exc(request: Request, exc: HTTPException):
    cid = correlation_id.get("-")
    log.warning(
        "HTTP exception",
        extra={"status_code": exc.status_code, "detail": exc.detail, "cid": cid},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "cid": cid},
    )


@app.exception_handler(Exception)
async def _generic_exc(request: Request, exc: Exception):
    cid = correlation_id.get("-")
    log.exception("Unhandled exception", extra={"cid": cid})
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "cid": cid,
            "error": str(exc),
        },
    )


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

@app.get("/", tags=["Meta"])
def root() -> Dict[str, Any]:
    """Return basic server information."""
    host_ip = _get_host_ip()
    return {
        "server": "Inceptrix MCP — Pentest Toolbox",
        "version": "1.0.0",
        "endpoints": {
            "rest_api": f"http://{host_ip}:{_API_PORT}/",
            "swagger_ui": f"http://{host_ip}:{_API_PORT}/docs",
            "mcp_via_fastapi": f"http://{host_ip}:{_API_PORT}/mcp",
            "mcp_standalone_http": f"http://{host_ip}:{_MCP_PORT}/",
        },
        "tools_count": len(_ALL_META),
    }


@app.get("/health", response_model=HealthResponse, tags=["Meta"])
def health() -> HealthResponse:
    """Liveness probe — returns 200 if the server is running."""
    return HealthResponse(
        status="ok",
        server="inceptrix-mcp",
        tools=[m["name"] for m in _ALL_META],
    )


@app.get("/tools", response_model=ToolsListResponse, tags=["Tools"])
def list_tools() -> ToolsListResponse:
    """List all registered pentest tools with metadata."""
    return ToolsListResponse(
        count=len(_ALL_META),
        tools=[ToolMeta(**m) for m in _ALL_META],
    )


# ---------------------------------------------------------------------------
# Helper — convert executor.ToolResult → models.ToolResponse
# ---------------------------------------------------------------------------

def _to_response(result) -> ToolResponse:
    if result.error:
        status_ = ToolStatus.NOT_FOUND if "not found" in (result.error or "").lower() else ToolStatus.ERROR
    elif result.timed_out:
        status_ = ToolStatus.TIMEOUT
    else:
        status_ = ToolStatus.OK
    return ToolResponse(
        run_id=result.run_id,
        tool=result.tool_name,
        status=status_,
        duration_s=result.duration_s,
        returncode=result.returncode,
        output=result.combined_output,
        error=result.error,
    )


# ---------------------------------------------------------------------------
# Tool endpoints  — POST /tools/<name>
# ---------------------------------------------------------------------------

@app.post("/tools/nmap", response_model=ToolResponse, tags=["Tools"])
async def api_nmap(body: NmapInput) -> ToolResponse:
    """Run nmap against a host/IP/CIDR range."""
    cmd = ["nmap"] + body.flags.split() + [body.target]
    result = await asyncio.to_thread(run_tool, "nmap", cmd, timeout=body.timeout)
    return _to_response(result)


@app.post("/tools/nikto", response_model=ToolResponse, tags=["Tools"])
async def api_nikto(body: NiktoInput) -> ToolResponse:
    """Run Nikto web vulnerability scanner."""
    cmd = ["nikto", "-host", body.target, "-nointeractive"]
    if body.extra_flags:
        cmd += body.extra_flags.split()
    result = await asyncio.to_thread(run_tool, "nikto", cmd, timeout=body.timeout)
    return _to_response(result)


@app.post("/tools/whatweb", response_model=ToolResponse, tags=["Tools"])
async def api_whatweb(body: WhatWebInput) -> ToolResponse:
    """Fingerprint a web application with WhatWeb."""
    aggression = max(1, min(4, body.aggression))
    cmd = ["whatweb", f"--aggression={aggression}", "--color=never", body.target]
    result = await asyncio.to_thread(run_tool, "whatweb", cmd, timeout=body.timeout)
    return _to_response(result)


@app.post("/tools/sqlmap", response_model=ToolResponse, tags=["Tools"])
async def api_sqlmap(body: SqlmapInput) -> ToolResponse:
    """Run sqlmap SQL injection scanner."""
    flags = body.extra_flags.split()
    if "--batch" not in flags:
        flags.insert(0, "--batch")
    cmd = ["sqlmap", "-u", body.target] + flags
    result = await asyncio.to_thread(run_tool, "sqlmap", cmd, timeout=body.timeout)
    return _to_response(result)


@app.post("/tools/wfuzz", response_model=ToolResponse, tags=["Tools"])
async def api_wfuzz(body: WfuzzInput) -> ToolResponse:
    """Fuzz a URL with wfuzz — use FUZZ as the placeholder in the target."""
    cmd = ["wfuzz", "-w", body.wordlist] + body.extra_flags.split() + [body.target]
    result = await asyncio.to_thread(run_tool, "wfuzz", cmd, timeout=body.timeout)
    return _to_response(result)


@app.post("/tools/ffuf", response_model=ToolResponse, tags=["Tools"])
async def api_ffuf(body: FfufInput) -> ToolResponse:
    """Directory/parameter fuzz with ffuf — use FUZZ in the target URL."""
    cmd = ["ffuf", "-u", body.target, "-w", body.wordlist] + body.extra_flags.split()
    result = await asyncio.to_thread(run_tool, "ffuf", cmd, timeout=body.timeout)
    return _to_response(result)


@app.post("/tools/nuclei", response_model=ToolResponse, tags=["Tools"])
async def api_nuclei(body: NucleiInput) -> ToolResponse:
    """Run Nuclei template-based vulnerability scanner."""
    cmd = ["nuclei", "-u", body.target, "-severity", body.severity, "-no-color", "-silent"]
    if body.tags:
        cmd += ["-tags", body.tags]
    result = await asyncio.to_thread(run_tool, "nuclei", cmd, timeout=body.timeout)
    return _to_response(result)


@app.post("/tools/httpx", response_model=ToolResponse, tags=["Tools"])
async def api_httpx(body: HttpxInput) -> ToolResponse:
    """Probe HTTP/HTTPS services with httpx."""
    host_list = body.targets.split()
    tmp_path = None
    try:
        if len(host_list) == 1:
            cmd = ["httpx", "-u", host_list[0]] + body.extra_flags.split()
        else:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False, prefix="httpx_api_"
            ) as f:
                f.write("\n".join(host_list) + "\n")
                tmp_path = f.name
            cmd = ["httpx", "-l", tmp_path] + body.extra_flags.split()
        result = await asyncio.to_thread(run_tool, "httpx", cmd, timeout=body.timeout)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
    return _to_response(result)


@app.post("/tools/dalfox", response_model=ToolResponse, tags=["Tools"])
async def api_dalfox(body: DalfoxInput) -> ToolResponse:
    """Scan a URL for XSS vulnerabilities with Dalfox."""
    cmd = ["dalfox", "url", body.target]
    if body.extra_flags:
        cmd += body.extra_flags.split()
    result = await asyncio.to_thread(run_tool, "dalfox", cmd, timeout=body.timeout)
    return _to_response(result)


@app.post("/tools/jwt", response_model=ToolResponse, tags=["Tools"])
async def api_jwt(body: JwtToolInput) -> ToolResponse:
    """Analyse or attack a JWT token with jwt_tool."""
    cmd = ["jwt_tool"] + body.mode.split() + [body.token]
    result = await asyncio.to_thread(run_tool, "jwt_tool", cmd, timeout=body.timeout)
    return _to_response(result)


@app.post("/tools/shell", response_model=ToolResponse, tags=["Tools"])
async def api_shell(body: ShellInput) -> ToolResponse:
    """Run an arbitrary bash command inside the Kali Linux container."""
    result = await asyncio.to_thread(
        run_tool, "shell", ["bash", "-c", body.command], timeout=body.timeout
    )
    return _to_response(result)


# ---------------------------------------------------------------------------
# Mount FastMCP on /mcp  (Streamable-HTTP transport)
# ---------------------------------------------------------------------------

# mcp_asgi is created above (before lifespan) so lifespan can reuse it.
app.mount("/mcp", mcp_asgi)
log.info("FastMCP mounted at /mcp")


# ---------------------------------------------------------------------------
# Helpers
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


def _print_banner(ip: str, api_port: int, mcp_port: int) -> None:
    tool_names = " · ".join(m["name"] for m in _ALL_META)
    banner = f"""
{'=' * 66}
  Inceptrix MCP — Pentest Toolbox
  ──────────────────────────────────────────────────────────
  REST API          :  http://{ip}:{api_port}/
  Swagger UI        :  http://{ip}:{api_port}/docs
  MCP via FastAPI   :  http://{ip}:{api_port}/mcp
  MCP standalone    :  http://{ip}:{mcp_port}/          ← direct MCP HTTP
  ──────────────────────────────────────────────────────────
  Tools      :  {tool_names}
  Log level  :  {os.environ.get('LOG_LEVEL', 'INFO')}
{'=' * 66}"""
    print(banner, flush=True)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    log_level = os.environ.get("LOG_LEVEL", "info").lower()

    # The lifespan handler automatically spawns the standalone MCP server on
    # _MCP_PORT; uvicorn here serves the full FastAPI app (REST + /mcp).
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=_API_PORT,
        log_level=log_level,
        access_log=False,
        reload=os.environ.get("DEV_RELOAD", "").lower() in ("1", "true", "yes"),
    )
