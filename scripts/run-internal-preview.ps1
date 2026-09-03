param(
    [string]$RuntimeRoot = ".tmp/internal-preview",
    [ValidateRange(1, 65535)]
    [int]$BackendPort = 8000,
    [ValidateRange(1, 65535)]
    [int]$FrontendPort = 3000,
    [string]$AccessToken = "",
    # Optional operator-controlled manifest so the verified disease-import flow
    # (POST /api/network/disease-import/verify) is exercisable in the preview.
    [string]$OpenTargetsManifestPath = "",
    [switch]$Stop
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$runtimePath = Join-Path $repoRoot $RuntimeRoot
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"
$backendPython = Join-Path $backendDir ".uv-test-venv\Scripts\python.exe"
$processHelper = Join-Path $PSScriptRoot "start-configured-process.ps1"
$processFile = Join-Path $runtimePath "processes.json"
$backendLog = Join-Path $runtimePath "backend.log"
$frontendLog = Join-Path $runtimePath "frontend.log"

function Stop-ProcessTree {
    param([int]$ProcessId)

    $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if ($null -eq $process) {
        return
    }

    & taskkill /T /F /PID $ProcessId | Out-Null
}

function Stop-InternalPreview {
    if (-not (Test-Path $processFile)) {
        Write-Host "No process file found at $processFile. Nothing to stop." -ForegroundColor Yellow
        return
    }

    $processes = Get-Content $processFile -Raw | ConvertFrom-Json
    foreach ($entry in @($processes)) {
        Stop-ProcessTree -ProcessId ([int]$entry.pid)
    }
    Remove-Item -LiteralPath $processFile -Force
    Write-Host "Stopped internal preview processes recorded in $processFile." -ForegroundColor Green
}

if ($Stop) {
    Stop-InternalPreview
    return
}

if (-not (Test-Path $backendPython)) {
    throw "Backend venv not found at $backendPython. Run backend setup from README.md first."
}

function Assert-PortAvailable {
    param([int]$Port, [string]$Name)

    $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($null -ne $listener) {
        $owner = Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
        $ownerName = if ($null -ne $owner) { $owner.ProcessName } else { "unknown" }
        throw (
            "$Name port $Port is already in use by PID $($listener.OwningProcess) ($ownerName). " +
            "Stop that process, or rerun with -BackendPort/-FrontendPort to pick free ports " +
            "(for example: -BackendPort 8010 -FrontendPort 3100)."
        )
    }
}

Assert-PortAvailable -Port $BackendPort -Name "backend"
Assert-PortAvailable -Port $FrontendPort -Name "frontend"

$pnpm = Get-Command "pnpm" -ErrorAction SilentlyContinue
if ($null -eq $pnpm) {
    throw "pnpm was not found on PATH. Install pnpm before running the frontend preview."
}
$powerShellHost = Get-Command "pwsh" -ErrorAction SilentlyContinue
if ($null -eq $powerShellHost) {
    $powerShellHost = Get-Command "powershell" -ErrorAction Stop
}

New-Item -ItemType Directory -Force -Path $runtimePath | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $runtimePath "uploads") | Out-Null

if (Test-Path $processFile) {
    Write-Host "Existing process file found. Stopping previous internal preview first." -ForegroundColor Yellow
    Stop-InternalPreview
}

$backendEnv = @{
    "PYTHONIOENCODING" = "utf-8"
    "PYTHONUTF8" = "1"
    "QIYAN_LLM_PROVIDER" = "deterministic"
    "QIYAN_RETRIEVAL_PROVIDER" = "keyword"
    "QIYAN_STATE_BACKEND" = "json"
    "QIYAN_ACCESS_TOKENS" = $AccessToken
    "LITERATURE_RUNTIME_STATE_PATH" = (Join-Path $runtimePath "literature_state.json")
    "CHUNK_RUNTIME_STATE_PATH" = (Join-Path $runtimePath "chunk_state.json")
    "NETWORK_TASKS_RUNTIME_STATE_PATH" = (Join-Path $runtimePath "network_tasks_state.json")
    "VECTOR_INDEX_RUNTIME_CACHE_PATH" = (Join-Path $runtimePath "vector-index.npy")
    "UPLOAD_STORAGE_DIR" = (Join-Path $runtimePath "uploads")
}
if ($OpenTargetsManifestPath.Trim()) {
    if (-not (Test-Path $OpenTargetsManifestPath)) {
        throw "Open Targets manifest not found at $OpenTargetsManifestPath."
    }
    $backendEnv["NETWORK_OPEN_TARGETS_MANIFEST_PATH"] = (Resolve-Path $OpenTargetsManifestPath).Path
}

$frontendEnv = @{
    "NEXT_PUBLIC_API_BASE_URL" = "http://127.0.0.1:$BackendPort"
}

function Start-ConfiguredProcess {
    param(
        [string]$WorkingDirectory,
        [string]$Executable,
        [string[]]$Arguments,
        [string]$LogPath,
        [hashtable]$Environment
    )

    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $powerShellHost.Source
    $startInfo.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$processHelper`""
    $startInfo.WorkingDirectory = $WorkingDirectory
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
    [void]$startInfo.EnvironmentVariables.Remove("QIYAN_ACCESS_TOKENS")
    [void]$startInfo.EnvironmentVariables.Remove("NEXT_PUBLIC_QIYAN_ACCESS_TOKEN")
    foreach ($entry in $Environment.GetEnumerator()) {
        $startInfo.EnvironmentVariables[[string]$entry.Key] = [string]$entry.Value
    }
    $startInfo.EnvironmentVariables["QIYAN_PROCESS_EXECUTABLE"] = $Executable
    $startInfo.EnvironmentVariables["QIYAN_PROCESS_ARGUMENTS_JSON"] = ($Arguments | ConvertTo-Json -Compress)
    $startInfo.EnvironmentVariables["QIYAN_PROCESS_LOG_PATH"] = $LogPath

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo
    if (-not $process.Start()) {
        throw "Failed to start configured process in $WorkingDirectory."
    }
    return $process
}

$backendProcess = Start-ConfiguredProcess `
    -WorkingDirectory $backendDir `
    -Executable $backendPython `
    -Arguments @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", [string]$BackendPort) `
    -LogPath $backendLog `
    -Environment $backendEnv

$frontendProcess = Start-ConfiguredProcess `
    -WorkingDirectory $frontendDir `
    -Executable $pnpm.Source `
    -Arguments @("dev", "--hostname", "127.0.0.1", "--port", [string]$FrontendPort) `
    -LogPath $frontendLog `
    -Environment $frontendEnv

@(
    [pscustomobject]@{ name = "backend"; pid = $backendProcess.Id; port = $BackendPort; log = $backendLog },
    [pscustomobject]@{ name = "frontend"; pid = $frontendProcess.Id; port = $FrontendPort; log = $frontendLog }
) | ConvertTo-Json | Set-Content -Path $processFile -Encoding utf8

function Wait-PreviewUrl {
    param([string]$Url, [int]$TimeoutSeconds)

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return $true
            }
        }
        catch {
            Start-Sleep -Seconds 2
        }
    }
    return $false
}

if (Wait-PreviewUrl -Url "http://127.0.0.1:$BackendPort/health" -TimeoutSeconds 60) {
    Write-Host "Backend health check passed." -ForegroundColor Green
}
else {
    Write-Host "WARNING: backend /health did not answer within 60s. See $backendLog" -ForegroundColor Yellow
}
if (Wait-PreviewUrl -Url "http://127.0.0.1:$FrontendPort" -TimeoutSeconds 90) {
    Write-Host "Frontend health check passed." -ForegroundColor Green
}
else {
    Write-Host "WARNING: frontend did not answer within 90s. See $frontendLog" -ForegroundColor Yellow
    Write-Host "If the log mentions 'Another next dev server is already running', stop that dev server (its PID is in the log) and rerun with -Stop." -ForegroundColor Yellow
}

Write-Host "Internal preview started." -ForegroundColor Green
Write-Host "Frontend: http://127.0.0.1:$FrontendPort"
Write-Host "Backend:  http://127.0.0.1:$BackendPort"
Write-Host "Runtime:  $runtimePath"
Write-Host "Logs:     $backendLog ; $frontendLog"
if ($AccessToken.Trim()) {
    Write-Host "Access:   backend API token profile enabled for direct scripted calls." -ForegroundColor Yellow
    Write-Host "Browser:  direct :$FrontendPort UI cannot authenticate to a protected :$BackendPort; use open dev mode or an authenticated reverse proxy." -ForegroundColor Yellow
}
else {
    Write-Host "Access:   open dev mode."
}
