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
  assert.match(shellSource, /内部预览版/);
  assert.match(shellSource, /className="meteor-shower"/);
  assert.match(shellSource, /aria-hidden="true"/);
  assert.match(shellSource, /next\/link/);
});

test("workbench shell uses a clean meteor background without legacy decorative clutter", () => {
  const source = getPageSource("app/workbench.css");

  assert.match(source, /--qiyan-glass-bg/);
  assert.match(source, /\.workbench-page:not\(\.home-page\)::before\s*{/);
  assert.match(source, /\.workbench-page:not\(\.home-page\)::after\s*{/);
  assert.match(source, /\.meteor-shower\s*{/);
  assert.match(source, /\.meteor::before\s*{/);
  assert.match(source, /qiyanStarDrift/);
  assert.match(source, /meteorFall/);
  assert.doesNotMatch(source, /qiyanMeteorDrift/);
  assert.doesNotMatch(source, /linear-gradient\(rgba\(56, 189, 248/);
  assert.match(source, /@media \(prefers-reduced-motion: reduce\)[\s\S]*\.meteor[\s\S]*animation:\s*none/);
});

test("non-home workbench pages keep homepage rail and glass surface continuity", () => {
  const source = getPageSource("app/workbench.css");

  assert.match(source, /\.workbench-frame\s*{[\s\S]*width:\s*min\(1480px, 100%\);[\s\S]*grid-template-columns:\s*260px minmax\(0, 1fr\)/);
  assert.match(source, /\.home-main-stack,\s*\.workbench-main-stack\s*{/);
  assert.match(source, /\.workbench-page \.home-app-rail \.workbench-nav\s*{/);
  assert.match(source, /\.workbench-page:not\(\.home-page\) \.workbench-nav\s*{[\s\S]*background:\s*var\(--qiyan-glass-bg\)/);
  assert.match(source, /\.workbench-page:not\(\.home-page\) \.workbench-nav a\[aria-current="page"\]\s*{[\s\S]*box-shadow:\s*inset 3px 0 0 var\(--qiyan-teal\)/);
  assert.match(source, /\.workbench-page:not\(\.home-page\) \.workbench-content-band\s*{[\s\S]*border-radius:\s*24px;[\s\S]*background:\s*rgba\(5, 12, 20, 0\.025\)/);
  assert.match(source, /\.workbench-page:not\(\.home-page\) \.workbench-content-band\s*{[\s\S]*backdrop-filter:\s*var\(--qiyan-glass-filter\)/);
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

test("literature detail page offers a next-step path into evidence question answering", () => {
  const source = getPageSource("app/literature/[id]/page.tsx");

  assert.match(source, /aria-label="文献详情下一步"/);
  assert.match(source, /下一步：带这篇文献去问证据/);
  assert.match(source, /const literatureQuestion = encodeURIComponent\(/);
  assert.match(source, /请基于证据概述《\$\{item\.title\}》与特应性皮炎中医药研究的关系，并列出可核对引用。/);
  assert.match(source, /href=\{`\/rag\?question=\$\{literatureQuestion\}`\}/);
  assert.match(source, /带这篇文献去问证据 →/);
});

test("home page presents the core evidence workflow instead of a module inventory", () => {
  const source = getPageSource("app/page.tsx");

  assert.match(source, /查证据/);
  assert.match(source, /问证据/);
  assert.match(source, /看机制线索/);
  assert.match(source, /可导出的证据材料/);
  assert.match(source, /查文献[\s\S]*上传\/归档证据[\s\S]*提问[\s\S]*核引用[\s\S]*导出/);
  assert.doesNotMatch(source, /title: "网络药理学"/);
});

test("workbench navigation uses user-facing mechanism exploration language", () => {
  const shellSource = getPageSource("components/WorkbenchShell.tsx");
  const networkPageSource = getPageSource("app/network/page.tsx");
  const networkClientSource = getPageSource("components/NetworkAnalysisClient.tsx");

  assert.match(shellSource, /label: "机制线索"/);
  assert.doesNotMatch(shellSource, /label: "网络药理学"/);
  assert.match(networkPageSource, /机制线索探索（mock）/);
  assert.match(networkPageSource, /不是正式网络药理学分析结论/);
  assert.match(networkPageSource, /aria-label="机制线索能力边界"/);
  assert.match(networkPageSource, /aria-label="机制线索演示数据说明"/);
  assert.match(networkPageSource, /加载机制线索面板/);
  assert.match(networkClientSource, /aria-label="机制线索分析对象"/);
  assert.match(networkClientSource, /aria-label="机制线索对象类型"/);
  assert.doesNotMatch(networkClientSource, /aria-label="网络药理学分析对象"/);
});
