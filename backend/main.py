import os
import json
import time
import shutil
import socket
import logging
import tempfile
import threading
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

import docker
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import EngagementRequest, EngagementResponse, EngagementStatus, BulkEngagementRequest, BulkEngagementResponse

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("inceptrix")

app = FastAPI(title="Inceptrix Provisioner")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_docker_client = None

def get_docker() -> docker.DockerClient:
    """Lazily initialize the Docker client so the server starts without Docker."""
    global _docker_client
    if _docker_client is None:
        try:
            log.info("Connecting to Docker daemon...")
            _docker_client = docker.from_env()
            log.info("Docker daemon connected successfully.")
        except docker.errors.DockerException as e:
            log.error(f"Docker is not running or not reachable: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"Docker is not running or not reachable: {e}",
            )
    return _docker_client

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_host_ip() -> str:
    """Returns the host machine's LAN IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        log.debug(f"Resolved host IP: {ip}")
        return ip
    except Exception:
        log.warning("Could not resolve host IP — falling back to 127.0.0.1")
        return "127.0.0.1"


WEBSITE_INDICATORS = [
    "package.json",
    "index.html",
    "vite.config.js",
    "vite.config.ts",
    "next.config.js",
    "next.config.ts",
    "webpack.config.js",
    "angular.json",
    "svelte.config.js",
    "nuxt.config.js",
]


def _is_website_repo(github_url: str) -> bool:
    """
    Checks the GitHub API to see if the repo contains any known website
    indicator files without cloning the full repository.
    """
    log.info(f"Checking if '{github_url}' is a website repo...")
    parts = github_url.rstrip("/").replace(".git", "").split("github.com/")
    if len(parts) < 2:
        log.warning(f"Invalid GitHub URL format: {github_url}")
        return False
    owner_repo = parts[-1]

    api_url = f"https://api.github.com/repos/{owner_repo}/contents/"
    try:
        resp = requests.get(api_url, timeout=10)
        if resp.status_code != 200:
            log.warning(f"GitHub API returned {resp.status_code} for {api_url}")
            return False
        filenames = {item["name"] for item in resp.json()}
        matched = filenames & set(WEBSITE_INDICATORS)
        if matched:
            log.info(f"Website indicators found: {matched}")
        else:
            log.info("No website indicators found in repo root.")
        return bool(matched)
    except Exception as e:
        log.error(f"GitHub API check failed: {e}")
        return False


def _stream_build_logs(build_log_generator):
    """Iterate Docker build log generator and emit each line to the logger."""
    docker_log = logging.getLogger("inceptrix.docker.build")
    for chunk in build_log_generator:
        # High-level SDK yields dicts already; low-level yields bytes
        if isinstance(chunk, bytes):
            chunk = json.loads(chunk)
        line = chunk.get("stream") or chunk.get("error") or chunk.get("status") or ""
        line = line.rstrip()
        if line:
            if chunk.get("error"):
                docker_log.error(line)
            else:
                docker_log.debug(line)


def _tail_container_logs(container, engagement_id: str):
    """Stream container stdout/stderr to the logger in a background thread."""
    container_log = logging.getLogger(f"inceptrix.container.{engagement_id}")
    try:
        for line in container.logs(stream=True, follow=True):
            container_log.info(line.decode(errors="replace").rstrip())
    except Exception as e:
        container_log.warning(f"Log stream ended: {e}")


BASE_IMAGE = "inceptrix-base"


def _ensure_base_image(client: docker.DockerClient):
    """Build the base image once and cache it. Skip if it already exists."""
    try:
        client.images.get(BASE_IMAGE)
        log.info(f"Base image '{BASE_IMAGE}' already cached — skipping build.")
    except docker.errors.ImageNotFound:
        log.info(f"Base image '{BASE_IMAGE}' not found — building now...")
        dockerfile_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "Dockerfile")
        )
        context_path = os.path.dirname(dockerfile_path)
        _, build_logs = client.images.build(
            path=context_path,
            dockerfile=dockerfile_path,
            tag=BASE_IMAGE,
            rm=True,
        )
        _stream_build_logs(build_logs)
        log.info(f"Base image '{BASE_IMAGE}' built and cached successfully.")


def _build_and_run(engagement_id: str, github_url: str) -> tuple[str, int, str]:
    """
    Ensures the base image is cached, then launches a new container for
    this engagement by passing REPO_URL as an env var to entrypoint.sh.
    Returns (host_ip, host_port, image_tag).
    """
    network_name = f"net-{engagement_id.lower()}"
    client = get_docker()

    # ── 1. Build base image once; reuse on all subsequent calls ──
    _ensure_base_image(client)

    # ── 2. Create an isolated bridge network ──
    try:
        client.networks.get(network_name)
        log.info(f"Reusing existing Docker network '{network_name}'.")
    except docker.errors.NotFound:
        client.networks.create(network_name, driver="bridge")
        log.info(f"Created Docker network '{network_name}'.")

    # ── 3. Run container — entrypoint.sh will clone & npm install ──
    log.info(f"[{engagement_id}] Starting container from '{BASE_IMAGE}' with REPO_URL={github_url}")
    container = client.containers.run(
        BASE_IMAGE,
        detach=True,
        network=network_name,
        ports={"5173/tcp": None},   # let Docker pick a free host port
        environment={"REPO_URL": github_url},
        labels={"engagement_id": engagement_id},
    )
    log.info(f"[{engagement_id}] Container started: {container.short_id}")

    # ── 4. Tail container logs in the background ──
    t = threading.Thread(
        target=_tail_container_logs,
        args=(container, engagement_id),
        daemon=True,
    )
    t.start()
    log.info(f"[{engagement_id}] Container log streaming started (background thread).")

    # ── 5. Give the process time to clone + install, then reload metadata ──
    log.info(f"[{engagement_id}] Waiting for container to clone and install deps...")
    time.sleep(5)
    container.reload()

    # ── 5. Detect host port ──
    port_bindings = container.ports.get("5173/tcp")
    if not port_bindings:
        log.error(f"[{engagement_id}] Could not detect exposed port. Container logs:\n{container.logs().decode()}")
        raise RuntimeError("Could not detect exposed port from container.")
    host_port = int(port_bindings[0]["HostPort"])

    host_ip = _get_host_ip()
    log.info(f"[{engagement_id}] Deployed at {host_ip}:{host_port}")
    return host_ip, host_port, BASE_IMAGE



# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/provision", response_model=EngagementResponse)
def provision(req: EngagementRequest):
    """
    Clone a GitHub repo, build it into a container, and deploy it.

    - Checks whether the repo is a website.
    - Builds a Docker image using the project Dockerfile (REPO_URL build-arg).
    - Launches the container on an isolated Docker network.
    - Returns target_ip and target_port once DEPLOYED.
    """
    log.info(f"[{req.engagement_id}] Provision request received for {req.github_url}")

    # ── Validate it's a website repo ──
    if not _is_website_repo(req.github_url):
        log.warning(f"[{req.engagement_id}] Rejected — not a website repo: {req.github_url}")
        raise HTTPException(
            status_code=400,
            detail="The provided GitHub URL does not appear to be a website repository.",
        )

    # ── Provision ──
    try:
        target_ip, target_port, image_tag = _build_and_run(
            req.engagement_id, req.github_url
        )
    except Exception as e:
        log.exception(f"[{req.engagement_id}] Provisioning failed")
        raise HTTPException(status_code=500, detail=f"Provisioning failed: {e}")

    return EngagementResponse(
        engagement_id=req.engagement_id,
        status=EngagementStatus.DEPLOYED,
        message="Container deployed successfully.",
        target_ip=target_ip,
        target_port=target_port,
        image_tag=image_tag,
    )


def _provision_single(req: EngagementRequest) -> EngagementResponse:
    """Provision one engagement; always returns an EngagementResponse (never raises)."""
    if not _is_website_repo(req.github_url):
        log.warning(f"[{req.engagement_id}] Not a website repo: {req.github_url}")
        return EngagementResponse(
            engagement_id=req.engagement_id,
            status=EngagementStatus.FAILED,
            message="Not a website repository.",
        )
    try:
        target_ip, target_port, image_tag = _build_and_run(req.engagement_id, req.github_url)
        return EngagementResponse(
            engagement_id=req.engagement_id,
            status=EngagementStatus.DEPLOYED,
            message="Container deployed successfully.",
            target_ip=target_ip,
            target_port=target_port,
            image_tag=image_tag,
        )
    except Exception as e:
        log.exception(f"[{req.engagement_id}] Provisioning failed")
        return EngagementResponse(
            engagement_id=req.engagement_id,
            status=EngagementStatus.FAILED,
            message=f"Provisioning failed: {e}",
        )


@app.post("/provision/bulk", response_model=BulkEngagementResponse)
def provision_bulk(req: BulkEngagementRequest):
    """
    Accept multiple {engagement_id, github_url} pairs.
    Each gets its own container on its own isolated network with a unique host port.
    All containers are provisioned in parallel.
    """
    log.info(f"Bulk provision request: {len(req.engagements)} engagements.")

    # Ensure base image is ready before spinning up parallel workers
    _ensure_base_image(get_docker())

    results = []
    with ThreadPoolExecutor(max_workers=len(req.engagements)) as pool:
        futures = {pool.submit(_provision_single, eng): eng for eng in req.engagements}
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            log.info(
                f"[{result.engagement_id}] Bulk result: {result.status} "
                f"— {result.target_ip}:{result.target_port}"
            )

    deployed = sum(1 for r in results if r.status == EngagementStatus.DEPLOYED)
    failed = len(results) - deployed
    log.info(f"Bulk provision complete: {deployed} deployed, {failed} failed.")

    return BulkEngagementResponse(
        total=len(results),
        deployed=deployed,
        failed=failed,
        results=results,
    )


@app.get("/status/{engagement_id}", response_model=EngagementResponse)
def get_status(engagement_id: str):
    """
    Returns the running status of a deployed container by engagement_id.
    """
    log.info(f"[{engagement_id}] Status check requested.")
    containers = get_docker().containers.list(
        filters={"label": f"engagement_id={engagement_id}"}
    )

    if not containers:
        log.warning(f"[{engagement_id}] No container found.")
        raise HTTPException(status_code=404, detail="No container found for this engagement_id.")

    container = containers[0]
    container.reload()

    port_bindings = container.ports.get("5173/tcp")
    host_port = int(port_bindings[0]["HostPort"]) if port_bindings else None
    host_ip = _get_host_ip()

    status = (
        EngagementStatus.DEPLOYED
        if container.status == "running"
        else EngagementStatus.FAILED
    )
    log.info(f"[{engagement_id}] Container {container.short_id} is '{container.status}' → {status}")

    return EngagementResponse(
        engagement_id=engagement_id,
        status=status,
        message=f"Container status: {container.status}",
        target_ip=host_ip,
        target_port=host_port,
    )


@app.delete("/teardown/{engagement_id}")
def teardown(engagement_id: str):
    """
    Stops and removes the container and network for a given engagement_id.
    """
    log.info(f"[{engagement_id}] Teardown requested.")
    client = get_docker()
    containers = client.containers.list(
        all=True, filters={"label": f"engagement_id={engagement_id}"}
    )
    for c in containers:
        log.info(f"[{engagement_id}] Stopping and removing container {c.short_id}...")
        c.stop(timeout=5)
        c.remove(force=True)
        log.info(f"[{engagement_id}] Container {c.short_id} removed.")

    network_name = f"net-{engagement_id.lower()}"
    try:
        network = client.networks.get(network_name)
        network.remove()
        log.info(f"[{engagement_id}] Network '{network_name}' removed.")
    except docker.errors.NotFound:
        log.debug(f"[{engagement_id}] Network '{network_name}' not found — nothing to remove.")

    log.info(f"[{engagement_id}] Teardown complete.")
    return {"engagement_id": engagement_id, "message": "Teardown complete."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
