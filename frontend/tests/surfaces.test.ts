import assert from "node:assert/strict";
import { test } from "node:test";

import { getSurfaceCardStyle, getSurfaceSectionStyle } from "../lib/ui/surfaces";

test("getSurfaceCardStyle returns shared off-white evidence card container for result items", () => {
  assert.deepEqual(getSurfaceCardStyle(), {
    background: "var(--qiyan-surface)",
    border: "1px solid var(--qiyan-line)",
    borderRadius: 8,
    boxShadow: "0 14px 36px rgba(18, 39, 35, 0.07)",
    padding: 24,
  });
});

test("getSurfaceSectionStyle returns shared off-white framed section container for form and result blocks", () => {
  assert.deepEqual(getSurfaceSectionStyle(), {
    background: "var(--qiyan-surface)",
    border: "1px solid var(--qiyan-line)",
    borderRadius: 8,
    boxShadow: "0 18px 54px rgba(18, 39, 35, 0.07)",
    padding: 24,
  });
});
