import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import { getNetworkEvidenceLevelLabel } from "../lib/api/network";

const testFilePath = fileURLToPath(import.meta.url);

function getSource(relativePath: string) {
  return readFileSync(resolve(testFilePath, "..", "..", relativePath), "utf8");
}

test("network analysis client renders an evidence-grading badge per chain (ADR-0015)", () => {
  const clientSource = getSource("components/NetworkAnalysisClient.tsx");

  assert.match(clientSource, /getNetworkEvidenceLevelLabel/);
  assert.match(clientSource, /证据分级/);
  assert.match(clientSource, /chain\.evidence_level/);
});

test("evidence-level labels map every level and default to the honest floor", () => {
  assert.equal(getNetworkEvidenceLevelLabel("experimental"), "实验证据");
  assert.equal(getNetworkEvidenceLevelLabel("literature_supported"), "文献支撑");
  assert.equal(getNetworkEvidenceLevelLabel("predicted"), "预测证据");
  assert.equal(getNetworkEvidenceLevelLabel("mock_inferred"), "演示推断（未验证）");
  // Ungraded chains (null/undefined) must render as the lowest level, never blank.
  assert.equal(getNetworkEvidenceLevelLabel(null), "演示推断（未验证）");
  assert.equal(getNetworkEvidenceLevelLabel(undefined), "演示推断（未验证）");
});
