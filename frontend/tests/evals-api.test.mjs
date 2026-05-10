import assert from "node:assert/strict";
import { test } from "node:test";

import {
  buildRagAdEvalReportUrl,
  formatEvalPassRate,
  getEvalItemStatusLabel,
} from "../lib/api/evals.mjs";

test("buildRagAdEvalReportUrl returns rag eval report endpoint", () => {
  assert.equal(buildRagAdEvalReportUrl(), "http://127.0.0.1:8000/api/evals/rag-ad/report");
});

test("formatEvalPassRate formats ratio as percentage", () => {
  assert.equal(formatEvalPassRate(0), "0%");
  assert.equal(formatEvalPassRate(0.625), "63%");
  assert.equal(formatEvalPassRate(1), "100%");
});

test("getEvalItemStatusLabel returns compact result labels", () => {
  assert.equal(getEvalItemStatusLabel(true), "通过");
  assert.equal(getEvalItemStatusLabel(false), "需复核");
});

test("getRagAdEvalReport fetches report payload", async () => {
  const originalFetch = globalThis.fetch;
  const captured = [];
  globalThis.fetch = async (url) => {
    captured.push(url);
    return {
      ok: true,
      async json() {
        return {
          summary: {
            total_questions: 20,
            passed_questions: 14,
            pass_rate: 0.7,
            citation_hit_count: 18,
            chunk_hit_count: 6,
            disclaimer_coverage_count: 20,
            must_not_violation_count: 0,
          },
          items: [],
        };
      },
    };
  };

  try {
    const { getRagAdEvalReport } = await import(`../lib/api/evals.mjs?ts=${Date.now()}`);
    const report = await getRagAdEvalReport();

    assert.deepEqual(captured, ["http://127.0.0.1:8000/api/evals/rag-ad/report"]);
    assert.equal(report.summary.total_questions, 20);
    assert.equal(report.summary.pass_rate, 0.7);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
