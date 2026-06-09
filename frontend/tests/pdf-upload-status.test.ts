import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import { getPdfActionLabels, getPdfStatusCopy, getPdfStatusTone } from "../lib/ui/status-card";

const testFilePath = fileURLToPath(import.meta.url);

function getSource(relativePath: string) {
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
  assert.match(source, /触发方式/);
  assert.match(source, /解析次数/);
  assert.match(source, /开始时间/);
  assert.match(source, /完成时间/);
  assert.doesNotMatch(source, /触发 \${currentParseTrigger}/);
  assert.doesNotMatch(source, /开始 \${formatTimestamp\(currentParseStartedAt\)}/);
  assert.doesNotMatch(source, /结束 \${formatTimestamp\(currentParseFinishedAt\)}/);
  assert.doesNotMatch(source, /state\.fileName \? <CardMetaRow items=\{\[`当前文件 \$\{state\.fileName\}`\]\} \/> : null/);
  assert.doesNotMatch(source, /Upload ID/);
});

test("pdf file picker and upload submit button have distinct accessible names", () => {
  const source = getSource("components/LiteraturePdfUploadClient.tsx");

  assert.match(source, /aria-label="选择 PDF 文件"/);
  assert.match(source, /: "上传 PDF"\}/);
  assert.doesNotMatch(source, /aria-label="上传 PDF"/);
});

test("parse result description branches on extraction_method", () => {
  const source = getSource("components/LiteraturePdfUploadClient.tsx");

  // pypdf success branch: describes that a real text-layer preview is shown,
  // and must NOT claim the capability is still upcoming.
  assert.match(source, /已抽取文本层预览/);

  // placeholder fallback branch: keeps the honest "still upcoming" copy
  // anchored on the file-level placeholder situation.
  assert.match(source, /回退到文件级占位说明/);
  assert.match(source, /OCR 能力将在后续接入/);

  // The previous unconditional sentence must not survive verbatim — it
  // contradicted the pypdf success path.
  assert.doesNotMatch(
    source,
    /当前仅展示文件级信息与预览提示，正文抽取与 OCR 能力将在后续接入。/,
  );

  // Must actually switch on the extraction_method discriminator.
  assert.match(source, /extraction_method === "pypdf-text-preview"/);
});

test("pdf preview surfaces parser quality warnings without hiding extracted text", () => {
  const source = getSource("components/LiteraturePdfUploadClient.tsx");

  assert.match(source, /currentParseResult\.quality_warning/);
  assert.match(source, /抽取质量提示/);
  assert.match(source, /预览说明 \$\{currentParseResult\.preview_text\}/);
});
