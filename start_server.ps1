# start_server.ps1
# Runs inceptrix-mcp:latest (uses existing local image by default).
#
# Usage:
#   .\start_server.ps1           # interactive (logs in foreground)
#   .\start_server.ps1 -Detach   # run container in background
#   .\start_server.ps1 -Build    # rebuild image before starting
# =============================================================
param(
    [switch]$Detach,
    [switch]$Build
)

$ErrorActionPreference = 'Stop'

$IMAGE      = 'inceptrix-mcp:latest'
$CONTAINER  = 'inceptrix-mcp'
$MCP_PORT   = 8090
$API_PORT   = 8091

function Get-HostIP {
    $nics = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
            Where-Object { $_.IPAddress -notmatch '^(127\.|169\.254)' } |
            Sort-Object InterfaceMetric
    if ($nics) { return $nics[0].IPAddress }
    return '127.0.0.1'
}

# Stop any existing container with the same name
$existing = docker ps -a --filter "name=^${CONTAINER}$" --format '{{.Names}}' 2>$null
if ($existing -eq $CONTAINER) {
    Write-Host "Stopping existing container '$CONTAINER' ..." -ForegroundColor Yellow
    docker rm -f $CONTAINER | Out-Null
}

# Build (only when -Build flag is passed)
if ($Build) {
    Write-Host ''
    Write-Host "Building $IMAGE ..." -ForegroundColor Cyan
    docker build -f Dockerfile.minimal -t $IMAGE .
    if ($LASTEXITCODE -ne 0) { Write-Error 'Docker build failed.'; exit 1 }
}

# Pre-flight: verify network access and every tool binary
Write-Host ''
Write-Host 'Running pre-flight checks ...' -ForegroundColor Cyan

$PREFLIGHT_CHECKS = @(
    # Network reachability — just check DNS resolves
    @{ label = 'Network';  cmd = 'curl -sf --max-time 5 -o /dev/null https://1.1.1.1 && echo OK || echo FAIL' },
    # Tool binaries — command -v returns 0 if found
    @{ label = 'nmap';     cmd = 'command -v nmap && nmap --version 2>&1 | head -1' },
    @{ label = 'nikto';    cmd = 'command -v nikto && nikto -Version 2>&1 | head -1' },
    @{ label = 'sqlmap';   cmd = 'command -v sqlmap && sqlmap --version 2>&1 | head -1' },
    @{ label = 'whatweb';  cmd = 'command -v whatweb && whatweb --version 2>&1 | head -1' },
    @{ label = 'ffuf';     cmd = 'command -v ffuf && ffuf -V 2>&1 | head -1' },
    @{ label = 'wfuzz';    cmd = 'command -v wfuzz && wfuzz --version 2>&1 | head -1' },
    @{ label = 'nuclei';   cmd = 'command -v nuclei && nuclei -version 2>&1 | head -1' },
    @{ label = 'httpx';    cmd = 'command -v httpx && httpx -version 2>&1 | head -1' },
    @{ label = 'dalfox';   cmd = 'command -v dalfox && dalfox version 2>&1 | head -1' },
    @{ label = 'jwt_tool'; cmd = 'command -v python3 && python3 /opt/jwt_tool/jwt_tool.py --help 2>&1 | head -1' },
    @{ label = 'node';     cmd = 'command -v node && node --version 2>&1 | head -1' },
    @{ label = 'npm';      cmd = 'command -v npm && npm --version 2>&1 | head -1' }
)

$allOk = $true
foreach ($check in $PREFLIGHT_CHECKS) {
    # --entrypoint overrides start_services.sh so bash runs our one-shot command
    $out = docker run --rm --entrypoint bash $IMAGE -c $check.cmd 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK]  $($check.label)" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] $($check.label)" -ForegroundColor Red
        $allOk = $false
    }
}

if (-not $allOk) {
    Write-Host ''
    Write-Host 'One or more pre-flight checks failed. Rebuild with:  docker build -f docker_mcp/Dockerfile -t inceptrix-mcp:latest .' -ForegroundColor Yellow
    Write-Host 'Continue anyway? (y/N) ' -ForegroundColor Yellow -NoNewline
    $ans = Read-Host
    if ($ans -notmatch '^[Yy]') { exit 1 }
}

Write-Host ''

# Run
$runArgs = @(
    'run', '--rm',
    '--name', $CONTAINER,
    '-p', "${API_PORT}:${API_PORT}",
    '-p', "${MCP_PORT}:${MCP_PORT}",
    '-p', '3000-3010:3000-3010',
    '-e', "API_PORT=${API_PORT}",
    '-e', "MCP_PORT=${MCP_PORT}",
    '-e', 'LOG_LEVEL=INFO'
)

if ($Detach) {
    $runArgs += '-d'
}

$runArgs += $IMAGE

$HOST_IP = Get-HostIP

Write-Host ''
Write-Host ('=' * 62) -ForegroundColor Green
Write-Host '  Inceptrix MCP - Pentest Toolbox' -ForegroundColor Green
Write-Host ('  ' + '-' * 58) -ForegroundColor Green
Write-Host "  MCP       :  http://${HOST_IP}:${MCP_PORT}/" -ForegroundColor White
Write-Host "  REST API  :  http://${HOST_IP}:${API_PORT}/" -ForegroundColor White
Write-Host "  Swagger   :  http://${HOST_IP}:${API_PORT}/docs" -ForegroundColor White
Write-Host ('=' * 62) -ForegroundColor Green
Write-Host ''

if ($Detach) {
    Write-Host 'Starting container in background ...' -ForegroundColor Cyan
    docker @runArgs
    Write-Host ''
    Write-Host "Container '$CONTAINER' is running." -ForegroundColor Green
    Write-Host "  Stop with:  docker rm -f $CONTAINER"
} else {
    Write-Host 'Starting container (Ctrl+C to stop) ...' -ForegroundColor Cyan
    docker @runArgs
}