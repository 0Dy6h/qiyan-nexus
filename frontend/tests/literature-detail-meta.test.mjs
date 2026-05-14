import assert from "node:assert/strict";
import { test } from "node:test";

import { joinMetaItems } from "../lib/ui/card-meta.mjs";

test("joinMetaItems can build literature detail metadata line", () => {
  assert.equal(
    joinMetaItems(["语言 中文", "来源 中文文献", "期刊 中国中西医结合皮肤性病学杂志", "年份 2024", "文献 ID cn-ad-gbs-001"]),
    "语言 中文 · 来源 中文文献 · 期刊 中国中西医结合皮肤性病学杂志 · 年份 2024 · 文献 ID cn-ad-gbs-001",
  );
});
