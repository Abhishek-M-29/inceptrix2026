"""
tools/__init__.py — re-exports every tool registration function.

Each module exposes a ``register(mcp)`` callable that attaches its
``@mcp.tool()`` decorated functions to the shared FastMCP instance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP

from tools import (
    nmap,
    nikto,
    whatweb,
    sqlmap,
    wfuzz,
    ffuf,
    nuclei,
    httpx_tool,
    dalfox,
    jwt_tool,
    sandbox,
    shell,
)

_MODULES = [
    nmap,
    nikto,
    whatweb,
    sqlmap,
    wfuzz,
    ffuf,
    nuclei,
    httpx_tool,
    dalfox,
    jwt_tool,
    sandbox,
    shell,
]


def register_all(mcp: "FastMCP") -> None:
    """Register every tool module's tools onto *mcp*."""
    for mod in _MODULES:
        mod.register(mcp)
