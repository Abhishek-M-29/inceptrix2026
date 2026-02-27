"""
jwt_tool — JWT token analysis, tampering, and cracking.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from executor import run_tool

if TYPE_CHECKING:
    from fastmcp import FastMCP

log = logging.getLogger("inceptrix.mcp.tools.jwt_tool")

TOOL_NAME = "jwt_tool"
DEFAULT_TIMEOUT = 60

# jwt_tool is installed in a venv — the wrapper at /usr/local/bin/jwt_tool
# handles the interpreter path automatically.
JWT_BINARY = "jwt_tool"

META = {
    "name": TOOL_NAME,
    "description": "JWT token decoder, tamperer, and cracker",
    "binary": JWT_BINARY,
    "default_timeout": DEFAULT_TIMEOUT,
}


def register(mcp: "FastMCP") -> None:

    @mcp.tool(name="run_jwt_decode", description=(
        "Decode and display a JWT token's header and payload without verifying.\n\n"
        "token   : raw JWT string (three base64url-encoded parts)\n"
        "timeout : max seconds (default 60)"
    ))
    def run_jwt_decode(token: str, timeout: int = DEFAULT_TIMEOUT) -> str:
        log.info("run_jwt_decode invoked", extra={"token_prefix": token[:20]})
        cmd = [JWT_BINARY, "-d", token]
        result = run_tool(TOOL_NAME, cmd, timeout=timeout)
        return result.to_mcp_text()

    @mcp.tool(name="run_jwt_tamper", description=(
        "Run jwt_tool's full tamper/test mode against a JWT.\n\n"
        "Tests for: alg:none, algorithm confusion (RS256→HS256), "
        "key injection, and more.\n\n"
        "token   : raw JWT string\n"
        "timeout : max seconds (default 60)"
    ))
    def run_jwt_tamper(token: str, timeout: int = DEFAULT_TIMEOUT) -> str:
        log.info("run_jwt_tamper invoked", extra={"token_prefix": token[:20]})
        cmd = [JWT_BINARY, "-t", token]
        result = run_tool(TOOL_NAME, cmd, timeout=timeout)
        return result.to_mcp_text()

    @mcp.tool(name="run_jwt_crack", description=(
        "Brute-force the HMAC secret of a JWT token using a wordlist.\n\n"
        "token    : raw JWT string\n"
        "wordlist : absolute container path to the password file "
        "(default: /usr/share/wordlists/rockyou.txt)\n"
        "timeout  : max seconds (default 300)"
    ))
    def run_jwt_crack(
        token: str,
        wordlist: str = "/usr/share/wordlists/rockyou.txt",
        timeout: int = 300,
    ) -> str:
        log.info("run_jwt_crack invoked", extra={"token_prefix": token[:20], "wordlist": wordlist})
        cmd = [JWT_BINARY, "-C", "-d", wordlist, token]
        result = run_tool(TOOL_NAME, cmd, timeout=timeout)
        return result.to_mcp_text()

    @mcp.tool(name="run_jwt_exploit_none_alg", description=(
        "Attempt the 'alg:none' exploit — strip the signature and change "
        "the algorithm header to 'none', then return the forged token.\n\n"
        "token   : raw JWT string\n"
        "timeout : max seconds (default 30)"
    ))
    def run_jwt_exploit_none_alg(token: str, timeout: int = 30) -> str:
        log.info("run_jwt_exploit_none_alg invoked", extra={"token_prefix": token[:20]})
        # jwt_tool -X a → exploit alg:none
        cmd = [JWT_BINARY, token, "-X", "a"]
        result = run_tool(TOOL_NAME, cmd, timeout=timeout)
        return result.to_mcp_text()

    log.debug("jwt_tool tools registered")
