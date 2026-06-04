import assert from "node:assert/strict";
import { test } from "node:test";

import { buildAnswerMarkdownFileName } from "../lib/rag-export";

test("buildAnswerMarkdownFileName builds qiyan-rag-answer-YYYYMMDD-HHmm.md from ISO timestamp", () => {
  assert.equal(
    buildAnswerMarkdownFileName("2026-05-21T07:42:11.123456+00:00"),
    "qiyan-rag-answer-20260521-0742.md",
  );
});

test("buildAnswerMarkdownFileName falls back when timestamp is malformed", () => {
  assert.equal(buildAnswerMarkdownFileName("not-an-iso-timestamp"), "qiyan-rag-answer.md");
});
