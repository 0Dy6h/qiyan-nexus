import assert from "node:assert/strict";
import { test } from "node:test";

import { buildNetworkReportFileName } from "../lib/network-report-export";

test("buildNetworkReportFileName uses sanitized task id and UTC timestamp", () => {
  assert.equal(
    buildNetworkReportFileName("network-abc123", "2026-05-30T01:02:03.000Z"),
    "qiyan-network-report-network-abc123-20260530-0102.md",
  );
});

test("buildNetworkReportFileName falls back when timestamp is malformed", () => {
  assert.equal(
    buildNetworkReportFileName("network/abc 123", "not-an-iso-timestamp"),
    "qiyan-network-report-network-abc-123.md",
  );
});
