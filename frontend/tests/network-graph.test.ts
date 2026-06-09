import assert from "node:assert/strict";
import { test } from "node:test";

import type { NetworkChain } from "../lib/api/network";
import {
  buildNetworkGraphModel,
  countEdgeCrossings,
  type GraphModel,
  type GraphNode,
  type GraphEdge,
} from "../lib/network-graph";

const LAYER_ORDER = ["herb", "compound", "target", "pathway", "disease"] as const;
const LAYER_LABELS = ["中药/复方", "化合物", "靶点", "通路", "疾病"] as const;

const SAMPLE_CHAINS: NetworkChain[] = [
  {
    herb: "防风",
    formula: "消风散",
    compound: "升麻素苷",
    target: "JAK1",
    pathway: "JAK-STAT",
    disease: "特应性皮炎",
    score: 0.92,
    related_entity_ids: [],
  },
  {
    herb: "防风",
    formula: "消风散",
    compound: "5-O-甲基维斯阿米醇苷",
    target: "STAT3",
    pathway: "JAK-STAT",
    disease: "特应性皮炎",
    score: 0.85,
    related_entity_ids: [],
  },
];

test("empty chains returns empty model with 5 layers", () => {
  const model = buildNetworkGraphModel([]);

  assert.equal(model.nodes.length, 0);
  assert.equal(model.edges.length, 0);
  assert.equal(model.layers.length, 5);
  assert.deepEqual(
    model.layers.map((l) => l.key),
    [...LAYER_ORDER],
  );
  assert.deepEqual(
    model.layers.map((l) => l.label),
    [...LAYER_LABELS],
  );
});

test("single chain produces 5 nodes and 4 edges", () => {
  const singleChain: NetworkChain[] = [
    {
      herb: "黄芪",
      compound: "槲皮素",
      target: "IL6",
      pathway: "PI3K-Akt",
      disease: "特应性皮炎",
      score: 0.78,
      related_entity_ids: [],
    },
  ];
  const model = buildNetworkGraphModel(singleChain);

  assert.equal(model.nodes.length, 5);
  assert.equal(model.edges.length, 4);

  // Verify node labels match chain fields
  const herbNode = model.nodes.find((n) => n.layer === "herb");
  assert.ok(herbNode);
  assert.equal(herbNode!.label, "黄芪");

  const compoundNode = model.nodes.find((n) => n.layer === "compound");
  assert.ok(compoundNode);
  assert.equal(compoundNode!.label, "槲皮素");

  const targetNode = model.nodes.find((n) => n.layer === "target");
  assert.ok(targetNode);
  assert.equal(targetNode!.label, "IL6");

  const pathwayNode = model.nodes.find((n) => n.layer === "pathway");
  assert.ok(pathwayNode);
  assert.equal(pathwayNode!.label, "PI3K-Akt");

  const diseaseNode = model.nodes.find((n) => n.layer === "disease");
  assert.ok(diseaseNode);
  assert.equal(diseaseNode!.label, "特应性皮炎");
});

test("duplicate nodes are deduplicated across chains", () => {
  const model = buildNetworkGraphModel(SAMPLE_CHAINS);

  // Both chains share herb "防风" (but formula overrides to "消风散")
  const herbNodes = model.nodes.filter((n) => n.layer === "herb");
  assert.equal(herbNodes.length, 1);

  // Both chains share pathway "JAK-STAT"
  const pathwayNodes = model.nodes.filter((n) => n.layer === "pathway");
  assert.equal(pathwayNodes.length, 1);

  // Both chains share disease "特应性皮炎"
  const diseaseNodes = model.nodes.filter((n) => n.layer === "disease");
  assert.equal(diseaseNodes.length, 1);

  // Two different compounds
  const compoundNodes = model.nodes.filter((n) => n.layer === "compound");
  assert.equal(compoundNodes.length, 2);

  // Two different targets
  const targetNodes = model.nodes.filter((n) => n.layer === "target");
  assert.equal(targetNodes.length, 2);

  // Total nodes: 1 herb + 2 compounds + 2 targets + 1 pathway + 1 disease = 7
  assert.equal(model.nodes.length, 7);

  // 2 chains × 4 edges each = 8 edges
  assert.equal(model.edges.length, 8);
});

test("node ids follow layer-label format", () => {
  const model = buildNetworkGraphModel(SAMPLE_CHAINS);

  for (const node of model.nodes) {
    assert.match(node.id, new RegExp(`^${node.layer}-`), `Node id "${node.id}" should start with layer "${node.layer}-"`);
    assert.ok(node.id.includes(node.label), `Node id "${node.id}" should contain label "${node.label}"`);
  }
});

test("coordinates are deterministic across calls", () => {
  const model1 = buildNetworkGraphModel(SAMPLE_CHAINS);
  const model2 = buildNetworkGraphModel(SAMPLE_CHAINS);

  assert.equal(model1.nodes.length, model2.nodes.length);
  for (let i = 0; i < model1.nodes.length; i++) {
    assert.equal(model1.nodes[i].id, model2.nodes[i].id);
    assert.equal(model1.nodes[i].x, model2.nodes[i].x);
    assert.equal(model1.nodes[i].y, model2.nodes[i].y);
  }
});

test("layers are in correct order herb→compound→target→pathway→disease", () => {
  const model = buildNetworkGraphModel(SAMPLE_CHAINS);

  const layerKeys = model.layers.map((l) => l.key);
  assert.deepEqual(layerKeys, [...LAYER_ORDER]);

  // Verify x coordinates increase with layer index
  const layerXValues = LAYER_ORDER.map((layerKey) => {
    const node = model.nodes.find((n) => n.layer === layerKey);
    assert.ok(node, `Expected a node in layer ${layerKey}`);
    return node!.x;
  });

  for (let i = 1; i < layerXValues.length; i++) {
    assert.ok(
      layerXValues[i]! > layerXValues[i - 1]!,
      `Layer ${LAYER_ORDER[i]} x=${layerXValues[i]} should be > layer ${LAYER_ORDER[i - 1]} x=${layerXValues[i - 1]}`,
    );
  }
});

test("edges carry correct score from their source chain", () => {
  const model = buildNetworkGraphModel(SAMPLE_CHAINS);

  // Chain 0 has score 0.92, chain 1 has score 0.85
  const edgesWithScore92 = model.edges.filter((e) => e.score === 0.92);
  const edgesWithScore85 = model.edges.filter((e) => e.score === 0.85);

  assert.equal(edgesWithScore92.length, 4, "Chain 0 should produce 4 edges with score 0.92");
  assert.equal(edgesWithScore85.length, 4, "Chain 1 should produce 4 edges with score 0.85");
});

test("formula field overrides herb label in herb layer node", () => {
  const model = buildNetworkGraphModel(SAMPLE_CHAINS);

  const herbNode = model.nodes.find((n) => n.layer === "herb");
  assert.ok(herbNode, "Should have a herb node");
  // When formula is present, herb-layer node label should use formula, not herb
  assert.equal(herbNode!.label, "消风散", "Herb node label should be formula '消风散', not herb '防风'");
});

test("multiple chains with different targets produce correct edge count", () => {
  const chains: NetworkChain[] = [
    {
      herb: "黄芪",
      compound: "槲皮素",
      target: "IL6",
      pathway: "PI3K-Akt",
      disease: "特应性皮炎",
      score: 0.9,
      related_entity_ids: [],
    },
    {
      herb: "甘草",
      compound: "甘草酸",
      target: "TNF",
      pathway: "NF-kB",
      disease: "银屑病",
      score: 0.7,
      related_entity_ids: [],
    },
  ];

  const model = buildNetworkGraphModel(chains);

  // 2 chains × 4 edges = 8 total edges
  assert.equal(model.edges.length, 8);

  // All 5 layers should have nodes
  const uniqueLayers = new Set(model.nodes.map((n) => n.layer));
  assert.equal(uniqueLayers.size, 5);
});

test("node y coordinates increase monotonically within each layer", () => {
  // Use chains that produce multiple nodes in the same layer
  const model = buildNetworkGraphModel(SAMPLE_CHAINS);

  const layersWithMultipleNodes = ["compound", "target"] as const;
  for (const layerKey of layersWithMultipleNodes) {
    const layerNodes = model.nodes
      .filter((n) => n.layer === layerKey)
      .sort((a, b) => a.y - b.y);

    for (let i = 1; i < layerNodes.length; i++) {
      assert.ok(
        layerNodes[i]!.y > layerNodes[i - 1]!.y,
        `In layer ${layerKey}, node ${i} y=${layerNodes[i]!.y} should be > node ${i - 1} y=${layerNodes[i - 1]!.y}`,
      );
    }
  }
});

// --- Crossing-reduction (barycenter) layout ---------------------------------

// Three chains sharing one herb / pathway / disease so only the compound→target
// band varies. First-occurrence order yields compound=[C1,C2], target=[T1,T2],
// but the edges C2→T1 and C1→T2 cross under that ordering. The barycenter pass
// should reorder the target layer to remove the crossing.
const CROSSING_CHAINS: NetworkChain[] = [
  {
    herb: "药X",
    compound: "化合物1",
    target: "靶点1",
    pathway: "通路P",
    disease: "特应性皮炎",
    score: 0.9,
    related_entity_ids: [],
  },
  {
    herb: "药X",
    compound: "化合物2",
    target: "靶点1",
    pathway: "通路P",
    disease: "特应性皮炎",
    score: 0.8,
    related_entity_ids: [],
  },
  {
    herb: "药X",
    compound: "化合物1",
    target: "靶点2",
    pathway: "通路P",
    disease: "特应性皮炎",
    score: 0.7,
    related_entity_ids: [],
  },
];

test("countEdgeCrossings returns 0 for a single chain", () => {
  const model = buildNetworkGraphModel([
    {
      herb: "黄芪",
      compound: "槲皮素",
      target: "IL6",
      pathway: "PI3K-Akt",
      disease: "特应性皮炎",
      score: 0.9,
      related_entity_ids: [],
    },
  ]);
  assert.equal(countEdgeCrossings(model), 0);
});

test("barycenter layout reduces crossings vs naive first-occurrence order", () => {
  const model = buildNetworkGraphModel(CROSSING_CHAINS);

  // Recompute crossings under the naive (first-occurrence) ordering to prove
  // the optimised layout is no worse — and on this fixture, strictly better.
  const naivePos = computeFirstOccurrencePositions(CROSSING_CHAINS);
  const naiveCrossings = countCrossingsWithPositions(model.edges, naivePos);
  const optimisedCrossings = countEdgeCrossings(model);

  assert.ok(
    optimisedCrossings <= naiveCrossings,
    `Optimised crossings ${optimisedCrossings} should be <= naive ${naiveCrossings}`,
  );
  assert.ok(
    naiveCrossings > 0,
    "Fixture should produce crossings under naive ordering (guards the test itself)",
  );
  assert.equal(optimisedCrossings, 0, "Barycenter should fully untangle this fixture");
});

test("barycenter layout is deterministic across calls", () => {
  const m1 = buildNetworkGraphModel(CROSSING_CHAINS);
  const m2 = buildNetworkGraphModel(CROSSING_CHAINS);
  assert.deepEqual(
    m1.nodes.map((n) => [n.id, n.x, n.y]),
    m2.nodes.map((n) => [n.id, n.x, n.y]),
  );
});

test("barycenter layout preserves node/edge counts and layer X positions", () => {
  const model = buildNetworkGraphModel(CROSSING_CHAINS);

  // 1 herb + 2 compounds + 2 targets + 1 pathway + 1 disease = 7 nodes.
  assert.equal(model.nodes.length, 7);
  // 3 chains × 4 edges = 12 edges.
  assert.equal(model.edges.length, 12);

  // Each layer still sits at a single, monotonically increasing X.
  const xByLayer = new Map<string, number>();
  for (const node of model.nodes) {
    const existing = xByLayer.get(node.layer);
    if (existing === undefined) xByLayer.set(node.layer, node.x);
    else assert.equal(node.x, existing, `Layer ${node.layer} must share one X`);
  }
  const xs = LAYER_ORDER.map((k) => xByLayer.get(k)!);
  for (let i = 1; i < xs.length; i++) {
    assert.ok(xs[i]! > xs[i - 1]!, "Layer X must increase left-to-right");
  }
});

// Helpers: reproduce the pre-barycenter (first-occurrence) vertical ordering so
// the test can independently measure the crossings the optimiser started from.
function computeFirstOccurrencePositions(chains: NetworkChain[]): Map<string, number> {
  const orderByLayer = new Map<string, string[]>();
  const seenByLayer = new Map<string, Set<string>>();
  for (const layer of LAYER_ORDER) {
    orderByLayer.set(layer, []);
    seenByLayer.set(layer, new Set());
  }
  for (const chain of chains) {
    const entries: [string, string][] = [
      ["herb", chain.formula ?? chain.herb],
      ["compound", chain.compound],
      ["target", chain.target],
      ["pathway", chain.pathway],
      ["disease", chain.disease],
    ];
    for (const [layer, label] of entries) {
      const seen = seenByLayer.get(layer)!;
      if (!seen.has(label)) {
        seen.add(label);
        orderByLayer.get(layer)!.push(label);
      }
    }
  }
  const pos = new Map<string, number>();
  for (const layer of LAYER_ORDER) {
    orderByLayer.get(layer)!.forEach((label, i) => pos.set(`${layer}-${label}`, i));
  }
  return pos;
}

function countCrossingsWithPositions(
  edges: GraphEdge[],
  posById: Map<string, number>,
): number {
  let crossings = 0;
  for (let i = 0; i < edges.length; i++) {
    for (let j = i + 1; j < edges.length; j++) {
      const a = edges[i]!;
      const b = edges[j]!;
      if (a.sourceLayer !== b.sourceLayer || a.targetLayer !== b.targetLayer) continue;
      const aSrc = posById.get(a.sourceId)!;
      const aTgt = posById.get(a.targetId)!;
      const bSrc = posById.get(b.sourceId)!;
      const bTgt = posById.get(b.targetId)!;
      if ((aSrc - bSrc) * (aTgt - bTgt) < 0) crossings++;
    }
  }
  return crossings;
}