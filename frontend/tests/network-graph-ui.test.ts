/**
 * Tests for NetworkGraph UI source-string assertions.
 */

import { readFileSync } from "node:fs";
import { strict as assert } from "node:assert";
import { test } from "node:test";

test("NetworkGraph is imported in NetworkAnalysisClient", () => {
  const source = readFileSync("components/NetworkAnalysisClient.tsx", "utf-8");

  assert(source.includes("import NetworkGraph"));
  assert(source.includes("<NetworkGraph"));
  assert(source.includes("result.chains"));
});

test("NetworkGraph renders SVG with role=img", () => {
  const source = readFileSync("components/NetworkGraph.tsx", "utf-8");

  assert(source.includes("<svg"));
  assert(source.includes('role="img"'));
  assert(source.includes('aria-label="网络药理学成分-靶点-通路-疾病链图"'));
});

test("NetworkGraph renders layer headers", () => {
  const source = readFileSync("components/NetworkGraph.tsx", "utf-8");

  assert(source.includes("中药/复方"));
  assert(source.includes("化合物"));
  assert(source.includes("靶点"));
  assert(source.includes("通路"));
  assert(source.includes("疾病"));
});

test("NetworkGraph renders legend", () => {
  const source = readFileSync("components/NetworkGraph.tsx", "utf-8");

  assert(source.includes("图例"));
  assert(source.includes("≥0.9"));
  assert(source.includes("≥0.7"));
});

test("NetworkGraph renders node with title tooltip", () => {
  const source = readFileSync("components/NetworkGraph.tsx", "utf-8");

  assert(source.includes("<title"));
  assert(source.includes("buildNetworkGraphModel"));
});

test("NetworkGraph handles empty chains", () => {
  const source = readFileSync("components/NetworkGraph.tsx", "utf-8");

  assert(source.includes("暂无网络数据"));
});

test("NetworkGraph imports buildNetworkGraphModel", () => {
  const source = readFileSync("components/NetworkGraph.tsx", "utf-8");

  assert(source.includes('from "../lib/network-graph"'));
});