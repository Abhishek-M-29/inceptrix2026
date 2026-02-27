import os
import socket
import subprocess
from fastmcp import FastMCP

mcp = FastMCP("Inceptrix-Tools")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(cmd: list, timeout: int = 300) -> str:
    """Run a command and return combined stdout + stderr."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout
        if result.stderr:
            output += "\n[stderr]\n" + result.stderr
        return output or "(no output)"
    except subprocess.TimeoutExpired:
        return f"[ERROR] Command timed out after {timeout}s: {' '.join(cmd)}"
    except FileNotFoundError:
        return f"[ERROR] Tool not found: {cmd[0]}"
    except Exception as e:
        return f"[ERROR] {e}"


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool
def run_nmap(target: str, flags: str = "-sV") -> str:
    """
    Run nmap against a host/IP.
    target : hostname or IP (e.g. 'example.com' or '10.0.0.1')
    flags  : nmap flags string (default '-sV'; e.g. '-sV -sC -p 80,443')
    """
    return _run(["nmap"] + flags.split() + [target], timeout=300)


@mcp.tool
def run_nikto(target: str, extra_flags: str = "") -> str:
    """
    Run Nikto web-server vulnerability scanner.
    target      : full URL (e.g. 'http://example.com')
    extra_flags : additional nikto flags (e.g. '-Tuning 9')
    """
    cmd = ["nikto", "-host", target]
    if extra_flags:
        cmd += extra_flags.split()
    return _run(cmd, timeout=300)


@mcp.tool
def run_whatweb(target: str, aggression: int = 1) -> str:
    """
    Fingerprint a web application with WhatWeb.
    target     : URL (e.g. 'https://example.com')
    aggression : 1 (passive) to 4 (aggressive) — default 1
    """
    return _run(["whatweb", f"--aggression={aggression}", target], timeout=120)


@mcp.tool
def run_sqlmap(target: str, extra_flags: str = "--batch") -> str:
    """
    Run sqlmap SQL injection scanner.
    target      : URL with parameter (e.g. 'http://site.com/page?id=1')
    extra_flags : sqlmap flags (default '--batch'; e.g. '--dbs --batch --level=3')
    """
    return _run(["sqlmap", "-u", target] + extra_flags.split(), timeout=600)


@mcp.tool
def run_wfuzz(
    target: str,
    wordlist: str = "/usr/share/wordlists/dirb/common.txt",
    extra_flags: str = "--hc 404",
) -> str:
    """
    Fuzz a URL with wfuzz — use the literal string FUZZ in the target URL.
    target      : URL containing FUZZ placeholder (e.g. 'http://site.com/FUZZ')
    wordlist    : path to wordlist file
    extra_flags : wfuzz flags (default '--hc 404')
    """
    cmd = ["wfuzz", "-w", wordlist] + extra_flags.split() + [target]
    return _run(cmd, timeout=300)


@mcp.tool
def run_ffuf(
    target: str,
    wordlist: str = "/usr/share/wordlists/dirb/common.txt",
    extra_flags: str = "-mc 200,301,302,403",
) -> str:
    """
    Directory/parameter fuzz with ffuf — use FUZZ in the target URL.
    target      : URL containing FUZZ placeholder (e.g. 'http://site.com/FUZZ')
    wordlist    : path to wordlist file
    extra_flags : ffuf flags (default '-mc 200,301,302,403')
    """
    cmd = ["ffuf", "-u", target, "-w", wordlist] + extra_flags.split()
    return _run(cmd, timeout=300)


@mcp.tool
def run_nuclei(
    target: str,
    severity: str = "critical,high,medium",
    tags: str = "",
) -> str:
    """
    Run Nuclei template-based vulnerability scanner.
    target   : URL (e.g. 'https://example.com')
    severity : comma-separated severities (default 'critical,high,medium')
    tags     : comma-separated template tags to filter (e.g. 'cve,rce,lfi')
    """
    cmd = ["nuclei", "-u", target, "-severity", severity, "-no-color"]
    if tags:
        cmd += ["-tags", tags]
    return _run(cmd, timeout=600)


@mcp.tool
def run_httpx(
    targets: str,
    extra_flags: str = "-status-code -title -tech-detect -follow-redirects",
) -> str:
    """
    Probe HTTP services with httpx.
    targets     : space-separated list of hosts or URLs
    extra_flags : httpx flags (default includes status-code, title, tech-detect)
    """
    # httpx reads from stdin or -l file; use -u for a single target
    host_list = targets.split()
    if len(host_list) == 1:
        cmd = ["httpx", "-u", host_list[0]] + extra_flags.split()
    else:
        # write to a temp file and use -l
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("\n".join(host_list))
            tmp = f.name
        cmd = ["httpx", "-l", tmp] + extra_flags.split()
    return _run(cmd, timeout=180)


@mcp.tool
def run_dalfox(target: str, extra_flags: str = "") -> str:
    """
    Run Dalfox XSS scanner against a URL.
    target      : URL (e.g. 'http://site.com/search?q=test')
    extra_flags : dalfox flags (e.g. '--silence --only-discovery')
    """
    cmd = ["dalfox", "url", target]
    if extra_flags:
        cmd += extra_flags.split()
    return _run(cmd, timeout=300)


@mcp.tool
def run_jwt_tool(token: str, mode: str = "-t") -> str:
    """
    Analyse or attack a JWT token with jwt_tool.
    token : the raw JWT string
    mode  : jwt_tool mode flag (default '-t' for tamper/test; use '-d' to decode)
    """
    cmd = ["python3", "/opt/jwt_tool/jwt_tool.py"] + mode.split() + [token]
    return _run(cmd, timeout=60)


# ---------------------------------------------------------------------------
# Network helpers
# ---------------------------------------------------------------------------

def get_network_ip() -> str:
    """Return the machine's outbound network IP address."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "0.0.0.0"


def find_free_port(start: int = 8090) -> int:
    """Find the first available TCP port starting from `start`."""
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("0.0.0.0", port)) != 0:
                return port
    raise RuntimeError("No free port found in range 8090-8189")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("MCP_PORT", find_free_port(8090)))
    ip = get_network_ip()

    banner = f"""
{'=' * 58}
  MCP Server  :  Inceptrix-Tools
  Transport   :  HTTP (SSE-compatible)
  Network URL :  http://{ip}:{port}/mcp
  Local URL   :  http://127.0.0.1:{port}/mcp
  Tools       :  nmap · nikto · whatweb · sqlmap
                 wfuzz · ffuf · nuclei · httpx
                 dalfox · jwt_tool
{'=' * 58}"""
    print(banner, flush=True)

    mcp.run(transport="http", host="0.0.0.0", port=port)
