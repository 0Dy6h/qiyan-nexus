param(
    [string]$RuntimeRoot = ".tmp/internal-preview",
    [string]$BackendPort = "8000",
    [string]$FrontendPort = "3000",
    [string]$AccessToken = "",
    [switch]$Stop
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$runtimePath = Join-Path $repoRoot $RuntimeRoot
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"
$backendPython = Join-Path $backendDir ".uv-test-venv\Scripts\python.exe"
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

$pnpm = Get-Command "pnpm" -ErrorAction SilentlyContinue
if ($null -eq $pnpm) {
    throw "pnpm was not found on PATH. Install pnpm before running the frontend preview."
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

$frontendEnv = @{
    "NEXT_PUBLIC_API_BASE_URL" = "http://127.0.0.1:$BackendPort"
    "NEXT_PUBLIC_QIYAN_ACCESS_TOKEN" = $AccessToken
}

function ConvertTo-EnvCommand {
    param([hashtable]$Environment)

    return ($Environment.GetEnumerator() | ForEach-Object {
            "`$env:$($_.Key) = '$($_.Value -replace "'", "''")'"
        }) -join "; "
}

$backendEnvCommand = ConvertTo-EnvCommand -Environment $backendEnv
$frontendEnvCommand = ConvertTo-EnvCommand -Environment $frontendEnv

$backendCommand = "& '$backendPython' -m uvicorn app.main:app --host 127.0.0.1 --port $BackendPort"
$frontendCommand = "& '$($pnpm.Source)' dev --hostname 127.0.0.1 --port $FrontendPort"

$backendProcess = Start-Process `
    -FilePath "powershell" `
    -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command", "$backendEnvCommand; Set-Location '$backendDir'; $backendCommand *> '$backendLog'"
    ) `
    -WindowStyle Hidden `
    -PassThru

$frontendProcess = Start-Process `
    -FilePath "powershell" `
    -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command", "$frontendEnvCommand; Set-Location '$frontendDir'; $frontendCommand *> '$frontendLog'"
    ) `
    -WindowStyle Hidden `
    -PassThru

@(
    [pscustomobject]@{ name = "backend"; pid = $backendProcess.Id; port = $BackendPort; log = $backendLog },
    [pscustomobject]@{ name = "frontend"; pid = $frontendProcess.Id; port = $FrontendPort; log = $frontendLog }
) | ConvertTo-Json | Set-Content -Path $processFile -Encoding utf8

Write-Host "Internal preview started." -ForegroundColor Green
Write-Host "Frontend: http://127.0.0.1:$FrontendPort"
Write-Host "Backend:  http://127.0.0.1:$BackendPort"
Write-Host "Runtime:  $runtimePath"
Write-Host "Logs:     $backendLog ; $frontendLog"
if ($AccessToken.Trim()) {
    Write-Host "Access:   token profile enabled via X-Access-Token." -ForegroundColor Yellow
}
else {
    Write-Host "Access:   open dev mode."
}
