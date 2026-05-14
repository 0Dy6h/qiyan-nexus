import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const testFilePath = fileURLToPath(import.meta.url);

function getPageSource(relativePath) {
  return readFileSync(resolve(testFilePath, "..", "..", relativePath), "utf8");
}

test("rag and literature page shells align with compliance shell navigation, intro, and usage reminder block", () => {
  const pages = [
    ["app/rag/page.tsx", "/rag"],
    ["app/literature/page.tsx", "/literature"],
  ];

  for (const [pagePath, currentHref] of pages) {
    const source = getPageSource(pagePath);

    assert.match(source, /padding:\s*"clamp\(20px, 4vw, 48px\)"/);
    assert.match(source, /aria-label=\"工作台导航\"/);
    assert.match(source, /getComplianceNavigationLinks\(\)/);
    assert.match(source, new RegExp(`link\\.href === \\"${currentHref.replace("/", "\\/")}\\"`));
    assert.match(source, /Evidence workbench/);
    assert.match(source, /aria-label=\"使用提醒\"/);
    assert.match(source, /使用提醒/);
    assert.doesNotMatch(source, /← 返回首页/);
    assert.doesNotMatch(source, /非诊断结论、需结合临床。/);
  }
});

test("literature detail page keeps workbench navigation and review-first reminder language", () => {
  const source = getPageSource("app/literature/[id]/page.tsx");

  assert.match(source, /padding:\s*"clamp\(20px, 4vw, 48px\)"/);
  assert.match(source, /aria-label=\"工作台导航\"/);
  assert.match(source, /getComplianceNavigationLinks\(\)/);
  assert.match(source, /link\.href === \"\/literature\"/);
  assert.match(source, /aria-current=\{isCurrent \? "page" : undefined\}/);
  assert.match(source, /Evidence workbench/);
  assert.match(source, /文献详情/);
  assert.match(source, /先核对文献来源、摘要与年份，再进入 PDF 上传、解析状态与后续人工校正流程/);
  assert.match(source, /aria-label=\"使用提醒\"/);
  assert.doesNotMatch(source, /← 返回 RAG 问答/);
});
