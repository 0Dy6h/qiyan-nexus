"use client";

import { DownloadOutlined } from "@ant-design/icons";
import { useRef, useState, type ReactNode } from "react";

import { exportSvgToPng, exportSvgToSvg } from "../lib/export-svg";
import { buildNetworkGraphModel } from "../lib/network-graph";
import type { NetworkChain } from "../lib/api/network";

interface NetworkGraphProps {
  chains: NetworkChain[];
  taskId?: string;
}

type LayerKey = "herb" | "compound" | "target" | "pathway" | "disease";
type NodeShape = "hexagon" | "circle" | "rounded-rect" | "diamond" | "pill";

interface LayerVisual {
  label: string;
  fill: string;
  stroke: string;
  softFill: string;
  bandFill: string;
  shape: NodeShape;
}

const LAYER_VISUALS: Record<LayerKey, LayerVisual> = {
  herb: {
    label: "中药/复方",
    fill: "#0f766e",
    stroke: "#0d9488",
    softFill: "#d9f4ef",
    bandFill: "#effaf7",
    shape: "hexagon",
  },
  compound: {
    label: "化合物",
    fill: "#2563eb",
    stroke: "#3b82f6",
    softFill: "#dbeafe",
    bandFill: "#f0f7ff",
    shape: "circle",
  },
  target: {
    label: "靶点",
    fill: "#b45309",
    stroke: "#d97706",
    softFill: "#fef3c7",
    bandFill: "#fffbeb",
    shape: "rounded-rect",
  },
  pathway: {
    label: "通路",
    fill: "#15803d",
    stroke: "#22c55e",
    softFill: "#dcfce7",
    bandFill: "#f0fdf4",
    shape: "diamond",
  },
  disease: {
    label: "疾病",
    fill: "#be123c",
    stroke: "#e11d48",
    softFill: "#ffe4e6",
    bandFill: "#fff1f2",
    shape: "pill",
  },
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
const GRAPH_OFFSET_X = 48;
const GRAPH_OFFSET_Y = 78;
const NODE_MIN_RADIUS = 16;
const NODE_MAX_RADIUS = 34;
const EDGE_PORT_OFFSET = 38;
const LABEL_GAP_X = 6;
const LAYER_BAND_WIDTH = 170;
const MAX_LABEL_LINES = 2;
const MAX_LABEL_CHARS = 10;

function getLayerVisual(layer: string): LayerVisual {
  return LAYER_VISUALS[layer as LayerKey] ?? LAYER_VISUALS.target;
}

function getEdgeStyle(score: number): {
  stroke: string;
  strokeWidth: number;
  opacity: number;
} {
  if (score >= 0.9) {
    return { stroke: "#1e293b", strokeWidth: 2.6, opacity: 0.92 };
  }
  if (score >= 0.7) {
    return { stroke: "#64748b", strokeWidth: 1.8, opacity: 0.72 };
  }
  return { stroke: "#cbd5e1", strokeWidth: 1.2, opacity: 0.56 };
}

function formatDegree(degree: number): string {
  return `degree ${degree}`;
}

function computeNodeRadius(degree: number, maxDegree: number): number {
  const t = maxDegree > 1 ? degree / maxDegree : 0.5;
  return NODE_MIN_RADIUS + Math.round(t * (NODE_MAX_RADIUS - NODE_MIN_RADIUS));
}

function splitLabelIntoLines(label: string): string[] {
  const trimmed = label.trim();
  if (trimmed.length <= MAX_LABEL_CHARS) {
    return [trimmed];
  }

  const lines: string[] = [];
  let remaining = trimmed;
  while (remaining.length > 0 && lines.length < MAX_LABEL_LINES) {
    lines.push(remaining.slice(0, MAX_LABEL_CHARS));
    remaining = remaining.slice(MAX_LABEL_CHARS);
  }
  if (remaining.length > 0 && lines.length > 0) {
    const last = lines.length - 1;
    lines[last] = `${lines[last]!.slice(0, MAX_LABEL_CHARS - 3)}...`;
  }
  return lines;
}

function polygonPoints(cx: number, cy: number, radius: number, sides: number, rotation = 0): string {
  return Array.from({ length: sides }, (_, index) => {
    const angle = rotation + (index / sides) * Math.PI * 2;
    const x = cx + Math.cos(angle) * radius;
    const y = cy + Math.sin(angle) * radius;
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  }).join(" ");
}

function renderNodeSymbol({
  cx,
  cy,
  radius,
  visual,
  opacity,
}: {
  cx: number;
  cy: number;
  radius: number;
  visual: LayerVisual;
  opacity: number;
}): ReactNode {
  const common = {
    fill: visual.fill,
    stroke: "#ffffff",
    strokeWidth: 1.8,
    opacity,
  };

  if (visual.shape === "hexagon") {
    return <polygon points={polygonPoints(cx, cy, radius, 6, Math.PI / 6)} {...common} />;
  }
  if (visual.shape === "diamond") {
    return <polygon points={polygonPoints(cx, cy, radius * 1.08, 4, Math.PI / 4)} {...common} />;
  }
  if (visual.shape === "rounded-rect") {
    return (
      <rect
        x={cx - radius * 1.16}
        y={cy - radius * 0.82}
        width={radius * 2.32}
        height={radius * 1.64}
        rx={5}
        {...common}
      />
    );
  }
  if (visual.shape === "pill") {
    return (
      <rect
        x={cx - radius * 1.24}
        y={cy - radius * 0.78}
        width={radius * 2.48}
        height={radius * 1.56}
        rx={radius}
        {...common}
      />
    );
  }

  return <circle cx={cx} cy={cy} r={radius} {...common} />;
}

function buildEdgePath(sourceX: number, sourceY: number, targetX: number, targetY: number): string {
  const curve = Math.max(34, Math.abs(targetX - sourceX) * 0.42);
  return `M ${sourceX} ${sourceY} C ${sourceX + curve} ${sourceY}, ${targetX - curve} ${targetY}, ${targetX} ${targetY}`;
}

function createDegreeMap(edges: ReturnType<typeof buildNetworkGraphModel>["edges"]): Map<string, number> {
  const degreeByNodeId = new Map<string, number>();
  for (const edge of edges) {
    degreeByNodeId.set(edge.sourceId, (degreeByNodeId.get(edge.sourceId) ?? 0) + 1);
    degreeByNodeId.set(edge.targetId, (degreeByNodeId.get(edge.targetId) ?? 0) + 1);
  }
  return degreeByNodeId;
}

function renderLegendShape(
  visual: LayerVisual,
  x: number,
  y: number,
  radius = 8,
): ReactNode {
  return renderNodeSymbol({ cx: x, cy: y, radius, visual, opacity: 1 });
}

export default function NetworkGraph({ chains, taskId }: NetworkGraphProps) {
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [focusedNodeId, setFocusedNodeId] = useState<string | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const nodeRefs = useRef(new Map<string, SVGGElement>());
  const svgRef = useRef<SVGSVGElement>(null);

  const model = buildNetworkGraphModel(chains);
  const { layers, nodes, edges } = model;
  const degreeByNodeId = createDegreeMap(edges);
  const maxDegree = Math.max(1, ...Array.from(degreeByNodeId.values()));

  const renderX = (x: number) => x + GRAPH_OFFSET_X;
  const renderY = (y: number) => y + GRAPH_OFFSET_Y;
  const layerX = (index: number) => START_X + index * LAYER_GAP_X + GRAPH_OFFSET_X;

  const handleExportPng = async () => {
    if (!svgRef.current || isExporting) return;
    setIsExporting(true);
    try {
      const filename = taskId
        ? `network-graph-${taskId}.png`
        : "network-graph.png";
      await exportSvgToPng(svgRef.current, filename);
    } catch (err) {
      console.error("Failed to export PNG:", err);
      alert("导出 PNG 失败，请重试");
    } finally {
      setIsExporting(false);
    }
  };

  const handleExportSvg = () => {
    if (!svgRef.current || isExporting) return;
    setIsExporting(true);
    try {
      const filename = taskId
        ? `network-graph-${taskId}.svg`
        : "network-graph.svg";
      exportSvgToSvg(svgRef.current, filename);
    } catch (err) {
      console.error("Failed to export SVG:", err);
      alert("导出 SVG 失败，请重试");
    } finally {
      setIsExporting(false);
    }
  };

  if (nodes.length === 0) {
    return (
      <div style={{ overflowX: "auto", marginTop: 24 }}>
        <svg
          viewBox="0 0 1040 220"
          role="img"
          aria-label="网络药理学成分-靶点-通路-疾病链图"
          style={{ width: "100%", minWidth: 720 }}
        >
          <rect x={0} y={0} width={1040} height={220} fill="#ffffff" />
          {layers.map((layer, index) => {
            const visual = getLayerVisual(layer.key);
            const x = layerX(index);
            return (
              <g key={layer.key}>
                <rect
                  x={x - LAYER_BAND_WIDTH / 2}
                  y={40}
                  width={LAYER_BAND_WIDTH}
                  height={120}
                  rx={6}
                  fill={visual.bandFill}
                  opacity={0.5}
                />
                <text
                  x={x}
                  y={70}
                  textAnchor="middle"
                  fontSize={11}
                  fontWeight={700}
                  fill="#475569"
                  fontFamily="'Noto Sans SC', sans-serif"
                >
                  {layer.label}
                </text>
                {renderLegendShape(visual, x, 104, 10)}
              </g>
            );
          })}
          <text x={520} y={190} textAnchor="middle" fontSize={12} fontWeight={600} fill="#64748b" fontFamily="'Noto Sans SC', sans-serif">
            暂无网络数据
          </text>
        </svg>
      </div>
    );
  }

  const nodeMap = new Map(nodes.map((n) => [n.id, n]));
  const maxNodeX = Math.max(...nodes.map((n) => n.x));
  const maxNodeY = Math.max(...nodes.map((n) => n.y));
  const svgWidth = maxNodeX + GRAPH_OFFSET_X + 140;
  const svgHeight = maxNodeY + GRAPH_OFFSET_Y + 160;
  const graphBandHeight = Math.max(140, maxNodeY + GRAPH_OFFSET_Y - 30);
  const legendY = maxNodeY + GRAPH_OFFSET_Y + 56;

  // Focus takes priority so keyboard users get a stable highlight.
  const activeNodeId = focusedNodeId ?? hoveredNodeId;

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
    <div>
      {nodes.length > 0 && (
        <div
          style={{
            marginTop: 12,
            marginBottom: 12,
            display: "flex",
            gap: 10,
            alignItems: "center",
            flexWrap: "wrap",
          }}
        >
          <button
            onClick={handleExportPng}
            disabled={isExporting}
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 6,
              padding: "6px 12px",
              minHeight: 36,
              fontSize: 13,
              color: isExporting ? "#94a3b8" : "#334155",
              backgroundColor: "#ffffff",
              border: "1px solid #e2e8f0",
              borderRadius: 4,
              cursor: isExporting ? "not-allowed" : "pointer",
              fontWeight: 600,
            }}
          >
            <DownloadOutlined aria-hidden="true" />
            <span>{isExporting ? "导出中..." : "导出 PNG"}</span>
          </button>
          <button
            onClick={handleExportSvg}
            disabled={isExporting}
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 6,
              padding: "6px 12px",
              minHeight: 36,
              fontSize: 13,
              color: isExporting ? "#94a3b8" : "#334155",
              backgroundColor: "#ffffff",
              border: "1px solid #e2e8f0",
              borderRadius: 4,
              cursor: isExporting ? "not-allowed" : "pointer",
              fontWeight: 600,
            }}
          >
            <DownloadOutlined aria-hidden="true" />
            <span>{isExporting ? "导出中..." : "导出 SVG"}</span>
          </button>
        </div>
      )}
      <div
        style={{
          overflowX: "auto",
          border: "1px solid #e2e8f0",
          borderRadius: 4,
          background: "#ffffff",
        }}
      >
        <svg
          ref={svgRef}
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          role="img"
          aria-label="网络药理学成分-靶点-通路-疾病链图"
          style={{ width: "100%", minWidth: 820, display: "block" }}
        >
          <defs>
            <marker
              id="networkGraphArrow"
              viewBox="0 0 10 10"
              refX="8.5"
              refY="5"
              markerWidth="5"
              markerHeight="5"
              orient="auto-start-reverse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#475569" opacity={0.85} />
            </marker>
          </defs>

          <rect
            x={0}
            y={0}
            width={svgWidth}
            height={svgHeight}
            fill="#ffffff"
            onClick={() => setFocusedNodeId(null)}
          />

          {/* Layer columns */}
          {layers.map((layer, i) => {
            const visual = getLayerVisual(layer.key);
            const x = layerX(i);
            return (
              <g key={layer.key}>
                <rect
                  x={x - LAYER_BAND_WIDTH / 2}
                  y={44}
                  width={LAYER_BAND_WIDTH}
                  height={graphBandHeight}
                  rx={6}
                  fill={visual.bandFill}
                  opacity={0.5}
                />
                <text
                  x={x}
                  y={36}
                  textAnchor="middle"
                  fontSize={11}
                  fontWeight={700}
                  fill="#475569"
                  fontFamily="'Noto Sans SC', sans-serif"
                >
                  {layer.label}
                </text>
              </g>
            );
          })}

          {/* Focus indicator text */}
          {focusedNode ? (
            <text
              x={24}
              y={20}
              fontSize={10}
              fill="#334155"
              fontWeight={600}
              fontFamily="'Noto Sans SC', sans-serif"
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
                effectiveStroke = isFocusedEdge ? "#0f172a" : "#334155";
                effectiveStrokeWidth = style.strokeWidth + 0.6;
                effectiveOpacity = 0.95;
              } else {
                effectiveOpacity = 0.08;
              }
            }

            const sourceX = renderX(source.x) + EDGE_PORT_OFFSET;
            const targetX = renderX(target.x) - EDGE_PORT_OFFSET;
            const sourceY = renderY(source.y);
            const targetY = renderY(target.y);

            return (
              <path
                key={`${edge.sourceId}->${edge.targetId}#${index}`}
                d={buildEdgePath(sourceX, sourceY, targetX, targetY)}
                fill="none"
                stroke={effectiveStroke}
                strokeWidth={effectiveStrokeWidth}
                opacity={effectiveOpacity}
                strokeLinecap="round"
                markerEnd="url(#networkGraphArrow)"
              />
            );
          })}

          {/* Nodes */}
          {nodes.map((node) => {
            const visual = getLayerVisual(node.layer);
            const degree = degreeByNodeId.get(node.id) ?? 0;
            const nodeRadius = computeNodeRadius(degree, maxDegree);
            const isRelated = connectedNodeIds.has(node.id);
            const isFocused = focusedNodeId === node.id;
            const x = renderX(node.x);
            const y = renderY(node.y);

            let effectiveNodeOpacity = 1;
            if (activeNodeId) {
              effectiveNodeOpacity = isRelated ? 1 : 0.25;
            }

            const lines = splitLabelIntoLines(node.label);
            const labelX = x + nodeRadius + LABEL_GAP_X;

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
                {isFocused ? (
                  <circle
                    cx={x}
                    cy={y}
                    r={nodeRadius + 5}
                    fill="none"
                    stroke="#0f766e"
                    strokeWidth={2}
                    strokeDasharray="4 2"
                  />
                ) : null}
                {renderNodeSymbol({
                  cx: x,
                  cy: y,
                  radius: nodeRadius,
                  visual,
                  opacity: effectiveNodeOpacity,
                })}
                <text
                  x={labelX}
                  y={y - (lines.length - 1) * 6}
                  textAnchor="start"
                  dominantBaseline="central"
                  fontSize={lines.length > 1 ? 9 : 10}
                  fill="#1e293b"
                  fontWeight={600}
                  fontFamily="'Noto Sans SC', sans-serif"
                  opacity={effectiveNodeOpacity}
                >
                  {lines.map((line, index) => (
                    <tspan key={`${node.id}-line-${index}`} x={labelX} dy={index === 0 ? 0 : 12}>
                      {line}
                    </tspan>
                  ))}
                </text>
                <title>{`${LAYER_LABEL_MAP[node.layer] ?? node.layer}: ${node.label} (${formatDegree(degree)})`}</title>
              </g>
            );
          })}

          {/* Legend */}
          <g aria-hidden="true">
            <rect
              x={26}
              y={legendY - 18}
              width={svgWidth - 52}
              height={86}
              rx={4}
              fill="#ffffff"
              stroke="#e2e8f0"
              strokeWidth={0.8}
            />
            <text x={40} y={legendY} fontSize={10} fill="#334155" fontWeight={700} fontFamily="'Noto Sans SC', sans-serif">
              {"图例: 节点形状/颜色表示类别，节点符号大小表示 degree，连线粗细表示置信度"}
            </text>
            {layers.map((layer, index) => {
              const visual = getLayerVisual(layer.key);
              const lx = 40 + index * 100;
              return (
                <g key={`legend-${layer.key}`}>
                  {renderLegendShape(visual, lx, legendY + 20, 7)}
                  <text x={lx + 12} y={legendY + 24} fontSize={9} fill="#475569" fontWeight={600} fontFamily="'Noto Sans SC', sans-serif">
                    {visual.label}
                  </text>
                </g>
              );
            })}
            <text x={40} y={legendY + 50} fontSize={9} fill="#475569" fontWeight={600}>
              {"置信度:"}
            </text>
            <line
              x1={88}
              y1={legendY + 47}
              x2={120}
              y2={legendY + 47}
              stroke="#1e293b"
              strokeWidth={2.6}
              opacity={0.92}
              strokeLinecap="round"
            />
            <text x={126} y={legendY + 50} fontSize={9} fill="#475569" fontWeight={600}>
              {"≥0.9"}
            </text>
            <line
              x1={160}
              y1={legendY + 47}
              x2={192}
              y2={legendY + 47}
              stroke="#64748b"
              strokeWidth={1.8}
              opacity={0.72}
              strokeLinecap="round"
            />
            <text x={198} y={legendY + 50} fontSize={9} fill="#475569" fontWeight={600}>
              {"≥0.7"}
            </text>
            <line
              x1={232}
              y1={legendY + 47}
              x2={264}
              y2={legendY + 47}
              stroke="#cbd5e1"
              strokeWidth={1.2}
              opacity={0.56}
              strokeLinecap="round"
            />
            <text x={270} y={legendY + 50} fontSize={9} fill="#475569" fontWeight={600}>
              {"<0.7"}
            </text>
            <circle cx={320} cy={legendY + 47} r={5} fill="#94a3b8" opacity={0.5} />
            <text x={330} y={legendY + 50} fontSize={9} fill="#475569" fontWeight={600}>
              {"小 = 低 degree"}
            </text>
            <circle cx={410} cy={legendY + 47} r={10} fill="#94a3b8" opacity={0.5} />
            <text x={424} y={legendY + 50} fontSize={9} fill="#475569" fontWeight={600}>
              {"大 = 高 degree"}
            </text>
          </g>

          {/* Figure caption */}
          <text
            x={svgWidth / 2}
            y={svgHeight - 12}
            textAnchor="middle"
            fontSize={10}
            fill="#334155"
            fontWeight={600}
            fontFamily="'Noto Sans SC', sans-serif"
          >
            {`Fig. 「成分-靶点-通路-疾病」网络图 (nodes: ${nodes.length}, edges: ${edges.length})`}
          </text>
        </svg>
      </div>
    </div>
  );
}
