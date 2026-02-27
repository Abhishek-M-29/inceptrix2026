"""
dalfox tool — XSS scanner and parameter analyser.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from executor import run_tool

if TYPE_CHECKING:
    from fastmcp import FastMCP

log = logging.getLogger("inceptrix.mcp.tools.dalfox")

TOOL_NAME = "dalfox"
DEFAULT_TIMEOUT = 300

META = {
    "name": TOOL_NAME,
    "description": "Automated XSS scanning and parameter analysis",
    "binary": "dalfox",
    "default_timeout": DEFAULT_TIMEOUT,
}


def register(mcp: "FastMCP") -> None:

    @mcp.tool(name="run_dalfox", description=(
        "Scan a URL for Cross-Site Scripting (XSS) vulnerabilities using Dalfox.\n\n"
        "target      : URL with injectable parameter, e.g. 'http://site.com/search?q=test'\n"
        "extra_flags : dalfox flags, e.g. '--silence --only-discovery'\n"
        "timeout     : max seconds (default 300)\n\n"
        "Returns Dalfox's XSS findings."
    ))
    def run_dalfox(
        target: str,
        extra_flags: str = "--only-discovery --silence",
        timeout: int = 60,
    ) -> str:
        log.info("run_dalfox invoked", extra={"target": target})
        cmd = ["dalfox", "url", target]
        flags = extra_flags.split() if extra_flags.strip() else ["--only-discovery", "--silence"]
        cmd += flags
        result = run_tool(TOOL_NAME, cmd, timeout=timeout)
        return result.to_mcp_text()

    @mcp.tool(name="run_dalfox_discovery_only", description=(
        "Run Dalfox in discovery-only mode — identifies injectable parameters "
        "without executing payloads.\n\n"
        "target  : target URL\n"
        "timeout : max seconds (default 180)"
    ))
    def run_dalfox_discovery_only(target: str, timeout: int = 180) -> str:
        log.info("run_dalfox_discovery_only invoked", extra={"target": target})
        cmd = ["dalfox", "url", target, "--only-discovery", "--silence"]
        result = run_tool(TOOL_NAME, cmd, timeout=timeout)
        return result.to_mcp_text()

    @mcp.tool(name="run_dalfox_blind", description=(
        "Run Dalfox with a blind XSS callback URL to catch out-of-band XSS.\n\n"
        "target      : target URL\n"
        "callback    : your blind-XSS callback URL (e.g. from xsshunter or bXSS)\n"
        "timeout     : max seconds (default 300)"
    ))
    def run_dalfox_blind(
        target: str,
        callback: str,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> str:
        log.info("run_dalfox_blind invoked", extra={"target": target})
        cmd = ["dalfox", "url", target, "--blind", callback]
        result = run_tool(TOOL_NAME, cmd, timeout=timeout)
        return result.to_mcp_text()

    log.debug("dalfox tools registered")
