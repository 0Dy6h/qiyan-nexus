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
    idle: "输入中医药或疾病相关关键词，检索 AD 证据文献。例如：特应性皮炎、消风散、肠道菌群。",
    error: "检索失败，请确认后端服务已启动。",
  });
});

test("getEmptyStateCopy returns unified empty and error copy for rag page", () => {
  assert.deepEqual(getEmptyStateCopy("rag"), {
    idle: "基于已检索到的文献证据提问，系统会给出附引用来源的证据简报。例如：消风散对特应性皮炎皮肤屏障功能有什么影响？",
    error: "请求失败，请确认后端服务已启动。",
  });
});
