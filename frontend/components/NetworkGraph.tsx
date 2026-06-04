"use client";

import { useRef, useState } from "react";
import { buildNetworkGraphModel } from "../lib/network-graph";
import type { NetworkChain } from "../lib/api/network";

interface NetworkGraphProps {
  chains: NetworkChain[];
}

const LAYER_FILL: Record<string, string> = {
  herb: "#d8efea",
  compound: "#e4e8f3",
  target: "#f7e9bf",
  pathway: "#dfeedd",
  disease: "#f3dfeb",
};

const LAYER_LABEL_MAP: Record<string, string> = {
  herb: "中药/复方",
  compound: "化合物",
  target: "靶点",
  pathway: "通路",
  disease: "疾病",
};

const START_X = 60;
const LAYER_GAP_X = 220;
const START_Y = 40;

function getEdgeStyle(score: number): {
  stroke: string;
  strokeWidth: number;
  opacity: number;
} {
  if (score >= 0.9) {
    return { stroke: "#0d9488", strokeWidth: 2.5, opacity: 0.85 };
  }
  if (score >= 0.7) {
    return { stroke: "#14b8a6", strokeWidth: 1.8, opacity: 0.65 };
  }
  return { stroke: "#84c9bf", strokeWidth: 1.5, opacity: 0.45 };
}

export default function NetworkGraph({ chains }: NetworkGraphProps) {
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [focusedNodeId, setFocusedNodeId] = useState<string | null>(null);
  const nodeRefs = useRef(new Map<string, SVGGElement>());

  const model = buildNetworkGraphModel(chains);
  const { layers, nodes, edges } = model;

  if (nodes.length === 0) {
    return (
      <div style={{ overflowX: "auto", marginTop: 24 }}>
        <svg
          viewBox="0 0 1000 200"
          role="img"
          aria-label="网络药理学成分-靶点-通路-疾病链图"
          style={{ width: "100%", minWidth: 600 }}
        >
          <rect x={0} y={0} width={1000} height={200} fill="#fbfcfb" />
          {layers.map((layer, i) => (
            <text
              key={layer.key}
              x={START_X + i * LAYER_GAP_X}
              y={START_Y - 12}
              textAnchor="middle"
              fontSize={14}
              fontWeight={700}
              fill="#0f1f1d"
            >
              {layer.label}
            </text>
          ))}
          <text x={500} y={110} textAnchor="middle" fontSize={16} fill="#6b7d78">
            暂无网络数据
          </text>
        </svg>
      </div>
    );
  }

  const nodeMap = new Map(nodes.map((n) => [n.id, n]));
  const maxNodeX = Math.max(...nodes.map((n) => n.x));
  const maxNodeY = Math.max(...nodes.map((n) => n.y));
  const svgWidth = maxNodeX + 180;
  const svgHeight = maxNodeY + 180;
  const legendY = maxNodeY + 60;

  // Determine which node is active for highlighting (focus takes priority)
  const activeNodeId = focusedNodeId ?? hoveredNodeId;

  // Pre-compute connected edge/node sets for the active node
  const connectedEdgeIndices = new Set<number>();
  const connectedNodeIds = new Set<string>();
  if (activeNodeId) {
    for (let i = 0; i < edges.length; i++) {
      const edge = edges[i]!;
      if (edge.sourceId === activeNodeId || edge.targetId === activeNodeId) {
        connectedEdgeIndices.add(i);
        connectedNodeIds.add(edge.sourceId);
        connectedNodeIds.add(edge.targetId);
      }
    }
    connectedNodeIds.add(activeNodeId);
  }

  // Find the focused node object for the indicator text
  const focusedNode = focusedNodeId
    ? nodes.find((n) => n.id === focusedNodeId) ?? null
    : null;

  // Arrow-key navigation: ArrowUp/Down move within the current layer;
  // ArrowLeft/Right move to the node with the closest Y in the adjacent layer.
  const layerOrder = layers.map((l) => l.key);
  function findAdjacentNodeId(currentId: string, key: string): string | null {
    const cur = nodeMap.get(currentId);
    if (!cur) return null;
    const sameLayer = nodes.filter((n) => n.layer === cur.layer);
    const inLayerIndex = sameLayer.findIndex((n) => n.id === currentId);
    if (key === "ArrowDown") {
      return inLayerIndex < sameLayer.length - 1 ? sameLayer[inLayerIndex + 1]!.id : null;
    }
    if (key === "ArrowUp") {
      return inLayerIndex > 0 ? sameLayer[inLayerIndex - 1]!.id : null;
    }
    const layerIndex = layerOrder.indexOf(cur.layer);
    const targetLayerIndex = key === "ArrowRight" ? layerIndex + 1 : layerIndex - 1;
    if (targetLayerIndex < 0 || targetLayerIndex >= layerOrder.length) return null;
    const targetLayer = nodes.filter((n) => n.layer === layerOrder[targetLayerIndex]);
    if (targetLayer.length === 0) return null;
    return targetLayer.reduce((best, n) =>
      Math.abs(n.y - cur.y) < Math.abs(best.y - cur.y) ? n : best,
    ).id;
  }

  return (
    <div style={{ overflowX: "auto", marginTop: 24 }}>
      <svg
        viewBox={`0 0 ${svgWidth} ${svgHeight}`}
        role="img"
        aria-label="网络药理学成分-靶点-通路-疾病链图"
        style={{ width: "100%", minWidth: 600 }}
      >
        <rect
          x={0}
          y={0}
          width={svgWidth}
          height={svgHeight}
          fill="#fbfcfb"
          onClick={() => setFocusedNodeId(null)}
        />

        {/* Layer headers */}
        {layers.map((layer, i) => (
          <text
            key={layer.key}
            x={START_X + i * LAYER_GAP_X}
            y={START_Y - 12}
            textAnchor="middle"
            fontSize={14}
            fontWeight={700}
            fill="#0f1f1d"
          >
            {layer.label}
          </text>
        ))}

        {/* Focus indicator text */}
        {focusedNode ? (
          <text
            x={20}
            y={START_Y - 28}
            fontSize={13}
            fill="#0d9488"
            fontWeight={600}
          >
            {`聚焦：${LAYER_LABEL_MAP[focusedNode.layer] ?? focusedNode.layer}: ${focusedNode.label}（点击空白处取消）`}
          </text>
        ) : null}

        {/* Edges */}
        {edges.map((edge, index) => {
          const source = nodeMap.get(edge.sourceId);
          const target = nodeMap.get(edge.targetId);
          if (!source || !target) return null;
          const style = getEdgeStyle(edge.score);

          const isConnected = connectedEdgeIndices.has(index);
          const isFocusedEdge = focusedNodeId != null && isConnected;

          let effectiveStroke = style.stroke;
          let effectiveStrokeWidth = style.strokeWidth;
          let effectiveOpacity = style.opacity;

          if (activeNodeId) {
            if (isConnected) {
              // Connected edge: keep color, thicken, full opacity
              effectiveStroke = isFocusedEdge ? "#0d9488" : "#0f766e";
              effectiveStrokeWidth = style.strokeWidth + 0.5;
              effectiveOpacity = 1;
            } else {
              // Dim unrelated edges
              effectiveOpacity = 0.08;
            }
          }

          return (
            <line
              key={`${edge.sourceId}->${edge.targetId}#${index}`}
              x1={source.x}
              y1={source.y}
              x2={target.x}
              y2={target.y}
              stroke={effectiveStroke}
              strokeWidth={effectiveStrokeWidth}
              opacity={effectiveOpacity}
            />
          );
        })}

        {/* Nodes */}
        {nodes.map((node) => {
          const isRelated = connectedNodeIds.has(node.id);
          const isFocused = focusedNodeId === node.id;

          let effectiveNodeOpacity = 1;
          let effectiveStroke = "#0d9488";

          if (activeNodeId) {
            if (isRelated) {
              // Connected node: keep fill, deepen stroke slightly
              effectiveStroke = "#0f766e";
            } else {
              // Dim unrelated nodes
              effectiveNodeOpacity = 0.3;
            }
          }

          return (
            <g
              key={node.id}
              ref={(el) => {
                if (el) {
                  nodeRefs.current.set(node.id, el);
                } else {
                  nodeRefs.current.delete(node.id);
                }
              }}
              tabIndex={0}
              role="button"
              aria-pressed={isFocused}
              aria-label={`${LAYER_LABEL_MAP[node.layer] ?? node.layer}: ${node.label}`}
              onMouseEnter={() => setHoveredNodeId(node.id)}
              onMouseLeave={() => setHoveredNodeId(null)}
              onFocus={() => setHoveredNodeId(node.id)}
              onBlur={() => setHoveredNodeId(null)}
              onClick={(e) => {
                e.stopPropagation();
                setFocusedNodeId(focusedNodeId === node.id ? null : node.id);
              }}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  setFocusedNodeId(focusedNodeId === node.id ? null : node.id);
                } else if (event.key === "Escape") {
                  event.preventDefault();
                  setFocusedNodeId(null);
                } else if (
                  event.key === "ArrowUp" ||
                  event.key === "ArrowDown" ||
                  event.key === "ArrowLeft" ||
                  event.key === "ArrowRight"
                ) {
                  const nextId = findAdjacentNodeId(node.id, event.key);
                  if (nextId) {
                    event.preventDefault();
                    nodeRefs.current.get(nextId)?.focus();
                  }
                }
              }}
              style={{ cursor: "pointer", outline: "none" }}
            >
              {/* Focus ring */}
              {isFocused ? (
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={24}
                  fill="none"
                  stroke="#0d9488"
                  strokeWidth={2}
                />
              ) : null}
              <circle
                cx={node.x}
                cy={node.y}
                r={20}
                fill={LAYER_FILL[node.layer] ?? "#edf3f1"}
                stroke={effectiveStroke}
                strokeWidth={1.5}
                opacity={effectiveNodeOpacity}
              />
              <text
                x={node.x}
                y={node.y}
                textAnchor="middle"
                dominantBaseline="central"
                fontSize={11}
                fill="#0f1f1d"
                fontWeight={600}
                opacity={effectiveNodeOpacity}
              >
                {node.label}
              </text>
              <title>{`${LAYER_LABEL_MAP[node.layer] ?? node.layer}: ${node.label}`}</title>
            </g>
          );
        })}

        {/* Legend */}
        <text x={20} y={legendY} fontSize={12} fill="#6b7d78" fontWeight={600}>
          {"图例: 连线粗细表示置信度（越粗越高）"}
        </text>
        <line
          x1={20}
          y1={legendY + 20}
          x2={60}
          y2={legendY + 20}
          stroke="#0d9488"
          strokeWidth={2.5}
          opacity={0.85}
        />
        <text x={68} y={legendY + 24} fontSize={11} fill="#6b7d78">
          {"≥0.9"}
        </text>
        <line
          x1={120}
          y1={legendY + 20}
          x2={160}
          y2={legendY + 20}
          stroke="#14b8a6"
          strokeWidth={1.8}
          opacity={0.65}
        />
        <text x={168} y={legendY + 24} fontSize={11} fill="#6b7d78">
          {"≥0.7"}
        </text>
        <line
          x1={220}
          y1={legendY + 20}
          x2={260}
          y2={legendY + 20}
          stroke="#84c9bf"
          strokeWidth={1.5}
          opacity={0.45}
        />
        <text x={268} y={legendY + 24} fontSize={11} fill="#6b7d78">
          {"<0.7"}
        </text>
      </svg>
    </div>
  );
}
