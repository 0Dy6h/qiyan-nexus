import assert from "node:assert/strict";
import { test } from "node:test";

import {
  getComplianceHighlights,
  getComplianceNavigationLinks,
  getCompliancePageIntro,
} from "../lib/compliance-page.mjs";

test("getCompliancePageIntro returns page title and boundary summary", () => {
  assert.deepEqual(getCompliancePageIntro(), {
    eyebrow: "Qiyan Nexus · 合规说明",
    title: "合规与使用边界",
    summary: "说明当前证据工作台的适用对象、输出边界、引用要求与隐私处理原则。",
  });
});

test("getComplianceHighlights returns the four minimum compliance sections", () => {
  assert.deepEqual(getComplianceHighlights().map((item) => item.title), [
    "适用对象",
    "输出边界",
    "引用与证据",
    "隐私与数据处理",
  ]);
  assert.equal(getComplianceHighlights()[1].items[0], "所有 AI 输出均为非诊断结论，需结合临床判断。 ");
});

test("getComplianceNavigationLinks includes literature and rag entry points", () => {
  assert.deepEqual(getComplianceNavigationLinks(), [
    { href: "/", label: "返回首页" },
    { href: "/literature", label: "查看文献检索" },
    { href: "/rag", label: "查看 RAG 问答" },
    { href: "/evals/rag-ad", label: "运行 RAG 评估" },
  ]);
});
