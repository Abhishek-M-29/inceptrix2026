from app.worker.celery_app import celery_app
from app.core.redis import redis_client
from app.core.state_manager import transition_state, force_fail
from app.schemas import JobState
import docker
import json
import time
import os

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
    Queued → Provisioning → Provisioned → Attacking → Normalizing → Generating_Report → Completed
    
    In DEMO_MODE, each state has a configurable delay for visibility.
    """
    scan_results = {}

    try:
        # ═══════════════════════════════════════════════════════════════════
        # STAGE 1: PROVISIONING
        # Start container, create network, wait for health check
        # ═══════════════════════════════════════════════════════════════════
        transition_state(engagement_id, JobState.PROVISIONING)
        
        if docker_client:
            print(f"[{engagement_id}] Provisioning Docker container for {target_url}...")
        else:
            print(f"[{engagement_id}] Mock provisioning (Docker unavailable)...")
        
        state_delay(JobState.PROVISIONING)
        
        # ═══════════════════════════════════════════════════════════════════
        # STAGE 2: PROVISIONED
        # Container ready, endpoint reachable
        # ═══════════════════════════════════════════════════════════════════
        transition_state(engagement_id, JobState.PROVISIONED)
        
        # Store target metadata
        redis_client.set(f"job:{engagement_id}:target", target_url)
        
        state_delay(JobState.PROVISIONED)
        
        # ═══════════════════════════════════════════════════════════════════
        # STAGE 3: ATTACKING
        # Execute scan tools (nmap, nuclei, etc.)
        # ═══════════════════════════════════════════════════════════════════
        transition_state(engagement_id, JobState.ATTACKING)
        
        if docker_client:
            print(f"[{engagement_id}] Starting attack scan for {target_url}...")
            
            # Run the Docker container
            image = "alpine"
            
            # Construct mock scan output
            mock_data = {
                "target": target_url,
                "timestamp": time.time(),
                "findings": [
                    {"vulnerability": "XSS", "severity": "High"},
                    {"vulnerability": "Missing Headers", "severity": "Low"}
                ]
            }
            json_str = json.dumps(mock_data).replace('"', '\\"')
            
            # Run container and wait for it to finish
            logs = docker_client.containers.run(
                image,
                command=f"/bin/sh -c 'echo \"{json_str}\"'",
                detach=False,
                remove=True
            )
            
            # Process output
            if isinstance(logs, bytes):
                output_str = logs.decode('utf-8').strip()
            else:
                output_str = logs.strip()

            try:
                raw_results = json.loads(output_str)
            except json.JSONDecodeError:
                raw_results = {"raw_output": output_str, "error": "Output was not valid JSON"}
        else:
            # Fallback Mock Mode
            print(f"[{engagement_id}] Mock attack scan (Docker unavailable)...")
            raw_results = {
                "target": target_url,
                "timestamp": time.time(),
                "findings": [
                    {"vulnerability": "Mock SQL Injection", "severity": "Critical"},
                    {"vulnerability": "Mock XSS", "severity": "High"}
                ],
                "note": "Docker unavailable - ran in simulation mode"
            }
        
        state_delay(JobState.ATTACKING)
        
        # Store raw findings
        redis_client.set(f"job:{engagement_id}:raw_findings", json.dumps(raw_results))
        
        # ═══════════════════════════════════════════════════════════════════
        # STAGE 4: NORMALIZING
        # Parse tool outputs, map to schema, assign severity
        # ═══════════════════════════════════════════════════════════════════
        transition_state(engagement_id, JobState.NORMALIZING)
        
        print(f"[{engagement_id}] Normalizing scan results...")
        
        # Normalize findings into structured format
        normalized_findings = []
        for finding in raw_results.get("findings", []):
            normalized_findings.append({
                "id": f"FINDING-{len(normalized_findings)+1:03d}",
                "type": finding.get("vulnerability", "Unknown"),
                "severity": finding.get("severity", "Info"),
                "description": f"Detected {finding.get('vulnerability', 'issue')} vulnerability",
                "remediation": f"Address {finding.get('vulnerability', 'issue')} according to best practices"
            })
        
        scan_results = {
            "target": target_url,
            "scan_timestamp": raw_results.get("timestamp", time.time()),
            "total_findings": len(normalized_findings),
            "findings": normalized_findings
        }
        
        state_delay(JobState.NORMALIZING)
        
        # ═══════════════════════════════════════════════════════════════════
        # STAGE 5: GENERATING_REPORT
        # Generate final report
        # ═══════════════════════════════════════════════════════════════════
        transition_state(engagement_id, JobState.GENERATING_REPORT)
        
        print(f"[{engagement_id}] Generating report...")
        
        # Add report metadata
        scan_results["report"] = {
            "generated_at": time.time(),
            "engagement_id": engagement_id,
            "summary": f"Security scan completed for {target_url}. Found {len(normalized_findings)} vulnerabilities."
        }
        
        # Store final report
        redis_client.set(f"job:{engagement_id}:report", json.dumps(scan_results))
        
        state_delay(JobState.GENERATING_REPORT)
        
        # ═══════════════════════════════════════════════════════════════════
        # STAGE 6: COMPLETED
        # All done, cleanup resources
        # ═══════════════════════════════════════════════════════════════════
        transition_state(engagement_id, JobState.COMPLETED)
        
        # Cleanup (in real implementation: stop containers, remove network)
        print(f"[{engagement_id}] Scan completed successfully!")

    except Exception as e:
        print(f"[{engagement_id}] Task Failed: {e}")
        force_fail(engagement_id, str(e))
