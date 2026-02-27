"""
Pydantic models shared across the MCP server and FastAPI layer.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Tool status
# ---------------------------------------------------------------------------

class ToolStatus(str, Enum):
    OK = "ok"
    TIMEOUT = "timeout"
    ERROR = "error"
    NOT_FOUND = "not_found"


# ---------------------------------------------------------------------------
# Generic tool response envelope
# ---------------------------------------------------------------------------

class ToolResponse(BaseModel):
    run_id: str = Field(..., description="Unique ID for this invocation")
    tool: str = Field(..., description="Name of the tool that was invoked")
    status: ToolStatus
    duration_s: float = Field(..., description="Wall-clock seconds the tool ran for")
    returncode: Optional[int] = Field(None, description="Process exit code")
    output: str = Field(..., description="Combined stdout + stderr")
    error: Optional[str] = Field(None, description="Executor-level error message if any")


# ---------------------------------------------------------------------------
# Per-tool input models  (used for FastAPI typed endpoints + docs)
# ---------------------------------------------------------------------------

class NmapInput(BaseModel):
    target: str = Field(..., description="Host, IP, or CIDR range to scan")
    flags: str = Field("-T4 -F --open", description="nmap flags — default is fast top-100 scan; use '-T4 -sV -sC' for service detection")
    timeout: int = Field(60, ge=10, le=1800, description="Max seconds to wait")

    @field_validator("flags")
    @classmethod
    def _default_flags(cls, v: str) -> str:
        return v.strip() if v.strip() else "-T4 -F --open"


class NiktoInput(BaseModel):
    target: str = Field(..., description="Full URL, e.g. 'http://example.com'")
    extra_flags: str = Field("", description="Extra nikto flags, e.g. '-Tuning 9 -maxtime 120'")
    timeout: int = Field(90, ge=10, le=1800)


class WhatWebInput(BaseModel):
    target: str = Field(..., description="URL to fingerprint")
    aggression: int = Field(1, ge=1, le=4, description="1=passive … 4=aggressive")
    timeout: int = Field(120, ge=10, le=600)


class SqlmapInput(BaseModel):
    target: str = Field(..., description="Target URL with parameter(s), e.g. 'http://site.com/page?id=1'")
    extra_flags: str = Field("--batch --level=1 --risk=1 --smart", description="sqlmap flags — use '--level=3 --risk=2' for deeper scan")
    timeout: int = Field(120, ge=10, le=3600)


class WfuzzInput(BaseModel):
    target: str = Field(..., description="URL with FUZZ placeholder, e.g. 'http://site.com/FUZZ'")
    wordlist: str = Field(
        "/usr/share/wordlists/dirb/common.txt",
        description="Absolute path to wordlist inside the container",
    )
    extra_flags: str = Field("--hc 404 -t 40", description="wfuzz flags")
    timeout: int = Field(120, ge=10, le=1800)


class FfufInput(BaseModel):
    target: str = Field(..., description="URL with FUZZ placeholder")
    wordlist: str = Field(
        "/usr/share/wordlists/dirb/common.txt",
        description="Absolute path to wordlist inside the container",
    )
    extra_flags: str = Field("-mc 200,301,302,403 -t 40 -timeout 5", description="ffuf flags")
    timeout: int = Field(120, ge=10, le=1800)


class NucleiInput(BaseModel):
    target: str = Field(..., description="Target URL")
    severity: str = Field("critical,high", description="Comma-separated severity levels — add 'medium' for wider scan")
    tags: str = Field("", description="Comma-separated template tags, e.g. 'cve,rce'")
    timeout: int = Field(120, ge=10, le=3600)


class HttpxInput(BaseModel):
    targets: str = Field(..., description="Space-separated list of hosts or URLs")
    extra_flags: str = Field(
        "-status-code -title -tech-detect -follow-redirects",
        description="httpx flags",
    )
    timeout: int = Field(180, ge=10, le=900)


class DalfoxInput(BaseModel):
    target: str = Field(..., description="URL to test for XSS, e.g. 'http://site.com/search?q=test'")
    extra_flags: str = Field("--only-discovery --silence", description="Dalfox flags — default is fast param discovery; remove --only-discovery for full XSS scan")
    timeout: int = Field(60, ge=10, le=1800)


class JwtToolInput(BaseModel):
    token: str = Field(..., description="Raw JWT string")
    mode: str = Field("-t", description="jwt_tool mode: '-t' tamper, '-d' decode, '-C' crack")
    timeout: int = Field(60, ge=5, le=300)


class ShellInput(BaseModel):
    command: str = Field(..., description="Bash command to run inside the Kali container, e.g. 'whoami' or 'cat /etc/os-release'")
    timeout: int = Field(60, ge=1, le=3600, description="Max seconds to wait")


# ---------------------------------------------------------------------------
# Health + metadata
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str = "ok"
    server: str = "inceptrix-mcp"
    tools: List[str] = Field(default_factory=list)


class ToolMeta(BaseModel):
    name: str
    description: str
    binary: str
    default_timeout: int


class ToolsListResponse(BaseModel):
    count: int
    tools: List[ToolMeta]
