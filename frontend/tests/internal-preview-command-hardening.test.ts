import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const testFilePath = fileURLToPath(import.meta.url);

function getRepoSource(relativePath: string) {
  return readFileSync(resolve(testFilePath, "..", "..", "..", relativePath), "utf8");
}

test("internal preview launcher passes process data without constructing PowerShell code", () => {
  const source = getRepoSource("scripts/run-internal-preview.ps1");
  const helperPath = resolve(
    testFilePath,
    "..",
    "..",
    "..",
    "scripts",
    "start-configured-process.ps1",
  );

  assert.equal(existsSync(helperPath), true);
  assert.match(source, /\[ValidateRange\(1,\s*65535\)\]\s*\[int\]\$BackendPort\s*=\s*8010/);
  assert.match(source, /\[ValidateRange\(1,\s*65535\)\]\s*\[int\]\$FrontendPort\s*=\s*3000/);
  assert.match(source, /-File/);
  assert.match(source, /QIYAN_PROCESS_EXECUTABLE/);
  assert.match(source, /QIYAN_PROCESS_ARGUMENTS_JSON/);
  assert.match(source, /QIYAN_PROCESS_LOG_PATH/);
  assert.match(source, /Get-Command\s+"pwsh"/);
  assert.doesNotMatch(source, /Arguments\s*=\s*[^\r\n]*-Command/);
  assert.doesNotMatch(source, /\$backendCommand|\$frontendCommand/);

  const helper = readFileSync(helperPath, "utf8");
  assert.match(helper, /ConvertFrom-Json/);
  assert.match(helper, /\[string\[\]\]\$arguments\s*=/);
  assert.match(helper, /\$ErrorActionPreference\s*=\s*"Continue"[\s\S]*&\s+\$executable\s+@arguments/);
  assert.match(helper, /&\s+\$executable\s+@arguments/);
  assert.doesNotMatch(helper, /Invoke-Expression|\biex\b/);
});

test("internal preview smoke parameters reject header and curl-config injection characters", () => {
  const source = getRepoSource("scripts/smoke-internal-preview.ps1");

  assert.ok(source.includes("[ValidatePattern('^[a-z0-9][a-z0-9._-]{0,63}$')]"));
  assert.ok(source.includes("[ValidatePattern('^[A-Za-z0-9._~-]*$')]"));
  assert.match(source, /\[string\]\$ReviewerId\s*=\s*"preview-smoke"/);
});

test("tcmtech honors an explicit -Stop and refuses unknown parameters", () => {
  const source = getRepoSource("scripts/tcmtech.ps1");

  // CmdletBinding 是防线:没有它,未知参数(如曾经的 -Stop)会被静默吞掉后照常启动
  assert.match(source, /\[CmdletBinding\(\)\]/);
  assert.match(source, /\[switch\]\$Stop/);
  assert.match(source, /&\s+\$previewScript\s+@stopArgs\s+-Stop/);
  // 停止分支必须在启动调用与浏览器启动之前,保证 -Stop 不产生任何服务/窗口
  const stopBranch = source.indexOf("if ($Stop)");
  const startCall = source.indexOf("@startArgs");
  const browserLaunch = source.indexOf("Start-Process");
  assert.ok(stopBranch >= 0);
  assert.ok(startCall > stopBranch);
  assert.ok(browserLaunch > stopBranch);
});

test("command entrypoints default to isolated ports and hard-fail on the reserved 8000", () => {
  const runSource = getRepoSource("scripts/run-internal-preview.ps1");
  assert.match(runSource, /\[int\]\$BackendPort\s*=\s*8010/);
  assert.match(runSource, /if \(\$BackendPort -eq 8000\)\s*\{[\s\S]{0,200}throw/);

  const verifySource = getRepoSource("scripts/verify-local.ps1");
  assert.match(verifySource, /else\s*\{\s*8010\s*\}/);
  assert.match(verifySource, /if \(\$E2eBackendPort -eq 8000\)\s*\{[\s\S]{0,200}throw/);

  const smokeSource = getRepoSource("scripts/smoke-internal-preview.ps1");
  assert.match(smokeSource, /\[string\]\$BackendUrl\s*=\s*"http:\/\/127\.0\.0\.1:8010"/);
  // 守卫拒绝把 smoke 请求打进本机回环 8000(会写进常驻项目)
  assert.ok(smokeSource.includes("(127\\.0\\.0\\.1|localhost):8000"));

  const collectSource = getRepoSource("scripts/collect-internal-preview-evidence.ps1");
  assert.match(collectSource, /\[string\]\$BackendPort\s*=\s*"8010"/);

  const playwrightSource = getRepoSource("frontend/playwright.config.ts");
  assert.match(playwrightSource, /QIYAN_E2E_BACKEND_PORT\s*\?\?\s*8010/);

  const startBackendSource = getRepoSource("frontend/e2e/start-backend.mjs");
  assert.match(startBackendSource, /QIYAN_E2E_BACKEND_PORT\s*\?\?\s*"8010"/);
});
