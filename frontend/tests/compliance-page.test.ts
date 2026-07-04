import assert from "node:assert/strict";
import { test } from "node:test";

import {
  getComplianceHighlights,
  getComplianceNavigationLinks,
  getCompliancePageIntro,
  getCompliancePlatformScope,
  getComplianceTrustPrinciples,
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

test("getComplianceHighlights privacy section discloses external LLM egress and PIPL handling", () => {
  const privacy = getComplianceHighlights().find((section) => section.title === "隐私与数据处理");
  assert.ok(privacy, "expected 隐私与数据处理 section to exist");

  const joined = privacy!.items.join("\n");
  // default deterministic path does not send data externally
  assert.match(joined, /默认/);
  assert.match(joined, /deterministic|不外发|不发送/);
  // when a real provider is enabled, question + cited chunks go to an external gateway
  assert.match(joined, /opencode_go|外部/);
  assert.match(joined, /问题|引用片段/);
  // PIPL minimal-necessary + no patient identity
  assert.match(joined, /PIPL/);
  assert.match(joined, /最小必要/);
  assert.match(joined, /患者身份|身份信息/);
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

test("getComplianceTrustPrinciples maps the forum's five trust principles to enforced backing", () => {
  const principles = getComplianceTrustPrinciples();
  assert.deepEqual(
    principles.map((p) => p.title),
    ["数据来源可追溯", "分析流程可审计", "模型输出保留证据链", "不替代实验/诊断结论", "大模型输出受控"],
  );
  // Every principle must state concrete repo backing, not just an aspiration.
  for (const principle of principles) {
    assert.ok(principle.detail.length > 0);
    assert.ok(principle.backing.length > 0);
  }
  // The evidence-chain principle must tie to the load-bearing citation contract.
  const evidenceChain = principles.find((p) => p.title === "模型输出保留证据链");
  assert.match(evidenceChain!.backing, /literature_id|grounding/);
});

test("getCompliancePlatformScope separates what the platform can do from what it cannot replace", () => {
  const scope = getCompliancePlatformScope();
  assert.ok(scope.canDo.length >= 3);
  assert.ok(scope.cannotReplace.length >= 3);
  const cannot = scope.cannotReplace.join("\n");
  // Honest non-substitution boundaries from the forum "不替代" slide.
  assert.match(cannot, /诊断|处方/);
  assert.match(cannot, /临床试验|药效/);
  assert.match(cannot, /网络药理学/);
});

test("getComplianceNavigationLinks includes literature and rag entry points", () => {
  assert.deepEqual(getComplianceNavigationLinks(), [
    { href: "/", label: "返回首页" },
    { href: "/literature", label: "查看文献检索" },
    { href: "/rag", label: "查看 RAG 问答" },
    { href: "/network", label: "查看机制线索" },
    { href: "/evals/rag-ad", label: "运行 RAG 评估" },
  ]);
});
