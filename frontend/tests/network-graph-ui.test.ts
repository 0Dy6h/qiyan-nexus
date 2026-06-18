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
  assert(source.includes('aria-label="机制线索成分-靶点-通路-疾病链图"'));
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

test("NetworkGraph uses publication-style category shapes and curved edges", () => {
  const source = readFileSync("components/NetworkGraph.tsx", "utf-8");

  assert(source.includes('shape: "hexagon"'));
  assert(source.includes('shape: "circle"'));
  assert(source.includes('shape: "rounded-rect"'));
  assert(source.includes('shape: "diamond"'));
  assert(source.includes('shape: "pill"'));
  assert(source.includes("buildEdgePath"));
  assert(source.includes("markerEnd=\"url(#networkGraphArrow)\""));
});

test("NetworkGraph renders node degree and category legend copy", () => {
  const source = readFileSync("components/NetworkGraph.tsx", "utf-8");

  assert(source.includes("createDegreeMap"));
  assert(source.includes("formatDegree(degree)"));
  assert(source.includes("节点形状/颜色表示类别"));
  assert(source.includes("节点符号大小表示 degree"));
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

test("NetworkGraph node groups expose keyboard a11y affordances", () => {
  const source = readFileSync("components/NetworkGraph.tsx", "utf-8");

  // Tab-focusable + announced as button with toggle state
  assert(source.includes("tabIndex={0}"));
  assert(source.includes('role="button"'));
  assert(source.includes("aria-pressed={isFocused}"));
  // Per-node accessible name
  assert.match(source, /aria-label=\{`\$\{LAYER_LABEL_MAP\[node\.layer\][^`]*\}: \$\{node\.label\}`\}/);
  // Keyboard focus mirrors hover so highlight state is visible to keyboard users
  assert(source.includes("onFocus={() => setHoveredNodeId(node.id)}"));
  assert(source.includes("onBlur={() => setHoveredNodeId(null)}"));
});

test("NetworkGraph onKeyDown handles Enter/Space toggle and Escape clear", () => {
  const source = readFileSync("components/NetworkGraph.tsx", "utf-8");

  assert(source.includes("onKeyDown="));
  // Enter/Space toggle behaviour
  assert.match(source, /event\.key === "Enter" \|\| event\.key === " "/);
  // Escape clears focus
  assert(source.includes('event.key === "Escape"'));
  assert(source.includes("setFocusedNodeId(null)"));
});

test("NetworkGraph onKeyDown handles ArrowUp/Down within layer and ArrowLeft/Right across layers", () => {
  const source = readFileSync("components/NetworkGraph.tsx", "utf-8");

  // Ref map to programmatically move browser focus between nodes
  assert(source.includes("useRef"));
  assert.match(source, /Map<string, SVGGElement>/);
  // Ref callback on the node group attaches/detaches via the map
  assert.match(source, /ref=\{\(el\) =>/);

  // Arrow key branches present
  assert(source.includes('event.key === "ArrowUp"'));
  assert(source.includes('event.key === "ArrowDown"'));
  assert(source.includes('event.key === "ArrowLeft"'));
  assert(source.includes('event.key === "ArrowRight"'));

  // Programmatic focus call after navigation
  assert.match(source, /\.focus\(\)/);
});
