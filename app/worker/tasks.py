from app.worker.celery_app import celery_app
from app.core.redis import redis_client
from app.core.state_manager import transition_state, force_fail
from app.schemas import JobState
import docker
import json
import time
import os
from datetime import datetime, timezone

# ═══════════════════════════════════════════════════════════════════════════════
# STATE TRANSITION DELAYS (seconds)
# Configure how long each state takes before transitioning to the next
# Set DEMO_MODE=true for visible state transitions, false for fast execution
# ═══════════════════════════════════════════════════════════════════════════════
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"

# Delays for each state (in seconds) - only applied in DEMO_MODE
STATE_DELAYS = {
    JobState.PROVISIONING: float(os.getenv("DELAY_PROVISIONING", "3")),
    JobState.PROVISIONED: float(os.getenv("DELAY_PROVISIONED", "1")),
    JobState.ATTACKING: float(os.getenv("DELAY_ATTACKING", "5")),
    JobState.NORMALIZING: float(os.getenv("DELAY_NORMALIZING", "2")),
    JobState.GENERATING_REPORT: float(os.getenv("DELAY_GENERATING_REPORT", "2")),
}

def state_delay(state: JobState):
    """Apply configured delay for a state (only in demo mode)."""
    if DEMO_MODE:
        delay = STATE_DELAYS.get(state, 1)
        time.sleep(delay)

# Initialize Docker client
try:
    # Use environment variables for connection, or default to socket
    docker_client = docker.from_env()
    # Check if we can actually reach the daemon
    docker_client.ping()
except Exception as e:
    print(f"Warning: Docker client init/ping failed: {e}. Worker will use mock mode.")
    docker_client = None

@celery_app.task(name="app.worker.tasks.run_scan_task")
def run_scan_task(engagement_id, target_url):
    """
    Executes a security scan using an isolated Docker container.
    
    State transitions:
    Provisioning → Provisioned → Attacking → Normalizing → Generating_Report → Completed
    
    In DEMO_MODE, each state has a configurable delay for visibility.
    """
    # Track execution time and log records for the report
    start_time = time.time()
    _log_records = []

    def log(message: str):
        """Log to stdout and keep an in-memory record with timestamp."""
        timestamp = datetime.now(timezone.utc).isoformat()
        entry = f"{timestamp} - {message}"
        print(message)
        _log_records.append(entry)

    scan_results = {}

    try:
        # ═══════════════════════════════════════════════════════════════════
        # STAGE 1: PROVISIONING
        # State should already be Provisioning (set at POST /scan)
        # Simulate provisioning: record metadata and basic endpoint checks
        # ═══════════════════════════════════════════════════════════════════
        log(f"[{engagement_id}] Provisioning target for {target_url}...")

        # Basic endpoint validation to satisfy "health" conditions in this demo
        endpoint = str(target_url).strip()
        if not endpoint:
            raise RuntimeError("Target endpoint is empty during provisioning")

        # Store job metadata (id, target, created_at)
        meta_key = f"job:{engagement_id}:meta"
        redis_client.hset(meta_key, mapping={
            "target_url": endpoint,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

        if docker_client:
            log(f"[{engagement_id}] Docker available, would start target container and health check here")
        else:
            log(f"[{engagement_id}] Docker unavailable, running in mock provisioning mode")

        state_delay(JobState.PROVISIONING)

        # If we reached here without raising, provisioning is considered successful
        transition_state(engagement_id, JobState.PROVISIONED)

        # ═══════════════════════════════════════════════════════════════════
        # STAGE 2: PROVISIONED
        # Container ready, endpoint reachable; prepare attack payload
        # ═══════════════════════════════════════════════════════════════════
        redis_client.set(f"job:{engagement_id}:target", endpoint)

        # Simple endpoint format sanity check (acts as "endpoint reachable" proxy here)
        if not (endpoint.startswith("http://") or endpoint.startswith("https://")):
            raise RuntimeError("Provisioned endpoint is not an HTTP/HTTPS URL")

        state_delay(JobState.PROVISIONED)

        # Immediately move to Attacking, as Provisioned is short-lived
        transition_state(engagement_id, JobState.ATTACKING)

        # ═══════════════════════════════════════════════════════════════════
        # STAGE 3: ATTACKING
        # Execute scan tools (simulated via Docker or mock data)
        # Stay here until raw JSON findings are available
        # ═══════════════════════════════════════════════════════════════════
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

            logs = docker_client.containers.run(
                image,
                command=f"/bin/sh -c 'echo \"{json_str}\"'",
                detach=False,
                remove=True,
            )

            if isinstance(logs, bytes):
                output_str = logs.decode("utf-8").strip()
            else:
                output_str = str(logs).strip()

            raw_results = json.loads(output_str)
        else:
            log(f"[{engagement_id}] Mock attack scan for {endpoint} (Docker unavailable)...")
            raw_results = {
                "target": endpoint,
                "timestamp": time.time(),
                "findings": [
                    {"vulnerability": "Mock SQL Injection", "severity": "Critical"},
                    {"vulnerability": "Mock XSS", "severity": "High"},
                ],
                "note": "Docker unavailable - ran in simulation mode",
            }

        # Validate raw_results structure per spec (must have findings JSON)
        if not isinstance(raw_results, dict):
            raise RuntimeError("Raw scan results are not a JSON object")
        findings = raw_results.get("findings")
        if not isinstance(findings, list) or len(findings) == 0:
            raise RuntimeError("Raw scan results missing non-empty 'findings' list")

        state_delay(JobState.ATTACKING)

        # Store raw findings for traceability
        redis_client.set(f"job:{engagement_id}:raw_findings", json.dumps(raw_results))

        # ═══════════════════════════════════════════════════════════════════
        # STAGE 4: NORMALIZING
        # Parse tool outputs, map to schema, assign severity
        # ═══════════════════════════════════════════════════════════════════
        transition_state(engagement_id, JobState.NORMALIZING)

        log(f"[{engagement_id}] Normalizing scan results...")

        normalized_findings = []
        for finding in findings:
            normalized_findings.append(
                {
                    "id": f"FINDING-{len(normalized_findings) + 1:03d}",
                    "type": finding.get("vulnerability", "Unknown"),
                    "severity": finding.get("severity", "Info"),
                    "description": f"Detected {finding.get('vulnerability', 'issue')} vulnerability",
                    "remediation": f"Address {finding.get('vulnerability', 'issue')} according to best practices",
                }
            )

        if len(normalized_findings) == 0:
            raise RuntimeError("Normalization produced no findings")

        scan_results = {
            "target": endpoint,
            "scan_timestamp": raw_results.get("timestamp", time.time()),
            "total_findings": len(normalized_findings),
            "findings": normalized_findings,
        }

        state_delay(JobState.NORMALIZING)

        # ═══════════════════════════════════════════════════════════════════
        # STAGE 5: GENERATING_REPORT
        # Generate final report and persist in Redis
        # ═══════════════════════════════════════════════════════════════════
        transition_state(engagement_id, JobState.GENERATING_REPORT)

        log(f"[{engagement_id}] Generating report...")

        # Build report in the nested schema expected by /report
        elapsed = time.time() - start_time
        job_id = engagement_id
        target = endpoint
        findings = normalized_findings

        # Retrieve any sandbox/global state metadata if present
        meta_key = f"job:{engagement_id}:meta"
        state = redis_client.hgetall(meta_key) or {}

        # Derive additional fields
        logs = _log_records[-50:]

        # Hardcoded / simple demo values for sandbox & summary
        sandbox = {
            "sandbox_id": state.get("sandbox_id", ""),
            "sandbox_url": state.get("sandbox_url", ""),
            "github_url": state.get("github_url", ""),
        }

        scan_summary = {
            "open_ports": [80, 443],
            "services_detected": ["http", "https"],
            "total_findings": len(findings),
        }

        metadata = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "agent": "RedShell v2.0",
            "total_steps": len(_log_records),
            "total_actions": len(findings),
            "elapsed_seconds": float(elapsed),
        }

        report = {
            "job_id": job_id,
            "status": JobState.COMPLETED.value,
            "target": target,
            "sandbox": sandbox,
            "scan_summary": scan_summary,
            "findings": findings,
            "metadata": metadata,
            "logs": logs,
        }

        report_key = f"job:{engagement_id}:report"
        redis_client.set(report_key, json.dumps(report))

        # Verify report exists before moving to Completed
        if redis_client.get(report_key) is None:
            raise RuntimeError("Report storage verification failed")

        state_delay(JobState.GENERATING_REPORT)

        # ═══════════════════════════════════════════════════════════════════
        # STAGE 6: COMPLETED
        # All done, cleanup resources (containers/networks in real impl)
        # ═══════════════════════════════════════════════════════════════════
        transition_state(engagement_id, JobState.COMPLETED)
        log(f"[{engagement_id}] Scan completed successfully!")

    except Exception as e:
        print(f"[{engagement_id}] Task Failed: {e}")
        force_fail(engagement_id, str(e))
