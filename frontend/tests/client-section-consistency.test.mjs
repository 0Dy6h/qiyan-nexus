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

test("literature and rag client result sections include supporting copy for review guidance", () => {
  const literatureSource = getSource("components/LiteratureSearchClient.tsx");
  const ragSource = getSource("components/RagAnswerClient.tsx");

  assert.match(literatureSource, /请优先核对来源、年份与解析状态/);
  assert.match(ragSource, /核对证据来源与检索边界/);
  assert.match(ragSource, /可核对证据数量/);
});
