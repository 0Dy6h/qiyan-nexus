import assert from "node:assert/strict";
import { test } from "node:test";

import {
  getMetaRowStyle,
  getMetaTextStyle,
  joinMetaItems,
} from "../lib/ui/card-meta.mjs";

test("joinMetaItems drops empty items and joins with bullets", () => {
  assert.equal(joinMetaItems(["中文", "", null, "PubMed", undefined, "2024"]), "中文 · PubMed · 2024");
});

test("getMetaRowStyle returns shared card meta layout", () => {
  assert.deepEqual(getMetaRowStyle(), {
    color: "#64748b",
    margin: 0,
    fontSize: 14,
    lineHeight: 1.6,
  });
});

test("getMetaTextStyle returns shared body text layout", () => {
  assert.deepEqual(getMetaTextStyle(), {
    color: "#475569",
    margin: "0 0 12px",
    lineHeight: 1.7,
  });
});
