import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const testFilePath = fileURLToPath(import.meta.url);

function getSource(relativePath: string) {
  return readFileSync(resolve(testFilePath, "..", "..", relativePath), "utf8");
}

test("LiteraturePubmedSyncClient renders sync form with query, max_results, and submit", () => {
  const source = getSource("components/LiteraturePubmedSyncClient.tsx");

  assert.match(source, /同步 PubMed/);
  assert.match(source, /\/api\/literature\/sync/);
  assert.match(source, /检索关键词/);
  assert.match(source, /aria-label="PubMed 检索关键词"/);
  assert.match(source, /拉取数量 max_results/);
  assert.match(source, /aria-label="PubMed 拉取数量"/);
  assert.match(source, /syncLiteratureFromPubmed/);
  assert.match(source, /LITERATURE_SYNC_MAX_RESULTS_CAP/);
  assert.match(source, /minHeight: 44/);
});

test("LiteraturePubmedSyncClient renders fetched/created/updated counts on success", () => {
  const source = getSource("components/LiteraturePubmedSyncClient.tsx");

  assert.match(source, /`检索关键词 \$\{state\.result\.query\}`/);
  assert.match(source, /`拉取条数 \$\{state\.result\.fetched\}`/);
  assert.match(source, /`新增 \$\{state\.result\.created\}`/);
  assert.match(source, /`刷新 \$\{state\.result\.updated\}`/);
});

test("literature page mounts LiteraturePubmedSyncClient above LiteratureSearchClient", () => {
  const source = getSource("app/literature/page.tsx");

  assert.match(source, /import LiteraturePubmedSyncClient from/);
  const syncIndex = source.indexOf("<LiteraturePubmedSyncClient />");
  const searchIndex = source.indexOf("<LiteratureSearchClient />");
  assert.ok(syncIndex > 0, "sync client should be rendered");
  assert.ok(searchIndex > 0, "search client should still be rendered");
  assert.ok(syncIndex < searchIndex, "sync client should render above search client");
});

test("literature page wraps the search client in Suspense so URL query prefill can prerender", () => {
  const source = getSource("app/literature/page.tsx");

  assert.match(source, /import \{ Suspense \} from "react"/);
  assert.match(source, /<Suspense[\s\S]*<LiteratureSearchClient \/>/);
});
