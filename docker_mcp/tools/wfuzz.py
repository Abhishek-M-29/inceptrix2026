"""
wfuzz tool — web content and parameter fuzzer.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from executor import run_tool

if TYPE_CHECKING:
    from fastmcp import FastMCP

log = logging.getLogger("inceptrix.mcp.tools.wfuzz")

TOOL_NAME = "wfuzz"
DEFAULT_TIMEOUT = 300
DEFAULT_WORDLIST = "/usr/share/wordlists/dirb/common.txt"

META = {
    "name": TOOL_NAME,
    "description": "Web content / parameter fuzzer",
    "binary": "wfuzz",
    "default_timeout": DEFAULT_TIMEOUT,
}


def register(mcp: "FastMCP") -> None:

    @mcp.tool(name="run_wfuzz", description=(
        "Fuzz a URL with wfuzz — place the literal string 'FUZZ' inside the URL.\n\n"
        "target      : URL with FUZZ placeholder, e.g. 'http://site.com/FUZZ'\n"
        "wordlist    : absolute path to the wordlist file inside the container\n"
        "extra_flags : wfuzz flags (default '--hc 404')\n"
        "timeout     : max seconds (default 300)\n\n"
        "Returns all matching responses."
    ))
    def run_wfuzz(
        target: str,
        wordlist: str = DEFAULT_WORDLIST,
        extra_flags: str = "--hc 404 -t 40",
        timeout: int = 120,
    ) -> str:
        log.info("run_wfuzz invoked", extra={"target": target, "wordlist": wordlist})
        flags = extra_flags.split() if extra_flags.strip() else ["--hc", "404", "-t", "40"]
        cmd = ["wfuzz", "-w", wordlist] + flags + [target]
        result = run_tool(TOOL_NAME, cmd, timeout=timeout)
        return result.to_mcp_text()

    @mcp.tool(name="run_wfuzz_dirs", description=(
        "Directory brute-force via wfuzz using the common.txt wordlist.\n\n"
        "base_url : target without trailing slash, e.g. 'http://site.com'\n"
        "timeout  : max seconds (default 300)"
    ))
    def run_wfuzz_dirs(base_url: str, timeout: int = 120) -> str:
        log.info("run_wfuzz_dirs invoked", extra={"base_url": base_url})
        target = base_url.rstrip("/") + "/FUZZ"
        cmd = ["wfuzz", "-w", DEFAULT_WORDLIST, "--hc", "404", "-t", "40", target]
        result = run_tool(TOOL_NAME, cmd, timeout=timeout)
        return result.to_mcp_text()

    @mcp.tool(name="run_wfuzz_params", description=(
        "Fuzz a GET parameter value with wfuzz.\n\n"
        "base_url   : URL containing 'FUZZ' in a query parameter value, "
        "e.g. 'http://site.com/page?id=FUZZ'\n"
        "wordlist   : wordlist path\n"
        "hide_codes : comma-separated HTTP codes to suppress, e.g. '404,403'\n"
        "timeout    : max seconds"
    ))
    def run_wfuzz_params(
        base_url: str,
        wordlist: str = DEFAULT_WORDLIST,
        hide_codes: str = "404",
        timeout: int = 120,
    ) -> str:
        log.info("run_wfuzz_params invoked", extra={"base_url": base_url})
        cmd = ["wfuzz", "-w", wordlist, "--hc", hide_codes, "-t", "40", base_url]
        result = run_tool(TOOL_NAME, cmd, timeout=timeout)
        return result.to_mcp_text()

    log.debug("wfuzz tools registered")
