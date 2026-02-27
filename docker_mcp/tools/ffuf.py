"""
ffuf tool — fast web fuzzer (directory/file/parameter discovery).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from executor import run_tool

if TYPE_CHECKING:
    from fastmcp import FastMCP

log = logging.getLogger("inceptrix.mcp.tools.ffuf")

TOOL_NAME = "ffuf"
DEFAULT_TIMEOUT = 300
DEFAULT_WORDLIST = "/usr/share/wordlists/dirb/common.txt"

META = {
    "name": TOOL_NAME,
    "description": "Fast HTTP fuzzer for directory, file, and parameter discovery",
    "binary": "ffuf",
    "default_timeout": DEFAULT_TIMEOUT,
}


def register(mcp: "FastMCP") -> None:

    @mcp.tool(name="run_ffuf", description=(
        "Fuzz a URL with ffuf — place the literal string 'FUZZ' in the URL.\n\n"
        "target      : URL with FUZZ placeholder, e.g. 'http://site.com/FUZZ'\n"
        "wordlist    : absolute container path to the wordlist file\n"
        "extra_flags : ffuf flags (default '-mc 200,301,302,403')\n"
        "timeout     : max seconds (default 300)\n\n"
        "Returns ffuf's discovered paths."
    ))
    def run_ffuf(
        target: str,
        wordlist: str = DEFAULT_WORDLIST,
        extra_flags: str = "-mc 200,301,302,403 -t 40 -timeout 5",
        timeout: int = 120,
    ) -> str:
        log.info("run_ffuf invoked", extra={"target": target, "wordlist": wordlist})
        flags = extra_flags.split() if extra_flags.strip() else ["-mc", "200,301,302,403", "-t", "40", "-timeout", "5"]
        cmd = ["ffuf", "-u", target, "-w", wordlist] + flags
        result = run_tool(TOOL_NAME, cmd, timeout=timeout)
        return result.to_mcp_text()

    @mcp.tool(name="run_ffuf_dirs", description=(
        "Discover directories at a base URL using ffuf.\n\n"
        "base_url : target without trailing slash, e.g. 'http://site.com'\n"
        "timeout  : max seconds (default 300)"
    ))
    def run_ffuf_dirs(base_url: str, timeout: int = 120) -> str:
        log.info("run_ffuf_dirs invoked", extra={"base_url": base_url})
        target = base_url.rstrip("/") + "/FUZZ"
        cmd = [
            "ffuf", "-u", target,
            "-w", DEFAULT_WORDLIST,
            "-mc", "200,301,302,403",
            "-t", "40", "-timeout", "5",
            "-of", "json",
        ]
        result = run_tool(TOOL_NAME, cmd, timeout=timeout)
        return result.to_mcp_text()

    @mcp.tool(name="run_ffuf_vhost", description=(
        "Virtual-host brute-force using ffuf.\n\n"
        "target     : base URL, e.g. 'http://10.0.0.1'\n"
        "wordlist   : wordlist of sub-domain/vhost names\n"
        "host_header: base domain for the Host header, e.g. 'example.com'\n"
        "timeout    : max seconds"
    ))
    def run_ffuf_vhost(
        target: str,
        wordlist: str = DEFAULT_WORDLIST,
        host_header: str = "FUZZ.example.com",
        timeout: int = DEFAULT_TIMEOUT,
    ) -> str:
        log.info("run_ffuf_vhost invoked", extra={"target": target})
        cmd = [
            "ffuf", "-w", wordlist,
            "-u", target,
            "-H", f"Host: {host_header}",
            "-mc", "200,301,302,403",
        ]
        result = run_tool(TOOL_NAME, cmd, timeout=timeout)
        return result.to_mcp_text()

    log.debug("ffuf tools registered")
