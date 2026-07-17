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
    background: "var(--qiyan-status-idle-bg)",
    border: "1px solid var(--qiyan-status-idle-line)",
    borderRadius: 14,
    padding: "16px 18px",
  });
});

test("getStatusCardStyle returns shared error card visuals", () => {
  assert.deepEqual(getStatusCardStyle("error"), {
    background: "var(--qiyan-status-error-bg)",
    border: "1px solid var(--qiyan-status-error-line)",
    borderRadius: 14,
    padding: "16px 18px",
  });
});

test("getStatusCardStyle returns distinct warning card visuals", () => {
  assert.deepEqual(getStatusCardStyle("warning"), {
    background: "var(--qiyan-status-warning-bg)",
    border: "1px solid var(--qiyan-status-warning-line)",
    borderRadius: 14,
    padding: "16px 18px",
  });
});

test("getStatusCardStyle returns distinct success and danger card visuals", () => {
  assert.deepEqual(getStatusCardStyle("success"), {
    background: "var(--qiyan-status-success-bg)",
    border: "1px solid var(--qiyan-status-success-line)",
    borderRadius: 14,
    padding: "16px 18px",
  });
  assert.deepEqual(getStatusCardStyle("danger"), {
    background: "var(--qiyan-status-danger-bg)",
    border: "1px solid var(--qiyan-status-danger-line)",
    borderRadius: 14,
    padding: "16px 18px",
  });
});

test("getStatusMessageStyle returns shared idle text visuals", () => {
  assert.deepEqual(getStatusMessageStyle("idle"), {
    color: "var(--qiyan-muted)",
    margin: 0,
    lineHeight: 1.6,
  });
});

test("getStatusMessageStyle returns shared error text visuals", () => {
  assert.deepEqual(getStatusMessageStyle("error"), {
    color: "var(--qiyan-status-error-text)",
    margin: 0,
    lineHeight: 1.6,
  });
});

test("getStatusMessageStyle returns distinct warning text visuals", () => {
  assert.deepEqual(getStatusMessageStyle("warning"), {
    color: "var(--qiyan-status-warning-text)",
    margin: 0,
    lineHeight: 1.6,
  });
});

test("getStatusMessageStyle returns distinct success and danger text visuals", () => {
  assert.deepEqual(getStatusMessageStyle("success"), {
    color: "var(--qiyan-status-success-text)",
    margin: 0,
    lineHeight: 1.6,
  });
  assert.deepEqual(getStatusMessageStyle("danger"), {
    color: "var(--qiyan-status-danger-text)",
    margin: 0,
    lineHeight: 1.6,
  });
});
