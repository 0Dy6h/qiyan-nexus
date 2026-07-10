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
  assert.match(source, /\[ValidateRange\(1,\s*65535\)\]\s*\[int\]\$BackendPort\s*=\s*8000/);
  assert.match(source, /\[ValidateRange\(1,\s*65535\)\]\s*\[int\]\$FrontendPort\s*=\s*3000/);
  assert.match(source, /\[string\]\$AccessToken\s*=\s*""/);
  assert.match(source, /\[switch\]\$Stop/);
  assert.match(source, /LITERATURE_RUNTIME_STATE_PATH/);
  assert.match(source, /CHUNK_RUNTIME_STATE_PATH/);
  assert.match(source, /NETWORK_TASKS_RUNTIME_STATE_PATH/);
  assert.match(source, /VECTOR_INDEX_RUNTIME_CACHE_PATH/);
  assert.match(source, /UPLOAD_STORAGE_DIR/);
  assert.match(source, /QIYAN_ACCESS_TOKENS/);
  assert.match(source, /ProcessStartInfo/);
  assert.match(source, /EnvironmentVariables/);
  assert.doesNotMatch(source, /ConvertTo-EnvCommand/);
  assert.doesNotMatch(source, /["']NEXT_PUBLIC_QIYAN_ACCESS_TOKEN["']\s*=/);
  assert.match(source, /EnvironmentVariables\.Remove\("NEXT_PUBLIC_QIYAN_ACCESS_TOKEN"\)/);
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
  assert.match(source, /\[string\]\$ReviewerId\s*=\s*"preview-smoke"/);
  assert.match(source, /\[string\]\$ProfileName\s*=\s*""/);
  assert.match(source, /\[string\]\$OutputJson\s*=\s*""/);
  assert.match(source, /\[string\]\$OutputMarkdown\s*=\s*""/);
  assert.match(source, /\[string\]\$PdfPath\s*=\s*""/);
  assert.match(source, /function Resolve-SmokePdfPath/);
  assert.match(source, /local-review-pdfs/);
  assert.match(source, /Get-ChildItem[\s\S]*-Filter "\*\.pdf"/);
  assert.match(source, /function New-UnicodeString/);
  assert.match(source, /X-Access-Token/);
  assert.match(source, /X-Qiyan-Reviewer/);
  assert.match(source, /--config\s+"-"/);
  assert.doesNotMatch(source, /"-H",\s*"X-Access-Token:/);
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
  assert.match(source, /\[string\]\$RawBody\s*=\s*""/);
  assert.match(source, /-RawBody\s+\$rag\.RawContent/);
  assert.match(source, /Internal preview smoke evidence/);
  assert.match(source, /Write-SmokeArtifacts/);
});

test("browser E2E stays open and never passes an access token through public frontend env", () => {
  const backendSource = getRepoSource("frontend/e2e/start-backend.mjs");
  const frontendSource = getRepoSource("frontend/e2e/start-frontend.mjs");
  const configSource = getRepoSource("frontend/playwright.config.ts");
  const verifySource = getRepoSource("scripts/verify-local.ps1");

  assert.doesNotMatch(backendSource, /QIYAN_E2E_ACCESS_TOKEN/);
  assert.match(backendSource, /QIYAN_ACCESS_TOKENS:\s*""/);
  assert.doesNotMatch(frontendSource, /QIYAN_E2E_ACCESS_TOKEN/);
  assert.doesNotMatch(frontendSource, /NEXT_PUBLIC_QIYAN_ACCESS_TOKEN/);
  assert.doesNotMatch(configSource, /hasE2EAccessToken/);
  assert.match(configSource, /reuseExistingServer:\s*!process\.env\.CI/);
  assert.doesNotMatch(verifySource, /E2ETokenProfile/);
  assert.doesNotMatch(verifySource, /QIYAN_E2E_ACCESS_TOKEN/);
});

test("cloud trial runbook keeps the backend token server-side behind per-reviewer Basic Auth", () => {
  const source = getRepoSource("docs/guides/cloud-trial-deployment-runbook.md");
  const readme = getRepoSource("README.md");

  assert.doesNotMatch(source, /NEXT_PUBLIC_QIYAN_ACCESS_TOKEN/);
  assert.match(source, /auth_basic\s+"Qiyan Nexus reviewer trial"/);
  assert.match(source, /auth_basic_user_file\s+\/etc\/nginx\/qiyan-reviewers\.htpasswd/);
  assert.match(source, /htpasswd[\s\S]*reviewer-a/);
  assert.match(source, /map\s+(?:\\)?\$host\s+(?:\\)?\$qiyan_backend_token/);
  assert.match(source, /chmod\s+600\s+\/etc\/nginx\/conf\.d\/qiyan-backend-token\.conf/);
  assert.doesNotMatch(source, /sed[^\n]*\$BACKEND_TOKEN(?![A-Z0-9_])/);
  assert.doesNotMatch(source, /grep[^\n]*\$BACKEND_TOKEN(?![A-Z0-9_])/);
  assert.match(source, /grep\s+-R\s+-F\s+-f\s+"\$BACKEND_TOKEN_FILE"/);
  assert.match(source, /proxy_set_header\s+X-Access-Token\s+\$qiyan_backend_token/);
  assert.match(source, /location\s+=\s+\/api\s*\{\s*return\s+308\s+\/api\/;\s*\}/);
  const reviewerHeaderOverrides = source.match(
    /proxy_set_header\s+X-Qiyan-Reviewer\s+\$remote_user/g,
  );
  assert.ok(reviewerHeaderOverrides && reviewerHeaderOverrides.length >= 2);
  assert.match(source, /log_format\s+qiyan_trial[\s\S]*(?:\\)?\$remote_user/);
  assert.match(
    source,
    /log_format\s+qiyan_trial[\s\S]{0,240}request="(?:\\)?\$request_method (?:\\)?\$uri"/,
  );
  assert.doesNotMatch(
    source,
    /log_format\s+qiyan_trial[\s\S]{0,240}request="(?:\\)?\$request"/,
  );
  assert.match(source, /access_log\s+\/var\/log\/nginx\/qiyan-trial-access\.log\s+qiyan_trial/);
  assert.match(source, /QIYAN_INTERNAL_API_BASE_URL=http:\/\/127\.0\.0\.1:8000/);
  assert.match(source, /QIYAN_INTERNAL_API_TOKEN=BACKEND_ONLY_TOKEN/);
  assert.match(source, /EnvironmentFile=\/etc\/qiyan\/frontend\.env/);
  assert.match(source, /chmod\s+640\s+\/etc\/qiyan\/frontend\.env/);
  assert.match(source, /X-Qiyan-Reviewer:\s+reviewer-b/);
  assert.match(source, /set\s+-euo\s+pipefail/);
  assert.match(source, /assert_status\s+401[\s\S]*"\$BASE\/"/);
  assert.match(source, /CREATE_STATUS[\s\S]*-w\s+"%\{http_code\}"[\s\S]*"202"/);
  assert.match(source, /\[\[\s+-n\s+"\$TASK_ID"\s+\]\]/);
  assert.match(source, /assert_status\s+404\s+--user\s+reviewer-b[\s\S]*\/result\/\$TASK_ID/);
  assert.match(source, /assert_status\s+404\s+--user\s+reviewer-b[\s\S]*\/result\/\$TASK_ID\/report/);
  assert.match(source, /assert_status\s+200\s+--user\s+reviewer-a[\s\S]*\/result\/\$TASK_ID\/report/);
  assert.match(
    source,
    /轮换时必须同时更新[^\n]*backend env[^\n]*frontend env[^\n]*nginx map/,
  );
  assert.match(source, /systemctl restart qiyan-api qiyan-web[\s\S]{0,120}systemctl reload nginx/);
  assert.match(source, /qiyan-trial access log[^\n]*不记录 query string/);
  assert.match(source, /nginx error log[^\n]*query/);
  const teardownSource = source.slice(source.indexOf("## 9. 拆除"));
  for (const requiredPath of [
    "/etc/qiyan/backend.env",
    "/etc/qiyan/frontend.env",
    "/etc/nginx/sites-available/qiyan",
    "/etc/systemd/system/qiyan-api.service",
    "/etc/systemd/system/qiyan-web.service",
    "/etc/fail2ban/filter.d/qiyan-basic-auth.conf",
    "/etc/fail2ban/jail.d/qiyan-basic-auth.local",
    "/etc/logrotate.d/qiyan-trial",
  ]) {
    assert.match(teardownSource, new RegExp(requiredPath.replaceAll("/", "\\/")));
  }
  assert.match(
    teardownSource,
    /qiyan-backend-token\.conf[\s\S]*nginx -t && sudo systemctl reload nginx/,
  );
  assert.doesNotMatch(readme, /不把 token 留在长驻子进程/);
  assert.match(readme, /token[^\n]*后端进程环境[^\n]*command line[^\n]*curl argv[^\n]*浏览器/);
  const redirectServerIndex = source.indexOf("return 301 https://$host$request_uri;");
  const tlsServerIndex = source.indexOf("listen 443 ssl http2;");
  const basicAuthIndex = source.indexOf('auth_basic "Qiyan Nexus reviewer trial";');
  assert.ok(redirectServerIndex >= 0);
  const httpListenMatches = [...source.matchAll(/listen 80;/g)];
  assert.ok(httpListenMatches.length >= 2);
  for (const match of httpListenMatches) {
    const listenIndex = match.index;
    assert.notEqual(listenIndex, undefined);
    const serverStart = source.lastIndexOf("server {", listenIndex);
    const nextServer = source.indexOf("server {", listenIndex + match[0].length);
    const serverSource = source.slice(serverStart, nextServer >= 0 ? nextServer : source.length);
    assert.match(
      serverSource,
      /access_log\s+(?:\/var\/log\/nginx\/qiyan-trial-access\.log\s+qiyan_trial|off);/,
    );
  }
  const redirectServerStart = source.lastIndexOf("server {", redirectServerIndex);
  const redirectServerSource = source.slice(redirectServerStart, tlsServerIndex);
  assert.match(
    redirectServerSource,
    /access_log\s+(?:\/var\/log\/nginx\/qiyan-trial-access\.log\s+qiyan_trial|off);/,
  );
  assert.ok(tlsServerIndex > redirectServerIndex);
  assert.ok(basicAuthIndex > tlsServerIndex);
});

test("current operator docs never recommend a browser-visible backend token", () => {
  for (const relativePath of [
    "README.md",
    "docs/current-state.md",
    "docs/checklists/internal-preview-reviewer-walkthrough.md",
    "frontend/e2e/README.md",
  ]) {
    assert.doesNotMatch(getRepoSource(relativePath), /NEXT_PUBLIC_QIYAN_ACCESS_TOKEN/);
  }
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
