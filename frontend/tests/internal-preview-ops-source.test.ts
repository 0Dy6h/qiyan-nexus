import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const testFilePath = fileURLToPath(import.meta.url);

function getRepoSource(relativePath: string) {
  return readFileSync(resolve(testFilePath, "..", "..", "..", relativePath), "utf8");
}

function repoFileExists(relativePath: string) {
  return existsSync(resolve(testFilePath, "..", "..", "..", relativePath));
}

test("internal preview run script exposes isolated open/token profiles and stop cleanup", () => {
  assert.equal(repoFileExists("scripts/run-internal-preview.ps1"), true);
  const source = getRepoSource("scripts/run-internal-preview.ps1");

  assert.match(source, /\[string\]\$RuntimeRoot\s*=\s*"\.tmp\/internal-preview"/);
  assert.match(source, /\[string\]\$BackendPort\s*=\s*"8000"/);
  assert.match(source, /\[string\]\$FrontendPort\s*=\s*"3000"/);
  assert.match(source, /\[string\]\$AccessToken\s*=\s*""/);
  assert.match(source, /\[switch\]\$Stop/);
  assert.match(source, /LITERATURE_RUNTIME_STATE_PATH/);
  assert.match(source, /CHUNK_RUNTIME_STATE_PATH/);
  assert.match(source, /NETWORK_TASKS_RUNTIME_STATE_PATH/);
  assert.match(source, /VECTOR_INDEX_RUNTIME_CACHE_PATH/);
  assert.match(source, /UPLOAD_STORAGE_DIR/);
  assert.match(source, /QIYAN_ACCESS_TOKENS/);
  assert.match(source, /NEXT_PUBLIC_QIYAN_ACCESS_TOKEN/);
  assert.match(source, /backend\.log/);
  assert.match(source, /frontend\.log/);
  assert.match(source, /processes\.json/);
  assert.match(source, /taskkill/);
});

test("internal preview smoke script covers core API flows and token header", () => {
  assert.equal(repoFileExists("scripts/smoke-internal-preview.ps1"), true);
  const source = getRepoSource("scripts/smoke-internal-preview.ps1");

  assert.match(source, /\[string\]\$BackendUrl\s*=\s*"http:\/\/127\.0\.0\.1:8000"/);
  assert.match(source, /\[string\]\$AccessToken\s*=\s*""/);
  assert.match(source, /\[string\]\$ProfileName\s*=\s*""/);
  assert.match(source, /\[string\]\$OutputJson\s*=\s*""/);
  assert.match(source, /\[string\]\$OutputMarkdown\s*=\s*""/);
  assert.match(source, /\[string\]\$PdfPath\s*=\s*""/);
  assert.match(source, /function Resolve-SmokePdfPath/);
  assert.match(source, /local-review-pdfs/);
  assert.match(source, /Get-ChildItem[\s\S]*-Filter "\*\.pdf"/);
  assert.match(source, /function New-UnicodeString/);
  assert.match(source, /X-Access-Token/);
  assert.match(source, /\/health/);
  assert.match(source, /\/api\/literature\/search/);
  assert.match(source, /has_pdf_upload=true/);
  assert.match(source, /\/api\/uploads\/pdf/);
  assert.match(source, /\/api\/uploads\/pdf\/auto-parse/);
  assert.match(source, /\/api\/rag\/answer/);
  assert.match(source, /\/api\/rag\/answer\/export/);
  assert.match(source, /\/api\/network\/analyze/);
  assert.match(source, /\/api\/network\/result/);
  assert.match(source, /\/report/);
  assert.match(source, /0x975E/);
  assert.doesNotMatch(source, /非诊断结论、需结合临床。/);
  assert.match(source, /X-Request-ID/);
  assert.match(source, /curl\.exe/);
  assert.match(source, /ConvertTo-Json/);
  assert.match(source, /Internal preview smoke evidence/);
  assert.match(source, /Write-SmokeArtifacts/);
});

test("E2E token profile disables server reuse and passes token to both app servers", () => {
  const backendSource = getRepoSource("frontend/e2e/start-backend.mjs");
  const frontendSource = getRepoSource("frontend/e2e/start-frontend.mjs");
  const configSource = getRepoSource("frontend/playwright.config.ts");
  const verifySource = getRepoSource("scripts/verify-local.ps1");

  assert.match(backendSource, /QIYAN_E2E_ACCESS_TOKEN/);
  assert.match(backendSource, /QIYAN_ACCESS_TOKENS:\s*e2eAccessToken/);
  assert.match(frontendSource, /QIYAN_E2E_ACCESS_TOKEN/);
  assert.match(frontendSource, /NEXT_PUBLIC_QIYAN_ACCESS_TOKEN/);
  assert.match(configSource, /hasE2EAccessToken/);
  assert.match(configSource, /reuseExistingServer:\s*!hasE2EAccessToken && !process\.env\.CI/);
  assert.match(verifySource, /\[switch\]\$E2ETokenProfile/);
  assert.match(verifySource, /qiyan-e2e-token/);
  assert.match(verifySource, /QIYAN_E2E_ACCESS_TOKEN/);
});

test("internal preview evidence collector archives open and token smoke results", () => {
  assert.equal(repoFileExists("scripts/collect-internal-preview-evidence.ps1"), true);
  const source = getRepoSource("scripts/collect-internal-preview-evidence.ps1");

  assert.match(source, /\[string\]\$OutputRoot\s*=\s*"\.tmp\/internal-preview-evidence"/);
  assert.match(source, /\[string\]\$AccessToken\s*=\s*"trial-token"/);
  assert.match(source, /\[switch\]\$SkipTokenProfile/);
  assert.match(source, /\[switch\]\$KeepServicesOnFailure/);
  assert.match(source, /run-internal-preview\.ps1/);
  assert.match(source, /smoke-internal-preview\.ps1/);
  assert.match(source, /runtime-open/);
  assert.match(source, /runtime-token/);
  assert.match(source, /open-smoke\.json/);
  assert.match(source, /token-smoke\.json/);
  assert.match(source, /metadata\.json/);
  assert.match(source, /evidence-summary\.md/);
  assert.match(source, /X-Request-ID/);
  assert.match(source, /formal clinician\/research reviewer sign-off/);
  assert.match(source, /finally/);
  assert.match(source, /Stop-PreviewProfile/);
  assert.match(source, /Access token value is intentionally omitted/);
});
