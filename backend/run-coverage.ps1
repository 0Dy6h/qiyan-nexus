# Run pytest with coverage reporting.
#
# This script runs the test suite with coverage enabled and generates
# both terminal and HTML reports.

param(
    [string]$CoverageThreshold = "80"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$backendDir = $PSScriptRoot
$pythonExe = Join-Path $backendDir ".uv-test-venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    throw "Python venv not found at $pythonExe. Run backend setup first."
}

Write-Host "Running pytest with coverage..." -ForegroundColor Cyan
Write-Host "Coverage threshold: $CoverageThreshold%" -ForegroundColor Cyan
Write-Host ""

Push-Location $backendDir
try {
    & $pythonExe -m pytest --cov=app --cov-report=term-missing --cov-report=html --cov-fail-under=$CoverageThreshold

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "Coverage report generated successfully!" -ForegroundColor Green
        Write-Host "HTML report: backend/htmlcov/index.html" -ForegroundColor Green
    } else {
        throw "Coverage tests failed with exit code $LASTEXITCODE"
    }
} finally {
    Pop-Location
}
