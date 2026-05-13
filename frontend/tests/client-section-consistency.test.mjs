import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const testFilePath = fileURLToPath(import.meta.url);

function getSource(relativePath) {
  return readFileSync(resolve(testFilePath, "..", "..", relativePath), "utf8");
}

test("literature and rag client forms share labeled hierarchy and primary action rhythm", () => {
  const literatureSource = getSource("components/LiteratureSearchClient.tsx");
  const ragSource = getSource("components/RagAnswerClient.tsx");

  assert.match(literatureSource, /<form onSubmit=\{onSubmit\} style=\{\{ display: "grid", gap: 16 \}\}>/);
  assert.match(ragSource, /<form onSubmit=\{onSubmit\} style=\{\{ display: "grid", gap: 16 \}\}>/);

  assert.match(literatureSource, /检索关键词/);
  assert.match(literatureSource, /文献来源/);
  assert.match(literatureSource, /每页数量/);
  assert.match(ragSource, /问题/);
  assert.match(ragSource, /文献来源/);
  assert.match(ragSource, /引用数量 top_k/);

  assert.match(literatureSource, /minHeight: 44/);
  assert.match(ragSource, /minHeight: 44/);
  assert.match(literatureSource, /background: state\.isLoading \|\| state\.page >= state\.totalPages \? "#94a3b8" : "#0d9488"/);
});

test("literature detail and rag evidence sections share review-first supporting copy", () => {
  const literatureDetailSource = getSource("app/literature/[id]/page.tsx");
  const literaturePdfSource = getSource("components/LiteraturePdfUploadClient.tsx");
  const ragSource = getSource("components/RagAnswerClient.tsx");

  assert.match(literatureDetailSource, /先核对文献来源、摘要与年份，再进入 PDF 上传、解析状态与后续人工校正流程/);
  assert.match(literaturePdfSource, /先确认当前 PDF 与解析状态，再决定是继续自动解析、预览原文，还是进入人工校正/);
  assert.match(literaturePdfSource, /用于后续证据核对、解析与人工校正/);
  assert.match(literaturePdfSource, /可回到原文预览与状态面板，再人工标记当前 PDF 是否解析完成/);
  assert.match(ragSource, /核对证据来源与检索边界/);
  assert.match(ragSource, /可核对证据数量/);
});
