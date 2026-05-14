import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import { getPdfActionLabels, getPdfStatusCopy, getPdfStatusTone } from "../lib/ui/status-card.mjs";

const testFilePath = fileURLToPath(import.meta.url);

function getSource(relativePath) {
  return readFileSync(resolve(testFilePath, "..", "..", relativePath), "utf8");
}

test("pending pdf parse status maps to warning tone", () => {
  assert.equal(getPdfStatusTone("pending"), "warning");
});

test("parsed pdf parse status maps to success tone", () => {
  assert.equal(getPdfStatusTone("parsed"), "success");
});

test("failed pdf parse status maps to danger tone", () => {
  assert.equal(getPdfStatusTone("failed"), "danger");
});

test("pending status exposes both parse action labels", () => {
  assert.deepEqual(getPdfActionLabels("pending"), ["标记已解析", "标记解析失败"]);
});

test("missing status exposes no parse action labels", () => {
  assert.deepEqual(getPdfActionLabels(null), []);
});

test("parsed status copy prefers parser message over default label", () => {
  assert.equal(getPdfStatusCopy("parsed", false, "Mock parser completed successfully"), "Mock parser completed successfully");
});

test("parsing state copy takes precedence over parser message", () => {
  assert.equal(getPdfStatusCopy("pending", true, "Mock parser completed successfully"), "解析中...");
});

test("pdf upload metadata uses explicit labeled review-first copy", () => {
  const source = getSource("components/LiteraturePdfUploadClient.tsx");

  assert.match(source, /上传 ID/);
  assert.match(source, /当前文件/);
  assert.match(source, /存储路径/);
  assert.doesNotMatch(source, /Upload ID/);
});
