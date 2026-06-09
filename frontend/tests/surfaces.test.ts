import assert from "node:assert/strict";
import { test } from "node:test";

import { getSurfaceCardStyle, getSurfaceSectionStyle } from "../lib/ui/surfaces";

test("getSurfaceCardStyle returns shared frosted evidence card container for result items", () => {
  assert.deepEqual(getSurfaceCardStyle(), {
    backdropFilter: "blur(2px)",
    background: "rgba(13, 23, 36, 0.025)",
    border: "1px solid rgba(204, 226, 241, 0.12)",
    borderRadius: 18,
    boxShadow: "0 18px 54px rgba(0, 0, 0, 0.26)",
    padding: 24,
  });
});

test("getSurfaceSectionStyle returns shared frosted framed section container for form and result blocks", () => {
  assert.deepEqual(getSurfaceSectionStyle(), {
    backdropFilter: "blur(2px)",
    background: "rgba(10, 24, 39, 0.03)",
    border: "1px solid rgba(204, 226, 241, 0.13)",
    borderRadius: 20,
    boxShadow: "0 22px 70px rgba(0, 0, 0, 0.28)",
    padding: 24,
  });
});
