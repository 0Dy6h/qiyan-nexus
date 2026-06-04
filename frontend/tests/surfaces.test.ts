import assert from "node:assert/strict";
import { test } from "node:test";

import { getSurfaceCardStyle, getSurfaceSectionStyle } from "../lib/ui/surfaces";

test("getSurfaceCardStyle returns shared light evidence card container for result items", () => {
  assert.deepEqual(getSurfaceCardStyle(), {
    background: "white",
    border: "1px solid #dbe7e3",
    borderRadius: 8,
    boxShadow: "0 14px 36px rgba(15, 23, 42, 0.05)",
    padding: 24,
  });
});

test("getSurfaceSectionStyle returns shared light framed section container for form and result blocks", () => {
  assert.deepEqual(getSurfaceSectionStyle(), {
    background: "white",
    border: "1px solid #dbe7e3",
    borderRadius: 8,
    boxShadow: "0 18px 54px rgba(15, 23, 42, 0.05)",
    padding: 24,
  });
});
