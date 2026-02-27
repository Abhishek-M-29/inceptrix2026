"""
sqlmap tool — automated SQL injection detection and exploitation.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from executor import run_tool

if TYPE_CHECKING:
    from fastmcp import FastMCP

log = logging.getLogger("inceptrix.mcp.tools.sqlmap")

TOOL_NAME = "sqlmap"
DEFAULT_TIMEOUT = 600

META = {
    "name": TOOL_NAME,
    "description": "Automated SQL injection detection and exploitation tool",
    "binary": "sqlmap",
    "default_timeout": DEFAULT_TIMEOUT,
}


def register(mcp: "FastMCP") -> None:

    @mcp.tool(name="run_sqlmap", description=(
        "Run sqlmap SQL injection scanner against a URL.\n\n"
        "target      : URL with injectable parameter(s), e.g. 'http://site.com/page?id=1'\n"
        "extra_flags : sqlmap flags (default '--batch'); "
        "e.g. '--dbs --batch --level=3 --risk=2'\n"
        "timeout     : max seconds (default 600)\n\n"
        "Returns sqlmap's findings."
    ))
    def run_sqlmap(
        target: str,
        extra_flags: str = "--batch --level=1 --risk=1 --smart",
        timeout: int = 120,
    ) -> str:
        log.info("run_sqlmap invoked", extra={"target": target, "extra_flags": extra_flags})
        flags = extra_flags.split() if extra_flags.strip() else ["--batch", "--level=1", "--risk=1", "--smart"]
        # Always ensure non-interactive
        if "--batch" not in flags:
            flags.insert(0, "--batch")
        cmd = ["sqlmap", "-u", target] + flags
        result = run_tool(TOOL_NAME, cmd, timeout=timeout)
        return result.to_mcp_text()

    @mcp.tool(name="run_sqlmap_enumerate_dbs", description=(
        "Enumerate databases on a vulnerable SQL injection endpoint.\n\n"
        "target  : URL with injectable parameter\n"
        "timeout : max seconds (default 600)"
    ))
    def run_sqlmap_enumerate_dbs(target: str, timeout: int = DEFAULT_TIMEOUT) -> str:
        log.info("run_sqlmap_enumerate_dbs invoked", extra={"target": target})
        cmd = ["sqlmap", "-u", target, "--batch", "--dbs", "--level=2", "--risk=1"]
        result = run_tool(TOOL_NAME, cmd, timeout=timeout)
        return result.to_mcp_text()

    @mcp.tool(name="run_sqlmap_post", description=(
        "Run sqlmap against a POST endpoint.\n\n"
        "target  : URL of the form endpoint\n"
        "data    : POST body string, e.g. 'user=admin&pass=test'\n"
        "timeout : max seconds (default 600)"
    ))
    def run_sqlmap_post(target: str, data: str, timeout: int = DEFAULT_TIMEOUT) -> str:
        log.info("run_sqlmap_post invoked", extra={"target": target})
        cmd = ["sqlmap", "-u", target, "--data", data, "--batch", "--level=2"]
        result = run_tool(TOOL_NAME, cmd, timeout=timeout)
        return result.to_mcp_text()

    log.debug("sqlmap tools registered")
