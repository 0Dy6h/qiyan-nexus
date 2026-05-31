import assert from "node:assert/strict";
import { test } from "node:test";

import type { RagAnswerResponse } from "../lib/api/rag";
import { buildAnswerMarkdown, buildAnswerMarkdownFileName } from "../lib/rag-export";

const SAMPLE_RESULT: RagAnswerResponse = {
  question: "特应性皮炎和肠-脑-皮肤轴有什么关系？",
  answer: "基于当前检索到的证据片段，已优先返回与问题最相关的文献。",
  disclaimer: "非诊断结论、需结合临床。",
  answered_at: "2026-05-21T07:42:11.123456+00:00",
  provider_name: "deterministic",
  input_tokens: null,
  output_tokens: null,
  grounding: {
    status: "skipped",
    policy: "structured_claim_refs_v3",
    checked: false,
    blocked_reason: null,
    allowed_evidence_refs: ["chunk-cn-ad-gbs-001-abstract", "chunk-pdf-cn-ad-uploaded-007-uploaded"],
    matched_evidence_refs: [],
    unsupported_evidence_refs: [],
    claim_count: 0,
    cited_claim_count: 0,
    structured_claims: [
      {
        text: "证据提示肠道菌群与皮肤屏障异常之间存在关联",
        evidence_refs: ["chunk-cn-ad-gbs-001-abstract"],
      },
    ],
    provider_native_grounding: false,
    tool_name: null,
    tool_call_count: 0,
  },
  retrieval: {
    applied_source: "all",
    applied_top_k: 2,
    available_citation_count: 16,
    strategy: "keyword",
  },
  citations: [
    {
      literature_id: "cn-ad-gbs-001",
      chunk_id: "chunk-cn-ad-gbs-001-abstract",
      title: "肠-脑-皮肤轴与特应性皮炎中医证候研究",
      source: "CNKI curated AD sample",
      snippet: "围绕特应性皮炎、肠-脑-皮肤轴与中医证候关联进行综述。",
      quote: "脾虚湿蕴、血虚风燥与肠道微生态失衡的可解释关联",
      reason: "gut_skin_axis, tcm_syndrome",
      confidence: 0.86,
      source_type: "sample",
      pdf_upload_id: null,
    },
    {
      literature_id: "cn-ad-uploaded-007",
      chunk_id: "chunk-pdf-cn-ad-uploaded-007-uploaded",
      title: "上传 PDF：ad-evidence.pdf",
      source: "Uploaded PDF",
      snippet: "上传 PDF ad-evidence.pdf 已完成解析。",
      quote: "Mock parser 提取了特应性皮炎证据片段",
      reason: "uploaded_pdf, pdf_parse",
      confidence: 0.86,
      source_type: "uploaded_pdf",
      pdf_upload_id: "pdf-cn-ad-uploaded-007-ad-evidence-pdf",
    },
  ],
};

test("buildAnswerMarkdown includes question, answer, citations, retrieval, disclaimer, timestamp", () => {
  const md = buildAnswerMarkdown(SAMPLE_RESULT);

  assert.match(md, /^# Qiyan Nexus RAG 答案导出/);
  assert.ok(md.includes("特应性皮炎和肠-脑-皮肤轴有什么关系？"));
  assert.ok(md.includes("基于当前检索到的证据片段"));
  assert.ok(md.includes("2026-05-21T07:42:11.123456+00:00"));
  assert.ok(md.includes("应用来源：全部文献"));
  assert.ok(md.includes("应用 top_k：2"));
  assert.ok(md.includes("可用引用数：16"));
  assert.ok(md.includes("Provider：deterministic"));
  assert.ok(md.includes("检索策略：keyword"));
  assert.ok(md.includes("Grounding 状态：skipped"));
  assert.ok(md.includes("Grounding 策略：structured_claim_refs_v3"));
  assert.ok(md.includes("Provider-native grounding：false"));
  assert.ok(md.includes("Grounding Tool：无"));
  assert.ok(md.includes("Tool 调用数：0"));
  assert.ok(md.includes("句级引用覆盖：0/0"));
  assert.ok(md.includes("## 结构化声明"));
  assert.ok(md.includes("### Claim 1"));
  assert.ok(md.includes("证据提示肠道菌群与皮肤屏障异常之间存在关联"));
  assert.ok(md.includes("evidence_refs：chunk-cn-ad-gbs-001-abstract"));
  assert.ok(md.includes("Token 输入：未返回"));
  assert.ok(md.includes("Token 输出：未返回"));
  assert.ok(md.includes("## 引用证据"));
  assert.ok(md.includes("### 引用 1 — 肠-脑-皮肤轴与特应性皮炎中医证候研究"));
  assert.ok(md.includes("literature_id：cn-ad-gbs-001"));
  assert.ok(md.includes("chunk_id：chunk-cn-ad-gbs-001-abstract"));
  assert.ok(md.includes("置信度：86%"));
  assert.ok(md.includes("命中证据标签：gut_skin_axis, tcm_syndrome"));
  assert.ok(md.includes("### 引用 2 — 上传 PDF：ad-evidence.pdf"));
  assert.ok(md.includes("source_type：uploaded_pdf"));
  assert.ok(md.includes("pdf_upload_id：pdf-cn-ad-uploaded-007-ad-evidence-pdf"));
  assert.ok(md.includes("非诊断结论、需结合临床。"));
});

test("buildAnswerMarkdown includes token usage when provider returns it", () => {
  const md = buildAnswerMarkdown({
    ...SAMPLE_RESULT,
    provider_name: "opencode_go",
    input_tokens: 128,
    output_tokens: 64,
    retrieval: { ...SAMPLE_RESULT.retrieval, strategy: "hybrid" },
  });

  assert.ok(md.includes("Provider：opencode_go"));
  assert.ok(md.includes("检索策略：hybrid"));
  assert.ok(md.includes("Token 输入：128"));
  assert.ok(md.includes("Token 输出：64"));
});

test("buildAnswerMarkdown shows provider latency and cost when sli is present", () => {
  const md = buildAnswerMarkdown({
    ...SAMPLE_RESULT,
    provider_name: "opencode_go",
    input_tokens: 517,
    output_tokens: 1087,
    sli: {
      provider_latency_ms: 8423,
      estimated_cost_usd: 0.001234,
    },
  });

  assert.ok(md.includes("Provider 延迟：8423 ms"));
  assert.ok(md.includes("预估成本：$0.001234"));
});

test("buildAnswerMarkdown shows sli placeholders when latency and cost are absent", () => {
  const md = buildAnswerMarkdown(SAMPLE_RESULT);

  assert.ok(md.includes("Provider 延迟：未返回"));
  assert.ok(md.includes("预估成本：未估算"));
});

test("buildAnswerMarkdown includes OpenCode Go native grounding metadata", () => {
  const md = buildAnswerMarkdown({
    ...SAMPLE_RESULT,
    provider_name: "opencode_go",
    grounding: {
      ...SAMPLE_RESULT.grounding,
      policy: "opencode_go_tool_use_v1",
      provider_native_grounding: true,
      tool_name: "record_grounded_claims",
      tool_call_count: 1,
    },
  });

  assert.ok(md.includes("Provider：opencode_go"));
  assert.ok(md.includes("Grounding 策略：opencode_go_tool_use_v1"));
  assert.ok(md.includes("Provider-native grounding：true"));
  assert.ok(md.includes("Grounding Tool：record_grounded_claims"));
  assert.ok(md.includes("Tool 调用数：1"));
});

test("buildAnswerMarkdown includes blocked grounding details", () => {
  const md = buildAnswerMarkdown({
    ...SAMPLE_RESULT,
    provider_name: "opencode_go",
    answer: "当前模型草稿未通过引用证据校验，系统已拦截展示。",
    grounding: {
      ...SAMPLE_RESULT.grounding,
      status: "blocked",
      checked: true,
      blocked_reason: "unsupported_evidence_ref",
      matched_evidence_refs: [],
      unsupported_evidence_refs: ["chunk-unknown-ref"],
      claim_count: 2,
      cited_claim_count: 1,
    },
  });

  assert.ok(md.includes("Grounding 状态：blocked"));
  assert.ok(md.includes("Grounding 拦截原因：unsupported_evidence_ref"));
  assert.ok(md.includes("句级引用覆盖：1/2"));
  assert.ok(md.includes("Grounding 异常证据：chunk-unknown-ref"));
});

test("buildAnswerMarkdown includes semantic grounding gate details", () => {
  const md = buildAnswerMarkdown({
    ...SAMPLE_RESULT,
    provider_name: "opencode_go",
    answer: "当前模型草稿未通过引用证据校验，系统已拦截展示。",
    grounding: {
      ...SAMPLE_RESULT.grounding,
      status: "blocked",
      checked: true,
      blocked_reason: "semantic_low_support",
      semantic_threshold: 0.4,
      min_semantic_score: 0.12,
    },
  });

  assert.ok(md.includes("Grounding 拦截原因：semantic_low_support"));
  assert.ok(md.includes("语义阈值：0.40"));
  assert.ok(md.includes("最小语义支持度：12%"));
});

test("buildAnswerMarkdown shows semantic gate as disabled when threshold is null", () => {
  const md = buildAnswerMarkdown(SAMPLE_RESULT);

  assert.ok(md.includes("语义阈值：未启用"));
  assert.ok(md.includes("最小语义支持度：未计算"));
});

test("buildAnswerMarkdown emits empty-citation placeholder when citations are empty", () => {
  const md = buildAnswerMarkdown({ ...SAMPLE_RESULT, citations: [] });
  assert.ok(md.includes("（当前回答没有可核对的引用证据。）"));
  assert.ok(md.includes("非诊断结论、需结合临床。"));
});

test("buildAnswerMarkdownFileName builds qiyan-rag-answer-YYYYMMDD-HHmm.md from ISO timestamp", () => {
  assert.equal(
    buildAnswerMarkdownFileName("2026-05-21T07:42:11.123456+00:00"),
    "qiyan-rag-answer-20260521-0742.md",
  );
});

test("buildAnswerMarkdownFileName falls back when timestamp is malformed", () => {
  assert.equal(buildAnswerMarkdownFileName("not-an-iso-timestamp"), "qiyan-rag-answer.md");
});
