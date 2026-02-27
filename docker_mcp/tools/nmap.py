"""
nmap tool — network/port scanner.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from executor import run_tool

if TYPE_CHECKING:
    from fastmcp import FastMCP

log = logging.getLogger("inceptrix.mcp.tools.nmap")

TOOL_NAME = "nmap"
DEFAULT_TIMEOUT = 300

META = {
    "name": TOOL_NAME,
    "description": "Network port scanner and service/OS detection",
    "binary": "nmap",
    "default_timeout": DEFAULT_TIMEOUT,
}


def register(mcp: "FastMCP") -> None:
    """Attach nmap tools to the FastMCP instance."""

    @mcp.tool(name="run_nmap", description=(
        "Run nmap against a target host, IP address, or CIDR range.\n\n"
        "Parameters\n----------\n"
        "target : hostname or IP, e.g. 'example.com' or '10.0.0.1/24'\n"
        "flags  : nmap flag string — default is fast top-100 scan '-T4 -F --open';\n"
        "         use '-T4 -sV -sC' for service detection or '-p-' for all ports\n"
        "timeout: max seconds to wait (default 60)\n\n"
        "Returns the combined nmap stdout/stderr output."
    ))
    def run_nmap(target: str, flags: str = "-T4 -F --open", timeout: int = 60) -> str:
        log.info("run_nmap invoked", extra={"target": target, "flags": flags})
        # Empty flags → safe fast default
        if not flags.strip():
            flags = "-T4 -F --open"
        cmd = ["nmap"] + flags.split() + [target]
        result = run_tool(TOOL_NAME, cmd, timeout=timeout)
        return result.to_mcp_text()

    @mcp.tool(name="run_nmap_full_scan", description=(
        "Convenience wrapper — run a comprehensive nmap scan (sV, sC, OS detect, "
        "all ports 1-65535) against a single target. Slower but thorough.\n\n"
        "target : hostname or IP\n"
        "timeout: max seconds (default 900)"
    ))
    def run_nmap_full_scan(target: str, timeout: int = 900) -> str:
        log.info("run_nmap_full_scan invoked", extra={"target": target})
        cmd = ["nmap", "-sV", "-sC", "-O", "-p-", "--open", target]
        result = run_tool(TOOL_NAME, cmd, timeout=timeout)
        return result.to_mcp_text()

    log.debug("nmap tools registered")
