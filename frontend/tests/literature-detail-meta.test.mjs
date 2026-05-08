import assert from "node:assert/strict";
import { test } from "node:test";

import { joinMetaItems } from "../lib/ui/card-meta.mjs";

test("joinMetaItems can build literature detail metadata line", () => {
  assert.equal(
    joinMetaItems(["中文", "中文文献", "中国中西医结合皮肤性病学杂志", "2024", "文献 ID cn-ad-gbs-001"]),
    "中文 · 中文文献 · 中国中西医结合皮肤性病学杂志 · 2024 · 文献 ID cn-ad-gbs-001",
  );
});
