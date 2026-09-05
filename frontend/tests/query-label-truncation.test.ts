import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import { truncateLabel } from "../lib/format-text";

const testFilePath = fileURLToPath(import.meta.url);

function getSource(relativePath: string) {
  return readFileSync(resolve(testFilePath, "..", "..", relativePath), "utf8");
}

test("truncateLabel keeps short labels intact and elides long ones", () => {
  assert.equal(truncateLabel("消风散"), "消风散");
  assert.equal(truncateLabel("  消风散  "), "消风散");
  assert.equal(truncateLabel("a".repeat(40)), "a".repeat(40));
  assert.equal(truncateLabel("a".repeat(41)), `${"a".repeat(40)}…`);
  assert.equal(truncateLabel("超".repeat(3500), 20), `${"超".repeat(20)}…`);
});

test("task list renders bounded query labels and keeps full name in title", () => {
  const source = getSource("components/NetworkTaskListClient.tsx");

  assert.match(source, /<span title=\{row\.query\}>\{truncateLabel\(row\.query\)\}<\/span>/);
  assert.match(source, /aria-label=\{`查看任务 \$\{truncateLabel\(row\.query\)\}`\}/);
  // 全量 query 不得直接进入可访问名称或无截断的展示节点
  assert.doesNotMatch(source, /aria-label=\{`查看任务 \$\{row\.query\}`\}/);
  assert.doesNotMatch(source, /<span>\{row\.query\}<\/span>/);
});

test("result summary sentence truncates the query and preserves it via title", () => {
  const source = getSource("components/NetworkAnalysisClient.tsx");

  assert.match(source, /title=\{result\.query\}/);
  assert.match(source, /分析对象 \$\{truncateLabel\(result\.query\)\}/);
  assert.doesNotMatch(source, /分析对象 \$\{result\.query\}/);
});
