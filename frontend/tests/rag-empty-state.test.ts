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
