"""
whatweb tool — web-application fingerprinting.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from executor import run_tool

if TYPE_CHECKING:
    from fastmcp import FastMCP

log = logging.getLogger("inceptrix.mcp.tools.whatweb")

TOOL_NAME = "whatweb"
DEFAULT_TIMEOUT = 120

META = {
    "name": TOOL_NAME,
    "description": "Web technology & framework fingerprinter",
    "binary": "whatweb",
    "default_timeout": DEFAULT_TIMEOUT,
}


def register(mcp: "FastMCP") -> None:

    @mcp.tool(name="run_whatweb", description=(
        "Fingerprint a web application to identify its technologies.\n\n"
        "target     : URL, e.g. 'https://example.com'\n"
        "aggression : 1 (passive / stealth) → 4 (aggressive) — default 1\n"
        "timeout    : max seconds (default 120)\n\n"
        "Returns WhatWeb's fingerprint report."
    ))
    def run_whatweb(
        target: str,
        aggression: int = 1,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> str:
        log.info("run_whatweb invoked", extra={"target": target, "aggression": aggression})
        aggression = max(1, min(4, aggression))
        cmd = ["whatweb", f"--aggression={aggression}", "--color=never", target]
        result = run_tool(TOOL_NAME, cmd, timeout=timeout)
        return result.to_mcp_text()

    @mcp.tool(name="run_whatweb_aggressive", description=(
        "Run WhatWeb in aggressive mode (level 4) against a URL.\n\n"
        "target  : URL\n"
        "timeout : max seconds (default 180)"
    ))
    def run_whatweb_aggressive(target: str, timeout: int = 180) -> str:
        log.info("run_whatweb_aggressive invoked", extra={"target": target})
        cmd = ["whatweb", "--aggression=4", "--color=never", target]
        result = run_tool(TOOL_NAME, cmd, timeout=timeout)
        return result.to_mcp_text()

    log.debug("whatweb tools registered")
