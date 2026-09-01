import assert from "node:assert/strict";
import { test } from "node:test";

import { getSurfaceCardStyle, getSurfaceSectionStyle } from "../lib/ui/surfaces";

test("getSurfaceCardStyle returns shared porcelain evidence card container for result items", () => {
  assert.deepEqual(getSurfaceCardStyle(), {
    background: "var(--qiyan-surface)",
    border: "1px solid var(--qiyan-line)",
    borderRadius: 16,
    boxShadow: "var(--qiyan-shadow-card)",
    padding: 24,
  });
});

test("getSurfaceSectionStyle returns shared porcelain framed section container for form and result blocks", () => {
  assert.deepEqual(getSurfaceSectionStyle(), {
    background: "var(--qiyan-surface)",
    border: "1px solid var(--qiyan-line)",
    borderRadius: 18,
    boxShadow: "var(--qiyan-shadow-card)",
    padding: 26,
  });
});
