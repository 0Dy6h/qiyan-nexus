param(
    [string]$BackendUrl = "http://127.0.0.1:8000",
    [string]$AccessToken = "",
    [string]$PdfPath = "local-review-pdfs\健脾养血祛风法治疗特应性皮炎临床疗效及对皮肤屏障功能的影响_杨雪松.pdf"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$pdfFullPath = Resolve-Path (Join-Path $repoRoot $PdfPath) -ErrorAction SilentlyContinue
$disclaimer = "非诊断结论、需结合临床。"
$results = New-Object System.Collections.Generic.List[object]

if ($null -eq $pdfFullPath) {
    throw "PDF sample not found at $PdfPath. Provide -PdfPath explicitly."
}

function Join-Url {
    param([string]$Base, [string]$Path)
    return $Base.TrimEnd("/") + "/" + $Path.TrimStart("/")
}

function Get-Headers {
    $headers = @{}
    if ($AccessToken.Trim()) {
        $headers["X-Access-Token"] = $AccessToken
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
        [object]$Body = $null
    )

    $headers = Get-Headers
    $params = @{
        Method = $Method
        Uri = $Url
        Headers = $headers
        ResponseHeadersVariable = "responseHeaders"
        StatusCodeVariable = "statusCode"
    }
    if ($null -ne $Body) {
        $params["ContentType"] = "application/json"
        $params["Body"] = ($Body | ConvertTo-Json -Depth 30)
    }
    $payload = Invoke-RestMethod @params
    return [pscustomobject]@{
        Status = [int]$statusCode
        Headers = $responseHeaders
        Payload = $payload
    }
}

function Get-RequestId {
    param($Headers)
    if ($null -eq $Headers) {
        return ""
    }
    if ($Headers.ContainsKey("X-Request-ID")) {
        return ($Headers["X-Request-ID"] -join ",")
    }
    if ($Headers.ContainsKey("x-request-id")) {
        return ($Headers["x-request-id"] -join ",")
    }
    return ""
}

$health = Invoke-Json -Method "GET" -Url (Join-Url $BackendUrl "/health")
Assert-True ($health.Status -eq 200) "Health check failed."
Add-Result -Flow "health" -Status $health.Status -RequestId (Get-RequestId $health.Headers) -Notes "status=$($health.Payload.status)"

$literatureSources = @(
    @{ Label = "literature_all"; Query = "q=特应性皮炎&source=all" },
    @{ Label = "literature_pubmed"; Query = "q=atopic%20dermatitis&source=pubmed" },
    @{ Label = "literature_cnki"; Query = "q=特应性皮炎&source=cn_literature" },
    @{ Label = "literature_uploaded_filter"; Query = "q=特应性皮炎&has_pdf_upload=true" }
)

foreach ($source in $literatureSources) {
    $response = Invoke-Json -Method "GET" -Url (Join-Url $BackendUrl "/api/literature/search?$($source.Query)")
    Assert-True ($response.Status -eq 200) "$($source.Label) failed."
    Assert-True ($null -ne $response.Payload.items) "$($source.Label) did not return items."
    Add-Result -Flow $source.Label -Status $response.Status -RequestId (Get-RequestId $response.Headers) -Notes "total=$($response.Payload.total)"
}

$curlHeaders = @()
if ($AccessToken.Trim()) {
    $curlHeaders = @("-H", "X-Access-Token: $AccessToken")
}
$uploadUrl = Join-Url $BackendUrl "/api/uploads/pdf"
$uploadHeaderFile = [System.IO.Path]::GetTempFileName()
$uploadBodyFile = [System.IO.Path]::GetTempFileName()
try {
    & curl.exe -sS -D $uploadHeaderFile -o $uploadBodyFile -X POST $uploadUrl @curlHeaders `
        -F "literature_id=cn-ad-barrier-006" `
        -F "file=@$($pdfFullPath.Path);type=application/pdf"
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
    question = "特应性皮炎和皮肤屏障有什么关系？"
    source = "all"
    top_k = 2
}
Assert-True ($rag.Status -eq 200) "RAG answer failed."
Assert-True ($rag.Payload.disclaimer -eq $disclaimer) "RAG disclaimer mismatch."
Assert-True ($rag.Payload.citations.Count -gt 0) "RAG returned no citations."
Add-Result -Flow "rag_answer" -Status $rag.Status -RequestId (Get-RequestId $rag.Headers) -Notes "citations=$($rag.Payload.citations.Count)"

$ragExport = Invoke-Json -Method "POST" -Url (Join-Url $BackendUrl "/api/rag/answer/export") -Body $rag.Payload
Assert-True ($ragExport.Status -eq 200) "RAG Markdown export failed."
Assert-True (($ragExport.Payload | Out-String).Contains($disclaimer)) "RAG Markdown export missing disclaimer."
Add-Result -Flow "rag_export" -Status $ragExport.Status -RequestId (Get-RequestId $ragExport.Headers) -Notes "markdown=ok"

$network = Invoke-Json -Method "POST" -Url (Join-Url $BackendUrl "/api/network/analyze") -Body @{
    query = "消风散"
    analysis_type = "formula"
}
Assert-True ($network.Status -eq 202) "Network analyze failed."
$taskId = $network.Payload.task_id
Add-Result -Flow "network_analyze" -Status $network.Status -RequestId (Get-RequestId $network.Headers) -Notes "task=$taskId"

[void](Invoke-Json -Method "GET" -Url (Join-Url $BackendUrl "/api/network/result/$taskId"))
$networkResult = Invoke-Json -Method "GET" -Url (Join-Url $BackendUrl "/api/network/result/$taskId")
Assert-True ($networkResult.Status -eq 200) "Network result failed."
Assert-True ($networkResult.Payload.status -eq "completed") "Network result did not complete."
Assert-True ($networkResult.Payload.result.disclaimer -eq $disclaimer) "Network disclaimer mismatch."
Assert-True ($networkResult.Payload.result.chains.Count -gt 0) "Network result has no chains."
Assert-True ($networkResult.Payload.result.enrichment.terms.Count -gt 0) "Network result has no enrichment terms."
Add-Result -Flow "network_result" -Status $networkResult.Status -RequestId (Get-RequestId $networkResult.Headers) -Notes "chains=$($networkResult.Payload.result.chains.Count); enrichment=$($networkResult.Payload.result.enrichment.terms.Count)"

$networkReport = Invoke-Json -Method "GET" -Url (Join-Url $BackendUrl "/api/network/result/$taskId/report")
Assert-True ($networkReport.Status -eq 200) "Network report failed."
Assert-True (($networkReport.Payload | Out-String).Contains($disclaimer)) "Network report missing disclaimer."
Add-Result -Flow "network_report" -Status $networkReport.Status -RequestId (Get-RequestId $networkReport.Headers) -Notes "markdown=ok"

$results | Format-Table -AutoSize
Write-Host "Internal preview smoke passed." -ForegroundColor Green
