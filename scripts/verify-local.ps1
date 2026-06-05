param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [switch]$IncludeE2E
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
        [string[]]$Arguments
    )

    Write-Host ""
    Write-Host "==> $Name" -ForegroundColor Cyan
    Push-Location $WorkingDirectory
    try {
        & $Command @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "$Name failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
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
            -Arguments @("e2e")
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
