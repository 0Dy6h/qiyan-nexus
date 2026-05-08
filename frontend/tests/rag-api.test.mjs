import assert from "node:assert/strict";
import { test } from "node:test";

import {
  buildRagAnswerRequest,
  buildRagAnswerUrl,
  getRagSourceLabel,
} from "../lib/api/rag.mjs";

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
