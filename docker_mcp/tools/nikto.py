"""
nikto tool — web server vulnerability scanner.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from executor import run_tool

if TYPE_CHECKING:
    from fastmcp import FastMCP

log = logging.getLogger("inceptrix.mcp.tools.nikto")

TOOL_NAME = "nikto"
DEFAULT_TIMEOUT = 300

META = {
    "name": TOOL_NAME,
    "description": "Web server vulnerability and misconfiguration scanner",
    "binary": "nikto",
    "default_timeout": DEFAULT_TIMEOUT,
}


def register(mcp: "FastMCP") -> None:

    @mcp.tool(name="run_nikto", description=(
        "Run Nikto web vulnerability scanner against a target.\n\n"
        "target      : full URL, e.g. 'http://example.com' or 'https://example.com:8443'\n"
        "extra_flags : additional nikto CLI flags, e.g. '-Tuning 9' or '-ssl'\n"
        "timeout     : max seconds (default 300)\n\n"
        "Returns Nikto's findings as text."
    ))
    def run_nikto(
        target: str,
        extra_flags: str = "",
        timeout: int = 90,
    ) -> str:
        log.info("run_nikto invoked", extra={"target": target, "extra_flags": extra_flags})
        cmd = ["nikto", "-host", target, "-nointeractive", "-maxtime", "60"]
        if extra_flags:
            # Let caller override maxtime if they pass it explicitly
            if "-maxtime" in extra_flags:
                cmd = ["nikto", "-host", target, "-nointeractive"] + extra_flags.split()
            else:
                cmd += extra_flags.split()
        result = run_tool(TOOL_NAME, cmd, timeout=timeout)
        return result.to_mcp_text()

    @mcp.tool(name="run_nikto_ssl", description=(
        "Run Nikto against an HTTPS target with SSL checks enabled.\n\n"
        "target  : hostname or URL\n"
        "timeout : max seconds (default 300)"
    ))
    def run_nikto_ssl(target: str, timeout: int = 90) -> str:
        log.info("run_nikto_ssl invoked", extra={"target": target})
        cmd = ["nikto", "-host", target, "-ssl", "-nointeractive", "-maxtime", "60"]
        result = run_tool(TOOL_NAME, cmd, timeout=timeout)
        return result.to_mcp_text()

    log.debug("nikto tools registered")
