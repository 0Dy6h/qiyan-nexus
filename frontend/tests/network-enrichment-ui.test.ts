/**
 * Tests for network enrichment UI integration.
 */

import { readFileSync } from "node:fs";
import { strict as assert } from "node:assert";
import { test } from "node:test";

test("NetworkAnalysisClient renders enrichment section when result.enrichment exists", () => {
  const source = readFileSync("components/NetworkAnalysisClient.tsx", "utf-8");

  // Should check for enrichment existence
  assert(source.includes("result.enrichment"));

  // Should render enrichment section title
  assert(source.includes("富集分析结果"));

  // Should display input and background gene counts
  assert(source.includes("input_gene_count"));
  assert(source.includes("background_gene_count"));

  // Should render table with enrichment terms
  assert(source.includes("<table"));
  assert(source.includes("result.enrichment.terms"));
});

test("NetworkAnalysisClient enrichment table has required columns", () => {
  const source = readFileSync("components/NetworkAnalysisClient.tsx", "utf-8");

  // Required column headers
  assert(source.includes("Term ID"));
  assert(source.includes("通路/功能"));
  assert(source.includes("类别"));
  assert(source.includes("重叠基因"));
  assert(source.includes("P-value"));
  assert(source.includes("基因列表"));
});

test("NetworkAnalysisClient formats p-value with toExponential", () => {
  const source = readFileSync("components/NetworkAnalysisClient.tsx", "utf-8");

  // Should use scientific notation for p-values
  assert(source.includes("toExponential"));
});

test("NetworkAnalysisClient displays term_name_zh with fallback to term_name", () => {
  const source = readFileSync("components/NetworkAnalysisClient.tsx", "utf-8");

  // Should prefer Chinese name but fall back to English
  assert(source.includes("term_name_zh || term.term_name"));
});

test("NetworkAnalysisClient shows overlap as fraction", () => {
  const source = readFileSync("components/NetworkAnalysisClient.tsx", "utf-8");

  // Should display overlap_count/gene_count
  assert(source.includes("overlap_count"));
  assert(source.includes("gene_count"));
});

test("NetworkAnalysisClient limits enrichment display to top 10 terms", () => {
  const source = readFileSync("components/NetworkAnalysisClient.tsx", "utf-8");

  // Should slice to first 10 terms
  assert(source.includes("slice(0, 10)"));

  // Should show count message when more than 10
  assert(source.includes("显示前 10 条结果"));
});
