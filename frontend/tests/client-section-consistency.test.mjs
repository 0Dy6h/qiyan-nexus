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

test("literature result cards use explicit labeled metadata copy", () => {
  const literatureSource = getSource("components/LiteratureSearchClient.tsx");

  assert.match(literatureSource, /语言 \$\{item\.language === "zh" \? "中文" : "英文"\}/);
  assert.match(literatureSource, /来源 \$\{getLiteratureSourceLabel\(item\.source_type\)\}/);
  assert.match(literatureSource, /期刊 \$\{item\.source\}/);
  assert.match(literatureSource, /年份 \$\{String\(item\.year\)\}/);
  assert.match(literatureSource, /解析状态 \$\{getPdfParseStatusLabel\(item\.pdf_parse_status \?\? null\)\}/);
});

test("rag citation cards use explicit labeled metadata copy", () => {
  const ragSource = getSource("components/RagAnswerClient.tsx");

  assert.match(ragSource, /来源 \$\{citation\.source\}/);
  assert.match(ragSource, /置信度 \$\{formatConfidence\(citation\.confidence\)\}/);
  assert.doesNotMatch(ragSource, /\["证据来源", citation\.source/);
});

test("rag answer and retrieval metadata sections use unified applied retrieval labels", () => {
  const ragSource = getSource("components/RagAnswerClient.tsx");

  assert.match(ragSource, /`应用来源 \$\{getRagSourceLabel\(state\.result\.retrieval\.applied_source\)\}`/);
  assert.match(ragSource, /`应用 top_k \$\{state\.result\.retrieval\.applied_top_k\}`/);
  assert.match(ragSource, /`可用引用数 \$\{state\.result\.retrieval\.available_citation_count\}`/);
  assert.doesNotMatch(ragSource, /`当前可用引用数 \$\{state\.result\.retrieval\.available_citation_count\}`/);
  assert.doesNotMatch(ragSource, /`当前来源 \$\{getRagSourceLabel\(state\.result\.retrieval\.applied_source\)\}`/);
  assert.doesNotMatch(ragSource, /`当前 top_k \$\{state\.result\.retrieval\.applied_top_k\}`/);
});

test("rag citation section mirrors applied retrieval boundaries instead of request inputs", () => {
  const ragSource = getSource("components/RagAnswerClient.tsx");

  assert.match(ragSource, /应用来源：\{getRagSourceLabel\(state\.result\.retrieval\.applied_source\)\}/);
  assert.match(ragSource, /应用 top_k：[\s\S]*\{state\.result\.retrieval\.applied_top_k\}/);
  assert.doesNotMatch(ragSource, /当前应用来源过滤：\{getRagSourceLabel\(state\.result\.retrieval\.applied_source\)\}/);
  assert.doesNotMatch(ragSource, /当前应用 top_k：[\s\S]*\{state\.result\.retrieval\.applied_top_k\}/);
  assert.doesNotMatch(ragSource, /当前来源过滤：\{getRagSourceLabel\(state\.source\)\}/);
  assert.doesNotMatch(ragSource, /请求 top_k：\{state\.topK\}/);
});
