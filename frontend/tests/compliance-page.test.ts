import assert from "node:assert/strict";
import { test } from "node:test";

import {
  getComplianceHighlights,
  getComplianceNavigationLinks,
  getCompliancePageIntro,
} from "../lib/compliance-page";

test("getCompliancePageIntro returns page title and boundary summary", () => {
  assert.deepEqual(getCompliancePageIntro(), {
    eyebrow: "Qiyan Nexus · 合规说明",
    title: "合规与使用边界",
    summary:
      "说明当前证据工作台的适用对象、输出边界、引用要求、隐私处理原则、数据来源与 PDF 版权边界。",
  });
});

test("getComplianceHighlights returns the six minimum compliance sections in fixed order", () => {
  assert.deepEqual(getComplianceHighlights().map((item) => item.title), [
    "适用对象",
    "输出边界",
    "引用与证据",
    "隐私与数据处理",
    "数据来源说明",
    "PDF 版权声明",
  ]);
  assert.equal(getComplianceHighlights()[1].items[0], "所有 AI 输出均为非诊断结论，需结合临床判断。 ");
});

test("getComplianceHighlights data-source section explains seed, PubMed live sync, and uploaded pdf scope", () => {
  const dataSource = getComplianceHighlights().find((section) => section.title === "数据来源说明");
  assert.ok(dataSource, "expected 数据来源说明 section to exist");

  const joined = dataSource!.items.join("\n");
  assert.match(joined, /seed/);
  assert.match(joined, /PubMed/);
  assert.match(joined, /NCBI/);
  assert.match(joined, /上传 PDF/);
  assert.match(joined, /演示/);
});

test("getComplianceHighlights pdf-copyright section restricts redistribution and ties to runtime state", () => {
  const pdfCopyright = getComplianceHighlights().find((section) => section.title === "PDF 版权声明");
  assert.ok(pdfCopyright, "expected PDF 版权声明 section to exist");

  const joined = pdfCopyright!.items.join("\n");
  assert.match(joined, /仅在本地/);
  assert.match(joined, /不公开|不分发|不再分发/);
  assert.match(joined, /版权/);
  assert.match(joined, /研究/);
});

test("getComplianceNavigationLinks includes literature and rag entry points", () => {
  assert.deepEqual(getComplianceNavigationLinks(), [
    { href: "/", label: "返回首页" },
    { href: "/literature", label: "查看文献检索" },
    { href: "/rag", label: "查看 RAG 问答" },
    { href: "/evals/rag-ad", label: "运行 RAG 评估" },
  ]);
});
