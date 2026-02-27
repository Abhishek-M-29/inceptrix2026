# run.ps1 â€” Build, launch, and verify the Inceptrix MCP pentest server.
#
# Usage:
#   .\run.ps1                  # build + port-check (ask before killing) + start + test
#   .\run.ps1 --kill-dont-ask  # same but kills port conflicts without prompting
#   .\run.ps1 -NoBuild         # skip docker build, just start
#   .\run.ps1 -TestOnly        # only run test_mcp.py against a running container
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
param(
    [switch]$NoBuild,
    [switch]$TestOnly,
    [switch]$KillDontAsk        # also accepted as --kill-dont-ask via alias below
)

# Allow --kill-dont-ask as a CLI argument (PowerShell doesn't natively support - prefix aliases)
if ($args -contains '--kill-dont-ask') { $KillDontAsk = $true }

$ErrorActionPreference = 'Stop'

$IMAGE     = 'inceptrix-mcp:latest'
$CONTAINER = 'inceptrix-mcp'
$MCP_PORT  = 8090
$API_PORT  = 8091
$SANDBOX_PORTS = 3000..3010

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Helpers
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function Write-Step($msg) { Write-Host "  >> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "  [OK]  $msg" -ForegroundColor Green }
function Write-Fail($msg) { Write-Host "  [!!]  $msg" -ForegroundColor Red }
function Write-Warn($msg) { Write-Host "  [??]  $msg" -ForegroundColor Yellow }

function Get-HostIP {
    $nics = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
            Where-Object { $_.IPAddress -notmatch '^(127\.|169\.254)' } |
            Sort-Object InterfaceMetric
    if ($nics) { return $nics[0].IPAddress }
    return '127.0.0.1'
}

function Get-PidsOnPort([int]$port) {
    return @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
             Select-Object -ExpandProperty OwningProcess -Unique)
}

# Processes we must never kill â€” killing these would break Docker/WSL/system
$PROTECTED = @('com.docker.backend','dockerd','Docker Desktop','wslrelay','wsl','wslhost','vpnkit','containerd')

function Kill-Port([int]$port) {
    $pids = Get-PidsOnPort $port
    if (-not $pids) { return }

    foreach ($procId in $pids) {
        try {
            $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
            $name = if ($proc) { $proc.Name } else { "pid=$procId" }

            # Never kill Docker/WSL infrastructure
            if ($PROTECTED -contains $name) {
                Write-Warn "Port $port is held by '$name' (pid=$procId) - protected, skipping."
                Write-Warn "  Restart Docker Desktop if this port was left over from a previous run."
                continue
            }

            if (-not $KillDontAsk) {
                Write-Warn "Port $port is held by $name (pid=$procId)."
                $ans = Read-Host "  Kill it? [y/N]"
                if ($ans -notmatch '^[Yy]') {
                    Write-Warn "Skipped - port $port may still be in use."
                    continue
                }
            } else {
                Write-Warn "Port $port held by $name (pid=$procId) - killing (flag: kill-dont-ask)."
            }
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            Write-Ok "Killed $name (pid=$procId) on port $port."
        } catch {
            Write-Warn "Could not kill pid=${procId}: $_"
        }
    }
}

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Step 0 â€” TestOnly shortcut
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if ($TestOnly) {
    Write-Host ''
    Write-Host 'Running tests against existing container...' -ForegroundColor Cyan
    python test_mcp.py --api-port $API_PORT --mcp-port $MCP_PORT
    exit $LASTEXITCODE
}

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Step 1 â€” Clear port conflicts
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Write-Host ''
Write-Host ('â•' * 62) -ForegroundColor DarkGray
Write-Host '  Inceptrix MCP â€” Launch Script' -ForegroundColor White
Write-Host ('â•' * 62) -ForegroundColor DarkGray
Write-Host ''
Write-Step 'Checking for port conflicts...'

foreach ($port in @($MCP_PORT, $API_PORT)) {
    Kill-Port $port
}

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Step 2 â€” Stop any existing container
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
$existing = docker ps -a --filter "name=^${CONTAINER}$" --format '{{.Names}}' 2>$null
if ($existing -eq $CONTAINER) {
    Write-Step "Removing existing container '$CONTAINER'..."
    docker rm -f $CONTAINER | Out-Null
    Write-Ok "Old container removed."
}

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Step 3 â€” Build
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if (-not $NoBuild) {
    Write-Host ''
    Write-Step "Building $IMAGE from Dockerfile.minimal..."
    docker build -f Dockerfile.minimal -t $IMAGE .
    if ($LASTEXITCODE -ne 0) { Write-Fail 'Docker build failed.'; exit 1 }
    Write-Ok "Image built: $IMAGE"
}

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Step 4 â€” Run container
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Write-Host ''
Write-Step 'Starting container...'

$sandboxPortArgs = ($SANDBOX_PORTS | ForEach-Object { "-p", "${_}:${_}" })

$runArgs = @(
    'run', '-d',
    '--name', $CONTAINER,
    '-p', "${MCP_PORT}:${MCP_PORT}",
    '-p', "${API_PORT}:${API_PORT}"
) + $sandboxPortArgs + @(
    '-e', "MCP_PORT=${MCP_PORT}",
    '-e', "API_PORT=${API_PORT}",
    '-e', 'LOG_LEVEL=INFO',
    $IMAGE
)

docker @runArgs | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Fail 'Failed to start container.'; exit 1 }
Write-Ok "Container '$CONTAINER' started."

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Step 5 â€” Wait for health check
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Write-Host ''
Write-Step "Waiting for server to become healthy (max 60s)..."

$deadline = (Get-Date).AddSeconds(60)
$healthy = $false

while ((Get-Date) -lt $deadline) {
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:${API_PORT}/health" `
                                  -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        if ($resp.StatusCode -eq 200) { $healthy = $true; break }
    } catch { }
    Start-Sleep -Seconds 2
    Write-Host '    ...' -ForegroundColor DarkGray
}

if (-not $healthy) {
    Write-Fail "Server did not become healthy in 60s."
    Write-Warn "Container logs:"
    docker logs --tail 40 $CONTAINER
    exit 1
}
Write-Ok "Server is healthy."

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Step 6 â€” Run external tests
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Write-Host ''
Write-Step "Running test_mcp.py..."
python test_mcp.py --api-port $API_PORT --mcp-port $MCP_PORT
$testExit = $LASTEXITCODE

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Summary
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
$HOST_IP = Get-HostIP
Write-Host ''
Write-Host ('â•' * 62) -ForegroundColor $(if ($testExit -eq 0) { 'Green' } else { 'Red' })

if ($testExit -eq 0) {
    Write-Host '  All tests passed. Inceptrix MCP is live.' -ForegroundColor Green
} else {
    Write-Host "  Tests failed (exit $testExit). Check output above." -ForegroundColor Red
}

Write-Host ''
Write-Host "  REST API   :  http://${HOST_IP}:${API_PORT}/"    -ForegroundColor White
Write-Host "  Swagger    :  http://${HOST_IP}:${API_PORT}/docs" -ForegroundColor White
Write-Host "  MCP HTTP   :  http://${HOST_IP}:${MCP_PORT}/"    -ForegroundColor White
Write-Host ''
Write-Host "  Logs  :  docker logs -f $CONTAINER"              -ForegroundColor DarkGray
Write-Host "  Stop  :  docker rm -f $CONTAINER"                -ForegroundColor DarkGray
Write-Host ('â•' * 62) -ForegroundColor $(if ($testExit -eq 0) { 'Green' } else { 'Red' })
Write-Host ''

exit $testExit
