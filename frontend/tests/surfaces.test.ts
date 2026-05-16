import assert from "node:assert/strict";
import { test } from "node:test";

import { getSurfaceCardStyle, getSurfaceSectionStyle } from "../lib/ui/surfaces";

test("getSurfaceCardStyle returns shared white card container for result items", () => {
  assert.deepEqual(getSurfaceCardStyle(), {
    background: "white",
    border: "1px solid #e2e8f0",
    borderRadius: 12,
    padding: 24,
  });
});

test("getSurfaceSectionStyle returns shared framed section container for form and result blocks", () => {
  assert.deepEqual(getSurfaceSectionStyle(), {
    background: "white",
    border: "1px solid #e2e8f0",
    borderRadius: 16,
    padding: 24,
  });
});
