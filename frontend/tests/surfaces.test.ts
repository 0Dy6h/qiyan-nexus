import assert from "node:assert/strict";
import { test } from "node:test";

import { getSurfaceCardStyle, getSurfaceSectionStyle } from "../lib/ui/surfaces";

test("getSurfaceCardStyle returns shared dark evidence card container for result items", () => {
  assert.deepEqual(getSurfaceCardStyle(), {
    background: "linear-gradient(180deg, var(--qiyan-surface), rgba(13, 23, 36, 0.92))",
    border: "1px solid rgba(148, 163, 184, 0.18)",
    borderRadius: 18,
    boxShadow: "0 18px 54px rgba(0, 0, 0, 0.26)",
    padding: 24,
  });
});

test("getSurfaceSectionStyle returns shared dark framed section container for form and result blocks", () => {
  assert.deepEqual(getSurfaceSectionStyle(), {
    background: "linear-gradient(180deg, rgba(16, 31, 49, 0.94), rgba(13, 23, 36, 0.94))",
    border: "1px solid rgba(148, 163, 184, 0.2)",
    borderRadius: 20,
    boxShadow: "0 22px 70px rgba(0, 0, 0, 0.3)",
    padding: 24,
  });
});
