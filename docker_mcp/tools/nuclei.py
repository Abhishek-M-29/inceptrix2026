"""
nuclei tool — template-based vulnerability scanner.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from executor import run_tool

if TYPE_CHECKING:
    from fastmcp import FastMCP

log = logging.getLogger("inceptrix.mcp.tools.nuclei")

TOOL_NAME = "nuclei"
DEFAULT_TIMEOUT = 600

META = {
    "name": TOOL_NAME,
    "description": "YAML-template-based vulnerability scanner (CVEs, misconfigs, exposures)",
    "binary": "nuclei",
    "default_timeout": DEFAULT_TIMEOUT,
}

# Fast flags applied to every nuclei run to keep default scans quick
_FAST_FLAGS = ["-rate-limit", "150", "-timeout", "5", "-bulk-size", "25", "-concurrency", "25"]


def register(mcp: "FastMCP") -> None:

    @mcp.tool(name="run_nuclei", description=(
        "Run Nuclei template-based vulnerability scanner against a target URL.\n\n"
        "target   : URL to scan, e.g. 'https://example.com'\n"
        "severity : comma-separated severities — critical,high,medium,low,info,unknown "
        "(default 'critical,high')\n"
        "tags     : comma-separated template tags to filter, e.g. 'cve,rce,lfi'\n"
        "timeout  : max seconds (default 120)\n\n"
        "Returns Nuclei findings."
    ))
    def run_nuclei(
        target: str,
        severity: str = "critical,high",
        tags: str = "",
        timeout: int = 120,
    ) -> str:
        log.info("run_nuclei invoked", extra={"target": target, "severity": severity, "tags": tags})
        cmd = ["nuclei", "-u", target, "-severity", severity, "-no-color", "-silent"] + _FAST_FLAGS
        if tags:
            cmd += ["-tags", tags]
        result = run_tool(TOOL_NAME, cmd, timeout=timeout)
        return result.to_mcp_text()

    @mcp.tool(name="run_nuclei_cve", description=(
        "Scan a target exclusively with CVE-tagged Nuclei templates.\n\n"
        "target  : URL\n"
        "timeout : max seconds (default 600)"
    ))
    def run_nuclei_cve(target: str, timeout: int = 120) -> str:
        log.info("run_nuclei_cve invoked", extra={"target": target})
        cmd = ["nuclei", "-u", target, "-tags", "cve", "-no-color", "-silent"] + _FAST_FLAGS
        result = run_tool(TOOL_NAME, cmd, timeout=timeout)
        return result.to_mcp_text()

    @mcp.tool(name="run_nuclei_technologies", description=(
        "Detect technologies and exposed panels using Nuclei tech-detect templates.\n\n"
        "target  : URL\n"
        "timeout : max seconds (default 300)"
    ))
    def run_nuclei_technologies(target: str, timeout: int = 60) -> str:
        log.info("run_nuclei_technologies invoked", extra={"target": target})
        cmd = [
            "nuclei", "-u", target,
            "-tags", "tech,panel,login,exposure",
            "-no-color", "-silent",
        ] + _FAST_FLAGS
        result = run_tool(TOOL_NAME, cmd, timeout=timeout)
        return result.to_mcp_text()

    @mcp.tool(name="run_nuclei_update_templates", description=(
        "Update Nuclei's template database to the latest version. "
        "Call this before scanning if templates may be stale."
    ))
    def run_nuclei_update_templates() -> str:
        log.info("run_nuclei_update_templates invoked")
        cmd = ["nuclei", "-update-templates", "-silent"]
        result = run_tool(TOOL_NAME, cmd, timeout=120)
        return result.to_mcp_text()

    log.debug("nuclei tools registered")
