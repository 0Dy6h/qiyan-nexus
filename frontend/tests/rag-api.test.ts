import assert from "node:assert/strict";
import { test } from "node:test";

import {
  buildRagAnswerRequest,
  buildRagAnswerUrl,
  getRagSourceLabel,
  type RagAnswerResponse,
} from "../lib/api/rag";

test("buildRagAnswerUrl returns rag endpoint with default backend base URL", () => {
  assert.equal(buildRagAnswerUrl(), "http://127.0.0.1:8000/api/rag/answer");
});

test("buildRagAnswerRequest trims question and preserves source/top_k", () => {
  assert.deepEqual(buildRagAnswerRequest("  特应性皮炎和肠-脑-皮肤轴有什么关系？  ", "pubmed", 3), {
    question: "特应性皮炎和肠-脑-皮肤轴有什么关系？",
    source: "pubmed",
    top_k: 3,
  });
});

test("getRagSourceLabel returns display text", () => {
  assert.equal(getRagSourceLabel("all"), "全部文献");
  assert.equal(getRagSourceLabel("cn_literature"), "中文文献");
  assert.equal(getRagSourceLabel("pubmed"), "PubMed");
});

test("RagAnswerResponse type carries provider, retrieval strategy, and token usage", () => {
  const payload: RagAnswerResponse = {
    question: "特应性皮炎和肠-脑-皮肤轴有什么关系？",
    answer: "answer",
    disclaimer: "非诊断结论、需结合临床。",
    answered_at: "2026-05-27T00:00:00+00:00",
    provider_name: "opencode_go",
    input_tokens: 128,
    output_tokens: 64,
    grounding: {
      status: "passed",
      policy: "opencode_go_tool_use_v1",
      checked: true,
      blocked_reason: null,
      allowed_evidence_refs: ["chunk-cn-ad-gbs-001-abstract"],
      matched_evidence_refs: ["chunk-cn-ad-gbs-001-abstract"],
      unsupported_evidence_refs: [],
      claim_count: 2,
      cited_claim_count: 2,
      structured_claims: [
        {
          text: "证据提示肠道菌群与皮肤屏障异常之间存在关联",
          evidence_refs: ["chunk-cn-ad-gbs-001-abstract"],
        },
      ],
      provider_native_grounding: true,
      tool_name: "record_grounded_claims",
      tool_call_count: 1,
    },
    retrieval: {
      applied_source: "all",
      applied_top_k: 2,
      available_citation_count: 16,
      strategy: "hybrid",
    },
    citations: [],
  };

  assert.equal(payload.provider_name, "opencode_go");
  assert.equal(payload.retrieval.strategy, "hybrid");
  assert.equal(payload.grounding.status, "passed");
  assert.equal(payload.grounding.policy, "opencode_go_tool_use_v1");
  assert.equal(payload.grounding.provider_native_grounding, true);
  assert.equal(payload.grounding.tool_name, "record_grounded_claims");
  assert.equal(payload.grounding.tool_call_count, 1);
  assert.equal(payload.grounding.claim_count, 2);
  assert.equal(payload.grounding.cited_claim_count, 2);
  assert.equal(payload.grounding.structured_claims[0].text, "证据提示肠道菌群与皮肤屏障异常之间存在关联");
  assert.equal(payload.input_tokens, 128);
  assert.equal(payload.output_tokens, 64);
});
