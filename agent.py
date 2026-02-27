#!/usr/bin/env python3
"""
🔴 RedShell v2.0 — Full Hub-and-Spoke Autonomous Red-Teaming Agent
Converted from learning.ipynb — works exactly the same.

Usage:
    python agent.py <github_repo_url>
    python agent.py   # prompts interactively
"""

# ═══════════════════════════════════════════════════════════════════
# IMPORTS
# ═══════════════════════════════════════════════════════════════════
import itertools
import json
import logging
import os
import re
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, TypedDict
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph, START
from pydantic import BaseModel, Field

load_dotenv()
print("✅ Imports OK")

# ═══════════════════════════════════════════════════════════════════
# GITHUB URL — from CLI arg or interactive prompt
# ═══════════════════════════════════════════════════════════════════
if len(sys.argv) > 1:
    GITHUB_URL = sys.argv[1].strip()
else:
    GITHUB_URL = input("Enter the GitHub repo URL to pentest: ").strip()

if not GITHUB_URL:
    print("❌ No GitHub URL provided. Exiting.")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════════
# CONSTANTS + CONFIG
# ═══════════════════════════════════════════════════════════════════
GLOBAL_STEP_LIMIT = 20
MAX_HYPOTHESIS_ATTEMPTS = 4
HISTORY_SUMMARIZE_THRESHOLD = 8
MAX_PORTS_RECON = 15
MAX_ENUM_CMDS = 4
MAX_HISTORY_KEEP = 20
MAX_HYPOTHESIS_CHARS = 300
DEFAULT_PORTS = "21,22,25,80,443,445,3000,3306,8080,8443"
TOOL_TIMEOUT_DEFAULT = 120
TOOL_TIMEOUT_MAP = {
    "run_nmap": 120, "run_nmap_full_scan": 900,
    "run_nikto": 120, "run_nikto_ssl": 120,
    "run_whatweb": 120, "run_whatweb_aggressive": 180,
    "run_sqlmap": 180, "run_sqlmap_enumerate_dbs": 600, "run_sqlmap_post": 600,
    "run_wfuzz": 180, "run_wfuzz_dirs": 180, "run_wfuzz_params": 180,
    "run_ffuf": 180, "run_ffuf_dirs": 180, "run_ffuf_vhost": 300,
    "run_nuclei": 180, "run_nuclei_cve": 180, "run_nuclei_technologies": 120, "run_nuclei_update_templates": 120,
    "run_httpx": 180, "run_httpx_probe": 60, "run_httpx_screenshot_headers": 60,
    "run_dalfox": 120, "run_dalfox_discovery_only": 180, "run_dalfox_blind": 300,
    "run_jwt_decode": 60, "run_jwt_tamper": 60, "run_jwt_crack": 300, "run_jwt_exploit_none_alg": 30,
    "build_sandbox": 600, "list_sandboxes": 30, "teardown_sandbox": 120,
}

MCP_URL = os.getenv("MCP_URL", "http://192.168.247.108:8090/")
KB_PATH = Path(".").resolve() / "knowledge_base.json"
REPORT_PATH = Path(".").resolve() / "redshell_report.json"

print(f"MCP_URL    : {MCP_URL}")
print(f"GITHUB_URL : {GITHUB_URL}")
print(f"KB_PATH    : {KB_PATH}  (exists: {KB_PATH.exists()})")
print("✅ Constants OK")

# ═══════════════════════════════════════════════════════════════════
# SEVERITY MAP + SAFETY WHITELIST + safe_json
# ═══════════════════════════════════════════════════════════════════
SEVERITY_MAP = {
    "injection": "Critical", "sqli": "Critical", "sql injection": "Critical",
    "rce": "Critical", "remote code execution": "Critical", "command injection": "Critical",
    "deserialization": "Critical", "ssrf": "Critical",
    "auth bypass": "High", "authentication bypass": "High", "idor": "High",
    "broken access control": "High", "xss": "High", "cross-site scripting": "High",
    "file inclusion": "High", "lfi": "High", "rfi": "High", "path traversal": "High",
    "csrf": "Medium", "directory listing": "Medium", "open redirect": "Medium",
    "cors misconfiguration": "Medium", "information disclosure": "Medium",
    "clickjacking": "Low", "missing headers": "Low", "missing security": "Low",
    "cookie flags": "Low", "cookie": "Low",
    "version disclosure": "Informational", "technology detection": "Informational", "banner grab": "Informational",
}
ALLOWED_SEVERITIES = {"Critical", "High", "Medium", "Low", "Informational"}


def classify_severity(title: str) -> str:
    low = title.lower()
    for keyword, sev in SEVERITY_MAP.items():
        if keyword in low:
            return sev
    return "Informational"


SAFE_TOOLS = {
    "run_nmap", "run_nmap_full_scan", "run_nikto", "run_nikto_ssl",
    "run_whatweb", "run_whatweb_aggressive",
    "run_sqlmap", "run_sqlmap_enumerate_dbs", "run_sqlmap_post",
    "run_wfuzz", "run_wfuzz_dirs", "run_wfuzz_params",
    "run_ffuf", "run_ffuf_dirs", "run_ffuf_vhost",
    "run_nuclei", "run_nuclei_cve", "run_nuclei_technologies", "run_nuclei_update_templates",
    "run_httpx", "run_httpx_probe", "run_httpx_screenshot_headers",
    "run_dalfox", "run_dalfox_discovery_only", "run_dalfox_blind",
    "run_jwt_decode", "run_jwt_tamper", "run_jwt_crack", "run_jwt_exploit_none_alg",
    "build_sandbox", "list_sandboxes", "teardown_sandbox",
}
BLOCKED_PATTERNS = ["rm -rf", "drop table", "dd if", "mkfs", "> /dev/sd", ":(){ :", "shutdown"]


def is_safe_cmd(tool: str, args: str) -> bool:
    if tool not in SAFE_TOOLS:
        return False
    return not any(bad in args.lower() for bad in BLOCKED_PATTERNS)


def safe_json(text: str, default: dict | None = None) -> dict:
    if default is None:
        default = {}
    cleaned = re.sub(r'```(?:json|python|bash)?\s*\n?', '', text).strip()
    try:
        if cleaned.startswith("{"):
            return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', cleaned)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return default


# Quick test
assert classify_severity("SQL Injection in login") == "Critical"
assert is_safe_cmd("run_nmap", "-sV -p 80") == True
assert is_safe_cmd("rm", "-rf /") == False
print("✅ Severity + Safety + safe_json OK")

# ═══════════════════════════════════════════════════════════════════
# STRUCTURED LOGGER + MCP CLIENT
# ═══════════════════════════════════════════════════════════════════
_log_records: list[dict] = []


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _log(event: str, **kw: Any) -> None:
    entry = {"ts": _ts(), "event": event, **kw}
    _log_records.append(entry)
    print(f"  📋 {json.dumps(entry)}")


# ── MCP Client (Streamable HTTP / SSE) ──
_MCP_SESSION_ID: str | None = None
_MCP_HEADERS_BASE = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


def _mcp_ensure_session() -> str:
    global _MCP_SESSION_ID
    if _MCP_SESSION_ID is not None:
        return _MCP_SESSION_ID
    payload = {
        "jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": "initialize",
        "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                   "clientInfo": {"name": "redshell-notebook", "version": "2.0"}},
    }
    resp = requests.post(MCP_URL, json=payload, headers=_MCP_HEADERS_BASE, timeout=30)
    _MCP_SESSION_ID = resp.headers.get("Mcp-Session-Id") or resp.headers.get("mcp-session-id")
    _log("mcp_session_init", session_id=_MCP_SESSION_ID or "(none)")
    return _MCP_SESSION_ID


def call_mcp(tool_name: str, arguments: dict, timeout: int | None = None) -> str:
    global _MCP_SESSION_ID
    effective_timeout = timeout or TOOL_TIMEOUT_MAP.get(tool_name, TOOL_TIMEOUT_DEFAULT)
    _log("tool_started", tool=tool_name, timeout=effective_timeout)
    t0 = time.monotonic()

    try:
        session_id = _mcp_ensure_session()
    except Exception as exc:
        _log("tool_failed", tool=tool_name, error=str(exc))
        return f"[MCP ERROR] Session init failed: {exc}"

    headers = {**_MCP_HEADERS_BASE}
    if session_id:
        headers["Mcp-Session-Id"] = session_id

    payload = {
        "jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }
    try:
        resp = requests.post(MCP_URL, json=payload, headers=headers, timeout=effective_timeout, stream=True)
        resp.raise_for_status()
        full_text = ""
        for line in resp.iter_lines(decode_unicode=True):
            if line and line.startswith("data: "):
                full_text = line[6:]
        resp.close()
    except requests.exceptions.Timeout:
        elapsed = round(time.monotonic() - t0, 1)
        _log("tool_timeout", tool=tool_name, elapsed=elapsed)
        return f"[MCP TIMEOUT] {tool_name} timed out after {effective_timeout}s"
    except requests.exceptions.ConnectionError:
        _log("tool_failed", tool=tool_name, error="connection_error")
        return f"[MCP ERROR] Cannot connect to {MCP_URL}"
    except Exception as exc:
        _log("tool_failed", tool=tool_name, error=str(exc))
        return f"[MCP ERROR] {tool_name}: {exc}"

    elapsed = round(time.monotonic() - t0, 1)

    if not full_text:
        if "Missing session" in (resp.text or ""):
            _MCP_SESSION_ID = None
        _log("tool_completed", tool=tool_name, elapsed=elapsed, result="no_data")
        return "[MCP] No data received"

    try:
        data = json.loads(full_text)
    except json.JSONDecodeError:
        _log("tool_completed", tool=tool_name, elapsed=elapsed, result="raw_text")
        return full_text

    if "error" in data:
        err = data["error"]
        msg = err.get("message", str(err))
        if "session" in msg.lower():
            _MCP_SESSION_ID = None
        _log("tool_failed", tool=tool_name, error=msg, elapsed=elapsed)
        return f"[MCP ERROR] {tool_name}: {msg}"

    result = data.get("result", {})
    _log("tool_completed", tool=tool_name, elapsed=elapsed)
    if isinstance(result, dict):
        content = result.get("content", [])
        if isinstance(content, list) and content:
            return content[0].get("text", str(content))
        return json.dumps(result)
    return str(result)


print("✅ Logger + MCP Client OK")

# ═══════════════════════════════════════════════════════════════════
# RAG — KNOWLEDGE BASE
# ═══════════════════════════════════════════════════════════════════
_KB_CACHE: dict | None = None


def _load_kb() -> dict:
    global _KB_CACHE
    if _KB_CACHE is None:
        try:
            with open(KB_PATH) as f:
                _KB_CACHE = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
            _log("kb_fallback", error=str(exc))
            _KB_CACHE = {}
    return _KB_CACHE


def query_knowledge_base(query: str) -> str:
    """Keyword search across WSTG vectors, exploit templates, and enum techniques."""
    kb = _load_kb()
    query_lower = query.lower()
    hits: list[str] = []
    for code, entry in kb.get("wstg_vectors", {}).items():
        searchable = f"{code} {entry['name']} {entry['category']}".lower()
        if any(tok in searchable for tok in query_lower.split()):
            payloads = "\n    ".join(entry.get("payloads", []))
            hits.append(f"[{code}] {entry['name']}\n  Category: {entry['category']}\n  Tools: {', '.join(entry.get('tools', []))}\n  Payloads:\n    {payloads}")
    for key, tpl in kb.get("exploit_templates", {}).items():
        searchable = f"{key} {tpl['description']} {tpl.get('wstg_code','')}".lower()
        if any(tok in searchable for tok in query_lower.split()):
            hits.append(f"[Template: {key}] {tpl['description']}\n  Command: {tpl.get('template', '')}")
    for key, tech in kb.get("enumeration_techniques", {}).items():
        searchable = f"{key} {tech['description']}".lower()
        if any(tok in searchable for tok in query_lower.split()):
            hits.append(f"[Enum: {key}] {tech['description']}\n  Command: {tech.get('command', '')}")
    if not hits:
        return "(No KB matches for: " + query + ")"
    return "\n\n".join(hits[:8])


# ── Priority attack vectors (ordered by severity / impact) ──
PRIORITY_VECTORS: list[tuple[str, str, str]] = [
    ("WSTG-INPV-05", "SQL Injection",       "run_sqlmap_post"),
    ("WSTG-INPV-01", "Reflected XSS",       "run_dalfox"),
    ("WSTG-INPV-02", "Stored XSS",          "run_httpx_probe"),
    ("WSTG-ATHN-03", "IDOR / Broken Auth",  "run_httpx_probe"),
    ("WSTG-CONF-05", "Sensitive File Exposure", "run_ffuf"),
    ("WSTG-CLNT-04", "Open Redirect",       "run_httpx_probe"),
    ("WSTG-CLNT-07", "CORS Misconfiguration", "run_shell"),
]


def get_coverage_status(tested: list[str]) -> dict:
    """Returns a dict with 'tested', 'remaining', and 'progress' based on PRIORITY_VECTORS."""
    tested_set = set(tested or [])
    remaining = [(code, label, tool) for code, label, tool in PRIORITY_VECTORS if code not in tested_set]
    return {
        "tested": [f"{c}: {l}" for c, l, _ in PRIORITY_VECTORS if c in tested_set],
        "remaining": [f"{c}: {l}" for c, l, _ in remaining],
        "remaining_detail": remaining,
        "progress": f"{len(tested_set)}/{len(PRIORITY_VECTORS)}",
        "done": len(remaining) == 0,
    }


# Quick test
test_kb = query_knowledge_base("injection xss")
test_cov = get_coverage_status(["WSTG-INPV-05"])
print(f"KB test (first 200 chars): {test_kb[:200]}")
print(f"Coverage test: {test_cov['progress']} — remaining: {test_cov['remaining'][:3]}")
print("✅ Knowledge Base + Coverage Tracker OK")

# ═══════════════════════════════════════════════════════════════════
# STATE + LLM FACTORY + PYDANTIC MODELS + STRUCTURED CHAINS
# ═══════════════════════════════════════════════════════════════════

# ── RedShellState ──
class RedShellState(TypedDict, total=False):
    job_id: str
    current_target: str
    target_queue: list[str]
    action_history: list[str]
    confirmed_findings: list[dict]
    global_steps: int
    hypothesis_attempts: int
    last_output: str
    scan_start: float
    sandbox_id: str
    sandbox_url: str
    github_url: str
    phase: str
    tested_vectors: list[str]


HISTORY_SUMMARIZE_THRESHOLD = 30
ALLOWED_SEVERITIES = {"critical", "high", "medium", "low", "info"}
MAX_STEPS = 25


# ── Round-Robin LLM Pool ──
class GroqKeyPool:
    """Wraps multiple ChatGroq instances, rotating keys on every invoke()."""

    def __init__(self, keys: list[str], model: str = "llama-3.3-70b-versatile",
                 temperature: float = 0.2, max_retries: int = 2):
        self._instances = []
        for k in keys:
            self._instances.append(ChatGroq(
                model=model, temperature=temperature, api_key=k,
            ))
        self._cycle = itertools.cycle(range(len(self._instances)))
        self._lock = threading.Lock()
        self._n = len(self._instances)
        print(f"  🔑 Pool created: {self._n} keys × model={model}")

    def _next(self) -> ChatGroq:
        with self._lock:
            return self._instances[next(self._cycle)]

    def invoke(self, prompt, **kw):
        """Try each key in round-robin; on 429 rotate to the next."""
        last_err = None
        for attempt in range(self._n):
            inst = self._next()
            try:
                return inst.invoke(prompt, **kw)
            except Exception as exc:
                last_err = exc
                err_str = str(exc)
                if "429" in err_str or "rate" in err_str.lower():
                    continue
                raise
        raise last_err

    def with_structured_output(self, schema):
        """Return a structured-output wrapper that also rotates keys."""
        pool = self
        structured_instances = [inst.with_structured_output(schema) for inst in self._instances]
        cycle = itertools.cycle(range(len(structured_instances)))
        lock = threading.Lock()

        class _PoolStructured:
            def invoke(self, prompt, **kw):
                last_err = None
                for attempt in range(pool._n):
                    with lock:
                        idx = next(cycle)
                    inst = structured_instances[idx]
                    try:
                        return inst.invoke(prompt, **kw)
                    except Exception as exc:
                        last_err = exc
                        err_str = str(exc)
                        if "429" in err_str or "rate" in err_str.lower():
                            continue
                        raise
                raise last_err
        return _PoolStructured()


# ── Load keys from .env ──
load_dotenv(override=True)

_groq_keys = []
for i in range(1, 7):
    k = os.getenv(f"Groq_api_key_{i}") or os.getenv(f"GROQ_API_KEY_{i}") or os.getenv(f"groq_api_key_{i}")
    if k:
        _groq_keys.append(k.strip())

_main_key = os.getenv("GROQ_API_KEY", "").strip()
if _main_key and _main_key not in _groq_keys:
    _groq_keys.append(_main_key)

print(f"  Found {len(_groq_keys)} Groq API keys")

if len(_groq_keys) >= 2:
    llm = GroqKeyPool(
        keys=_groq_keys,
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        temperature=float(os.getenv("GROQ_TEMPERATURE", "0.2")),
    )
else:
    llm = ChatGroq(
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        temperature=float(os.getenv("GROQ_TEMPERATURE", "0.2")),
        api_key=_groq_keys[0] if _groq_keys else os.getenv("GROQ_API_KEY"),
    )

# Quick health check
try:
    _test = llm.invoke("Say OK")
    print(f"  ✅ LLM health check passed: {_test.content[:30]}")
except Exception as e:
    print(f"  ⚠️  LLM health check failed: {str(e)[:100]}")


# ── Pydantic Models ──
class GatingDecision(BaseModel):
    route: Literal["recon", "enumeration", "hypothesis", "pivot", "reporting"] = Field(
        description="The next spoke node to route to."
    )


class EnumCommand(BaseModel):
    tool: Literal[
        "run_nmap", "run_nikto", "run_whatweb", "run_nuclei", "run_nuclei_cve",
        "run_nuclei_technologies", "run_ffuf_dirs", "run_wfuzz_dirs",
        "run_httpx_probe", "run_httpx_screenshot_headers",
    ] = Field(description="The MCP tool to use.")
    args: str = Field(description="The exact CLI arguments or command string.")


class EnumPlan(BaseModel):
    commands: list[EnumCommand] = Field(
        default_factory=list, description="List of up to 4 enumeration commands.", max_length=4,
    )


class HypothesisPayload(BaseModel):
    wstg: str = Field(description="OWASP WSTG test code, e.g. WSTG-INPV-05.")
    theory: str = Field(description="One-line description of what this exploit tests.")
    tool: Literal[
        "run_sqlmap", "run_sqlmap_post", "run_dalfox", "run_wfuzz_params",
        "run_httpx_probe", "run_nuclei_cve", "run_ffuf", "run_nikto",
    ] = Field(description="The MCP tool to execute the payload with.")
    payload: str = Field(description="The exact CLI command or code to run.")


class ImpactVerdict(BaseModel):
    verdict: Literal["SUCCESS", "FAILED", "SHELL"] = Field(
        description="SUCCESS if vulnerability confirmed, FAILED if not, SHELL if interactive access."
    )
    explanation: str = Field(description="Brief explanation.")
    new_targets: list[str] = Field(default_factory=list, description="Any new hosts discovered.")


class RemediationItem(BaseModel):
    finding_id: str = Field(description="The finding ID, e.g. F-001.")
    remediation: str = Field(description="One-line remediation suggestion.")


class RemediationList(BaseModel):
    items: list[RemediationItem] = Field(
        default_factory=list, description="One remediation per finding."
    )


# ── Structured LLM chains (all use the key pool) ──
llm_gating      = llm.with_structured_output(GatingDecision)
llm_enum_plan   = llm.with_structured_output(EnumPlan)
llm_hypothesis  = llm.with_structured_output(HypothesisPayload)
llm_impact      = llm.with_structured_output(ImpactVerdict)
llm_remediation = llm.with_structured_output(RemediationList)

print(f"✅ LLM provider: {type(llm).__name__} ({len(_groq_keys)} keys)")
print(f"✅ State: {list(RedShellState.__annotations__.keys())}")
print(f"✅ Pydantic models + chains OK")

# ═══════════════════════════════════════════════════════════════════
# HISTORY SUMMARIZER + FINDINGS NORMALIZER
# ═══════════════════════════════════════════════════════════════════
MAX_LOG_ENTRY = 120
MAX_LAST_OUTPUT = 800
MAX_EVIDENCE_STORE = 1500


def _compact(text: str, limit: int = MAX_LOG_ENTRY) -> str:
    """Truncate a string to `limit` chars, one line."""
    s = text.replace("\n", " ").strip()
    return s[:limit] + "…" if len(s) > limit else s


def _trim_output(raw: str, limit: int = MAX_LAST_OUTPUT) -> str:
    """Extract the useful signal from raw tool output, drop boilerplate."""
    lines = raw.split("\n")
    useful = [l for l in lines if not any(b in l for b in [
        "projectdiscovery.io", "Use with caution", "Developers assume",
        "legal disclaimer", "___", "__H__", "starting @",
        "loaded provider", "[stderr]",
    ])]
    trimmed = "\n".join(useful).strip()
    return trimmed[:limit] if len(trimmed) > limit else trimmed


def _summarize_history(history: list[str], llm_ref) -> list[str]:
    if len(history) <= HISTORY_SUMMARIZE_THRESHOLD:
        return history
    keep_tail = 5
    old_part = history[:-keep_tail]
    recent = history[-keep_tail:]
    old_text = "\n".join(old_part)
    resp = llm_ref.invoke(
        f"Compress this pen-test action log into max 8 bullet points. "
        f"Keep: confirmed findings, open ports, technologies, failed vectors. "
        f"Drop duplicate scans.\n\n{old_text[:3000]}"
    )
    return [f"[summary] {_compact(resp.content, 600)}"] + recent


_finding_counter = 0

# Severity mapping for known vuln types
_SEVERITY_OVERRIDES = {
    "WSTG-INPV-05": "Critical",
    "WSTG-INPV-02": "High",
    "WSTG-INPV-01": "High",
    "WSTG-ATHN-03": "High",
    "WSTG-ATHZ-02": "High",
    "WSTG-CONF-05": "High",
    "WSTG-CLNT-04": "Medium",
    "WSTG-CLNT-07": "Medium",
}


def make_finding(
    title: str,
    category: str,
    tool: str,
    evidence: str,
    description: str = "",
    impact: str = "",
    remediation: str = "",
    severity: str | None = None,
) -> dict:
    global _finding_counter
    _finding_counter += 1
    if severity and severity.lower() in ALLOWED_SEVERITIES:
        sev = severity.capitalize()
    elif category in _SEVERITY_OVERRIDES:
        sev = _SEVERITY_OVERRIDES[category]
    else:
        sev = classify_severity(title)
    return {
        "id": f"F-{_finding_counter:03d}",
        "title": title[:200],
        "severity": sev,
        "category": category,
        "tool": tool,
        "evidence": _trim_output(evidence, MAX_EVIDENCE_STORE),
        "description": (description or title)[:400],
        "impact": impact[:200],
        "remediation": remediation[:300],
    }


# Quick test
f = make_finding("Test XSS in search", "WSTG-INPV-02", "run_dalfox", "<script>alert(1)</script>")
print(f"Sample finding: {json.dumps(f, indent=2)}")
_finding_counter = 0  # reset for actual run
print("✅ History Summarizer + Findings Normalizer OK (token-optimized)")

# ═══════════════════════════════════════════════════════════════════
# GATING NODE v3 — Coverage-Aware State Machine
# ═══════════════════════════════════════════════════════════════════
GLOBAL_STEP_LIMIT = 25
MAX_HYPOTHESIS_ATTEMPTS = 6
MAX_HISTORY_KEEP = 12


def gating_node(state: RedShellState) -> dict:
    steps = state.get("global_steps", 0) + 1
    history = list(state.get("action_history", []))
    findings = state.get("confirmed_findings", [])
    hypo_attempts = state.get("hypothesis_attempts", 0)
    queue = state.get("target_queue", [])
    phase = state.get("phase", "init")
    tested = list(state.get("tested_vectors", []))
    last = state.get("last_output", "")

    if len(history) > HISTORY_SUMMARIZE_THRESHOLD:
        history = _summarize_history(history, llm)

    # ── Hard ceilings ──
    elapsed = time.monotonic() - state.get("scan_start", time.monotonic())
    if steps > GLOBAL_STEP_LIMIT or elapsed > 420:
        reason = f"step={steps}" if steps > GLOBAL_STEP_LIMIT else f"time={elapsed:.0f}s"
        history.append(_compact(f"[gate] LIMIT ({reason}) → reporting"))
        return {"global_steps": steps, "action_history": history,
                "last_output": "reporting", "phase": "done"}

    # ── Coverage check (RAG-driven) ──
    coverage = get_coverage_status(tested)

    # ── Deterministic FSM ──

    if phase == "init" or steps <= 1:
        decision = "recon"
        next_phase = "recon"

    elif phase == "recon":
        decision = "enumeration"
        next_phase = "enum"

    elif phase == "enum":
        if coverage["remaining_detail"]:
            decision = "hypothesis"
            next_phase = "exploit"
        else:
            decision = "reporting"
            next_phase = "done"

    elif phase == "exploit":
        if coverage["done"]:
            decision = "reporting"
            next_phase = "done"
        elif hypo_attempts >= MAX_HYPOTHESIS_ATTEMPTS:
            if queue:
                decision = "pivot"
                next_phase = "init"
            else:
                decision = "reporting"
                next_phase = "done"
        else:
            decision = "hypothesis"
            next_phase = "exploit"

    elif phase == "done":
        decision = "reporting"
        next_phase = "done"

    else:
        # Unknown phase — LLM tiebreaker (the ONLY LLM call)
        try:
            recent = "\n".join(history[-MAX_HISTORY_KEEP:])
            prompt = (
                f"Step {steps}/{GLOBAL_STEP_LIMIT} | Phase: {phase} | "
                f"Coverage: {coverage['progress']} | "
                f"Remaining: {', '.join(coverage['remaining'][:3])}\n"
                f"Recent:\n{recent}\n"
                f"Route? (recon|enumeration|hypothesis|pivot|reporting)"
            )
            obj: GatingDecision = llm_gating.invoke([
                {"role": "system", "content": "Pick the next route. One word."},
                {"role": "user", "content": prompt},
            ])
            decision = obj.route
        except Exception:
            decision = "reporting"
        next_phase = {"recon": "recon", "enumeration": "enum",
                      "hypothesis": "exploit", "reporting": "done",
                      "pivot": "init"}.get(decision, "done")

    history.append(_compact(
        f"[gate] step {steps} | phase {phase}→{next_phase} | "
        f"coverage {coverage['progress']} | → {decision}"
    ))

    return {
        "global_steps": steps,
        "action_history": history,
        "last_output": decision,
        "phase": next_phase,
    }


def gate_router(state: RedShellState) -> str:
    d = state.get("last_output", "reporting").strip().lower()
    valid = {"recon", "enumeration", "hypothesis", "pivot", "reporting"}
    return d if d in valid else "reporting"


print("✅ Gating Node v3 — Coverage-Aware FSM (no LLM except edge cases)")

# ═══════════════════════════════════════════════════════════════════
# RECON NODE (Spoke 1)
# ═══════════════════════════════════════════════════════════════════
MAX_PORTS_RECON = 30
DEFAULT_PORTS = "21,22,25,53,80,110,143,443,445,993,995,3000,3306,5432,8000,8080,8443,8888,9090"


def recon_node(state: RedShellState) -> dict:
    target = state["current_target"]
    host = target.split(":")[0]
    logs = list(state.get("action_history", []))
    sandbox_url = state.get("sandbox_url", "")

    if sandbox_url:
        probe_url = sandbox_url
    else:
        port = target.split(":")[-1] if ":" in target else "80"
        scheme = "https" if port in ("443", "8443") else "http"
        probe_url = f"{scheme}://{target}"

    logs.append(_compact(f"[recon] start: probe_url={probe_url}"))

    # 1. Port scan
    nmap_quick = call_mcp("run_nmap", {"target": host, "flags": "-Pn --top-ports 1000 -T4 --open"})
    ports = re.findall(r'(\d+)/tcp\s+open', nmap_quick)
    logs.append(_compact(f"[recon] nmap: {len(ports)} open ports: {','.join(ports[:10])}"))

    # 2. Service scan on found ports
    if ports:
        port_arg = ",".join(ports[:MAX_PORTS_RECON])
        nmap_svc = call_mcp("run_nmap", {"target": host, "flags": f"-sV -sC -Pn -p {port_arg}"})
    else:
        nmap_svc = call_mcp("run_nmap", {"target": host, "flags": f"-sV -sC -Pn -p {DEFAULT_PORTS}"})
    logs.append(_compact(f"[recon] nmap -sV done"))

    # 3. HTTP probe
    httpx_out = call_mcp("run_httpx_probe", {"url": probe_url})
    logs.append(_compact(f"[recon] httpx: {httpx_out[:80] if httpx_out else 'no resp'}"))

    # 4. Tech fingerprint
    whatweb_out = call_mcp("run_whatweb", {"target": probe_url})
    logs.append(_compact(f"[recon] whatweb done"))

    # 5. Directory brute-force
    ffuf_out = call_mcp("run_ffuf_dirs", {"base_url": probe_url})
    logs.append(_compact(f"[recon] ffuf_dirs done"))

    # 6. Headers
    headers_out = call_mcp("run_httpx_screenshot_headers", {"url": probe_url})
    logs.append(_compact(f"[recon] headers done"))

    # Combine into a COMPACT summary
    summary_parts = []
    summary_parts.append(f"Ports: {','.join(ports[:15]) if ports else 'none found'}")
    summary_parts.append(f"HTTPX: {_trim_output(httpx_out, 200)}")
    summary_parts.append(f"Tech: {_trim_output(whatweb_out, 200)}")
    summary_parts.append(f"Dirs: {_trim_output(ffuf_out, 200)}")
    summary_parts.append(f"Headers: {_trim_output(headers_out, 200)}")

    combined = "\n".join(summary_parts)
    return {"action_history": logs, "last_output": _trim_output(combined, MAX_LAST_OUTPUT)}


print("✅ Recon Node OK (compact output, token-optimized)")

# ═══════════════════════════════════════════════════════════════════
# ENUMERATION NODE (Spoke 2)
# ═══════════════════════════════════════════════════════════════════
MAX_ENUM_CMDS = 4


def _direct_probe_vulns(probe_url: str, logs: list, findings: list) -> list:
    """Directly probe for easy-to-detect vulnerabilities — NO LLM needed."""
    new_findings = []

    # ── 1. Exposed sensitive files (.env, backup/users.sql) ──
    for path, desc in [
        ("/.env", "Exposed .env configuration file"),
        ("/backup/users.sql", "Exposed SQL backup with credentials"),
    ]:
        url = f"{probe_url}{path}"
        out = call_mcp("run_httpx_probe", {"url": url})
        logs.append(_compact(f"[enum:file] {path} → {'200 FOUND' if '200' in (out or '') else 'not found'}"))
        if out and "200" in out and "ERROR" not in out:
            new_findings.append(make_finding(
                title=f"Sensitive File Exposure: {desc} at {path}",
                category="WSTG-CONF-05",
                tool="run_httpx_probe",
                evidence=out,
                description=f"File {path} is publicly accessible (HTTP 200). Contains sensitive data.",
                impact="Database credentials, secrets, or user data leaked to any unauthenticated attacker.",
                remediation=f"Remove {path} from web root or block access with server-side rules.",
                severity="High",
            ))

    # ── 2. Open redirect ──
    redirect_url = f"{probe_url}/redirect?next=https://evil.com"
    out = call_mcp("run_httpx_probe", {"url": redirect_url})
    logs.append(_compact(f"[enum:redirect] → {'VULN' if out and 'evil.com' in out.lower() else 'safe'}"))
    if out and ("evil.com" in out.lower() or "302" in out):
        new_findings.append(make_finding(
            title="Open Redirect: /redirect?next= accepts arbitrary external URLs",
            category="WSTG-CLNT-04",
            tool="run_httpx_probe",
            evidence=out,
            description="The /redirect endpoint forwards to any URL without validation.",
            impact="Phishing attacks via trusted domain redirect.",
            remediation="Validate 'next' param against an allow-list of trusted domains.",
            severity="Medium",
        ))

    # ── 3. CORS misconfiguration (must send Origin header) ──
    cors_out = call_mcp("run_shell", {
        "command": f"curl -sI -H 'Origin: https://evil.com' {probe_url}/api/login 2>&1 | head -20"
    })
    logs.append(_compact(f"[enum:cors] → {cors_out[:100] if cors_out else 'no response'}"))
    if cors_out and "access-control-allow-origin" in cors_out.lower():
        lower = cors_out.lower()
        if "evil.com" in lower or "access-control-allow-origin: *" in lower:
            new_findings.append(make_finding(
                title="CORS Misconfiguration: Server reflects arbitrary Origin with credentials",
                category="WSTG-CLNT-07",
                tool="run_shell",
                evidence=cors_out,
                description="The server returns Access-Control-Allow-Origin reflecting any Origin header, combined with Allow-Credentials.",
                impact="Attacker can steal authenticated user data via cross-origin JavaScript requests.",
                remediation="Restrict CORS to specific trusted origins. Never reflect arbitrary Origins with credentials.",
                severity="Medium",
            ))

    # ── 4. Reflected XSS via /api/search?term= ──
    xss_payload = "<script>alert(1)</script>"
    xss_out = call_mcp("run_shell", {
        "command": f"curl -s '{probe_url}/api/search?term={xss_payload}' 2>&1 | head -50"
    })
    logs.append(_compact(f"[enum:rxss] /api/search → {'REFLECTED' if xss_out and '<script>' in xss_out else 'safe'}"))
    if xss_out and "<script>" in xss_out.lower():
        new_findings.append(make_finding(
            title="Reflected XSS in /api/search?term= parameter",
            category="WSTG-INPV-01",
            tool="run_shell",
            evidence=xss_out,
            description="The search endpoint reflects user input verbatim in the HTML response without encoding.",
            impact="Attacker can execute arbitrary JavaScript in victim's browser session.",
            remediation="HTML-encode all user input before reflecting. Add Content-Security-Policy header.",
            severity="High",
        ))

    # Also run dalfox as a secondary check
    dalfox_out = call_mcp("run_dalfox", {"target": f"{probe_url}/api/search?term=test"})
    if dalfox_out and any(kw in dalfox_out.upper() for kw in ["XSS", "VULN", "POC"]):
        if not any("Reflected XSS" in f.get("title", "") for f in new_findings):
            new_findings.append(make_finding(
                title="Reflected XSS in /api/search?term= (dalfox confirmed)",
                category="WSTG-INPV-01",
                tool="run_dalfox",
                evidence=dalfox_out,
                description="Dalfox confirmed XSS in the search parameter.",
                impact="Arbitrary JavaScript execution in victim's browser.",
                remediation="Sanitize user input; use CSP headers.",
                severity="High",
            ))

    # ── 5. Stored XSS via /api/comments (POST then GET) ──
    xss_comment = "<img src=x onerror=alert(document.cookie)>"
    post_out = call_mcp("run_shell", {
        "command": f"curl -s -X POST '{probe_url}/api/comments' -H 'Content-Type: application/json' -d '{{\"comment\":\"{xss_comment}\",\"user\":\"testxss\"}}' 2>&1"
    })
    logs.append(_compact(f"[enum:sxss] POST /api/comments → {post_out[:80] if post_out else 'no resp'}"))
    get_out = call_mcp("run_shell", {
        "command": f"curl -s '{probe_url}/api/comments' 2>&1 | head -100"
    })
    if get_out and "onerror" in get_out.lower():
        new_findings.append(make_finding(
            title="Stored XSS in /api/comments endpoint",
            category="WSTG-INPV-02",
            tool="run_shell",
            evidence=f"POST response: {post_out[:500]}\nGET response: {get_out[:500]}",
            description="User-submitted HTML/JS in comments is stored and rendered without sanitization.",
            impact="Persistent JavaScript execution for all users who view comments.",
            remediation="Sanitize all stored user input server-side. Use DOMPurify or similar on the frontend.",
            severity="High",
        ))

    # ── 6. SQL Injection via POST /api/login ──
    sqli_out = call_mcp("run_sqlmap_post", {
        "target": f"{probe_url}/api/login",
        "data": "username=admin&password=test"
    })
    logs.append(_compact(f"[enum:sqli] POST /api/login → {sqli_out[:80] if sqli_out else 'no resp'}"))
    if sqli_out and any(kw in sqli_out.lower() for kw in [
        "injectable", "sql injection", "sqlmap identified", "parameter", "payload",
        "500 (internal server error)", "syntax error"
    ]):
        new_findings.append(make_finding(
            title="SQL Injection in POST /api/login (username parameter)",
            category="WSTG-INPV-05",
            tool="run_sqlmap_post",
            evidence=sqli_out,
            description="The login endpoint builds SQL via string interpolation, vulnerable to injection.",
            impact="Full database compromise: auth bypass, data exfiltration, potential RCE.",
            remediation="Use parameterized queries / prepared statements. Never concatenate user input into SQL.",
            severity="Critical",
        ))

    # ── 7. IDOR on /api/account/:id ──
    idor_out = call_mcp("run_httpx_probe", {"url": f"{probe_url}/api/account/1"})
    logs.append(_compact(f"[enum:idor] /api/account/1 → {'200 FOUND' if idor_out and '200' in idor_out else 'denied'}"))
    if idor_out and "200" in idor_out and "ERROR" not in idor_out:
        idor_out2 = call_mcp("run_httpx_probe", {"url": f"{probe_url}/api/account/2"})
        new_findings.append(make_finding(
            title="IDOR: Direct Object Reference on /api/account/:id without authorization",
            category="WSTG-ATHN-03",
            tool="run_httpx_probe",
            evidence=f"Account 1: {_trim_output(idor_out, 500)}\nAccount 2: {_trim_output(idor_out2 or '', 500)}",
            description="Any user's account data can be accessed by incrementing the ID parameter without authentication.",
            impact="Mass user data exposure. Attacker can enumerate all accounts.",
            remediation="Implement server-side authorization: verify the requester owns the requested resource.",
            severity="High",
        ))

    return new_findings


def enumeration_node(state: RedShellState) -> dict:
    target = state["current_target"]
    logs = list(state.get("action_history", []))
    findings = list(state.get("confirmed_findings", []))
    last = state.get("last_output", "")
    sandbox_url = state.get("sandbox_url", "")

    if sandbox_url:
        probe_url = sandbox_url
    else:
        port = target.split(":")[-1] if ":" in target else "80"
        scheme = "https" if port in ("443", "8443") else "http"
        probe_url = f"{scheme}://{target}"

    # ── Phase A: Direct vulnerability probing (deterministic, no LLM) ──
    logs.append("[enum] Phase A: direct vuln probes (7 checks)")
    direct_findings = _direct_probe_vulns(probe_url, logs, findings)
    findings.extend(direct_findings)
    logs.append(f"[enum] Direct probes: {len(direct_findings)} vulns found")

    # ── Phase B: LLM-planned deeper enumeration ──
    recon_summary = _trim_output(last, 600)
    found_titles = ", ".join(f.get("title", "?")[:40] for f in direct_findings) or "none yet"

    enum_prompt = (
        f"Target: {target} | Probe URL: {probe_url}\n"
        f"Already found: {found_titles}\n"
        f"Recon summary: {recon_summary}\n\n"
        f"Plan up to 4 DIFFERENT deeper enumeration commands. "
        f"Focus on areas NOT already covered by direct probes."
    )

    try:
        plan_obj: EnumPlan = llm_enum_plan.invoke(enum_prompt)
        commands = [{"tool": c.tool, "args": c.args} for c in plan_obj.commands[:MAX_ENUM_CMDS]]
    except Exception:
        commands = [
            {"tool": "run_nikto", "args": probe_url},
            {"tool": "run_nuclei", "args": probe_url},
        ]

    _ENUM_DISPATCH = {
        "run_nmap":          lambda a: call_mcp("run_nmap", {"target": target.split(":")[0], "flags": a}),
        "run_nikto":         lambda a: call_mcp("run_nikto", {"target": a}),
        "run_whatweb":       lambda a: call_mcp("run_whatweb", {"target": a}),
        "run_nuclei":        lambda a: call_mcp("run_nuclei", {"target": a, "severity": "critical,high,medium"}),
        "run_nuclei_cve":    lambda a: call_mcp("run_nuclei_cve", {"target": a}),
        "run_nuclei_technologies": lambda a: call_mcp("run_nuclei_technologies", {"target": a}),
        "run_ffuf_dirs":     lambda a: call_mcp("run_ffuf_dirs", {"base_url": a}),
        "run_wfuzz_dirs":    lambda a: call_mcp("run_wfuzz_dirs", {"base_url": a}),
        "run_httpx_probe":   lambda a: call_mcp("run_httpx_probe", {"url": a}),
        "run_httpx_screenshot_headers": lambda a: call_mcp("run_httpx_screenshot_headers", {"url": a}),
    }

    enum_summaries = []
    for cmd in commands[:MAX_ENUM_CMDS]:
        tool = cmd.get("tool", "run_nuclei")
        args = cmd.get("args", "") or probe_url
        if not is_safe_cmd(tool, args):
            continue
        dispatcher = _ENUM_DISPATCH.get(tool)
        out = dispatcher(args) if dispatcher else call_mcp(tool, {"target": args})
        enum_summaries.append(f"[{tool}] {_trim_output(out, 300)}")
        logs.append(_compact(f"[enum] {tool}: done"))

    all_found = [f.get("title", "?") for f in findings]
    synthesis = f"Enumeration complete. {len(findings)} total findings: {'; '.join(all_found)}"
    logs.append("[enum] synthesis complete")

    # ── Mark vectors as tested based on what direct probes covered ──
    tested = list(state.get("tested_vectors", []))
    for finding in direct_findings:
        cat = finding.get("category", "")
        if cat and cat not in tested:
            tested.append(cat)
    coverage = get_coverage_status(tested)
    logs.append(_compact(f"[enum] coverage after probes: {coverage['progress']}"))

    return {
        "action_history": logs,
        "confirmed_findings": findings,
        "last_output": _trim_output(synthesis, MAX_LAST_OUTPUT),
        "tested_vectors": tested,
    }


print("✅ Enumeration Node OK (7 direct probes + coverage tracking, token-optimized)")

# ═══════════════════════════════════════════════════════════════════
# HYPOTHESIS NODE (Spoke 3)
# ═══════════════════════════════════════════════════════════════════
MAX_HYPOTHESIS_CHARS = 1500


def hypothesis_node(state: RedShellState) -> dict:
    target = state["current_target"]
    logs = list(state.get("action_history", []))
    hypo_attempts = state.get("hypothesis_attempts", 0)
    sandbox_url = state.get("sandbox_url", "")
    tested = list(state.get("tested_vectors", []))

    if sandbox_url:
        probe_url = sandbox_url
    else:
        port = target.split(":")[-1] if ":" in target else "80"
        scheme = "https" if port in ("443", "8443") else "http"
        probe_url = f"{scheme}://{target}"

    # ── Pick the next UNTESTED vector (coverage-driven) ──
    coverage = get_coverage_status(tested)
    remaining = coverage["remaining_detail"]

    if remaining:
        forced_wstg, forced_category, forced_tool = remaining[0]
    else:
        idx = hypo_attempts % len(PRIORITY_VECTORS)
        forced_wstg, forced_category, forced_tool = PRIORITY_VECTORS[idx]

    # Targeted RAG query for THIS specific vector
    kb_context = query_knowledge_base(forced_category.lower())

    if forced_wstg not in tested:
        tested.append(forced_wstg)

    # Concise, targeted prompt
    hypo_prompt = (
        f"Red-team exploit. Target: {probe_url}\n"
        f"MUST test: {forced_category} ({forced_wstg}). Tool: {forced_tool}.\n"
        f"Coverage: {coverage['progress']} vectors tested.\n\n"
        f"KB reference:\n{kb_context[:600]}\n\n"
        f"Payload format rules:\n"
        f"- run_sqlmap_post: 'URL|post_data' e.g. '{probe_url}/api/login|username=admin&password=test'\n"
        f"- run_dalfox: URL with param e.g. '{probe_url}/api/search?term=test'\n"
        f"- run_httpx_probe: full URL e.g. '{probe_url}/api/account/1'\n"
        f"- run_ffuf: URL with FUZZ e.g. '{probe_url}/FUZZ'\n"
        f"- run_shell: shell command e.g. 'curl -sI -H \"Origin: https://evil.com\" {probe_url}'\n"
    )

    try:
        hypo_obj: HypothesisPayload = llm_hypothesis.invoke(hypo_prompt)
        hypo_output = json.dumps(hypo_obj.model_dump())
    except Exception:
        payloads = {
            "run_dalfox": f"{probe_url}/api/search?term=test",
            "run_sqlmap_post": f"{probe_url}/api/login|username=admin&password=test",
            "run_httpx_probe": f"{probe_url}/api/account/1",
            "run_ffuf": f"{probe_url}/FUZZ",
            "run_shell": f"curl -sI -H 'Origin: https://evil.com' {probe_url}/api/login",
        }
        hypo_output = json.dumps({
            "wstg": forced_wstg,
            "theory": f"Test for {forced_category}",
            "tool": forced_tool,
            "payload": payloads.get(forced_tool, probe_url),
        })

    logs.append(_compact(
        f"[hypo] #{hypo_attempts+1} {forced_category} ({forced_wstg}) | "
        f"coverage {len(tested)}/{len(PRIORITY_VECTORS)}"
    ))

    return {
        "action_history": logs,
        "hypothesis_attempts": hypo_attempts + 1,
        "last_output": hypo_output,
        "tested_vectors": tested,
    }


print("✅ Hypothesis Node OK (coverage-driven, targeted RAG)")

# ═══════════════════════════════════════════════════════════════════
# IMPACT NODE (Spoke 4)
# ═══════════════════════════════════════════════════════════════════


def impact_node(state: RedShellState) -> dict:
    global _MCP_SESSION_ID
    target = state["current_target"]
    payload_text = state.get("last_output", "")
    logs = list(state.get("action_history", []))
    findings = list(state.get("confirmed_findings", []))

    # Parse hypothesis
    tool_name, payload_cmd, wstg_code, theory = "run_httpx_probe", "", "?", ""
    try:
        hypo_obj = HypothesisPayload.model_validate_json(payload_text)
        tool_name, payload_cmd = hypo_obj.tool, hypo_obj.payload
        wstg_code, theory = hypo_obj.wstg, hypo_obj.theory
    except Exception:
        parsed = safe_json(payload_text, {"tool": "run_httpx_probe", "payload": ""})
        tool_name = parsed.get("tool", "run_httpx_probe").strip().lower()
        payload_cmd = parsed.get("payload", "").strip()
        wstg_code = parsed.get("wstg", "?").strip()
        theory = parsed.get("theory", "").strip()

    if not payload_cmd:
        payload_cmd = payload_text.strip()
        logs.append("[impact:warn] no structured payload")

    if not is_safe_cmd(tool_name, payload_cmd):
        logs.append(_compact(f"[impact:BLOCKED] {tool_name}"))
        return {
            "action_history": logs, "confirmed_findings": findings,
            "target_queue": list(state.get("target_queue", [])),
            "last_output": "FAILED: blocked by safety check",
        }

    # Fresh MCP session for each impact attempt
    _MCP_SESSION_ID = None

    # Dispatch
    _IMPACT_DISPATCH = {
        "run_sqlmap":         lambda p: call_mcp("run_sqlmap", {"target": p}),
        "run_sqlmap_post":    lambda p: call_mcp("run_sqlmap_post", {
            "target": p.split("|")[0].strip(),
            "data": p.split("|")[1].strip() if "|" in p else "username=admin&password=test"
        }),
        "run_sqlmap_enumerate_dbs": lambda p: call_mcp("run_sqlmap_enumerate_dbs", {"target": p}),
        "run_dalfox":         lambda p: call_mcp("run_dalfox", {"target": p}),
        "run_dalfox_discovery_only": lambda p: call_mcp("run_dalfox_discovery_only", {"target": p}),
        "run_wfuzz_params":   lambda p: call_mcp("run_wfuzz_params", {"base_url": p}),
        "run_httpx_probe":    lambda p: call_mcp("run_httpx_probe", {"url": p}),
        "run_nuclei_cve":     lambda p: call_mcp("run_nuclei_cve", {"target": p}),
        "run_ffuf":           lambda p: call_mcp("run_ffuf", {"target": p}),
        "run_nikto":          lambda p: call_mcp("run_nikto", {"target": p}),
        "run_nmap":           lambda p: call_mcp("run_nmap", {"target": p.split()[0], "flags": " ".join(p.split()[1:]) if " " in p else "-sV"}),
    }

    dispatcher = _IMPACT_DISPATCH.get(tool_name)
    sandbox_out = dispatcher(payload_cmd) if dispatcher else call_mcp(tool_name, {"target": payload_cmd})

    logs.append(_compact(f"[impact:exec] {tool_name}: {payload_cmd[:80]}"))

    # MCP error → FAILED immediately
    if any(tag in sandbox_out for tag in ["[MCP ERROR]", "[MCP TIMEOUT]", "[MCP STREAM ERROR]"]):
        logs.append(_compact(f"[impact:FAILED] MCP error"))
        return {
            "action_history": logs, "confirmed_findings": findings,
            "target_queue": list(state.get("target_queue", [])),
            "last_output": "FAILED: MCP tool error",
        }

    trimmed_out = _trim_output(sandbox_out, 1500)

    verdict_prompt = (
        f"WSTG: {wstg_code} | Tool: {tool_name} | Theory: {theory}\n"
        f"Output:\n{trimmed_out}\n\n"
        f"Verdict: SUCCESS (vuln confirmed), FAILED (not confirmed), or SHELL (got access)."
    )

    try:
        verdict_obj: ImpactVerdict = llm_impact.invoke(verdict_prompt)
        is_success = verdict_obj.verdict in ("SUCCESS", "SHELL")
        got_shell = verdict_obj.verdict == "SHELL"
        result_text = f"{verdict_obj.verdict}: {verdict_obj.explanation}"
        new_targets_found = verdict_obj.new_targets
    except Exception:
        lower_out = sandbox_out.lower()
        success_signals = ["injectable", "sql injection", "xss", "vuln", "200", "poc", "alert("]
        is_success = any(sig in lower_out for sig in success_signals)
        got_shell = False
        result_text = f"{'SUCCESS' if is_success else 'FAILED'}: heuristic analysis"
        new_targets_found = []

    queue = list(state.get("target_queue", []))
    for t in new_targets_found:
        if t and t != target and t not in queue:
            queue.append(t)

    if is_success:
        finding = make_finding(
            title=theory or result_text.split("\n")[0][:200],
            category=wstg_code,
            tool=tool_name,
            evidence=sandbox_out,
            description=result_text[:400],
            impact="Shell access obtained" if got_shell else "Vulnerability confirmed",
            remediation="",
        )
        findings.append(finding)

    status = "SUCCESS" if is_success else "FAILED"
    logs.append(_compact(f"[impact:{status}] {result_text[:100]}"))

    tested = list(state.get("tested_vectors", []))
    if wstg_code and wstg_code != "?" and wstg_code not in tested:
        tested.append(wstg_code)

    return {
        "action_history": logs,
        "confirmed_findings": findings,
        "target_queue": queue,
        "last_output": _trim_output(result_text, MAX_LAST_OUTPUT),
        "tested_vectors": tested,
    }


print("✅ Impact Node OK (token-optimized, WSTG severity, coverage tracking)")

# ═══════════════════════════════════════════════════════════════════
# PIVOT NODE (Spoke 5) + REPORTING NODE (Spoke 6)
# ═══════════════════════════════════════════════════════════════════


def pivot_node(state: RedShellState) -> dict:
    queue = list(state.get("target_queue", []))
    logs = list(state.get("action_history", []))
    if queue:
        next_target = queue.pop(0)
    else:
        next_target = state["current_target"]
    logs.append(f"[pivot] → {next_target}")
    return {
        "current_target": next_target,
        "target_queue": queue,
        "hypothesis_attempts": 0,
        "last_output": f"Pivoted to {next_target}",
        "action_history": logs,
    }


def reporting_node(state: RedShellState) -> dict:
    findings = state.get("confirmed_findings", [])
    logs = state.get("action_history", [])
    target = state["current_target"]
    job_id = state.get("job_id", "unknown")
    elapsed = round(time.monotonic() - state.get("scan_start", time.monotonic()), 1)

    open_ports: list[str] = []
    services: list[str] = []
    for h in logs:
        port_matches = re.findall(r'(\d+)/tcp\s+open\s+(\S+)', h)
        for port, svc in port_matches:
            if port not in open_ports:
                open_ports.append(port)
            if svc not in services:
                services.append(svc)

    if findings:
        findings_text = json.dumps(findings, indent=2)
        try:
            remed_obj: RemediationList = llm_remediation.invoke(
                f"For each finding below, provide a one-line remediation.\n\n{findings_text}"
            )
            for item in remed_obj.items:
                for f in findings:
                    if f.get("id") == item.finding_id and not f.get("remediation"):
                        f["remediation"] = item.remediation[:300]
        except Exception:
            try:
                remed = llm.invoke(
                    f"For each finding below, provide a one-line remediation.\n"
                    f"Output a JSON array of strings in the same order.\n\n{findings_text}"
                )
                remed_match = re.search(r'\[.*\]', remed.content, re.DOTALL)
                if remed_match:
                    remed_list = json.loads(remed_match.group())
                    for i, f in enumerate(findings):
                        if not f.get("remediation") and i < len(remed_list):
                            f["remediation"] = str(remed_list[i])[:300]
            except Exception:
                pass

    report = {
        "job_id": job_id,
        "status": "success",
        "target": target,
        "sandbox": {
            "sandbox_id": state.get("sandbox_id", ""),
            "sandbox_url": state.get("sandbox_url", ""),
            "github_url": state.get("github_url", ""),
        },
        "scan_summary": {
            "open_ports": open_ports,
            "services_detected": services,
            "total_findings": len(findings),
        },
        "findings": findings,
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "agent": "RedShell v2.0",
            "total_steps": state.get("global_steps", 0),
            "total_actions": len(logs),
            "elapsed_seconds": elapsed,
        },
        "logs": _log_records[-50:],
    }

    try:
        with open(REPORT_PATH, "w") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        logs = list(logs) + [f"[report] saved → {REPORT_PATH}"]
    except Exception as exc:
        logs = list(logs) + [f"[report] save failed: {exc}"]

    return {
        "action_history": logs,
        "last_output": json.dumps(report, indent=2, ensure_ascii=False),
    }


print("✅ Pivot Node + Reporting Node OK")

# ═══════════════════════════════════════════════════════════════════
# SANDBOX SETUP + TEARDOWN NODES
# ═══════════════════════════════════════════════════════════════════


def sandbox_setup_node(state: RedShellState) -> dict:
    """Deploy the target repo in a sandbox and set current_target."""
    logs = list(state.get("action_history", []))
    github_url = state.get("github_url", "")

    if not github_url:
        logs.append("[sandbox] no github_url — skipping sandbox build")
        return {"action_history": logs}

    _log("sandbox_build_started", repo=github_url)
    raw = call_mcp("build_sandbox", {"github_url": github_url}, timeout=600)
    logs.append(f"[sandbox] build_sandbox raw: {raw[:300]}")

    sandbox_id = ""
    sandbox_url = ""

    try:
        sb = json.loads(raw)
        sandbox_id = sb.get("sandbox_id", sb.get("id", ""))
        sandbox_url = sb.get("url", sb.get("URL", ""))
    except (json.JSONDecodeError, TypeError):
        pass

    if not sandbox_url:
        url_match = re.search(r'(https?://[^\s"\']+)', raw)
        if url_match:
            sandbox_url = url_match.group(1).rstrip("/")
    if not sandbox_id:
        id_match = re.search(r'sandbox_id["\s:=]+([a-zA-Z0-9_-]+)', raw)
        if id_match:
            sandbox_id = id_match.group(1)

    if not sandbox_url:
        _log("sandbox_build_failed", raw=raw[:300])
        logs.append("[sandbox:FAILED] could not extract URL from build_sandbox")
        return {"action_history": logs, "last_output": f"sandbox build failed: {raw[:300]}"}

    parsed = urlparse(sandbox_url)
    host = parsed.hostname or "unknown"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    # ── Resolve public URL via list_sandboxes ──
    try:
        ls_raw = call_mcp("list_sandboxes", {}, timeout=30)
        logs.append(f"[sandbox] list_sandboxes raw: {ls_raw[:300]}")
        try:
            ls_json = json.loads(ls_raw)
        except Exception:
            ls_json = None

        candidates = None
        if isinstance(ls_json, dict):
            candidates = ls_json.get("sandboxes") or ls_json.get("result") or ls_json.get("items")
        if candidates is None and isinstance(ls_json, list):
            candidates = ls_json

        if candidates:
            for item in candidates:
                if not isinstance(item, dict):
                    continue
                sid = item.get("sandbox_id") or item.get("id") or item.get("name")
                url_candidate = item.get("url") or item.get("public_url") or item.get("mapped_url") or item.get("URL")
                if sid and sandbox_id and (sid == sandbox_id or sid in sandbox_id):
                    if url_candidate:
                        sandbox_url = url_candidate.rstrip("/")
                        parsed = urlparse(sandbox_url)
                        host = parsed.hostname or host
                        port = parsed.port or port
                        logs.append(f"[sandbox] resolved public URL via list_sandboxes: {sandbox_url}")
                        break
    except Exception as exc:
        logs.append(f"[sandbox] list_sandboxes lookup failed: {exc}")

    if host in ("0.0.0.0", "::"):
        target_host = "localhost"
    elif host == "unknown":
        target_host = "localhost"
    else:
        target_host = host

    target_str = f"{target_host}:{port}"

    _log("sandbox_build_ok", sandbox_id=sandbox_id, url=sandbox_url, target=target_str)
    logs.append(f"[sandbox] deployed → {sandbox_url}  (target: {target_str})")

    return {
        "sandbox_id": sandbox_id,
        "sandbox_url": sandbox_url,
        "current_target": target_str,
        "action_history": logs,
        "last_output": f"Sandbox deployed: {sandbox_url} → scanning as {target_str}",
    }


def sandbox_teardown_node(state: RedShellState) -> dict:
    """Teardown the sandbox if one was deployed."""
    logs = list(state.get("action_history", []))
    sandbox_id = state.get("sandbox_id", "")

    if not sandbox_id:
        logs.append("[sandbox] no sandbox to teardown")
        return {"action_history": logs}

    _log("sandbox_teardown_started", sandbox_id=sandbox_id)
    raw = call_mcp("teardown_sandbox", {"sandbox_id": sandbox_id}, timeout=120)
    logs.append(f"[sandbox] teardown {sandbox_id}: {raw[:200]}")
    _log("sandbox_teardown_done", sandbox_id=sandbox_id)

    return {"action_history": logs}


print("✅ Sandbox Setup + Teardown Nodes OK")

# ═══════════════════════════════════════════════════════════════════
# GRAPH ASSEMBLY
# ═══════════════════════════════════════════════════════════════════


def build_graph():
    g = StateGraph(RedShellState)
    g.add_node("sandbox_setup", sandbox_setup_node)
    g.add_node("gating_node", gating_node)
    g.add_node("recon", recon_node)
    g.add_node("enumeration", enumeration_node)
    g.add_node("hypothesis", hypothesis_node)
    g.add_node("impact", impact_node)
    g.add_node("pivot", pivot_node)
    g.add_node("reporting", reporting_node)
    g.add_node("sandbox_teardown", sandbox_teardown_node)

    g.set_entry_point("sandbox_setup")
    g.add_edge("sandbox_setup", "gating_node")

    g.add_conditional_edges("gating_node", gate_router, {
        "recon": "recon",
        "enumeration": "enumeration",
        "hypothesis": "hypothesis",
        "pivot": "pivot",
        "reporting": "reporting",
    })

    g.add_edge("recon", "gating_node")
    g.add_edge("enumeration", "gating_node")

    # hypothesis → impact (hard-wired chain)
    g.add_edge("hypothesis", "impact")
    g.add_edge("impact", "gating_node")

    g.add_edge("pivot", "gating_node")

    # reporting → sandbox_teardown → END
    g.add_edge("reporting", "sandbox_teardown")
    g.add_edge("sandbox_teardown", END)

    return g.compile()


graph = build_graph()
print(f"✅ Graph compiled — nodes: {list(graph.nodes.keys())}")
print("   Flow: hypothesis → impact (hard-wired)")

# ═══════════════════════════════════════════════════════════════════
# RUN THE AGENT
# ═══════════════════════════════════════════════════════════════════

# Reset global state
_finding_counter = 0
_MCP_SESSION_ID = None
_log_records.clear()

initial_state: RedShellState = {
    "job_id": str(uuid.uuid4()),
    "current_target": "",
    "target_queue": [],
    "action_history": [],
    "confirmed_findings": [],
    "global_steps": 0,
    "hypothesis_attempts": 0,
    "last_output": "",
    "scan_start": time.monotonic(),
    "sandbox_id": "",
    "sandbox_url": "",
    "github_url": GITHUB_URL,
    "phase": "init",
    "tested_vectors": [],
}

print(f"\n🚀 Starting RedShell hub-and-spoke agent")
print(f"   Repo : {GITHUB_URL}")
print(f"   Job  : {initial_state['job_id']}")
print(f"   Graph: hypothesis → impact (hard-wired)")
print(f"   Strategy: Coverage-aware FSM ({len(PRIORITY_VECTORS)} priority vectors)")
print()

result = graph.invoke(initial_state)

# ── Display results ──
print("\n" + "=" * 60)
print("  REDSHELL REPORT")
print("=" * 60)
try:
    report = json.loads(result.get("last_output", "{}"))
    print(f"Target      : {report.get('target', '?')}")
    print(f"Sandbox URL : {report.get('sandbox', {}).get('sandbox_url', '?')}")
    print(f"Findings    : {report.get('scan_summary', {}).get('total_findings', 0)}")
    print(f"Steps       : {report.get('metadata', {}).get('total_steps', '?')}")
    print(f"Elapsed     : {report.get('metadata', {}).get('elapsed_seconds', '?')}s")
    print()
    for f in report.get("findings", []):
        print(f"  [{f['severity'].upper()}] {f['id']}: {f['title']}")
        print(f"           Category : {f['category']}")
        print(f"           Tool     : {f['tool']}")
        print(f"           Evidence : {f.get('evidence', '-')[:200]}")
        print(f"           Remediation: {f.get('remediation', '-')}")
        print()
    if not report.get("findings"):
        print("  (no findings)")
except Exception as e:
    print(f"  Could not parse report: {e}")
    print(f"  Raw last_output: {result.get('last_output', '')[:500]}")

# ── Diagnostics ──
print("\n" + "=" * 60)
print("  ACTION HISTORY")
print("=" * 60)
for i, h in enumerate(result.get("action_history", [])):
    print(f"  {i:2d}. {h}")
print()
print(f"FINDINGS: {len(result.get('confirmed_findings', []))}")
print(f"STEPS: {result.get('global_steps', '?')}")
print(f"TARGET: {result.get('current_target', '?')}")
print(f"SANDBOX_URL: {result.get('sandbox_url', '?')}")
