import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const testFilePath = fileURLToPath(import.meta.url);

function getSource(relativePath: string) {
  return readFileSync(resolve(testFilePath, "..", "..", relativePath), "utf8");
}

test("network analysis client exposes completed-result markdown export", () => {
  const clientSource = getSource("components/NetworkAnalysisClient.tsx");

  assert.match(clientSource, /DownloadOutlined/);
  assert.match(clientSource, /fetchNetworkReportMarkdown/);
  assert.match(clientSource, /buildNetworkReportFileName/);
  assert.match(clientSource, /aria-label="导出报告为 Markdown"/);
  assert.match(clientSource, />\s*导出报告为 Markdown\s*</);
});

test("network analysis client downloads the report through a browser blob", () => {
  const clientSource = getSource("components/NetworkAnalysisClient.tsx");

  assert.match(clientSource, /await fetchNetworkReportMarkdown\(result\.task_id\)/);
  assert.match(clientSource, /new Blob\(\[markdown\], \{ type: "text\/markdown;charset=utf-8" \}\)/);
  assert.match(clientSource, /URL\.createObjectURL\(blob\)/);
  assert.match(clientSource, /anchor\.download = fileName/);
  assert.match(clientSource, /URL\.revokeObjectURL\(url\)/);
  assert.match(clientSource, /导出报告失败，请稍后重试。/);
});

test("network page surfaces a prominent mock-data boundary note", () => {
  const pageSource = getSource("app/network/page.tsx");

  assert.match(pageSource, /aria-label="网络药理学演示数据说明"/);
  assert.match(pageSource, /演示数据边界/);
  assert.match(pageSource, /不可作为科研发表、临床决策或真实数据库分析结果/);
});
