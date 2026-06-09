import type { NetworkChain } from "./api/network";

export interface GraphNode {
  id: string;
  label: string;
  layer: string;
  x: number;
  y: number;
}

export interface GraphEdge {
  sourceId: string;
  targetId: string;
  score: number;
  sourceLayer: string;
  targetLayer: string;
}

export interface GraphModel {
  layers: { key: string; label: string }[];
  nodes: GraphNode[];
  edges: GraphEdge[];
}

const LAYER_ORDER = ["herb", "compound", "target", "pathway", "disease"] as const;
const LAYER_LABELS = ["中药/复方", "化合物", "靶点", "通路", "疾病"] as const;

const LAYER_GAP_X = 220;
const NODE_GAP_Y = 60;
const START_X = 60;
const START_Y = 40;

export function buildNetworkGraphModel(chains: NetworkChain[]): GraphModel {
  const layers = LAYER_ORDER.map((key, i) => ({
    key,
    label: LAYER_LABELS[i]!,
  }));

  // Collect unique nodes per layer, preserving first-occurrence order
  const layerLabelSets: Map<string, Set<string>> = new Map();
  const layerLabelOrder: Map<string, string[]> = new Map();

  for (const layerKey of LAYER_ORDER) {
    layerLabelSets.set(layerKey, new Set());
    layerLabelOrder.set(layerKey, []);
  }

  for (const chain of chains) {
    const herbLabel = chain.formula ?? chain.herb;
    const entries: [string, string][] = [
      ["herb", herbLabel],
      ["compound", chain.compound],
      ["target", chain.target],
      ["pathway", chain.pathway],
      ["disease", chain.disease],
    ];

    for (const [layerKey, label] of entries) {
      const seen = layerLabelSets.get(layerKey)!;
      const order = layerLabelOrder.get(layerKey)!;
      if (!seen.has(label)) {
        seen.add(label);
        order.push(label);
      }
    }
  }

  // Build edges first: for each chain, connect adjacent layer nodes.
  // Edges are needed to compute the barycenter ordering below.
  const edges: GraphEdge[] = [];
  for (const chain of chains) {
    const herbLabel = chain.formula ?? chain.herb;
    const nodeLabels: string[] = [
      herbLabel,
      chain.compound,
      chain.target,
      chain.pathway,
      chain.disease,
    ];

    for (let i = 0; i < nodeLabels.length - 1; i++) {
      const sourceLayer = LAYER_ORDER[i]!;
      const targetLayer = LAYER_ORDER[i + 1]!;
      edges.push({
        sourceId: `${sourceLayer}-${nodeLabels[i]!}`,
        targetId: `${targetLayer}-${nodeLabels[i + 1]!}`,
        score: chain.score,
        sourceLayer,
        targetLayer,
      });
    }
  }

  // Reorder nodes within each layer to reduce edge crossings, keeping the
  // five-layer left-to-right semantics intact (X and layer membership never
  // change — only the vertical order within a layer). Uses the classic
  // barycenter heuristic with deterministic tie-breaking.
  const orderedLabelsByLayer = orderLayersByBarycenter(layerLabelOrder, edges);

  // Build nodes with coordinates from the crossing-reduced ordering.
  const nodes: GraphNode[] = [];
  for (let layerIndex = 0; layerIndex < LAYER_ORDER.length; layerIndex++) {
    const layerKey = LAYER_ORDER[layerIndex]!;
    const x = START_X + layerIndex * LAYER_GAP_X;
    const labels = orderedLabelsByLayer.get(layerKey)!;

    for (let posIndex = 0; posIndex < labels.length; posIndex++) {
      const label = labels[posIndex]!;
      const y = START_Y + posIndex * NODE_GAP_Y;
      nodes.push({
        id: `${layerKey}-${label}`,
        label,
        layer: layerKey,
        x,
        y,
      });
    }
  }

  return { layers, nodes, edges };
}

/**
 * Count edge crossings in a layered graph given a per-layer label ordering.
 * Two edges between the same adjacent layer pair cross when their endpoints
 * are in opposite vertical order. Used by tests as a quality guard and by the
 * barycenter pass below as the optimisation target.
 */
export function countEdgeCrossings(model: GraphModel): number {
  const posById = new Map<string, number>();
  const seenPerLayer = new Map<string, number>();
  for (const node of model.nodes) {
    const next = seenPerLayer.get(node.layer) ?? 0;
    posById.set(node.id, next);
    seenPerLayer.set(node.layer, next + 1);
  }

  let crossings = 0;
  for (let i = 0; i < model.edges.length; i++) {
    for (let j = i + 1; j < model.edges.length; j++) {
      const a = model.edges[i]!;
      const b = model.edges[j]!;
      // Only edges spanning the same adjacent layer pair can cross.
      if (a.sourceLayer !== b.sourceLayer || a.targetLayer !== b.targetLayer) {
        continue;
      }
      const aSrc = posById.get(a.sourceId)!;
      const aTgt = posById.get(a.targetId)!;
      const bSrc = posById.get(b.sourceId)!;
      const bTgt = posById.get(b.targetId)!;
      if ((aSrc - bSrc) * (aTgt - bTgt) < 0) {
        crossings++;
      }
    }
  }
  return crossings;
}

/**
 * Reorder labels within each layer to reduce edge crossings using the
 * barycenter heuristic. Sweeps forward (layer 1..n, ordering each layer by the
 * average position of its neighbours in the previous layer) and backward
 * (n-1..0, using the next layer), repeating until the ordering stabilises or a
 * fixed iteration cap is hit. Fully deterministic: the initial order is
 * first-occurrence order, and ties keep their current relative position via a
 * stable sort on (barycenter, currentIndex).
 */
function orderLayersByBarycenter(
  initialOrder: Map<string, string[]>,
  edges: GraphEdge[],
): Map<string, string[]> {
  // Working copy of per-layer ordering (arrays of labels).
  const order = new Map<string, string[]>();
  for (const layerKey of LAYER_ORDER) {
    order.set(layerKey, [...(initialOrder.get(layerKey) ?? [])]);
  }

  // Index edges by adjacent layer pair for quick neighbour lookups.
  // For layer i, forward edges come from pair (i-1, i); backward from (i, i+1).
  const labelOf = (id: string, layerKey: string): string =>
    id.slice(layerKey.length + 1);

  function positionsOf(layerKey: string): Map<string, number> {
    const labels = order.get(layerKey)!;
    const pos = new Map<string, number>();
    labels.forEach((label, i) => pos.set(label, i));
    return pos;
  }

  function reorderLayer(layerKey: string, neighbourLayer: string, useSource: boolean): boolean {
    const neighbourPos = positionsOf(neighbourLayer);
    const labels = order.get(layerKey)!;
    const currentIndex = new Map<string, number>();
    labels.forEach((label, i) => currentIndex.set(label, i));

    // Accumulate neighbour positions for each label in this layer.
    const sums = new Map<string, { total: number; count: number }>();
    for (const label of labels) sums.set(label, { total: 0, count: 0 });

    for (const edge of edges) {
      let ownId: string;
      let neighbourId: string;
      let ownLayer: string;
      let neighbourLayerKey: string;
      if (useSource) {
        // layerKey is the target side; neighbour is the source side.
        ownLayer = edge.targetLayer;
        neighbourLayerKey = edge.sourceLayer;
        ownId = edge.targetId;
        neighbourId = edge.sourceId;
      } else {
        // layerKey is the source side; neighbour is the target side.
        ownLayer = edge.sourceLayer;
        neighbourLayerKey = edge.targetLayer;
        ownId = edge.sourceId;
        neighbourId = edge.targetId;
      }
      if (ownLayer !== layerKey || neighbourLayerKey !== neighbourLayer) continue;
      const ownLabel = labelOf(ownId, layerKey);
      const np = neighbourPos.get(labelOf(neighbourId, neighbourLayer));
      if (np === undefined) continue;
      const acc = sums.get(ownLabel);
      if (acc) {
        acc.total += np;
        acc.count += 1;
      }
    }

    // Barycenter = average neighbour position; nodes with no neighbour keep
    // their current index so they don't jump around arbitrarily.
    const bary = (label: string): number => {
      const acc = sums.get(label)!;
      return acc.count > 0 ? acc.total / acc.count : currentIndex.get(label)!;
    };

    const sorted = [...labels].sort((a, b) => {
      const d = bary(a) - bary(b);
      if (d !== 0) return d;
      return currentIndex.get(a)! - currentIndex.get(b)!;
    });

    const changed = sorted.some((label, i) => label !== labels[i]);
    if (changed) order.set(layerKey, sorted);
    return changed;
  }

  const MAX_SWEEPS = 8;
  for (let sweep = 0; sweep < MAX_SWEEPS; sweep++) {
    let changed = false;
    // Forward: order each layer by its previous (left) neighbour.
    for (let i = 1; i < LAYER_ORDER.length; i++) {
      if (reorderLayer(LAYER_ORDER[i]!, LAYER_ORDER[i - 1]!, true)) changed = true;
    }
    // Backward: order each layer by its next (right) neighbour.
    for (let i = LAYER_ORDER.length - 2; i >= 0; i--) {
      if (reorderLayer(LAYER_ORDER[i]!, LAYER_ORDER[i + 1]!, false)) changed = true;
    }
    if (!changed) break;
  }

  return order;
}