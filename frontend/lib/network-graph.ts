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

  // Build nodes with coordinates
  const nodes: GraphNode[] = [];
  for (let layerIndex = 0; layerIndex < LAYER_ORDER.length; layerIndex++) {
    const layerKey = LAYER_ORDER[layerIndex]!;
    const x = START_X + layerIndex * LAYER_GAP_X;
    const labels = layerLabelOrder.get(layerKey)!;

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

  // Build edges: for each chain, connect adjacent layer nodes
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

  return { layers, nodes, edges };
}