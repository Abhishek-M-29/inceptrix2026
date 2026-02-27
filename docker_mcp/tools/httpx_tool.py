"""
httpx tool — fast HTTP probe / service discovery.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from executor import run_tool

if TYPE_CHECKING:
    from fastmcp import FastMCP

log = logging.getLogger("inceptrix.mcp.tools.httpx")

TOOL_NAME = "httpx"
DEFAULT_TIMEOUT = 180
# Use the projectdiscovery Go binary (installed as httpx-toolkit)
# so it doesn't get shadowed by the Python httpx CLI in /opt/mcp_venv/bin/httpx.
_HTTPX_BIN = "httpx-toolkit"

META = {
    "name": TOOL_NAME,
    "description": "Fast HTTP probing, technology detection, and status-code enumeration",
    "binary": _HTTPX_BIN,
    "default_timeout": DEFAULT_TIMEOUT,
}


def register(mcp: "FastMCP") -> None:

    @mcp.tool(name="run_httpx", description=(
        "Probe one or more HTTP/HTTPS services with httpx.\n\n"
        "targets     : space-separated list of hosts or URLs, "
        "e.g. 'example.com 10.0.0.1:8080'\n"
        "extra_flags : httpx flags (default includes status-code, title, tech-detect)\n"
        "timeout     : max seconds (default 180)\n\n"
        "Returns probe results — live hosts, status codes, titles, technologies."
    ))
    def run_httpx(
        targets: str,
        extra_flags: str = "-status-code -title -tech-detect -follow-redirects -silent",
        timeout: int = DEFAULT_TIMEOUT,
    ) -> str:
        log.info("run_httpx invoked", extra={"targets": targets})
        host_list = targets.split()
        # httpx-toolkit reads targets from stdin; pipe them in via bash -c
        targets_str = "\n".join(host_list)
        shell_cmd = f"printf '%s\\n' {' '.join(repr(h) for h in host_list)} | {_HTTPX_BIN} {extra_flags}"
        cmd = ["bash", "-c", shell_cmd]
        result = run_tool(TOOL_NAME, cmd, timeout=timeout)
        return result.to_mcp_text()

    @mcp.tool(name="run_httpx_probe", description=(
        "Quick probe of a single URL — returns status code, title, "
        "server header, and detected technologies.\n\n"
        "url     : target URL\n"
        "timeout : max seconds (default 60)"
    ))
    def run_httpx_probe(url: str, timeout: int = 60) -> str:
        log.info("run_httpx_probe invoked", extra={"url": url})
        shell_cmd = f"echo {repr(url)} | {_HTTPX_BIN} -status-code -title -server -tech-detect -follow-redirects"
        cmd = ["bash", "-c", shell_cmd]
        result = run_tool(TOOL_NAME, cmd, timeout=timeout)
        return result.to_mcp_text()

    @mcp.tool(name="run_httpx_screenshot_headers", description=(
        "Dump all response headers from a URL using httpx.\n\n"
        "url     : target URL\n"
        "timeout : max seconds (default 60)"
    ))
    def run_httpx_screenshot_headers(url: str, timeout: int = 60) -> str:
        log.info("run_httpx_screenshot_headers invoked", extra={"url": url})
        shell_cmd = f"echo {repr(url)} | {_HTTPX_BIN} -include-response-header"
        cmd = ["bash", "-c", shell_cmd]
        result = run_tool(TOOL_NAME, cmd, timeout=timeout)
        return result.to_mcp_text()

    log.debug("httpx tools registered")
