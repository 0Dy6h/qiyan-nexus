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
