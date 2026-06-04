import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const testFilePath = fileURLToPath(import.meta.url);

function getSource(relativePath: string) {
  return readFileSync(resolve(testFilePath, "..", "..", relativePath), "utf8");
}

test("rag citation card renders EntityChips for related entities", () => {
  const ragSource = getSource("components/RagAnswerClient.tsx");

  assert.match(ragSource, /import EntityChips from "\.\/EntityChips"/);
  assert.match(ragSource, /<EntityChips ids=\{citation\.related_entity_ids \?\? \[\]\} \/>/);
});

test("literature detail page renders EntityChips below the metadata row", () => {
  const detailSource = getSource("app/literature/[id]/page.tsx");

  assert.match(detailSource, /import EntityChips from "\.\.\/\.\.\/\.\.\/components\/EntityChips"/);
  assert.match(detailSource, /<EntityChips[\s\S]*ids=\{item\.related_entity_ids \?\? \[\]\}/);
});

test("network result chains render EntityChips from backend related entity ids", () => {
  const networkSource = getSource("components/NetworkAnalysisClient.tsx");

  assert.match(networkSource, /import EntityChips from "\.\/EntityChips"/);
  assert.match(networkSource, /<EntityChips ids=\{chain\.related_entity_ids\}/);
});

test("network result cards expose literature, rag, and focus navigation links", () => {
  const networkSource = getSource("components/NetworkAnalysisClient.tsx");

  assert.match(networkSource, /href=\{`\/literature\?q=\$\{encodeURIComponent\(chain\.target\)\}`\}/);
  assert.match(networkSource, /href=\{`\/rag\?question=\$\{encodeURIComponent\(/);
  assert.match(networkSource, /href=\{buildNetworkFocusHref\(chain\.related_entity_ids\[0\]\)\}/);
});

test("network outbound links land on pages that consume the URL params", () => {
  const literatureSource = getSource("components/LiteratureSearchClient.tsx");
  const ragSource = getSource("components/RagAnswerClient.tsx");

  assert.match(literatureSource, /import \{ useSearchParams \} from "next\/navigation"/);
  assert.match(literatureSource, /searchParams\.get\("q"\)/);
  assert.match(literatureSource, /void runSearch\(linkedQuery, "all", 1, state\.pageSize, "relevance"\)/);
  assert.match(ragSource, /import \{ useSearchParams \} from "next\/navigation"/);
  assert.match(ragSource, /searchParams\.get\("question"\)/);
});

test("entity chips render kind labels for the five seed entity kinds", () => {
  const labelSource = getSource("lib/api/network-entities.ts");

  assert.match(labelSource, /"中药"/);
  assert.match(labelSource, /"复方"/);
  assert.match(labelSource, /"成分"/);
  assert.match(labelSource, /"靶点"/);
  assert.match(labelSource, /"通路"/);
});

test("entity chip href targets /network?focus= so prefill can pick up the entity id", () => {
  const lookupSource = getSource("lib/api/network-entities.ts");

  assert.match(lookupSource, /\/network\?focus=\$\{encodeURIComponent\(entityId\)\}/);
});

test("entity chip styles avoid mixing border shorthand with border overrides", () => {
  const chipSource = getSource("components/EntityChips.tsx");

  assert.doesNotMatch(chipSource, /border: "1px solid/);
  assert.match(chipSource, /borderWidth: 1/);
  assert.match(chipSource, /borderStyle: "solid"/);
  assert.match(chipSource, /borderColor: "#84c9bf"/);
});
