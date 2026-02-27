"""
Subprocess execution engine for Inceptrix MCP tools.

Responsibilities
----------------
* Build a fully traceable ``ToolRun`` context for every invocation.
* Stream combined stdout/stderr to the logger at TRACE level in real-time.
* Enforce per-tool timeouts and return a structured ``ToolResult``.
* Never raise — all errors are captured inside ``ToolResult``.
"""

from __future__ import annotations

import json
import logging
import os
import shlex
import subprocess
import threading
import time
import urllib.request
import uuid
from dataclasses import dataclass, field
from typing import List, Optional

from logging_config import TRACE, correlation_id

# ---------------------------------------------------------------------------
# Webhook
# ---------------------------------------------------------------------------

_BACKEND_URL: str | None = os.environ.get("BACKEND_URL")
_WEBHOOK_URL: str | None = (
    _BACKEND_URL.rstrip("/") + "/webhook/scan" if _BACKEND_URL else None
)

log_wh = logging.getLogger("inceptrix.mcp.webhook")


def _fire_webhook(tool_name: str, cmd: List[str], status: str) -> None:
    """POST a webhook event to the backend in a daemon thread (non-blocking)."""
    url = _WEBHOOK_URL
    if not url:
        return

    payload = json.dumps({
        "tool": tool_name,
        "target": cmd[-1] if cmd else "",
        "command_used": shlex.join(cmd),
        "status": status,
    }).encode()

    def _post() -> None:
        try:
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=5)
            log_wh.info(
                "WEBHOOK [%s] → %s  tool=%s  HTTP %s",
                status, url, tool_name, resp.status,
            )
        except Exception as exc:
            log_wh.warning("WEBHOOK [%s] → %s  FAILED: %s", status, url, exc)

    threading.Thread(target=_post, daemon=True, name=f"webhook-{tool_name}-{status}").start()

log = logging.getLogger("inceptrix.mcp.executor")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ToolRun:
    """Immutable description of a single tool invocation."""
    tool_name: str
    cmd: List[str]
    timeout: int
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    started_at: float = field(default_factory=time.monotonic)


@dataclass
class ToolResult:
    """Outcome of a single tool invocation."""
    run_id: str
    tool_name: str
    cmd: List[str]
    returncode: Optional[int]
    stdout: str
    stderr: str
    duration_s: float
    timed_out: bool = False
    error: Optional[str] = None

    # ---------- convenience ----------
    @property
    def success(self) -> bool:
        return self.error is None and not self.timed_out and self.returncode == 0

    @property
    def combined_output(self) -> str:
        """Merge stdout + stderr the same way the old _run() helper did."""
        out = self.stdout.strip()
        err = self.stderr.strip()
        if err:
            out = out + "\n[stderr]\n" + err if out else err
        return out or "(no output)"

    def to_mcp_text(self) -> str:
        """Format for MCP tool return value — always a non-empty string."""
        if self.error:
            return f"[EXECUTOR ERROR] {self.error}"
        if self.timed_out:
            return (
                f"[TIMEOUT] Tool '{self.tool_name}' exceeded {self.duration_s:.0f}s "
                f"and was killed.\n\n{self.combined_output}"
            )
        header = (
            f"# {self.tool_name.upper()} — run_id={self.run_id}  "
            f"rc={self.returncode}  duration={self.duration_s:.2f}s\n"
        )
        return header + self.combined_output


# ---------------------------------------------------------------------------
# Core execution function
# ---------------------------------------------------------------------------

def run_tool(
    tool_name: str,
    cmd: List[str],
    *,
    timeout: int = 300,
    env_override: Optional[dict] = None,
) -> ToolResult:
    """
    Execute *cmd* as a subprocess, stream its output to the logger, and
    return a ``ToolResult``.  Never raises.

    Parameters
    ----------
    tool_name:    Human-readable name used in log records.
    cmd:          Full argument list, e.g. ``["nmap", "-sV", "10.0.0.1"]``.
    timeout:      Seconds before the process is forcibly killed.
    env_override: Extra environment variables merged into the current env.
    """
    run = ToolRun(tool_name=tool_name, cmd=cmd, timeout=timeout)

    # Fire webhook — started
    _fire_webhook(tool_name, cmd, "started")

    # Set correlation ID so every log line from this run is linkable
    token = correlation_id.set(run.run_id)

    env = os.environ.copy()
    if env_override:
        env.update(env_override)

    log.info(
        "Tool started",
        extra={
            "run_id": run.run_id,
            "tool": tool_name,
            "cmd": shlex.join(cmd),
            "timeout": timeout,
        },
    )

    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    returncode: Optional[int] = None
    timed_out = False
    exec_error: Optional[str] = None
    wall_start = time.monotonic()

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

        # ── Stream stdout line-by-line ──────────────────────────────────────
        def _drain_stdout() -> None:
            assert proc.stdout is not None
            for line in proc.stdout:
                line = line.rstrip("\n")
                stdout_lines.append(line)
                log.log(
                    TRACE,
                    "[stdout] %s",
                    line,
                    extra={"run_id": run.run_id, "tool": tool_name},
                )

        t_out = threading.Thread(target=_drain_stdout, daemon=True)
        t_out.start()

        def _drain_stderr() -> None:
            assert proc.stderr is not None
            for line in proc.stderr:
                line = line.rstrip("\n")
                stderr_lines.append(line)
                log.log(
                    TRACE,
                    "[stderr] %s",
                    line,
                    extra={"run_id": run.run_id, "tool": tool_name},
                )

        t_err = threading.Thread(target=_drain_stderr, daemon=True)
        t_err.start()

        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            log.warning(
                "Timeout expired — killing process",
                extra={"run_id": run.run_id, "tool": tool_name, "pid": proc.pid},
            )
            proc.kill()
            proc.wait()

        t_out.join(timeout=5)
        t_err.join(timeout=5)
        returncode = proc.returncode

    except FileNotFoundError:
        exec_error = f"Tool binary not found: {cmd[0]!r}"
        log.error(exec_error, extra={"run_id": run.run_id, "tool": tool_name})
    except PermissionError:
        exec_error = f"Permission denied executing: {cmd[0]!r}"
        log.error(exec_error, extra={"run_id": run.run_id, "tool": tool_name})
    except Exception as exc:
        exec_error = f"Unexpected error: {exc}"
        log.exception(
            "Unexpected executor error",
            extra={"run_id": run.run_id, "tool": tool_name},
        )

    duration = time.monotonic() - wall_start
    correlation_id.reset(token)

    result = ToolResult(
        run_id=run.run_id,
        tool_name=tool_name,
        cmd=cmd,
        returncode=returncode,
        stdout="\n".join(stdout_lines),
        stderr="\n".join(stderr_lines),
        duration_s=round(duration, 3),
        timed_out=timed_out,
        error=exec_error,
    )

    _log_result(result)
    # Fire webhook — ended
    _fire_webhook(tool_name, cmd, "ended")
    return result


# ---------------------------------------------------------------------------
# Result logger
# ---------------------------------------------------------------------------

def _log_result(r: ToolResult) -> None:
    extra = {
        "run_id": r.run_id,
        "tool": r.tool_name,
        "returncode": r.returncode,
        "duration_s": r.duration_s,
        "timed_out": r.timed_out,
        "stdout_lines": r.stdout.count("\n") + 1 if r.stdout else 0,
        "stderr_lines": r.stderr.count("\n") + 1 if r.stderr else 0,
    }
    if r.error:
        log.error("Tool failed — executor error", extra=extra)
    elif r.timed_out:
        log.warning("Tool timed out", extra=extra)
    elif r.returncode != 0:
        log.warning("Tool exited with non-zero code", extra=extra)
    else:
        log.info("Tool completed successfully", extra=extra)
