"""
sandbox.py — Clone, build, and run a Node/React GitHub repo for live pentesting.

Tools exposed
-------------
build_sandbox(github_url, port)  — git clone + npm install + npm run dev/start
list_sandboxes()                 — show all running sandboxes
teardown_sandbox(sandbox_id)     — stop the dev server and clean up
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import socket
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP

log = logging.getLogger("inceptrix.mcp.tools.sandbox")

# sandbox_id -> {proc, port, repo_dir, github_url, started_at, last_used_at, framework}
_SANDBOXES: dict[str, dict] = {}

# Ports reserved for sandbox apps — 20 slots: 3000-3019
_PORT_RANGE = range(3000, 3020)
_MAX_SANDBOXES = 20


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _evict_lru_sandbox() -> str:
    """Teardown the least-recently-used sandbox to free a port slot.

    Returns the sandbox_id that was evicted.
    """
    if not _SANDBOXES:
        raise RuntimeError("No sandboxes to evict.")
    # Find the sandbox with the oldest last_used_at timestamp
    lru_id = min(_SANDBOXES, key=lambda sid: _SANDBOXES[sid]["last_used_at"])
    info = _SANDBOXES.pop(lru_id)
    proc: subprocess.Popen = info["proc"]
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    shutil.rmtree(info["repo_dir"], ignore_errors=True)
    log.info(
        f"[LRU eviction] Evicted sandbox '{lru_id}' "
        f"(port={info['port']}, last_used={info['last_used_at']:.0f})"
    )
    return lru_id


def _pick_port(requested: int = 0) -> int:
    """Return an available port from the sandbox range (or a requested one).

    If the pool is full (all _MAX_SANDBOXES slots occupied), the least-recently-
    used sandbox is automatically evicted to reclaim its port before retrying.
    """
    def _try_once(candidates: list[int]) -> int | None:
        used = {v["port"] for v in _SANDBOXES.values()}
        for port in candidates:
            if port in used:
                continue
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                if s.connect_ex(("127.0.0.1", port)) != 0:
                    return port
        return None

    candidates = [requested] if requested else list(_PORT_RANGE)

    # First attempt without eviction
    port = _try_once(candidates)
    if port is not None:
        return port

    # Pool is full — evict the LRU sandbox and retry once
    if len(_SANDBOXES) >= _MAX_SANDBOXES or requested == 0:
        evicted = _evict_lru_sandbox()
        log.info(f"Port pool full — evicted LRU sandbox '{evicted}' to make room.")
        port = _try_once(candidates)
        if port is not None:
            return port

    raise RuntimeError(
        f"No free sandbox ports available in range {_PORT_RANGE.start}-{_PORT_RANGE.stop - 1} "
        f"even after LRU eviction. All {_MAX_SANDBOXES} slots may be in use by OS processes."
    )


def _detect_framework(repo_dir: str) -> str:
    """Read package.json to decide how to start the dev server."""
    pkg = Path(repo_dir) / "package.json"
    if not pkg.exists():
        return "unknown"
    try:
        data = json.loads(pkg.read_text())
        scripts = data.get("scripts", {})
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        if "vite" in deps or "dev" in scripts:
            return "vite"
        if "react-scripts" in deps or "start" in scripts:
            return "cra"
        return "generic"
    except Exception:
        return "generic"


def _build_start_cmd(framework: str, port: int) -> list[str]:
    """Return the npm command list that starts the dev server on *port*."""
    if framework == "vite":
        # Vite accepts extra args after --
        return ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", str(port)]
    # CRA / generic — use PORT / HOST env vars injected via the environment
    return ["npm", "start"]


def _wait_for_port(port: int, timeout: int = 30) -> bool:
    """Poll until the port accepts connections or timeout expires."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(1)
    return False


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

def register(mcp: "FastMCP") -> None:

    @mcp.tool(name="build_sandbox", description=(
        "Clone a GitHub repo, install Node dependencies, and start the dev server "
        "so it can be pentested live.\n\n"
        "github_url : HTTPS URL of the repo, e.g. 'https://github.com/owner/repo'\n"
        "port       : host port to bind (0 = auto-assign from 3000-3010, default 0)\n\n"
        "Returns the sandbox_id, URL, and port to use as the pentest target."
    ))
    def build_sandbox(github_url: str, port: int = 0) -> str:
        sandbox_id = uuid.uuid4().hex[:8]
        log.info("build_sandbox invoked", extra={"sandbox_id": sandbox_id, "github_url": github_url})

        # ── 1. Pick port ──────────────────────────────────────────────────
        try:
            chosen_port = _pick_port(port)
        except RuntimeError as e:
            return f"[ERROR] {e}"

        # ── 2. Clone ──────────────────────────────────────────────────────
        repo_dir = tempfile.mkdtemp(prefix=f"sandbox_{sandbox_id}_")
        log.info(f"[{sandbox_id}] Cloning {github_url} → {repo_dir}")
        clone = subprocess.run(
            ["git", "clone", "--depth=1", github_url, repo_dir],
            capture_output=True, text=True, timeout=120,
        )
        if clone.returncode != 0:
            shutil.rmtree(repo_dir, ignore_errors=True)
            return (
                f"[ERROR] git clone failed (rc={clone.returncode})\n"
                f"{clone.stderr.strip()}"
            )

        # ── 3. npm install ────────────────────────────────────────────────
        log.info(f"[{sandbox_id}] Running npm install...")
        install = subprocess.run(
            ["npm", "install", "--prefer-offline", "--no-audit", "--no-fund"],
            cwd=repo_dir, capture_output=True, text=True, timeout=300,
        )
        if install.returncode != 0:
            shutil.rmtree(repo_dir, ignore_errors=True)
            return (
                f"[ERROR] npm install failed (rc={install.returncode})\n"
                f"{install.stderr[-2000:].strip()}"
            )

        # ── 4. Detect framework & build start command ─────────────────────
        framework = _detect_framework(repo_dir)
        cmd = _build_start_cmd(framework, chosen_port)
        env = {
            **os.environ,
            "PORT": str(chosen_port),
            "HOST": "0.0.0.0",
            "VITE_PORT": str(chosen_port),
            "CI": "false",           # prevents CRA treating warnings as errors
            "BROWSER": "none",       # don't open a browser
            "FORCE_COLOR": "0",
        }

        log.info(f"[{sandbox_id}] Starting dev server ({framework}) on port {chosen_port}: {cmd}")
        proc = subprocess.Popen(
            cmd,
            cwd=repo_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        # ── 5. Wait for the server to become reachable ────────────────────
        ready = _wait_for_port(chosen_port, timeout=45)

        if not ready or proc.poll() is not None:
            stdout = ""
            try:
                stdout, _ = proc.communicate(timeout=2)
            except Exception:
                pass
            proc.kill()
            shutil.rmtree(repo_dir, ignore_errors=True)
            return (
                f"[ERROR] Dev server did not start on port {chosen_port} within 45s.\n"
                f"Output:\n{(stdout or '')[-2000:].strip()}"
            )

        # ── 6. Register sandbox ───────────────────────────────────────────
        now = time.time()
        _SANDBOXES[sandbox_id] = {
            "proc": proc,
            "port": chosen_port,
            "repo_dir": repo_dir,
            "github_url": github_url,
            "framework": framework,
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "last_used_at": now,  # updated when sandbox is actively accessed
        }

        slots_used = len(_SANDBOXES)
        log.info(f"[{sandbox_id}] Sandbox ready at port {chosen_port} ({slots_used}/{_MAX_SANDBOXES} slots used)")
        return (
            f"Sandbox ready.\n"
            f"\n"
            f"  sandbox_id : {sandbox_id}\n"
            f"  framework  : {framework}\n"
            f"  target_url : http://0.0.0.0:{chosen_port}\n"
            f"  pentest at : http://<your-host-ip>:{chosen_port}\n"
            f"  slots used : {slots_used}/{_MAX_SANDBOXES}\n"
            f"\n"
            f"Use teardown_sandbox(sandbox_id='{sandbox_id}') when done."
        )

    # -----------------------------------------------------------------------

    @mcp.tool(name="list_sandboxes", description=(
        "List all currently running sandbox dev servers with their sandbox_id, "
        "URL, and source repo."
    ))
    def list_sandboxes() -> str:
        if not _SANDBOXES:
            return f"No sandboxes running. ({_MAX_SANDBOXES} slots available)"
        lines = [f"Running sandboxes ({len(_SANDBOXES)}/{_MAX_SANDBOXES} slots used):\n"]
        # Sort by last_used_at ascending so the LRU candidate is shown first
        for sid, info in sorted(_SANDBOXES.items(), key=lambda kv: kv[1]["last_used_at"]):
            alive = info["proc"].poll() is None
            age_s = int(time.time() - info["last_used_at"])
            lru_marker = " ← LRU (evicted next if pool is full)" if sid == min(
                _SANDBOXES, key=lambda s: _SANDBOXES[s]["last_used_at"]
            ) else ""
            lines.append(
                f"  {sid}  port={info['port']}  "
                f"framework={info['framework']}  "
                f"alive={alive}  "
                f"last_used={age_s}s ago  "
                f"repo={info['github_url']}"
                f"{lru_marker}"
            )
        return "\n".join(lines)

    # -----------------------------------------------------------------------

    @mcp.tool(name="teardown_sandbox", description=(
        "Stop the dev server and delete the cloned repo for a given sandbox.\n\n"
        "sandbox_id : the ID returned by build_sandbox"
    ))
    def teardown_sandbox(sandbox_id: str) -> str:
        info = _SANDBOXES.pop(sandbox_id, None)
        if info is None:
            return f"[ERROR] No sandbox found with id '{sandbox_id}'."
        proc: subprocess.Popen = info["proc"]
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        shutil.rmtree(info["repo_dir"], ignore_errors=True)
        log.info(f"[{sandbox_id}] Sandbox torn down.")
        return f"Sandbox '{sandbox_id}' stopped and cleaned up."

    # -----------------------------------------------------------------------

    @mcp.tool(name="teardown_all_sandboxes", description=(
        "Stop ALL running sandbox dev servers and delete every cloned repo.\n\n"
        "Use this to nuke the entire build environment in one shot — kills every\n"
        "process and wipes every temp directory created by build_sandbox."
    ))
    def teardown_all_sandboxes() -> str:
        if not _SANDBOXES:
            return "No sandboxes running — nothing to tear down."
        ids = list(_SANDBOXES.keys())
        results = []
        for sid in ids:
            info = _SANDBOXES.pop(sid, None)
            if info is None:
                continue
            proc: subprocess.Popen = info["proc"]
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
            shutil.rmtree(info["repo_dir"], ignore_errors=True)
            log.info(f"[{sid}] Sandbox torn down (bulk).")
            results.append(f"  {sid}  port={info['port']}  repo={info['github_url']}  → STOPPED & DELETED")
        return f"Torn down {len(results)} sandbox(es):\n" + "\n".join(results)

    log.debug("sandbox tools registered")
