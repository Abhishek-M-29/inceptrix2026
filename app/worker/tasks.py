"""
Scan Task — Orchestrated Job Lifecycle

Each scan progresses through a strict state machine:

    Provisioning → Provisioned → Attacking → Normalizing → Generating_Report → Completed

Any stage failure transitions the job to Failed with structured error metadata,
triggers resource cleanup, and halts execution.  Every stage is isolated in its
own function, wrapped in its own try/except — failures are caught *per-stage*,
never swallowed.
"""

from __future__ import annotations

import json
import logging
import os
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from celery.exceptions import SoftTimeLimitExceeded

from app.core.redis import redis_client
from app.core.state_manager import force_fail, get_state, transition_state
from app.schemas import JobState
from app.worker.celery_app import celery_app

try:
    import docker
except ImportError:  # pragma: no cover — optional dependency
    docker = None  # type: ignore[assignment]

logger = logging.getLogger("redshell.worker")

# ─── Configuration ────────────────────────────────────────────────────────────

DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"

STATE_DELAYS: Dict[JobState, float] = {
    JobState.PROVISIONING: float(os.getenv("DELAY_PROVISIONING", "3")),
    JobState.PROVISIONED: float(os.getenv("DELAY_PROVISIONED", "1")),
    JobState.ATTACKING: float(os.getenv("DELAY_ATTACKING", "5")),
    JobState.NORMALIZING: float(os.getenv("DELAY_NORMALIZING", "2")),
    JobState.GENERATING_REPORT: float(os.getenv("DELAY_GENERATING_REPORT", "2")),
}

STAGE_TIMEOUTS: Dict[JobState, float] = {
    JobState.PROVISIONING: float(os.getenv("TIMEOUT_PROVISIONING", "60")),
    JobState.ATTACKING: float(os.getenv("TIMEOUT_ATTACKING", "120")),
    JobState.NORMALIZING: float(os.getenv("TIMEOUT_NORMALIZING", "30")),
    JobState.GENERATING_REPORT: float(os.getenv("TIMEOUT_GENERATING_REPORT", "30")),
}

# ─── Docker Client (best-effort init) ────────────────────────────────────────

docker_client: Any = None

if docker is not None:
    try:
        docker_client = docker.from_env()
        docker_client.ping()
    except Exception as exc:
        logger.warning("Docker client init/ping failed: %s — using mock mode", exc)
        docker_client = None
else:
    logger.warning("docker package not installed — using mock mode")


# ─── Custom Exceptions ───────────────────────────────────────────────────────

class StageTimeoutError(Exception):
    """Raised when a stage exceeds its configured timeout."""


class StageError(Exception):
    """Raised to wrap any unexpected error inside a stage with contextual info."""

    def __init__(self, stage: str, original: Exception):
        self.stage = stage
        self.original = original
        super().__init__(f"[{stage}] {original}")


# ═════════════════════════════════════════════════════════════════════════════
#  STAGE FUNCTIONS
#
#  Each stage receives:
#    engagement_id : str   — the job identifier
#    ctx           : dict  — mutable context bag (endpoint, raw_results, etc.)
#    log           : Callable[[str], None]
#
#  Stages must NOT call transition_state themselves.  The orchestrator handles
#  all transitions (before entering the stage and after it succeeds).
# ═════════════════════════════════════════════════════════════════════════════


def _stage_provisioning(
    engagement_id: str,
    ctx: Dict[str, Any],
    log: Callable[[str], None],
) -> None:
    """Validate target, store metadata, check Docker availability."""
    target_url = ctx["target_url"]
    log(f"[{engagement_id}] Provisioning target for {target_url}...")

    endpoint = str(target_url).strip()
    if not endpoint:
        raise RuntimeError("Target endpoint is empty during provisioning")

    ctx["endpoint"] = endpoint

    # Persist job metadata
    meta_key = f"job:{engagement_id}:meta"
    redis_client.hset(meta_key, mapping={
        "target_url": endpoint,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    if docker_client:
        log(f"[{engagement_id}] Docker available — would start target container & health-check here")
    else:
        log(f"[{engagement_id}] Docker unavailable — mock provisioning mode")

    state_delay(JobState.PROVISIONING)

    log(f"[{engagement_id}] Provisioning succeeded")


def _stage_provisioned(
    engagement_id: str,
    ctx: Dict[str, Any],
    log: Callable[[str], None],
) -> None:
    """Store target endpoint metadata & validate URL format (short-lived)."""
    endpoint: str = ctx["endpoint"]

    redis_client.set(f"job:{engagement_id}:target", endpoint)

    if not (endpoint.startswith("http://") or endpoint.startswith("https://")):
        raise RuntimeError(
            f"Provisioned endpoint is not an HTTP/HTTPS URL: {endpoint}"
        )

    state_delay(JobState.PROVISIONED)

    log(f"[{engagement_id}] Endpoint validated — ready to attack")


def _stage_attacking(
    engagement_id: str,
    ctx: Dict[str, Any],
    log: Callable[[str], None],
) -> None:
    """Execute scan tools (Docker container or mock) and capture raw JSON output."""
    endpoint: str = ctx["endpoint"]

    if docker_client:
        log(f"[{engagement_id}] Starting attack scan for {endpoint} (Docker mode)...")

        image = "alpine"
        mock_data = {
            "target": endpoint,
            "timestamp": time.time(),
            "findings": [
                {"vulnerability": "XSS", "severity": "High"},
                {"vulnerability": "Missing Headers", "severity": "Low"},
            ],
        }
        json_str = json.dumps(mock_data).replace('"', '\\"')

        try:
            logs = docker_client.containers.run(
                image,
                command=f'/bin/sh -c \'echo "{json_str}"\'',
                detach=False,
                remove=True,
            )
        except Exception as exc:
            raise RuntimeError(f"Attack container crashed: {exc}") from exc

        output_str = logs.decode("utf-8").strip() if isinstance(logs, bytes) else str(logs).strip()

        try:
            raw_results = json.loads(output_str)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Attack container returned malformed JSON: {exc}"
            ) from exc
    else:
        log(f"[{engagement_id}] Mock attack scan for {endpoint} (Docker unavailable)...")
        raw_results = {
            "target": endpoint,
            "timestamp": time.time(),
            "findings": [
                {"vulnerability": "Mock SQL Injection", "severity": "Critical"},
                {"vulnerability": "Mock XSS", "severity": "High"},
            ],
            "note": "Docker unavailable — ran in simulation mode",
        }

    # ── Validate raw output ───────────────────────────────────────────────
    if not isinstance(raw_results, dict):
        raise RuntimeError("Raw scan results are not a JSON object")

    findings = raw_results.get("findings")
    if not isinstance(findings, list) or len(findings) == 0:
        raise RuntimeError("Raw scan results missing non-empty 'findings' list")

    ctx["raw_results"] = raw_results
    ctx["raw_findings"] = findings

    state_delay(JobState.ATTACKING)

    # Persist raw findings for traceability
    redis_client.set(
        f"job:{engagement_id}:raw_findings",
        json.dumps(raw_results),
    )

    log(f"[{engagement_id}] Attack complete — {len(findings)} raw finding(s)")


def _stage_normalizing(
    engagement_id: str,
    ctx: Dict[str, Any],
    log: Callable[[str], None],
) -> None:
    """Parse raw findings into structured schema, assign severity & IDs."""
    log(f"[{engagement_id}] Normalizing scan results...")

    raw_findings: list = ctx["raw_findings"]
    raw_results: dict = ctx["raw_results"]
    endpoint: str = ctx["endpoint"]

    normalized: List[Dict[str, Any]] = []
    for idx, finding in enumerate(raw_findings, start=1):
        normalized.append({
            "id": f"FINDING-{idx:03d}",
            "type": finding.get("vulnerability", "Unknown"),
            "severity": finding.get("severity", "Info"),
            "description": f"Detected {finding.get('vulnerability', 'issue')} vulnerability",
            "remediation": f"Address {finding.get('vulnerability', 'issue')} according to best practices",
        })

    if len(normalized) == 0:
        raise RuntimeError("Normalization produced zero findings")

    ctx["normalized_findings"] = normalized
    ctx["scan_results"] = {
        "target": endpoint,
        "scan_timestamp": raw_results.get("timestamp", time.time()),
        "total_findings": len(normalized),
        "findings": normalized,
    }

    state_delay(JobState.NORMALIZING)

    log(f"[{engagement_id}] Normalization complete — {len(normalized)} structured finding(s)")


def _stage_generating_report(
    engagement_id: str,
    ctx: Dict[str, Any],
    log: Callable[[str], None],
) -> None:
    """Build final report, persist to Redis, verify storage."""
    log(f"[{engagement_id}] Generating report...")

    endpoint: str = ctx["endpoint"]
    findings: list = ctx["normalized_findings"]
    log_records: list = ctx["log_records"]
    start_time: float = ctx["start_time"]

    elapsed = time.time() - start_time

    # Fetch stored metadata (sandbox info, etc.)
    meta = redis_client.hgetall(f"job:{engagement_id}:meta") or {}

    sandbox = {
        "sandbox_id": meta.get("sandbox_id", ""),
        "sandbox_url": meta.get("sandbox_url", ""),
        "github_url": meta.get("github_url", ""),
    }

    scan_summary = {
        "open_ports": [80, 443],
        "services_detected": ["http", "https"],
        "total_findings": len(findings),
    }

    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agent": "RedShell v2.0",
        "total_steps": len(log_records),
        "total_actions": len(findings),
        "elapsed_seconds": float(elapsed),
    }

    report = {
        "job_id": engagement_id,
        "status": JobState.COMPLETED.value,
        "target": endpoint,
        "sandbox": sandbox,
        "scan_summary": scan_summary,
        "findings": findings,
        "metadata": metadata,
        "logs": log_records[-50:],
    }

    report_key = f"job:{engagement_id}:report"
    redis_client.set(report_key, json.dumps(report))

    # Verify the write landed
    if redis_client.get(report_key) is None:
        raise RuntimeError("Report storage verification failed — Redis write returned None")

    state_delay(JobState.GENERATING_REPORT)

    log(f"[{engagement_id}] Report generated and stored ({len(findings)} findings, {elapsed:.1f}s elapsed)")


# ═════════════════════════════════════════════════════════════════════════════
#  RESOURCE CLEANUP
# ═════════════════════════════════════════════════════════════════════════════


def _cleanup_resources(
    engagement_id: str,
    ctx: Dict[str, Any],
    log: Callable[[str], None],
) -> None:
    """
    Release containers, networks, and other resources.

    Called on BOTH success (Completed) and failure (Failed) paths.
    Wrapped in its own try/except so cleanup errors never mask the original failure.
    """
    try:
        container_id = ctx.get("attack_container_id")
        if container_id and docker_client:
            try:
                container = docker_client.containers.get(container_id)
                container.stop(timeout=5)
                container.remove(force=True)
                log(f"[{engagement_id}] Cleanup: stopped attack container {container_id[:12]}")
            except Exception as exc:
                logger.warning("[%s] Cleanup: failed to stop attack container: %s", engagement_id, exc)

        target_container_id = ctx.get("target_container_id")
        if target_container_id and docker_client:
            try:
                container = docker_client.containers.get(target_container_id)
                container.stop(timeout=5)
                container.remove(force=True)
                log(f"[{engagement_id}] Cleanup: stopped target container {target_container_id[:12]}")
            except Exception as exc:
                logger.warning("[%s] Cleanup: failed to stop target container: %s", engagement_id, exc)

        network_id = ctx.get("network_id")
        if network_id and docker_client:
            try:
                network = docker_client.networks.get(network_id)
                network.remove()
                log(f"[{engagement_id}] Cleanup: removed network {network_id[:12]}")
            except Exception as exc:
                logger.warning("[%s] Cleanup: failed to remove network: %s", engagement_id, exc)

        log(f"[{engagement_id}] Cleanup: resource cleanup finished")

    except Exception as exc:
        # Last-resort catch — cleanup must never propagate
        logger.error("[%s] Cleanup: unexpected error during resource cleanup: %s", engagement_id, exc)


# ═════════════════════════════════════════════════════════════════════════════
#  FAILURE HANDLER
# ═════════════════════════════════════════════════════════════════════════════


def _fail_job(
    engagement_id: str,
    stage_name: str,
    error: Exception,
    ctx: Dict[str, Any],
    log: Callable[[str], None],
) -> None:
    """
    Centralized failure handler — logs, persists failure metadata, cleans up.

    Called by the orchestrator when any stage raises.
    """
    tb = traceback.format_exc()

    logger.error(
        "[%s] FAILED at stage %s: %s\n%s",
        engagement_id, stage_name, error, tb,
    )
    log(f"[{engagement_id}] FAILED at {stage_name}: {error}")

    # Persist structured failure metadata to Redis
    force_fail(
        engagement_id,
        error_message=str(error),
        failed_stage=stage_name,
        traceback_str=tb,
    )

    # Store last N log records for post-mortem debugging
    log_records: list = ctx.get("log_records", [])
    if log_records:
        redis_client.set(
            f"job:{engagement_id}:failure_logs",
            json.dumps(log_records[-100:]),
        )

    # Always clean up resources on failure
    _cleanup_resources(engagement_id, ctx, log)


# ═════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═════════════════════════════════════════════════════════════════════════════


def state_delay(state: JobState) -> None:
    """Apply a configurable delay for a stage (DEMO_MODE only)."""
    if DEMO_MODE:
        delay = STATE_DELAYS.get(state, 1.0)
        time.sleep(delay)


# ═════════════════════════════════════════════════════════════════════════════
#  ORCHESTRATOR — The Celery Task
# ═════════════════════════════════════════════════════════════════════════════

# Stage pipeline: (function, state-after-success)
# The first stage runs *inside* the Provisioning state (set by POST /scan).
# After it succeeds the orchestrator transitions to the exit_state.

_STAGE_PIPELINE: List[Tuple[Callable, str, JobState]] = [
    (_stage_provisioning,      "Provisioning",      JobState.PROVISIONED),
    (_stage_provisioned,       "Provisioned",        JobState.ATTACKING),
    (_stage_attacking,         "Attacking",          JobState.NORMALIZING),
    (_stage_normalizing,       "Normalizing",        JobState.GENERATING_REPORT),
    (_stage_generating_report, "Generating_Report",  JobState.COMPLETED),
]


@celery_app.task(
    name="app.worker.tasks.run_scan_task",
    soft_time_limit=270,   # raise SoftTimeLimitExceeded after 4.5 min
    time_limit=300,        # hard kill after 5 min
)
def run_scan_task(engagement_id: str, target_url: str) -> None:
    """
    Execute a full scan lifecycle for *engagement_id*.

    State is already set to Provisioning by the API layer's ``initialize_job()``.
    This task walks through each stage sequentially, transitioning state only
    after the previous stage has **fully and verifiably succeeded**.
    """
    start_time = time.time()
    log_records: List[str] = []

    def log(message: str) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        entry = f"{ts} - {message}"
        logger.info(message)
        log_records.append(entry)

    # Mutable context bag shared across stages
    ctx: Dict[str, Any] = {
        "target_url": target_url,
        "start_time": start_time,
        "log_records": log_records,
        "endpoint": None,
        "raw_results": None,
        "raw_findings": None,
        "normalized_findings": None,
        "scan_results": None,
        # Resource handles (populated by stages if/when they create them)
        "attack_container_id": None,
        "target_container_id": None,
        "network_id": None,
    }

    logger.info("[%s] ═══ Scan task started for %s ═══", engagement_id, target_url)

    # ── Walk through the stage pipeline ───────────────────────────────────
    for stage_fn, stage_name, exit_state in _STAGE_PIPELINE:
        # Guard: verify we haven't been forced to a terminal state externally
        current = get_state(engagement_id)
        if current in (JobState.COMPLETED, JobState.FAILED):
            logger.warning(
                "[%s] Job already in terminal state %s before stage %s — aborting",
                engagement_id, current.value, stage_name,
            )
            return

        try:
            stage_fn(engagement_id, ctx, log)
        except SoftTimeLimitExceeded:
            _fail_job(
                engagement_id,
                stage_name,
                StageTimeoutError(f"Celery soft time limit exceeded during {stage_name}"),
                ctx,
                log,
            )
            return
        except Exception as exc:
            _fail_job(engagement_id, stage_name, exc, ctx, log)
            return

        # Stage succeeded — transition to exit state
        try:
            transition_state(engagement_id, exit_state)
        except Exception as exc:
            _fail_job(
                engagement_id,
                stage_name,
                RuntimeError(f"State transition to {exit_state.value} failed: {exc}"),
                ctx,
                log,
            )
            return

    # ── All stages completed ──────────────────────────────────────────────
    log(f"[{engagement_id}] Scan completed successfully!")
    logger.info(
        "[%s] ═══ Scan finished in %.1fs ═══",
        engagement_id, time.time() - start_time,
    )

    # Final cleanup (containers, networks) on the success path
    _cleanup_resources(engagement_id, ctx, log)
