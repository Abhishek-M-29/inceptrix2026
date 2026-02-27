"""
shell.py — Execute arbitrary shell commands inside the Kali Linux environment.

Tools exposed
-------------
run_shell(command, timeout)  — run any bash command and return stdout+stderr
"""

from __future__ import annotations

import logging
import subprocess
import time
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP

log = logging.getLogger("inceptrix.mcp.tools.shell")

META = {
    "name": "shell",
    "description": "Run arbitrary bash commands inside the Kali Linux container",
    "binary": "bash",
    "default_timeout": 60,
}


def register(mcp: "FastMCP") -> None:

    @mcp.tool(name="run_shell", description=(
        "Execute any bash command inside the Kali Linux pentest environment.\n\n"
        "command : shell command string, e.g. 'whoami', 'ls /usr/bin', 'cat /etc/os-release'\n"
        "timeout : max seconds to wait (default 60)\n\n"
        "Returns combined stdout + stderr. Runs as root inside the container.\n"
        "Use this for one-off commands, quick checks, or anything not covered by a dedicated tool."
    ))
    def run_shell(command: str, timeout: int = 60) -> str:
        run_id = uuid.uuid4().hex[:8]
        log.info("run_shell invoked", extra={"run_id": run_id, "command": command[:200]})

        start = time.monotonic()
        try:
            proc = subprocess.run(
                ["bash", "-c", command],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            duration = round(time.monotonic() - start, 2)
            output = proc.stdout + proc.stderr
            status = "ok" if proc.returncode == 0 else f"rc={proc.returncode}"
            log.info(
                "run_shell completed",
                extra={"run_id": run_id, "returncode": proc.returncode, "duration_s": duration},
            )
            header = f"[run_id={run_id}  status={status}  duration={duration}s]\n"
            return header + (output.strip() or "(no output)")

        except subprocess.TimeoutExpired:
            duration = round(time.monotonic() - start, 2)
            log.warning("run_shell timed out", extra={"run_id": run_id, "timeout": timeout})
            return (
                f"[run_id={run_id}  status=TIMEOUT  duration={duration}s]\n"
                f"Command timed out after {timeout}s:\n  {command}"
            )
        except Exception as exc:
            log.exception("run_shell error", extra={"run_id": run_id})
            return f"[run_id={run_id}  status=ERROR]\n{exc}"

    log.debug("shell tools registered")
