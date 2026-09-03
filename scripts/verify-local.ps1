param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [switch]$IncludeE2E,
    # E2E-only: lets the Playwright webServers run on non-default ports when a
    # dev server or another app already occupies 3000/8000.
    [int]$E2eBackendPort = $(if ($env:QIYAN_E2E_BACKEND_PORT) { [int]$env:QIYAN_E2E_BACKEND_PORT } else { 8000 }),
    [int]$E2eFrontendPort = $(if ($env:QIYAN_E2E_FRONTEND_PORT) { [int]$env:QIYAN_E2E_FRONTEND_PORT } else { 3000 })
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($BackendOnly -and $FrontendOnly) {
    throw "BackendOnly and FrontendOnly cannot be used together."
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"
$backendPython = Join-Path $backendDir ".uv-test-venv\Scripts\python.exe"
$runBackend = -not $FrontendOnly
$runFrontend = -not $BackendOnly

function Invoke-NativeStep {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [string]$WorkingDirectory,
        [Parameter(Mandatory = $true)]
        [string]$Command,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,
        [hashtable]$ExtraEnvironment
    )

    Write-Host ""
    Write-Host "==> $Name" -ForegroundColor Cyan
    $savedEnvironment = @{}
    if ($ExtraEnvironment) {
        foreach ($key in $ExtraEnvironment.Keys) {
            $savedEnvironment[$key] = [string][Environment]::GetEnvironmentVariable($key)
            [Environment]::SetEnvironmentVariable($key, $ExtraEnvironment[$key], "Process")
        }
    }
    Push-Location $WorkingDirectory
    try {
        & $Command @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "$Name failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
        foreach ($key in $savedEnvironment.Keys) {
            [Environment]::SetEnvironmentVariable($key, $savedEnvironment[$key], "Process")
        }
    }
}

$startedAt = Get-Date
Write-Host "Qiyan Nexus local verification" -ForegroundColor Green
Write-Host "Repo: $repoRoot"
Write-Host "Started: $($startedAt.ToString("s"))"

if ($runBackend) {
    if (-not (Test-Path $backendPython)) {
        throw "Backend venv not found at $backendPython. Run the backend setup from README.md first."
    }

    Invoke-NativeStep `
        -Name "backend: ruff format --check" `
        -WorkingDirectory $backendDir `
        -Command $backendPython `
        -Arguments @("-m", "ruff", "format", "--check", "app", "tests")

    Invoke-NativeStep `
        -Name "backend: ruff check" `
        -WorkingDirectory $backendDir `
        -Command $backendPython `
        -Arguments @("-m", "ruff", "check", "app", "tests")

    Invoke-NativeStep `
        -Name "backend: mypy app" `
        -WorkingDirectory $backendDir `
        -Command $backendPython `
        -Arguments @("-m", "mypy", "app")

    Invoke-NativeStep `
        -Name "backend: pytest -q" `
        -WorkingDirectory $backendDir `
        -Command $backendPython `
        -Arguments @("-m", "pytest", "-q")
}

if ($runFrontend) {
    $pnpm = Get-Command "pnpm" -ErrorAction SilentlyContinue
    if ($null -eq $pnpm) {
        throw "pnpm was not found on PATH. Install pnpm before running frontend verification."
    }

    Invoke-NativeStep `
        -Name "frontend: pnpm test" `
        -WorkingDirectory $frontendDir `
        -Command $pnpm.Source `
        -Arguments @("test")

    # Keep typecheck/build sequential. Both touch Next route type artifacts in .next.
    Invoke-NativeStep `
        -Name "frontend: pnpm typecheck" `
        -WorkingDirectory $frontendDir `
        -Command $pnpm.Source `
        -Arguments @("typecheck")

    Invoke-NativeStep `
        -Name "frontend: pnpm build" `
        -WorkingDirectory $frontendDir `
        -Command $pnpm.Source `
        -Arguments @("build")

    if ($IncludeE2E) {
        Invoke-NativeStep `
            -Name "frontend: pnpm e2e" `
            -WorkingDirectory $frontendDir `
            -Command $pnpm.Source `
            -Arguments @("e2e") `
            -ExtraEnvironment @{
                "QIYAN_E2E_BACKEND_PORT"  = [string]$E2eBackendPort
                "QIYAN_E2E_FRONTEND_PORT" = [string]$E2eFrontendPort
            }
    }
    else {
        Write-Host ""
        Write-Host "Skipped frontend E2E. Run .\scripts\verify-local.ps1 -IncludeE2E when preparing reviewer walkthroughs or branch-level closeout." -ForegroundColor Yellow
    }
}

$finishedAt = Get-Date
$elapsed = $finishedAt - $startedAt
Write-Host ""
Write-Host "Verification passed in $([math]::Round($elapsed.TotalSeconds, 1))s." -ForegroundColor Green
