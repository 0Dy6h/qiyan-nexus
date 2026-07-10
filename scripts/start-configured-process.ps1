Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$executable = [string]$env:QIYAN_PROCESS_EXECUTABLE
$argumentsJson = [string]$env:QIYAN_PROCESS_ARGUMENTS_JSON
$logPath = [string]$env:QIYAN_PROCESS_LOG_PATH

if (-not $executable.Trim()) {
    throw "QIYAN_PROCESS_EXECUTABLE is required."
}
if (-not $argumentsJson.Trim()) {
    throw "QIYAN_PROCESS_ARGUMENTS_JSON is required."
}
if (-not $logPath.Trim()) {
    throw "QIYAN_PROCESS_LOG_PATH is required."
}

[string[]]$arguments = $argumentsJson | ConvertFrom-Json
$ErrorActionPreference = "Continue"
& $executable @arguments *> $logPath
exit $LASTEXITCODE
