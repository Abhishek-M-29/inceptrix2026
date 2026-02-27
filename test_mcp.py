#!/usr/bin/env python3
"""
test_mcp.py — External integration tests for the Inceptrix MCP server.

Verifies from *outside* the Docker container that:
  1. REST API  (/health, /tools)  is reachable and sane
  2. MCP HTTP endpoint is reachable and responds to an initialize request
  3. Every tool binary is present on PATH inside the container (via run_shell)
  4. End-to-end tool invocation works (run_shell + run_nmap)

Usage:
  python test_mcp.py                        # defaults: API=8091, MCP=8090
  python test_mcp.py --api-port 8091 --mcp-port 8090
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────
EXPECTED_TOOLS = [
    "nmap", "nikto", "whatweb", "sqlmap", "wfuzz",
    "ffuf", "nuclei", "httpx", "dalfox", "jwt_tool", "shell",
]

TOOL_BINARIES = {
    "nmap":          "nmap",
    "nikto":         "nikto",
    "whatweb":       "whatweb",
    "sqlmap":        "sqlmap",
    "wfuzz":         "wfuzz",
    "ffuf":          "ffuf",
    "nuclei":        "nuclei",
    "httpx-toolkit": "httpx-toolkit",   # Go binary name, distinct from Python httpx
    "dalfox":        "dalfox",
    "jwt_tool":      "jwt_tool",
    "node":          "node",
    "npm":           "npm",
}

# ─────────────────────────────────────────────────────────────────────────────
# Colour helpers (no external deps)
# ─────────────────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg: str)   -> None: print(f"  {GREEN}[PASS]{RESET}  {msg}")
def fail(msg: str) -> None: print(f"  {RED}[FAIL]{RESET}  {msg}")
def warn(msg: str) -> None: print(f"  {YELLOW}[WARN]{RESET}  {msg}")
def step(msg: str) -> None: print(f"\n{CYAN}{BOLD}▸ {msg}{RESET}")

PASSES = 0
FAILS  = 0

def record(passed: bool, msg: str) -> bool:
    global PASSES, FAILS
    if passed:
        ok(msg);   PASSES += 1
    else:
        fail(msg); FAILS  += 1
    return passed


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helpers
# ─────────────────────────────────────────────────────────────────────────────
def get(url: str, timeout: int = 10) -> tuple[int, Any]:
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)}


def post(url: str, body: dict, timeout: int = 30) -> tuple[int, Any]:
    try:
        data = json.dumps(body).encode()
        req  = urllib.request.Request(url, data=data,
                                      headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# Test suites
# ─────────────────────────────────────────────────────────────────────────────
def test_rest_health(api: str) -> None:
    step("REST API — /health")
    code, body = get(f"{api}/health")
    record(code == 200, f"GET /health → {code}")
    if code == 200:
        record(body.get("status") == "ok", f"status field = '{body.get('status')}'")
        listed = set(body.get("tools", []))
        record(bool(listed), f"tools list has {len(listed)} entries")


def test_rest_tools_list(api: str) -> None:
    step("REST API — /tools")
    code, body = get(f"{api}/tools")
    record(code == 200, f"GET /tools → {code}")
    if code != 200:
        return

    registered = {t["name"] for t in body.get("tools", [])}
    for name in EXPECTED_TOOLS:
        record(name in registered, f"tool '{name}' in registry")


def test_mcp_endpoint(mcp: str) -> None:
    step("MCP HTTP endpoint — initialize handshake")
    # FastMCP Streamable-HTTP: send a JSON-RPC initialize request
    init_req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "inceptrix-test", "version": "1.0"},
        },
    }
    code, body = post(f"{mcp}/", init_req, timeout=10)
    # Accept 200 or any response that contains a jsonrpc field
    passed = code == 200 or (isinstance(body, dict) and "jsonrpc" in body)
    record(passed, f"POST / (MCP initialize) → HTTP {code}")
    if isinstance(body, dict) and "result" in body:
        proto = body["result"].get("protocolVersion", "?")
        server = body["result"].get("serverInfo", {}).get("name", "?")
        ok(f"Server: {server}, protocol: {proto}")


def test_shell_execution(api: str) -> None:
    step("Shell execution — run_shell end-to-end")
    code, body = post(f"{api}/tools/shell", {
        "command": "echo 'inceptrix-shell-ok'",
        "timeout": 10,
    })
    record(code == 200, f"POST /tools/shell → {code}")
    if code == 200:
        output = body.get("output", "")
        record("inceptrix-shell-ok" in output,
               f"output contains expected string (got: {output[:80].strip()!r})")


def test_tool_binaries(api: str) -> None:
    step("Tool binaries — verify every binary is on PATH inside container")
    bins = " ".join(TOOL_BINARIES.values())
    code, body = post(f"{api}/tools/shell", {
        "command": f"which {bins} 2>&1",
        "timeout": 15,
    })
    if not record(code == 200, f"which check HTTP → {code}"):
        return
    output = body.get("output", "")
    for friendly, binary in TOOL_BINARIES.items():
        found = f"/{binary}" in output or f"/usr" in output   # `which` prints full path
        # More precise check: look for the binary name appearing after a /
        import re
        found = bool(re.search(rf"/[^\s]*{re.escape(binary)}", output))
        record(found, f"binary '{binary}' on PATH")


def test_nmap_e2e(api: str) -> None:
    step("End-to-end tool call — nmap on 127.0.0.1 (fast scan)")
    code, body = post(f"{api}/tools/nmap", {
        "target": "127.0.0.1",
        "flags": "-T4 -F --open",
        "timeout": 30,
    })
    record(code == 200, f"POST /tools/nmap → {code}")
    if code == 200:
        output = body.get("output", "")
        record("Nmap scan report" in output or "nmap" in output.lower(),
               f"nmap output looks valid (first 80 chars: {output[:80].strip()!r})")
        status = body.get("status", "?")
        record(status in ("ok", "timeout"),
               f"status is ok/timeout: got '{status}'")


def test_dalfox_discovery(api: str) -> None:
    step("End-to-end tool call — dalfox discovery on httpbin")
    code, body = post(f"{api}/tools/dalfox", {
        "target":      "http://127.0.0.1:1/test?q=test",
        "extra_flags": "--only-discovery --silence",
        "timeout":     15,
    })
    # We just want the HTTP call to succeed and not crash — the target won't respond
    record(code == 200, f"POST /tools/dalfox → {code} (connection refused is fine)")
    if code == 200:
        record(body.get("status") in ("ok", "error", "timeout"),
               f"dalfox status field present: '{body.get('status')}'")


def test_whatweb(api: str) -> None:
    step("End-to-end tool call — whatweb on localhost")
    code, body = post(f"{api}/tools/whatweb", {
        "target":     "http://127.0.0.1",
        "aggression": 1,
        "timeout":    15,
    })
    record(code == 200, f"POST /tools/whatweb → {code}")
    if code == 200:
        record(body.get("status") in ("ok", "error", "timeout"),
               f"whatweb status field: '{body.get('status')}'")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main() -> int:
    p = argparse.ArgumentParser(description="Inceptrix MCP external test suite")
    p.add_argument("--api-port", type=int, default=8091)
    p.add_argument("--mcp-port", type=int, default=8090)
    p.add_argument("--host",     default="localhost")
    args = p.parse_args()

    api = f"http://{args.host}:{args.api_port}"
    mcp = f"http://{args.host}:{args.mcp_port}"

    print(f"\n{BOLD}{'═' * 62}{RESET}")
    print(f"{BOLD}  Inceptrix MCP — External Test Suite{RESET}")
    print(f"  REST API  : {api}")
    print(f"  MCP HTTP  : {mcp}")
    print(f"{BOLD}{'═' * 62}{RESET}")

    # Connectivity pre-check
    step("Connectivity — waiting for API to respond (up to 10s)")
    for _ in range(10):
        code, _ = get(f"{api}/health", timeout=2)
        if code == 200:
            break
        time.sleep(1)
    else:
        fail("API did not respond after 10s — is the container running?")
        return 1

    # Run suites
    test_rest_health(api)
    test_rest_tools_list(api)
    test_mcp_endpoint(mcp)
    test_shell_execution(api)
    test_tool_binaries(api)
    test_nmap_e2e(api)
    test_dalfox_discovery(api)
    test_whatweb(api)

    # Summary
    total = PASSES + FAILS
    colour = GREEN if FAILS == 0 else RED
    print(f"\n{colour}{BOLD}{'═' * 62}{RESET}")
    print(f"{colour}{BOLD}  Results: {PASSES}/{total} passed"
          + (f"  —  {FAILS} FAILED" if FAILS else "  ✓ all good") + f"{RESET}")
    print(f"{colour}{BOLD}{'═' * 62}{RESET}\n")

    return 0 if FAILS == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
