#!/usr/bin/env bash
# run.sh — Build, launch, and verify the Inceptrix MCP pentest server.
#
# Usage:
#   ./run.sh                   # build + port-check (ask before killing) + start + test
#   ./run.sh --kill-dont-ask   # same but kills port conflicts without prompting
#   ./run.sh --no-build        # skip docker build, just start
#   ./run.sh --test-only       # only run test_mcp.py against a running container
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

IMAGE="inceptrix-mcp:latest"
CONTAINER="inceptrix-mcp"
MCP_PORT=8090
API_PORT=8091
SANDBOX_PORTS=($(seq 3000 3010))

NO_BUILD=false
TEST_ONLY=false
KILL_DONT_ASK=false

for arg in "$@"; do
    case "$arg" in
        --no-build)        NO_BUILD=true ;;
        --test-only)       TEST_ONLY=true ;;
        --kill-dont-ask)   KILL_DONT_ASK=true ;;
    esac
done

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
WHITE='\033[1;37m'
GRAY='\033[0;90m'
RESET='\033[0m'

step() { echo -e "${CYAN}  >> $*${RESET}"; }
ok()   { echo -e "${GREEN}  [OK]  $*${RESET}"; }
fail() { echo -e "${RED}  [!!]  $*${RESET}"; }
warn() { echo -e "${YELLOW}  [??]  $*${RESET}"; }

get_host_ip() {
    # First non-loopback, non-link-local IPv4
    ip -4 route get 1.1.1.1 2>/dev/null | awk '/src/{print $7; exit}' || echo "127.0.0.1"
}

get_pids_on_port() {
    local port=$1
    # lsof preferred; fall back to ss
    if command -v lsof &>/dev/null; then
        lsof -ti "tcp:${port}" -sTCP:LISTEN 2>/dev/null || true
    else
        ss -tlnp "sport = :${port}" 2>/dev/null \
            | grep -oP 'pid=\K[0-9]+' || true
    fi
}

kill_port() {
    local port=$1
    local pids
    pids=$(get_pids_on_port "$port")
    [[ -z "$pids" ]] && return 0

    for pid in $pids; do
        local name
        name=$(ps -p "$pid" -o comm= 2>/dev/null || echo "pid=$pid")

        if [[ "$KILL_DONT_ASK" == false ]]; then
            warn "Port $port is held by $name (pid=$pid)."
            read -rp "  Kill it? [y/N] " ans
            if [[ ! "$ans" =~ ^[Yy]$ ]]; then
                warn "Skipped — port $port may still be in use."
                return 0
            fi
        else
            warn "Port $port held by $name (pid=$pid) — killing (--kill-dont-ask)."
        fi

        kill -9 "$pid" 2>/dev/null && ok "Killed $name (pid=$pid) on port $port." \
                                    || warn "Could not kill pid=$pid."
    done
}

# ─────────────────────────────────────────────────────────────────────────────
# Step 0 — TestOnly shortcut
# ─────────────────────────────────────────────────────────────────────────────
if [[ "$TEST_ONLY" == true ]]; then
    echo ""
    echo -e "${CYAN}Running tests against existing container...${RESET}"
    python3 test_mcp.py --api-port "$API_PORT" --mcp-port "$MCP_PORT"
    exit $?
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Print banner, clear port conflicts
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GRAY}══════════════════════════════════════════════════════════════${RESET}"
echo -e "${WHITE}  Inceptrix MCP — Launch Script${RESET}"
echo -e "${GRAY}══════════════════════════════════════════════════════════════${RESET}"
echo ""
step "Checking for port conflicts..."

for port in "$MCP_PORT" "$API_PORT"; do
    kill_port "$port"
done

# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Remove existing container
# ─────────────────────────────────────────────────────────────────────────────
if docker ps -a --filter "name=^${CONTAINER}$" --format '{{.Names}}' 2>/dev/null | grep -q "^${CONTAINER}$"; then
    step "Removing existing container '$CONTAINER'..."
    docker rm -f "$CONTAINER" > /dev/null
    ok "Old container removed."
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Build
# ─────────────────────────────────────────────────────────────────────────────
if [[ "$NO_BUILD" == false ]]; then
    echo ""
    step "Building $IMAGE from Dockerfile.minimal..."
    docker build -f Dockerfile.minimal -t "$IMAGE" .
    ok "Image built: $IMAGE"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Run container
# ─────────────────────────────────────────────────────────────────────────────
echo ""
step "Starting container..."

sandbox_port_args=()
for p in "${SANDBOX_PORTS[@]}"; do
    sandbox_port_args+=("-p" "${p}:${p}")
done

docker run -d \
    --name "$CONTAINER" \
    -p "${MCP_PORT}:${MCP_PORT}" \
    -p "${API_PORT}:${API_PORT}" \
    "${sandbox_port_args[@]}" \
    -e "MCP_PORT=${MCP_PORT}" \
    -e "API_PORT=${API_PORT}" \
    -e "LOG_LEVEL=INFO" \
    "$IMAGE" > /dev/null

ok "Container '$CONTAINER' started."

# ─────────────────────────────────────────────────────────────────────────────
# Step 5 — Wait for health check
# ─────────────────────────────────────────────────────────────────────────────
echo ""
step "Waiting for server to become healthy (max 60s)..."

deadline=$(( $(date +%s) + 60 ))
healthy=false

while [[ $(date +%s) -lt $deadline ]]; do
    if curl -sf --max-time 3 "http://localhost:${API_PORT}/health" > /dev/null 2>&1; then
        healthy=true
        break
    fi
    echo -e "${GRAY}    ...${RESET}"
    sleep 2
done

if [[ "$healthy" == false ]]; then
    fail "Server did not become healthy in 60s."
    warn "Container logs:"
    docker logs --tail 40 "$CONTAINER"
    exit 1
fi
ok "Server is healthy."

# ─────────────────────────────────────────────────────────────────────────────
# Step 6 — Run external tests
# ─────────────────────────────────────────────────────────────────────────────
echo ""
step "Running test_mcp.py..."
python3 test_mcp.py --api-port "$API_PORT" --mcp-port "$MCP_PORT"
TEST_EXIT=$?

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
HOST_IP=$(get_host_ip)
echo ""

if [[ $TEST_EXIT -eq 0 ]]; then
    BORDER_COLOR="$GREEN"
    MSG="  All tests passed. Inceptrix MCP is live."
else
    BORDER_COLOR="$RED"
    MSG="  Tests failed (exit $TEST_EXIT). Check output above."
fi

echo -e "${BORDER_COLOR}══════════════════════════════════════════════════════════════${RESET}"
echo -e "${BORDER_COLOR}${MSG}${RESET}"
echo ""
echo -e "${WHITE}  REST API   :  http://${HOST_IP}:${API_PORT}/${RESET}"
echo -e "${WHITE}  Swagger    :  http://${HOST_IP}:${API_PORT}/docs${RESET}"
echo -e "${WHITE}  MCP HTTP   :  http://${HOST_IP}:${MCP_PORT}/${RESET}"
echo ""
echo -e "${GRAY}  Logs  :  docker logs -f $CONTAINER${RESET}"
echo -e "${GRAY}  Stop  :  docker rm -f $CONTAINER${RESET}"
echo -e "${BORDER_COLOR}══════════════════════════════════════════════════════════════${RESET}"
echo ""

exit $TEST_EXIT
