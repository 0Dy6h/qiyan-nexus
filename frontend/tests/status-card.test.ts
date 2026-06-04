import assert from "node:assert/strict";
import { test } from "node:test";

import {
  getStatusTone,
  getStatusCardStyle,
  getStatusMessageStyle,
} from "../lib/ui/status-card";

test("getStatusTone returns idle and error tones", () => {
  assert.equal(getStatusTone(false), "idle");
  assert.equal(getStatusTone(true), "error");
});

test("getStatusCardStyle returns shared idle card visuals", () => {
  assert.deepEqual(getStatusCardStyle("idle"), {
    background: "#f8fafc",
    border: "1px solid #dbe7e3",
    borderRadius: 8,
    padding: "16px 18px",
  });
});

test("getStatusCardStyle returns shared error card visuals", () => {
  assert.deepEqual(getStatusCardStyle("error"), {
    background: "#fff7ed",
    border: "1px solid #fdba74",
    borderRadius: 8,
    padding: "16px 18px",
  });
});

test("getStatusCardStyle returns distinct warning card visuals", () => {
  assert.deepEqual(getStatusCardStyle("warning"), {
    background: "#fffbeb",
    border: "1px solid #facc15",
    borderRadius: 8,
    padding: "16px 18px",
  });
});

test("getStatusCardStyle returns distinct success and danger card visuals", () => {
  assert.deepEqual(getStatusCardStyle("success"), {
    background: "#f0fdfa",
    border: "1px solid #99f6e4",
    borderRadius: 8,
    padding: "16px 18px",
  });
  assert.deepEqual(getStatusCardStyle("danger"), {
    background: "#fef2f2",
    border: "1px solid #fecaca",
    borderRadius: 8,
    padding: "16px 18px",
  });
});

test("getStatusMessageStyle returns shared idle text visuals", () => {
  assert.deepEqual(getStatusMessageStyle("idle"), {
    color: "#5f6e68",
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

test("getStatusMessageStyle returns distinct warning text visuals", () => {
  assert.deepEqual(getStatusMessageStyle("warning"), {
    color: "#92400e",
    margin: 0,
    lineHeight: 1.6,
  });
});

test("getStatusMessageStyle returns distinct success and danger text visuals", () => {
  assert.deepEqual(getStatusMessageStyle("success"), {
    color: "#0f766e",
    margin: 0,
    lineHeight: 1.6,
  });
  assert.deepEqual(getStatusMessageStyle("danger"), {
    color: "#991b1b",
    margin: 0,
    lineHeight: 1.6,
  });
});
