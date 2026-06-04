import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const testFilePath = fileURLToPath(import.meta.url);

function getSource(relativePath: string) {
  return readFileSync(resolve(testFilePath, "..", "..", relativePath), "utf8");
}

test("RagAnswerClient imports fetchRagAnswerMarkdown and exposes an async onExportAnswer handler", () => {
  const source = getSource("components/RagAnswerClient.tsx");

  assert.match(source, /fetchRagAnswerMarkdown/);
  assert.match(source, /from "\.\.\/lib\/rag-export"/);
  assert.match(source, /buildAnswerMarkdownFileName/);
  assert.match(source, /async function onExportAnswer\(\)/);
  assert.match(source, /await fetchRagAnswerMarkdown\(state\.result\)/);
  assert.match(source, /URL\.createObjectURL\(/);
  assert.match(source, /URL\.revokeObjectURL\(/);
  assert.match(source, /anchor\.download = fileName/);
  // buildAnswerMarkdown was removed; backend now owns the markdown string.
  assert.doesNotMatch(source, /import.*buildAnswerMarkdown[^F]/);
});

test("RagAnswerClient renders an export button labeled 导出答案为 Markdown next to the answer copy", () => {
  const source = getSource("components/RagAnswerClient.tsx");

  assert.match(source, /onClick=\{onExportAnswer\}/);
  assert.match(source, /aria-label="导出答案为 Markdown"/);
  assert.match(source, /导出答案为 Markdown ↓/);
});
