import assert from "node:assert/strict";
import { test } from "node:test";

import {
  getStatusTone,
  getStatusCardStyle,
  getStatusMessageStyle,
} from "../lib/ui/status-card.mjs";

test("getStatusTone returns idle and error tones", () => {
  assert.equal(getStatusTone(false), "idle");
  assert.equal(getStatusTone(true), "error");
});

test("getStatusCardStyle returns shared idle card visuals", () => {
  assert.deepEqual(getStatusCardStyle("idle"), {
    background: "#f8fafc",
    border: "1px solid #e2e8f0",
    borderRadius: 12,
    padding: "16px 18px",
  });
});

test("getStatusCardStyle returns shared error card visuals", () => {
  assert.deepEqual(getStatusCardStyle("error"), {
    background: "#fff7ed",
    border: "1px solid #fdba74",
    borderRadius: 12,
    padding: "16px 18px",
  });
});

test("getStatusMessageStyle returns shared idle text visuals", () => {
  assert.deepEqual(getStatusMessageStyle("idle"), {
    color: "#64748b",
    margin: 0,
    lineHeight: 1.6,
  });
});

test("getStatusMessageStyle returns shared error text visuals", () => {
  assert.deepEqual(getStatusMessageStyle("error"), {
    color: "#b45309",
    margin: 0,
    lineHeight: 1.6,
  });
});
