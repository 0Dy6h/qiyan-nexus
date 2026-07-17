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
  assert.match(shellSource, /aria-hidden="true"/);
  assert.match(shellSource, /next\/link/);
});

test("workbench shell uses a light porcelain research surface without decorative clutter", () => {
  const source = getPageSource("app/workbench.css");

  assert.match(source, /--qiyan-teal:\s*#0d9488/);
  assert.match(source, /--qiyan-teal-dark:\s*#0f766e/);
  assert.match(source, /--qiyan-page:\s*#f3f6f4/);
  assert.match(source, /--qiyan-surface:\s*#ffffff/);
  assert.match(source, /--qiyan-ink:\s*#172420/);
  assert.doesNotMatch(source, /meteor/);
  assert.doesNotMatch(source, /qiyanStarDrift/);
  assert.doesNotMatch(source, /--qiyan-glass-bg/);
  assert.doesNotMatch(source, /#020508/);
  assert.match(source, /@media \(prefers-reduced-motion: reduce\)/);
});

test("non-home workbench pages keep homepage rail and porcelain surface continuity", () => {
  const source = getPageSource("app/workbench.css");

  assert.match(source, /\.workbench-frame\s*{[\s\S]*width:\s*min\(1480px, 100%\);[\s\S]*grid-template-columns:\s*260px minmax\(0, 1fr\)/);
  assert.match(source, /\.home-main-stack,\s*\.workbench-main-stack\s*{/);
  assert.match(source, /\.home-app-rail\s*{[\s\S]*position:\s*sticky;[\s\S]*background:\s*var\(--qiyan-surface\)/);
  assert.match(source, /\.workbench-nav a\[aria-current="page"\]\s*{[\s\S]*background:\s*var\(--qiyan-teal-soft\)/);
  assert.match(source, /\.workbench-nav a\[aria-current="page"\]\s*{[\s\S]*box-shadow:\s*inset 3px 0 0 var\(--qiyan-teal\)/);
  assert.match(source, /\.workbench-content-band\s*{[\s\S]*display:\s*grid;[\s\S]*gap:\s*20px;/);
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

test("home page presents network pharmacology research as the primary workflow", () => {
  const source = getPageSource("app/page.tsx");

  assert.match(source, /窄领域网络药理学科研工作台/);
  assert.match(source, /定研究协议/);
  assert.match(source, /构建网络/);
  assert.match(source, /核证据/);
  assert.match(source, /出研究报告/);
  assert.match(source, /文献检索、PDF 归档与 RAG 问答是证据服务层/);
  assert.doesNotMatch(source, /先完成核心证据整理，再评价更多模块/);
});

test("workbench navigation makes network pharmacology the primary product surface", () => {
  const shellSource = getPageSource("components/WorkbenchShell.tsx");
  const networkPageSource = getPageSource("app/network/page.tsx");
  const networkClientSource = getPageSource("components/NetworkAnalysisClient.tsx");

  assert.match(shellSource, /label: "网络药理学"/);
  assert.match(shellSource, /Network Pharmacology Workbench/);
  assert.match(shellSource, /新建研究任务/);
  assert.doesNotMatch(shellSource, /label: "机制线索"/);
  assert.match(networkPageSource, /网络药理学研究工作台/);
  assert.match(networkPageSource, /研究协议/);
  assert.match(networkPageSource, /aria-label="机制线索能力边界"/);
  assert.match(networkPageSource, /aria-label="机制线索演示数据说明"/);
  assert.match(networkPageSource, /加载网络药理学研究面板/);
  assert.match(networkClientSource, /aria-label="机制线索分析对象"/);
  assert.match(networkClientSource, /aria-label="机制线索对象类型"/);
  assert.doesNotMatch(networkClientSource, /aria-label="网络药理学分析对象"/);
});
