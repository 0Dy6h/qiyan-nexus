import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const testFilePath = fileURLToPath(import.meta.url);

function getPageSource(relativePath: string) {
  return readFileSync(resolve(testFilePath, "..", "..", relativePath), "utf8");
}

test("root layout uses a persistent app-style left rail navigation and reserves account entry", () => {
  const layoutSource = getPageSource("app/layout.tsx");
  const shellSource = getPageSource("components/WorkbenchShell.tsx");

  assert.match(layoutSource, /<WorkbenchShell>\{children\}<\/WorkbenchShell>/);
  assert.match(shellSource, /usePathname\(\)/);
  assert.match(shellSource, /className="workbench-frame home-app-frame"/);
  assert.match(shellSource, /className="home-app-rail"/);
  assert.match(shellSource, /aria-label="工作台侧栏"/);
  assert.match(shellSource, /className="home-account-entry"/);
  assert.match(shellSource, /登录 \/ 注册/);
  assert.match(shellSource, /next\/link/);
});

test("non-home workbench pages use logged-in starfield background while home stays isolated", () => {
  const source = getPageSource("app/workbench.css");

  assert.match(source, /\.home-page\s*{/);
  assert.match(source, /\.home-page::before\s*{/);
  assert.match(source, /\.home-page::after\s*{\s*display:\s*none;/s);
  assert.match(source, /\.workbench-page:not\(\.home-page\)::before\s*{/);
  assert.match(source, /\.workbench-page:not\(\.home-page\)::after\s*{/);
  assert.match(source, /qiyanStarDrift/);
  assert.match(source, /qiyanMeteorDrift/);
  assert.match(source, /@media \(prefers-reduced-motion: reduce\)[\s\S]*\.workbench-page:not\(\.home-page\)::after[\s\S]*animation:\s*none/);
});

test("non-home workbench pages keep homepage rail and teal surface continuity", () => {
  const source = getPageSource("app/workbench.css");

  assert.match(source, /\.workbench-frame\s*{[\s\S]*width:\s*min\(1480px, 100%\);[\s\S]*grid-template-columns:\s*260px minmax\(0, 1fr\)/);
  assert.match(source, /\.home-main-stack,\s*\.workbench-main-stack\s*{/);
  assert.match(source, /\.workbench-page \.home-app-rail \.workbench-nav\s*{/);
  assert.match(source, /\.workbench-page:not\(\.home-page\) \.workbench-nav\s*{[\s\S]*background:\s*rgba\(5, 12, 20, 0\.9\)/);
  assert.match(source, /\.workbench-page:not\(\.home-page\) \.workbench-nav a\[aria-current="page"\]\s*{[\s\S]*box-shadow:\s*inset 3px 0 0 var\(--qiyan-teal\)/);
  assert.match(source, /\.workbench-page:not\(\.home-page\) \.workbench-content-band\s*{[\s\S]*border-radius:\s*24px;[\s\S]*background:\s*rgba\(5, 12, 20, 0\.78\)/);
});

test("workbench routes render only right-side content inside the persistent shell", () => {
  const pages = [
    "app/rag/page.tsx",
    "app/literature/page.tsx",
    "app/network/page.tsx",
    "app/evals/rag-ad/page.tsx",
    "app/compliance/page.tsx",
  ];

  for (const pagePath of pages) {
    const source = getPageSource(pagePath);

    assert.doesNotMatch(source, /className="workbench-page"/);
    assert.doesNotMatch(source, /className="workbench-nav"/);
    assert.doesNotMatch(source, /getComplianceNavigationLinks\(\)/);
    assert.doesNotMatch(source, /padding:\s*"clamp\(12px, 2vw, 24px\)"/);
    assert.match(source, /workbench-kicker/);
    assert.match(source, /className="workbench-hero"/);
    assert.match(source, /className="workbench-content-band"/);
    assert.match(source, /aria-label=\"使用提醒\"/);
    assert.match(source, /使用提醒/);
  }
});

test("literature detail page renders right-side content and review-first reminder language", () => {
  const source = getPageSource("app/literature/[id]/page.tsx");

  assert.doesNotMatch(source, /className="workbench-page"/);
  assert.doesNotMatch(source, /className="workbench-nav"/);
  assert.doesNotMatch(source, /getComplianceNavigationLinks\(\)/);
  assert.doesNotMatch(source, /padding:\s*"clamp\(12px, 2vw, 24px\)"/);
  assert.match(source, /Evidence workbench/);
  assert.match(source, /文献详情/);
  assert.match(source, /先核对文献来源、摘要与年份，再进入 PDF 上传、解析状态与后续人工校正流程/);
  assert.match(source, /aria-label=\"使用提醒\"/);
  assert.doesNotMatch(source, /← 返回 RAG 问答/);
});
