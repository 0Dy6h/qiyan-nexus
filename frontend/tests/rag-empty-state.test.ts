import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import { getCitationEmptyCopy } from "../lib/ui/states";

const testFilePath = fileURLToPath(import.meta.url);

function getSource(relativePath: string) {
  return readFileSync(resolve(testFilePath, "..", "..", relativePath), "utf8");
}

test("getCitationEmptyCopy returns shared rag empty citations message", () => {
  assert.equal(
    getCitationEmptyCopy(),
    "当前回答未返回可展示的引用卡片，请调整问题或来源后重试。",
  );
});

test("rag page wraps the answer client in Suspense so URL question prefill can prerender", () => {
  const source = getSource("app/rag/page.tsx");

  assert.match(source, /import \{ Suspense \} from "react"/);
  assert.match(source, /<Suspense[\s\S]*<RagAnswerClient \/>/);
});

// 与 network 提交路径同族：服务端已返回非 2xx 时不得宣称「后端未启动」，
// 状态码要进文案；只有真网络故障（非 ApiStatusError）才保留 backend-down 提示。
test("rag answer failures surface HTTP status and reserve backend-down claim for transport errors", () => {
  const ragApiSource = getSource("lib/api/rag.ts");
  const clientSource = getSource("components/RagAnswerClient.tsx");

  assert.match(ragApiSource, /throw new ApiStatusError\(response\.status, "RAG answer request failed"\)/);
  assert.match(ragApiSource, /throw new ApiStatusError\(response\.status, "RAG answer export request failed"\)/);
  assert.match(ragApiSource, /throw new ApiStatusError\(response\.status, "RAG answer docx export request failed"\)/);

  assert.match(clientSource, /生成回答失败（HTTP \$\{error\.status\}），请稍后重试或调整检索范围。/);
  assert.match(clientSource, /error instanceof ApiStatusError/);
  assert.match(clientSource, /请求失败，请确认后端服务已启动。/);
});
