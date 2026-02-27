from app.worker.celery_app import celery_app
from app.core.redis import redis_client
import docker
import json
import time

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
    """
    # 1. Update status to Running
    # Note: redis_client handles connection logic
    redis_client.set(f"job:{engagement_id}:status", "Running")
    print(f"[{engagement_id}] Status: Running")
    
    scan_results = {}

    try:
        if docker_client:
            print(f"[{engagement_id}] Starting Docker container scan for {target_url}...")
            
            # 2. Run the Docker container
            # In a real app, this would be a specialized image like 'owasp/zap2docker-stable'
            # Here we use 'alpine' to simulate a tool that outputs JSON findings.
            image = "alpine"
            
            # Construct a command that mimics a tool outputting JSON results
            # We must escape double quotes for the shell command inside the container
            mock_data = {
                "target": target_url,
                "timestamp": time.time(),
                "findings": [
                    {"vulnerability": "XSS", "severity": "High"},
                    {"vulnerability": "Missing Headers", "severity": "Low"}
                ]
            }
            json_str = json.dumps(mock_data).replace('"', '\\"')
            
            # Run container and wait for it to finish (detach=False)
            # 'remove=True' cleans up the container immediately after exit
            logs = docker_client.containers.run(
                image,
                command=f"/bin/sh -c 'echo \"{json_str}\"'",
                detach=False,
                remove=True
            )
            
            # 3. Process output
            if isinstance(logs, bytes):
                output_str = logs.decode('utf-8').strip()
            else:
                 output_str = logs.strip()

            try:
                scan_results = json.loads(output_str)
            except json.JSONDecodeError:
                scan_results = {"raw_output": output_str, "error": "Output was not valid JSON"}
                
        else:
            # Fallback Mock Mode if Docker isn't running locally
            print(f"[{engagement_id}] Docker unavailable. Sleeping to simulate scan...")
            time.sleep(5) 
            scan_results = {
                "target": target_url,
                "findings": ["Mock SQL Injection", "Mock XSS"],
                "note": "Docker unavailable - ran in simulation mode"
            }

        # 4. Store final report
        # We store the resulting JSON object as a string in Redis
        redis_client.set(f"job:{engagement_id}:report", json.dumps(scan_results))
        
        # 5. Update status to Completed
        redis_client.set(f"job:{engagement_id}:status", "Completed")
        print(f"[{engagement_id}] Status: Completed")

    except Exception as e:
        print(f"[{engagement_id}] Task Failed: {e}")
        redis_client.set(f"job:{engagement_id}:status", "Failed")
        redis_client.set(f"job:{engagement_id}:error", str(e))
