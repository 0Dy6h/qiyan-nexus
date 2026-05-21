import assert from "node:assert/strict";
import { test } from "node:test";

import type { RagAnswerResponse } from "../lib/api/rag";
import { buildAnswerMarkdown, buildAnswerMarkdownFileName } from "../lib/rag-export";

const SAMPLE_RESULT: RagAnswerResponse = {
  question: "特应性皮炎和肠-脑-皮肤轴有什么关系？",
  answer: "基于当前检索到的证据片段，已优先返回与问题最相关的文献。",
  disclaimer: "非诊断结论、需结合临床。",
  answered_at: "2026-05-21T07:42:11.123456+00:00",
  retrieval: {
    applied_source: "all",
    applied_top_k: 2,
    available_citation_count: 16,
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
