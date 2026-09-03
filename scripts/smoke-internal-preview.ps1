param(
    [string]$BackendUrl = "http://127.0.0.1:8000",
    [ValidatePattern('^[A-Za-z0-9._~-]*$')]
    [string]$AccessToken = "",
    [ValidatePattern('^[a-z0-9][a-z0-9._-]{0,63}$')]
    [string]$ReviewerId = "preview-smoke",
    [string]$PdfPath = "",
    [string]$ProfileName = "",
    [string]$OutputJson = "",
    [string]$OutputMarkdown = "",
    [switch]$NetworkLive
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function New-UnicodeString {
    param([int[]]$CodePoints)
    return -join ($CodePoints | ForEach-Object { [char]$_ })
}

function Resolve-SmokePdfPath {
    param(
        [string]$RepoRoot,
        [string]$RelativePath
    )

    if ($RelativePath.Trim()) {
        $resolved = Resolve-Path (Join-Path $RepoRoot $RelativePath) -ErrorAction SilentlyContinue
        if ($null -ne $resolved) {
            return $resolved.Path
        }
        return $null
    }

    $pdfDirectory = Join-Path $RepoRoot "local-review-pdfs"
    if (-not (Test-Path -LiteralPath $pdfDirectory)) {
        return $null
    }

    $sample = Get-ChildItem -LiteralPath $pdfDirectory -Filter "*.pdf" -File |
        Sort-Object Length -Descending |
        Select-Object -First 1
    if ($null -eq $sample) {
        return $null
    }
    return $sample.FullName
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$pdfFullPath = Resolve-SmokePdfPath -RepoRoot $repoRoot -RelativePath $PdfPath
$pdfFileName = if ($pdfFullPath) { Split-Path -Leaf $pdfFullPath } else { "" }
$disclaimer = New-UnicodeString @(0x975E, 0x8BCA, 0x65AD, 0x7ED3, 0x8BBA, 0x3001, 0x9700, 0x7ED3, 0x5408, 0x4E34, 0x5E8A, 0x3002)
$results = New-Object System.Collections.Generic.List[object]
$startedAt = Get-Date

if ($null -eq $pdfFullPath) {
    throw "PDF sample not found. Provide -PdfPath explicitly or add a PDF under local-review-pdfs."
}

if ($NetworkLive -and ([string]$env:QIYAN_NETWORK_DATA_PROVIDER).Trim().ToLowerInvariant() -ne "live") {
    throw "-NetworkLive requires QIYAN_NETWORK_DATA_PROVIDER=live in the current shell and a backend started with the same explicit opt-in."
}

function Join-Url {
    param([string]$Base, [string]$Path)
    return $Base.TrimEnd("/") + "/" + $Path.TrimStart("/")
}

function Get-Headers {
    $headers = @{}
    if ($AccessToken.Trim()) {
        $headers["X-Access-Token"] = $AccessToken
        $headers["X-Qiyan-Reviewer"] = $ReviewerId
    }
    return $headers
}

function Add-Result {
    param(
        [string]$Flow,
        [int]$Status,
        [string]$RequestId,
        [string]$Notes
    )

    $results.Add([pscustomobject]@{
            Flow = $Flow
            Status = $Status
            RequestId = $RequestId
            Notes = $Notes
        }) | Out-Null
}

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) {
        throw $Message
    }
}

function Invoke-Json {
    param(
        [string]$Method,
        [string]$Url,
        [object]$Body = $null,
        [string]$RawBody = ""
    )

    $headers = Get-Headers
    $params = @{
        Method = $Method
        Uri = $Url
        Headers = $headers
        UseBasicParsing = $true
    }
    if ($RawBody) {
        $params["ContentType"] = "application/json"
        $params["Body"] = [System.Text.Encoding]::UTF8.GetBytes($RawBody)
    }
    elseif ($null -ne $Body) {
        $params["ContentType"] = "application/json"
        $jsonBody = $Body | ConvertTo-Json -Depth 30
        $params["Body"] = [System.Text.Encoding]::UTF8.GetBytes($jsonBody)
    }
    $response = Invoke-WebRequest @params
    $content = Get-ResponseText -Response $response
    $contentTypeValue = $null
    try {
        $contentTypeValue = $response.Headers["Content-Type"]
    }
    catch {
        $contentTypeValue = $null
    }

    $contentType = (@($contentTypeValue) -join ",")
    $trimmedContent = $content.TrimStart()
    $payload = $content
    if ($contentType -match "json" -or $trimmedContent.StartsWith("{") -or $trimmedContent.StartsWith("[")) {
        $payload = $content | ConvertFrom-Json
    }

    return [pscustomobject]@{
        Status = [int]$response.StatusCode
        Headers = $response.Headers
        Payload = $payload
        RawContent = $content
    }
}

function Get-ResponseText {
    param($Response)

    $rawStreamProperty = $Response.PSObject.Properties["RawContentStream"]
    if ($null -ne $rawStreamProperty -and $null -ne $rawStreamProperty.Value) {
        $stream = $rawStreamProperty.Value
        if ($stream.CanSeek) {
            $stream.Position = 0
        }
        $memory = New-Object System.IO.MemoryStream
        $stream.CopyTo($memory)
        return [System.Text.Encoding]::UTF8.GetString($memory.ToArray())
    }

    return [string]$Response.Content
}

function Get-RequestId {
    param($Headers)
    if ($null -eq $Headers) {
        return ""
    }
    $value = $null
    try {
        $value = $Headers["X-Request-ID"]
    }
    catch {
        $value = $null
    }
    if ($null -eq $value) {
        try {
            $value = $Headers["x-request-id"]
        }
        catch {
            $value = $null
        }
    }
    if ($null -eq $value) {
        return ""
    }
    return (@($value) -join ",")
}

function Ensure-ParentDirectory {
    param([string]$Path)
    if (-not $Path.Trim()) {
        return
    }

    $parent = Split-Path -Parent $Path
    if ($parent.Trim()) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
}

function Write-SmokeArtifacts {
    param(
        [bool]$Passed,
        [string]$FailureMessage = ""
    )

    $finishedAt = Get-Date
    $profile = if ($ProfileName.Trim()) {
        $ProfileName.Trim()
    }
    elseif ($AccessToken.Trim()) {
        "token"
    }
    else {
        "open"
    }
    $flowResults = $results.ToArray()
    $requestIds = @(
        $flowResults |
            Where-Object { $_.RequestId.Trim() } |
            ForEach-Object {
                [pscustomobject]@{
                    flow = $_.Flow
                    request_id = $_.RequestId
                }
            }
    )
    $evidence = [pscustomobject]@{
        profile = $profile
        backend_url = $BackendUrl
        pdf_file_name = $pdfFileName
        started_at = $startedAt.ToString("o")
        finished_at = $finishedAt.ToString("o")
        duration_seconds = [math]::Round(($finishedAt - $startedAt).TotalSeconds, 3)
        passed = $Passed
        token_profile_enabled = [bool]$AccessToken.Trim()
        reviewer_id = if ($AccessToken.Trim()) { $ReviewerId } else { "local-preview" }
        network_live = [bool]$NetworkLive
        disclaimer = $disclaimer
        flows = $flowResults
        request_ids = $requestIds
        failure = $FailureMessage
    }

    if ($OutputJson.Trim()) {
        Ensure-ParentDirectory -Path $OutputJson
        $evidence | ConvertTo-Json -Depth 10 | Set-Content -Path $OutputJson -Encoding utf8
    }

    if ($OutputMarkdown.Trim()) {
        Ensure-ParentDirectory -Path $OutputMarkdown
        $lines = New-Object System.Collections.Generic.List[string]
        [void]$lines.Add("# Internal preview smoke evidence")
        [void]$lines.Add("")
        [void]$lines.Add("| Field | Value |")
        [void]$lines.Add("|---|---|")
        [void]$lines.Add("| Profile | ``$profile`` |")
        [void]$lines.Add("| Backend URL | ``$BackendUrl`` |")
        [void]$lines.Add("| Passed | ``$Passed`` |")
        [void]$lines.Add("| Token profile enabled | ``$([bool]$AccessToken.Trim())`` |")
        [void]$lines.Add("| Started | ``$($startedAt.ToString("s"))`` |")
        [void]$lines.Add("| Finished | ``$($finishedAt.ToString("s"))`` |")
        [void]$lines.Add("| PDF sample | ``$pdfFileName`` |")
        [void]$lines.Add("| Disclaimer assertion | ``$disclaimer`` |")
        if ($FailureMessage.Trim()) {
            [void]$lines.Add("| Failure | $FailureMessage |")
        }
        [void]$lines.Add("")
        [void]$lines.Add("## Flow Results")
        [void]$lines.Add("")
        [void]$lines.Add("| Flow | Status | Request ID | Notes |")
        [void]$lines.Add("|---|---:|---|---|")
        foreach ($flow in $flowResults) {
            [void]$lines.Add("| $($flow.Flow) | $($flow.Status) | ``$($flow.RequestId)`` | $($flow.Notes) |")
        }
        [void]$lines.Add("")
        [void]$lines.Add("This smoke evidence is a technical preview artifact and is not formal clinician/research reviewer sign-off.")
        $lines | Set-Content -Path $OutputMarkdown -Encoding utf8
    }
}

$health = Invoke-Json -Method "GET" -Url (Join-Url $BackendUrl "/health")
Assert-True ($health.Status -eq 200) "Health check failed."
Add-Result -Flow "health" -Status $health.Status -RequestId (Get-RequestId $health.Headers) -Notes "status=$($health.Payload.status)"

$literatureSources = @(
    @{ Label = "literature_all"; Query = "q=%E7%89%B9%E5%BA%94%E6%80%A7%E7%9A%AE%E7%82%8E&source=all" },
    @{ Label = "literature_pubmed"; Query = "q=atopic%20dermatitis&source=pubmed" },
    @{ Label = "literature_cnki"; Query = "q=%E7%89%B9%E5%BA%94%E6%80%A7%E7%9A%AE%E7%82%8E&source=cn_literature" },
    @{ Label = "literature_uploaded_filter"; Query = "q=%E7%89%B9%E5%BA%94%E6%80%A7%E7%9A%AE%E7%82%8E&has_pdf_upload=true" }
)

foreach ($source in $literatureSources) {
    $response = Invoke-Json -Method "GET" -Url (Join-Url $BackendUrl "/api/literature/search?$($source.Query)")
    Assert-True ($response.Status -eq 200) "$($source.Label) failed."
    Assert-True ($null -ne $response.Payload.items) "$($source.Label) did not return items."
    Add-Result -Flow $source.Label -Status $response.Status -RequestId (Get-RequestId $response.Headers) -Notes "total=$($response.Payload.total)"
}

$curlConfig = ""
if ($AccessToken.Trim()) {
    $curlConfig = @(
        "header = `"X-Access-Token: $AccessToken`""
        "header = `"X-Qiyan-Reviewer: $ReviewerId`""
    ) -join [Environment]::NewLine
}
$uploadUrl = Join-Url $BackendUrl "/api/uploads/pdf"
$uploadHeaderFile = [System.IO.Path]::GetTempFileName()
$uploadBodyFile = [System.IO.Path]::GetTempFileName()
try {
    if ($curlConfig) {
        $curlConfig | & curl.exe --config "-" -sS -D $uploadHeaderFile -o $uploadBodyFile `
            -X POST $uploadUrl `
            -F "literature_id=cn-ad-barrier-006" `
            -F "file=@$pdfFullPath;type=application/pdf"
    }
    else {
        & curl.exe -sS -D $uploadHeaderFile -o $uploadBodyFile -X POST $uploadUrl `
            -F "literature_id=cn-ad-barrier-006" `
            -F "file=@$pdfFullPath;type=application/pdf"
    }
    if ($LASTEXITCODE -ne 0) {
        throw "curl.exe PDF upload failed with exit code $LASTEXITCODE."
    }
    $headerText = Get-Content $uploadHeaderFile -Raw
    $uploadBody = Get-Content $uploadBodyFile -Raw
    Assert-True ($headerText -match "HTTP\/\S+\s+201") "PDF upload did not return 201."
    $uploadPayload = $uploadBody | ConvertFrom-Json
    Assert-True ($uploadPayload.pdf_parse_status -eq "pending") "PDF upload did not return pending parse status."
    $uploadRequestId = if ($headerText -match "(?im)^X-Request-ID:\s*(.+)$") { $Matches[1].Trim() } else { "" }
    Add-Result -Flow "pdf_upload" -Status 201 -RequestId $uploadRequestId -Notes "upload_id=$($uploadPayload.pdf_upload_id)"
}
finally {
    Remove-Item -LiteralPath $uploadHeaderFile, $uploadBodyFile -Force -ErrorAction SilentlyContinue
}

$parse = Invoke-Json -Method "POST" -Url (Join-Url $BackendUrl "/api/uploads/pdf/auto-parse") -Body @{
    literature_id = "cn-ad-barrier-006"
    file_name = $uploadPayload.file_name
}
Assert-True ($parse.Status -eq 200) "PDF auto-parse failed."
Assert-True ($parse.Payload.pdf_parse_status -eq "parsed") "PDF auto-parse did not produce parsed status."
Assert-True ($null -ne $parse.Payload.pdf_parse_result) "PDF auto-parse did not return parse result."
Add-Result -Flow "pdf_auto_parse" -Status $parse.Status -RequestId (Get-RequestId $parse.Headers) -Notes "method=$($parse.Payload.pdf_parse_result.extraction_method)"

$rag = Invoke-Json -Method "POST" -Url (Join-Url $BackendUrl "/api/rag/answer") -Body @{
    question = New-UnicodeString @(0x7279, 0x5E94, 0x6027, 0x76AE, 0x708E, 0x548C, 0x76AE, 0x80A4, 0x5C4F, 0x969C, 0x6709, 0x4EC0, 0x4E48, 0x5173, 0x7CFB, 0xFF1F)
    source = "all"
    top_k = 2
}
Assert-True ($rag.Status -eq 200) "RAG answer failed."
Assert-True ($rag.Payload.disclaimer -eq $disclaimer) "RAG disclaimer mismatch."
Assert-True ($rag.Payload.citations.Count -gt 0) "RAG returned no citations."
Add-Result -Flow "rag_answer" -Status $rag.Status -RequestId (Get-RequestId $rag.Headers) -Notes "citations=$($rag.Payload.citations.Count)"

$ragExport = Invoke-Json -Method "POST" -Url (Join-Url $BackendUrl "/api/rag/answer/export") -RawBody $rag.RawContent
Assert-True ($ragExport.Status -eq 200) "RAG Markdown export failed."
Assert-True (($ragExport.Payload | Out-String).Contains($disclaimer)) "RAG Markdown export missing disclaimer."
Add-Result -Flow "rag_export" -Status $ragExport.Status -RequestId (Get-RequestId $ragExport.Headers) -Notes "markdown=ok"

$networkQuery = if ($NetworkLive) { New-UnicodeString @(0x9EC4, 0x82AA) } else { New-UnicodeString @(0x6D88, 0x98CE, 0x6563) }
$networkAnalysisType = if ($NetworkLive) { "herb" } else { "formula" }
$network = Invoke-Json -Method "POST" -Url (Join-Url $BackendUrl "/api/network/analyze") -Body @{
    query = $networkQuery
    analysis_type = $networkAnalysisType
    research_protocol = @{
        disease = "atopic_dermatitis"
        phenotype = "AD type 2 inflammation and skin barrier dysfunction"
        species = "Homo sapiens"
        evidence_policy = "direct_human_first"
        query_date = (Get-Date).ToString("yyyy-MM-dd")
    }
}
Assert-True ($network.Status -eq 202) "Network analyze failed."
if ($NetworkLive) {
    Assert-True ($network.Payload.data_mode -eq "live") "Network analyze did not enter live data mode."
}
else {
    Assert-True ($network.Payload.data_mode -eq "mock") "Network analyze did not stay in mock data mode."
}
$taskId = $network.Payload.task_id
Add-Result -Flow "network_analyze" -Status $network.Status -RequestId (Get-RequestId $network.Headers) -Notes "task=$taskId"

[void](Invoke-Json -Method "GET" -Url (Join-Url $BackendUrl "/api/network/result/$taskId"))
$networkResult = Invoke-Json -Method "GET" -Url (Join-Url $BackendUrl "/api/network/result/$taskId")
Assert-True ($networkResult.Status -eq 200) "Network result failed."
Assert-True ($networkResult.Payload.status -eq "completed") "Network result did not complete."
if ($NetworkLive) {
    Assert-True ($networkResult.Payload.data_mode -eq "live") "Network result did not stay in live data mode."
}
else {
    Assert-True ($networkResult.Payload.data_mode -eq "mock") "Network result did not stay in mock data mode."
}
Assert-True ($networkResult.Payload.result.disclaimer -eq $disclaimer) "Network disclaimer mismatch."
Assert-True ($networkResult.Payload.result.chains.Count -gt 0) "Network result has no chains."
if ($NetworkLive) {
    Assert-True ($networkResult.Payload.result.data_sources.Count -gt 0) "Live network result has no data sources."
    Assert-True ($networkResult.Payload.result.pipeline_steps.Count -gt 0) "Live network result has no pipeline steps."
    Add-Result -Flow "network_result" -Status $networkResult.Status -RequestId (Get-RequestId $networkResult.Headers) -Notes "mode=live; chains=$($networkResult.Payload.result.chains.Count); sources=$($networkResult.Payload.result.data_sources.Count); warnings=$($networkResult.Payload.warnings.Count)"
}
else {
    Assert-True ($networkResult.Payload.result.enrichment.terms.Count -gt 0) "Network result has no enrichment terms."
    Add-Result -Flow "network_result" -Status $networkResult.Status -RequestId (Get-RequestId $networkResult.Headers) -Notes "mode=mock; chains=$($networkResult.Payload.result.chains.Count); enrichment=$($networkResult.Payload.result.enrichment.terms.Count)"
}

$networkTasks = Invoke-Json -Method "GET" -Url (Join-Url $BackendUrl "/api/network/tasks")
Assert-True ($networkTasks.Status -eq 200) "Network task list failed."
$listedTask = @($networkTasks.Payload.tasks | Where-Object { $_.task_id -eq $taskId })
Assert-True ($listedTask.Count -eq 1) "Network task list did not contain the analyzed task."
Assert-True (-not ($listedTask[0].PSObject.Properties.Name -contains "owner_id")) "Network task list leaked owner identity."
Assert-True (-not $listedTask[0].formal_network_ready) "Network task list claimed formal research readiness."
Add-Result -Flow "network_task_list" -Status $networkTasks.Status -RequestId (Get-RequestId $networkTasks.Headers) -Notes "tasks=$($networkTasks.Payload.tasks.Count)"

$diseaseLineageRows = @($networkResult.Payload.result.target_lineage.disease_targets)
$adjudicationRowId = $null
if ($diseaseLineageRows.Count -gt 0 -and $diseaseLineageRows[0].lineage_row_id) {
    $adjudicationRowId = $diseaseLineageRows[0].lineage_row_id
}
if ($adjudicationRowId) {
    $adjudication = Invoke-Json -Method "POST" -Url (Join-Url $BackendUrl "/api/network/result/$taskId/adjudications") -Body @{
        lineage_row_id = $adjudicationRowId
        decision       = "needs_review"
        reason         = "smoke check"
    }
    Assert-True ($adjudication.Status -eq 201) "Network adjudication submit failed."
    Assert-True ($null -eq $adjudication.Payload.reviewer_id) "Network adjudication leaked reviewer identity."

    $afterAdjudication = Invoke-Json -Method "GET" -Url (Join-Url $BackendUrl "/api/network/result/$taskId")
    Assert-True ($afterAdjudication.Status -eq 200) "Network result after adjudication failed."
    Assert-True ($afterAdjudication.Payload.adjudication.counts.needs_review -eq 1) "Adjudication was not projected back."
    Assert-True (-not $afterAdjudication.Payload.result.readiness.formal_network_ready) "Adjudication flipped scientific readiness."
    Add-Result -Flow "network_adjudication" -Status $adjudication.Status -RequestId (Get-RequestId $adjudication.Headers) -Notes "row=$adjudicationRowId; readiness=unchanged"
}
else {
    Add-Result -Flow "network_adjudication" -Status 0 -RequestId "" -Notes "skipped=no adjudicable lineage row"
}

$networkReport = Invoke-Json -Method "GET" -Url (Join-Url $BackendUrl "/api/network/result/$taskId/report")
Assert-True ($networkReport.Status -eq 200) "Network report failed."
$reportText = [string]$networkReport.Payload
Assert-True ($reportText.Contains($disclaimer)) "Network report missing disclaimer."
Assert-True ($reportText.Contains("## 人工判定")) "Network report missing adjudication section."
Assert-True ($reportText.Contains("## 证据分级")) "Network report missing evidence grading section."
Add-Result -Flow "network_report" -Status $networkReport.Status -RequestId (Get-RequestId $networkReport.Headers) -Notes "markdown=ok"

$results | Format-Table -AutoSize
Write-SmokeArtifacts -Passed $true
Write-Host "Internal preview smoke passed." -ForegroundColor Green
