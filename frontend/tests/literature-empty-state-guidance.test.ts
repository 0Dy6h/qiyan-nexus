import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const testFilePath = fileURLToPath(import.meta.url);

function getSource(relativePath: string) {
  return readFileSync(resolve(testFilePath, "..", "..", relativePath), "utf8");
}

// 网络链路「查相关文献」深链在演示语料上必然 0 结果（靶点缩写无命中记录）：
// 空态必须说明语料局限，并提供有命中的示例检索词，不能只留一句通用提示。
test("literature empty state explains demo-corpus limits and offers hit-tested suggestions", () => {
  const source = getSource("components/LiteratureSearchClient.tsx");

  assert.match(source, /未检索到匹配文献/);
  assert.match(source, /小型演示语料/);
  assert.match(source, /靶点缩写（如 IL6、TNF）暂无对应记录/);
  assert.match(source, /"消风散", "特应性皮炎", "atopic dermatitis"/);
  // 建议词点击后走同一 runSearch 路径，保持来源/排序/分页状态
  assert.match(source, /runSearch\(suggestion, state\.view, 1, state\.pageSize, state\.sort\)/);
});
