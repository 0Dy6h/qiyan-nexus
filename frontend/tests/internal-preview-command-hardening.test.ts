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
  assert.match(source, /\[ValidateRange\(1,\s*65535\)\]\s*\[int\]\$BackendPort\s*=\s*8000/);
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
