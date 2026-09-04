param(
    # 本机 8000 被另一项目常驻占用，默认必须走隔离端口（CORS 固定 3000）
    [ValidateRange(1, 65535)]
    [int]$BackendPort = 8010,
    [ValidateRange(1, 65535)]
    [int]$FrontendPort = 3000,
    # 留空则用 run-internal-preview.ps1 的默认 runtime root，
    # 这样 pnpm preview:stop 也能停掉 tcmtech 起的服务
    [string]$RuntimeRoot = "",
    [string]$AccessToken = "",
    [string]$OpenTargetsManifestPath = "",
    # 自动打开默认浏览器；自动化/无头场景加 -NoBrowser
    [switch]$NoBrowser
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$previewScript = Join-Path $PSScriptRoot "run-internal-preview.ps1"

$startArgs = @{
    BackendPort  = $BackendPort
    FrontendPort = $FrontendPort
}
$stopArgs = @{}
if ($RuntimeRoot.Trim()) {
    $startArgs["RuntimeRoot"] = $RuntimeRoot
    $stopArgs["RuntimeRoot"] = $RuntimeRoot
}
if ($AccessToken.Trim()) {
    $startArgs["AccessToken"] = $AccessToken
}
if ($OpenTargetsManifestPath.Trim()) {
    $startArgs["OpenTargetsManifestPath"] = $OpenTargetsManifestPath
}

# 复用内部预览脚本：隔离 runtime、端口占用预检、健康检查、processes.json 进程登记
& $previewScript @startArgs

if (-not $NoBrowser) {
    Start-Process "http://127.0.0.1:$FrontendPort"
}

Write-Host ""
Write-Host "tcmtech 正在本终端前台运行，按 Ctrl+C 停止前后端服务并退出。" -ForegroundColor Cyan
Write-Host "（直接关闭终端窗口时服务会残留；再次运行 tcmtech 会先自动停掉上一次的服务。）"
try {
    while ($true) {
        Start-Sleep -Seconds 3600
    }
}
finally {
    # Ctrl+C 会展开管道并保证执行 finally；服务由 -Stop 按 processes.json 杀进程树
    Write-Host ""
    Write-Host "正在停止 tcmtech 服务..." -ForegroundColor Yellow
    & $previewScript @stopArgs -Stop
}
