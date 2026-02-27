"""
Inceptrix — REST API Server
============================
Pure FastAPI server exposing every pentest tool as a POST endpoint.

Endpoints
---------
  GET  /          — server info
  GET  /health    — liveness probe
  GET  /tools     — list registered tools
  POST /tools/*   — invoke a specific tool

Port: API_PORT  (default 8091)
"""

from __future__ import annotations

import asyncio
import logging
import os
import socket
import sys
import tempfile
import time
import uuid

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from logging_config import setup_logging, correlation_id  # noqa: E402

setup_logging()
log = logging.getLogger("inceptrix.api")

from executor import run_tool  # noqa: E402
from models import (  # noqa: E402
    DalfoxInput, FfufInput, HealthResponse, HttpxInput, JwtToolInput,
    NiktoInput, NmapInput, NucleiInput, ShellInput, SqlmapInput, ToolMeta,
    ToolResponse, ToolStatus, ToolsListResponse, WfuzzInput, WhatWebInput,
)
import tools.nmap      as _nmap
import tools.nikto     as _nikto
import tools.whatweb   as _whatweb
import tools.sqlmap    as _sqlmap
import tools.wfuzz     as _wfuzz
import tools.ffuf      as _ffuf
import tools.nuclei    as _nuclei
import tools.httpx_tool as _httpx
import tools.dalfox    as _dalfox
import tools.jwt_tool  as _jwt
import tools.shell     as _shell

_ALL_META = [
    _nmap.META, _nikto.META, _whatweb.META, _sqlmap.META,
    _wfuzz.META, _ffuf.META, _nuclei.META, _httpx.META,
    _dalfox.META, _jwt.META, _shell.META,
]

_API_PORT = int(os.environ.get("API_PORT", 8091))

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Inceptrix — Pentest REST API",
    description=(
        "REST gateway exposing nmap, sqlmap, nikto, whatweb, wfuzz, ffuf, "
        "nuclei, httpx, dalfox, and jwt_tool as JSON endpoints."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Tracing middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def _trace(request: Request, call_next):
    cid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    token = correlation_id.set(cid)
    start = time.monotonic()
    try:
        response = await call_next(request)
    except Exception:
        log.exception("Unhandled exception", extra={"cid": cid})
        correlation_id.reset(token)
        return JSONResponse(status_code=500, content={"detail": "Internal server error", "cid": cid})
    duration = (time.monotonic() - start) * 1000
    # Skip logging for health-check polling
    if request.url.path not in ("/health", "/"):
        log.info("request", extra={"method": request.method, "path": request.url.path,
                                    "status": response.status_code, "ms": round(duration, 1), "cid": cid})
    response.headers["X-Request-ID"] = cid
    correlation_id.reset(token)
    return response


@app.exception_handler(HTTPException)
async def _http_exc(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code,
                        content={"detail": exc.detail, "cid": correlation_id.get("-")})

@app.exception_handler(Exception)
async def _generic_exc(request: Request, exc: Exception):
    log.exception("Unhandled exception")
    return JSONResponse(status_code=500, content={"detail": str(exc)})


# ---------------------------------------------------------------------------
# Meta endpoints
# ---------------------------------------------------------------------------

@app.get("/", tags=["Meta"])
def root():
    ip = _get_host_ip()
    return {
        "server": "Inceptrix REST API",
        "version": "1.0.0",
        "swagger": f"http://{ip}:{_API_PORT}/docs",
        "tools_count": len(_ALL_META),
    }


@app.get("/health", response_model=HealthResponse, tags=["Meta"])
def health():
    return HealthResponse(status="ok", server="inceptrix-api",
                          tools=[m["name"] for m in _ALL_META])


@app.get("/tools", response_model=ToolsListResponse, tags=["Tools"])
def list_tools():
    return ToolsListResponse(count=len(_ALL_META), tools=[ToolMeta(**m) for m in _ALL_META])


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _to_response(result) -> ToolResponse:
    if result.error:
        status_ = ToolStatus.NOT_FOUND if "not found" in (result.error or "").lower() else ToolStatus.ERROR
    elif result.timed_out:
        status_ = ToolStatus.TIMEOUT
    else:
        status_ = ToolStatus.OK
    return ToolResponse(run_id=result.run_id, tool=result.tool_name, status=status_,
                        duration_s=result.duration_s, returncode=result.returncode,
                        output=result.combined_output, error=result.error)


# ---------------------------------------------------------------------------
# Tool endpoints
# ---------------------------------------------------------------------------

@app.post("/tools/nmap", response_model=ToolResponse, tags=["Tools"])
async def api_nmap(body: NmapInput):
    cmd = ["nmap"] + body.flags.split() + [body.target]
    return _to_response(await asyncio.to_thread(run_tool, "nmap", cmd, timeout=body.timeout))


@app.post("/tools/nikto", response_model=ToolResponse, tags=["Tools"])
async def api_nikto(body: NiktoInput):
    cmd = ["nikto", "-host", body.target, "-nointeractive"]
    if body.extra_flags:
        cmd += body.extra_flags.split()
    return _to_response(await asyncio.to_thread(run_tool, "nikto", cmd, timeout=body.timeout))


@app.post("/tools/whatweb", response_model=ToolResponse, tags=["Tools"])
async def api_whatweb(body: WhatWebInput):
    cmd = ["whatweb", f"--aggression={max(1, min(4, body.aggression))}", "--color=never", body.target]
    return _to_response(await asyncio.to_thread(run_tool, "whatweb", cmd, timeout=body.timeout))


@app.post("/tools/sqlmap", response_model=ToolResponse, tags=["Tools"])
async def api_sqlmap(body: SqlmapInput):
    flags = body.extra_flags.split()
    if "--batch" not in flags:
        flags.insert(0, "--batch")
    cmd = ["sqlmap", "-u", body.target] + flags
    return _to_response(await asyncio.to_thread(run_tool, "sqlmap", cmd, timeout=body.timeout))


@app.post("/tools/wfuzz", response_model=ToolResponse, tags=["Tools"])
async def api_wfuzz(body: WfuzzInput):
    cmd = ["wfuzz", "-w", body.wordlist] + body.extra_flags.split() + [body.target]
    return _to_response(await asyncio.to_thread(run_tool, "wfuzz", cmd, timeout=body.timeout))


@app.post("/tools/ffuf", response_model=ToolResponse, tags=["Tools"])
async def api_ffuf(body: FfufInput):
    cmd = ["ffuf", "-u", body.target, "-w", body.wordlist] + body.extra_flags.split()
    return _to_response(await asyncio.to_thread(run_tool, "ffuf", cmd, timeout=body.timeout))


@app.post("/tools/nuclei", response_model=ToolResponse, tags=["Tools"])
async def api_nuclei(body: NucleiInput):
    cmd = ["nuclei", "-u", body.target, "-severity", body.severity, "-no-color", "-silent"]
    if body.tags:
        cmd += ["-tags", body.tags]
    return _to_response(await asyncio.to_thread(run_tool, "nuclei", cmd, timeout=body.timeout))


@app.post("/tools/httpx", response_model=ToolResponse, tags=["Tools"])
async def api_httpx(body: HttpxInput):
    hosts = body.targets.split()
    tmp = None
    try:
        if len(hosts) == 1:
            cmd = ["httpx", "-u", hosts[0]] + body.extra_flags.split()
        else:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
                f.write("\n".join(hosts) + "\n")
                tmp = f.name
            cmd = ["httpx", "-l", tmp] + body.extra_flags.split()
        return _to_response(await asyncio.to_thread(run_tool, "httpx", cmd, timeout=body.timeout))
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)


@app.post("/tools/dalfox", response_model=ToolResponse, tags=["Tools"])
async def api_dalfox(body: DalfoxInput):
    cmd = ["dalfox", "url", body.target]
    if body.extra_flags:
        cmd += body.extra_flags.split()
    return _to_response(await asyncio.to_thread(run_tool, "dalfox", cmd, timeout=body.timeout))


@app.post("/tools/jwt", response_model=ToolResponse, tags=["Tools"])
async def api_jwt(body: JwtToolInput):
    cmd = ["jwt_tool"] + body.mode.split() + [body.token]
    return _to_response(await asyncio.to_thread(run_tool, "jwt_tool", cmd, timeout=body.timeout))


@app.post("/tools/shell", response_model=ToolResponse, tags=["Tools"])
async def api_shell(body: ShellInput):
    """Run an arbitrary bash command inside the Kali Linux container."""
    result = await asyncio.to_thread(
        run_tool, "shell", ["bash", "-c", body.command], timeout=body.timeout
    )
    return _to_response(result)


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
    print(f"\n  REST API  :  http://{ip}:{_API_PORT}/")
    print(f"  Swagger   :  http://{ip}:{_API_PORT}/docs\n", flush=True)
    uvicorn.run("api_server:app", host="0.0.0.0", port=_API_PORT,
                log_level=os.environ.get("LOG_LEVEL", "info").lower(), access_log=False)
