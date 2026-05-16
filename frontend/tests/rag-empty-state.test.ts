import assert from "node:assert/strict";
import { test } from "node:test";

import { getCitationEmptyCopy } from "../lib/ui/states";

test("getCitationEmptyCopy returns shared rag empty citations message", () => {
  assert.equal(
    getCitationEmptyCopy(),
    "当前回答未返回可展示的引用卡片，请调整问题或来源后重试。",
  );
});
