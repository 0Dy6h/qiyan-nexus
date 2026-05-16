import assert from "node:assert/strict";
import { test } from "node:test";

import { getEmptyStateCopy, getStatusCopy } from "../lib/ui/states";

test("getStatusCopy returns unified submit/loading labels for literature page", () => {
  assert.deepEqual(getStatusCopy("literature", true), {
    submitLabel: "开始检索",
    loadingLabel: "检索中...",
  });
});

test("getStatusCopy returns unified submit/loading labels for rag page", () => {
  assert.deepEqual(getStatusCopy("rag", true), {
    submitLabel: "生成回答",
    loadingLabel: "生成中...",
  });
});

test("getEmptyStateCopy returns unified empty and error copy for literature page", () => {
  assert.deepEqual(getEmptyStateCopy("literature"), {
    idle: "提交检索后，从后端 API 获取文献结果。",
    error: "检索失败，请确认后端服务已启动。",
  });
});

test("getEmptyStateCopy returns unified empty and error copy for rag page", () => {
  assert.deepEqual(getEmptyStateCopy("rag"), {
    idle: "提交问题后，从后端 /api/rag/answer 获取 mock 回答与 citation cards。",
    error: "请求失败，请确认后端服务已启动。",
  });
});
