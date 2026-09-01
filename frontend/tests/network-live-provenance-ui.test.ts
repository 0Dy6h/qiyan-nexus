import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const testFilePath = fileURLToPath(import.meta.url);

function getSource(relativePath: string) {
  return readFileSync(resolve(testFilePath, "..", "..", relativePath), "utf8");
}

test("network analysis client renders live data provenance sections", () => {
  const source = getSource("components/NetworkAnalysisClient.tsx");

  assert.match(source, /真实数据 opt-in/);
  assert.match(source, /数据来源与缓存/);
  assert.match(source, /运行步骤/);
  assert.match(source, /运行警告/);
  assert.match(source, /getNetworkTargetEvidenceTypeLabel/);
  assert.match(source, /target_evidence_type/);
  assert.match(source, /evidence_refs/);
});

test("compound child snapshots override generic live-network copy with a frozen-lineage boundary", () => {
  const source = getSource("components/NetworkAnalysisClient.tsx");

  assert.match(source, /const isImportedSnapshotResult =/);
  assert.match(source, /result\?\.source_task_id/);
  assert.match(source, /compound_import_provenance/);
  assert.match(source, /冻结靶点快照与派生交集/);
  assert.match(source, /仅展示冻结 lineage 与服务端派生交集/);
  assert.match(source, /未构建 provider chains、PPI、pathway 或 enrichment/);
  assert.match(source, /isImportedSnapshotResult \? \(/);
  assert.match(source, /: isLiveResult \? \(/);
});

test("network analysis client handles failed backend task states", () => {
  const source = getSource("components/NetworkAnalysisClient.tsx");

  assert.match(source, /polled\.status === "failed"/);
  assert.match(source, /polled\.error/);
});

test("network page keeps mock boundary copy while allowing live opt-in copy", () => {
  const pageSource = getSource("app/network/page.tsx");

  assert.match(pageSource, /演示数据边界/);
  assert.match(pageSource, /真实数据链路需显式 opt-in/);
});
