param(
    [string]$OutputRoot = ".tmp/internal-preview-evidence",
    [string]$AccessToken = "trial-token",
    [string]$BackendPort = "8000",
    [string]$FrontendPort = "3000",
    [string]$PdfPath = "local-review-pdfs\健脾养血祛风法治疗特应性皮炎临床疗效及对皮肤屏障功能的影响_杨雪松.pdf",
    [switch]$SkipTokenProfile,
    [switch]$KeepServicesOnFailure
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$runScript = Join-Path $PSScriptRoot "run-internal-preview.ps1"
$smokeScript = Join-Path $PSScriptRoot "smoke-internal-preview.ps1"
$startedAt = Get-Date
$stamp = $startedAt.ToString("yyyyMMdd-HHmmss")
$evidenceRoot = Join-Path $repoRoot $OutputRoot
$evidenceDir = Join-Path $evidenceRoot $stamp
$backendUrl = "http://127.0.0.1:$BackendPort"
$frontendUrl = "http://127.0.0.1:$FrontendPort"
$ranProfiles = New-Object System.Collections.Generic.List[string]
$profileResults = New-Object System.Collections.Generic.List[object]

function Invoke-Native {
    param(
        [string]$Command,
        [string[]]$Arguments
    )

    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Command failed with exit code $LASTEXITCODE."
    }
}

function Get-GitValue {
    param([string[]]$Arguments)

    try {
        $value = & git @Arguments 2>$null
        if ($LASTEXITCODE -eq 0) {
            return (($value | Out-String).Trim())
        }
    }
    catch {
        return ""
    }
    return ""
}

function Wait-BackendHealth {
    param([string]$Url)

    $deadline = (Get-Date).AddSeconds(60)
    while ((Get-Date) -lt $deadline) {
        try {
            $health = Invoke-RestMethod -Method GET -Uri "$Url/health" -TimeoutSec 3
            if ($health.status -eq "ok") {
                return
            }
        }
        catch {
            Start-Sleep -Seconds 1
        }
    }

    throw "Backend health check did not pass within 60 seconds at $Url/health."
}

function Stop-PreviewProfile {
    param([string]$RuntimeRoot)

    if (-not $RuntimeRoot.Trim()) {
        return
    }
    & $runScript -RuntimeRoot $RuntimeRoot -Stop
}

function Invoke-PreviewProfile {
    param(
        [string]$ProfileName,
        [string]$RuntimeRoot,
        [string]$ProfileAccessToken = ""
    )

    $ranProfiles.Add($ProfileName) | Out-Null
    $smokeJson = Join-Path $evidenceDir "$ProfileName-smoke.json"
    $smokeMarkdown = Join-Path $evidenceDir "$ProfileName-smoke.md"

    $runParams = @{
        RuntimeRoot = $RuntimeRoot
        BackendPort = $BackendPort
        FrontendPort = $FrontendPort
    }
    if ($ProfileAccessToken.Trim()) {
        $runParams["AccessToken"] = $ProfileAccessToken
    }

    & $runScript @runParams
    Wait-BackendHealth -Url $backendUrl

    $smokeParams = @{
        BackendUrl = $backendUrl
        PdfPath = $PdfPath
        ProfileName = $ProfileName
        OutputJson = $smokeJson
        OutputMarkdown = $smokeMarkdown
    }
    if ($ProfileAccessToken.Trim()) {
        $smokeParams["AccessToken"] = $ProfileAccessToken
    }

    & $smokeScript @smokeParams

    $profileResults.Add([pscustomobject]@{
            profile = $ProfileName
            runtime_root = $RuntimeRoot
            smoke_json = $smokeJson
            smoke_markdown = $smokeMarkdown
        }) | Out-Null
}

function Copy-ProfileLogs {
    param(
        [string]$ProfileName,
        [string]$RuntimeRoot
    )

    $runtimePath = Join-Path $repoRoot $RuntimeRoot
    $backendLog = Join-Path $runtimePath "backend.log"
    $frontendLog = Join-Path $runtimePath "frontend.log"
    if (Test-Path $backendLog) {
        Copy-Item -LiteralPath $backendLog -Destination (Join-Path $evidenceDir "backend-$ProfileName.log") -Force
    }
    if (Test-Path $frontendLog) {
        Copy-Item -LiteralPath $frontendLog -Destination (Join-Path $evidenceDir "frontend-$ProfileName.log") -Force
    }
}

function Read-SmokeSummary {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return $null
    }
    return Get-Content $Path -Raw | ConvertFrom-Json
}

function Write-EvidenceSummary {
    param(
        [bool]$Passed,
        [string]$FailureMessage = ""
    )

    $finishedAt = Get-Date
    $openSmoke = Read-SmokeSummary -Path (Join-Path $evidenceDir "open-smoke.json")
    $tokenSmoke = Read-SmokeSummary -Path (Join-Path $evidenceDir "token-smoke.json")
    $branch = Get-GitValue -Arguments @("branch", "--show-current")
    $commit = Get-GitValue -Arguments @("rev-parse", "--short", "HEAD")
    $statusShort = Get-GitValue -Arguments @("status", "--short")
    $profiles = $profileResults.ToArray()
    $tokenProfileRun = -not [bool]$SkipTokenProfile
    $metadata = [pscustomobject]@{
        branch = $branch
        commit = $commit
        status_short = $statusShort
        started_at = $startedAt.ToString("o")
        finished_at = $finishedAt.ToString("o")
        passed = $Passed
        backend_url = $backendUrl
        frontend_url = $frontendUrl
        provider = "deterministic"
        retrieval = "keyword"
        state_backend = "json"
        token_profile_run = $tokenProfileRun
        access_token_note = "Access token value is intentionally omitted."
        profiles = $profiles
        failure = $FailureMessage
    }
    $metadata | ConvertTo-Json -Depth 10 | Set-Content -Path (Join-Path $evidenceDir "metadata.json") -Encoding utf8

    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add("# Internal Preview Evidence Package") | Out-Null
    $lines.Add("") | Out-Null
    $lines.Add("| Field | Value |") | Out-Null
    $lines.Add("|---|---|") | Out-Null
    $lines.Add("| Passed | ``$Passed`` |") | Out-Null
    $lines.Add("| Branch | ``$($metadata.branch)`` |") | Out-Null
    $lines.Add("| Commit | ``$($metadata.commit)`` |") | Out-Null
    $lines.Add("| Backend URL | ``$backendUrl`` |") | Out-Null
    $lines.Add("| Frontend URL | ``$frontendUrl`` |") | Out-Null
    $lines.Add("| Provider | ``deterministic`` |") | Out-Null
    $lines.Add("| Retrieval | ``keyword`` |") | Out-Null
    $lines.Add("| State backend | ``json`` |") | Out-Null
    $lines.Add("| Token profile | ``$tokenProfileRun`` |") | Out-Null
    $lines.Add("| Token note | Access token value is intentionally omitted. |") | Out-Null
    if ($FailureMessage.Trim()) {
        $lines.Add("| Failure | $FailureMessage |") | Out-Null
    }
    $lines.Add("") | Out-Null
    $lines.Add("## Smoke Profiles") | Out-Null
    $lines.Add("") | Out-Null
    $lines.Add("| Profile | Passed | Request IDs | Artifact |") | Out-Null
    $lines.Add("|---|---:|---:|---|") | Out-Null
    foreach ($smoke in @($openSmoke, $tokenSmoke)) {
        if ($null -eq $smoke) {
            continue
        }
        $requestIdCount = @($smoke.request_ids).Count
        $lines.Add("| $($smoke.profile) | $($smoke.passed) | $requestIdCount | ``$($smoke.profile)-smoke.md`` |") | Out-Null
    }
    $lines.Add("") | Out-Null
    $lines.Add("## Request IDs") | Out-Null
    $lines.Add("") | Out-Null
    $lines.Add("| Profile | Flow | X-Request-ID |") | Out-Null
    $lines.Add("|---|---|---|") | Out-Null
    foreach ($smoke in @($openSmoke, $tokenSmoke)) {
        if ($null -eq $smoke) {
            continue
        }
        foreach ($request in @($smoke.request_ids)) {
            $lines.Add("| $($smoke.profile) | $($request.flow) | ``$($request.request_id)`` |") | Out-Null
        }
    }
    $lines.Add("") | Out-Null
    $lines.Add("This evidence package is a technical artifact. It does not replace formal clinician/research reviewer sign-off.") | Out-Null
    $lines | Set-Content -Path (Join-Path $evidenceDir "evidence-summary.md") -Encoding utf8
}

New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null

$openRuntimeRoot = (Join-Path $OutputRoot "$stamp\runtime-open") -replace "\\", "/"
$tokenRuntimeRoot = (Join-Path $OutputRoot "$stamp\runtime-token") -replace "\\", "/"
$completed = $false
$failure = ""

try {
    Invoke-PreviewProfile -ProfileName "open" -RuntimeRoot $openRuntimeRoot
    Copy-ProfileLogs -ProfileName "open" -RuntimeRoot $openRuntimeRoot
    Stop-PreviewProfile -RuntimeRoot $openRuntimeRoot

    if (-not $SkipTokenProfile) {
        Invoke-PreviewProfile -ProfileName "token" -RuntimeRoot $tokenRuntimeRoot -ProfileAccessToken $AccessToken
        Copy-ProfileLogs -ProfileName "token" -RuntimeRoot $tokenRuntimeRoot
        Stop-PreviewProfile -RuntimeRoot $tokenRuntimeRoot
    }

    $completed = $true
    Write-EvidenceSummary -Passed $true
}
catch {
    $failure = $_.Exception.Message
    Write-EvidenceSummary -Passed $false -FailureMessage $failure
    throw
}
finally {
    if ($completed -or -not $KeepServicesOnFailure) {
        foreach ($profile in @($ranProfiles)) {
            if ($profile -eq "open") {
                Stop-PreviewProfile -RuntimeRoot $openRuntimeRoot
            }
            if ($profile -eq "token") {
                Stop-PreviewProfile -RuntimeRoot $tokenRuntimeRoot
            }
        }
    }
}

Write-Host "Internal preview evidence package created." -ForegroundColor Green
Write-Host "Summary: $(Join-Path $evidenceDir "evidence-summary.md")"
