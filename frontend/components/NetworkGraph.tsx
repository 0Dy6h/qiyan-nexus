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
  shape: NodeShape;
}

// Publication-standard network pharmacology palette (Cytoscape convention):
// pastel fill + saturated border, distinct per category, print-friendly.
const LAYER_VISUALS: Record<LayerKey, LayerVisual> = {
  herb: {
    label: "中药/复方",
    fill: "#a8e6cf",
    stroke: "#2e8b57",
    shape: "hexagon",
  },
  compound: {
    label: "化合物",
    fill: "#a8d8ea",
    stroke: "#2b6cb0",
    shape: "circle",
  },
  target: {
    label: "靶点",
    fill: "#ffd3b6",
    stroke: "#c05621",
    shape: "rounded-rect",
  },
  pathway: {
    label: "通路",
    fill: "#d9b8ff",
    stroke: "#6b46c1",
    shape: "diamond",
  },
  disease: {
    label: "疾病",
    fill: "#ffb3b3",
    stroke: "#c53030",
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
const GRAPH_OFFSET_Y = 56;
const NODE_MIN_RADIUS = 14;
const NODE_MAX_RADIUS = 26;
const EDGE_PORT_OFFSET = 30;
const LABEL_GAP_X = 4;
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
  // Publication convention: uniform gray edges, subtle thickness for weight.
  if (score >= 0.9) {
    return { stroke: "#666666", strokeWidth: 1.6, opacity: 0.7 };
  }
  if (score >= 0.7) {
    return { stroke: "#999999", strokeWidth: 1.1, opacity: 0.5 };
  }
  return { stroke: "#bbbbbb", strokeWidth: 0.7, opacity: 0.38 };
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
  // Publication style: pastel fill + saturated category-colored border.
  const common = {
    fill: visual.fill,
    stroke: visual.stroke,
    strokeWidth: 1.4,
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
  // Gentle cubic bezier — subtle curve like Cytoscape's bundled-bezier style.
  const dx = Math.abs(targetX - sourceX);
  const curve = Math.max(20, dx * 0.3);
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
          viewBox="0 0 1040 180"
          role="img"
          aria-label="网络药理学成分-靶点-通路-疾病链图"
          style={{ width: "100%", minWidth: 720 }}
        >
          <rect x={0} y={0} width={1040} height={180} fill="#ffffff" />
          {layers.map((layer, index) => {
            const x = layerX(index);
            return (
              <text
                key={layer.key}
                x={x}
                y={50}
                textAnchor="middle"
                fontSize={10}
                fontWeight={600}
                fill="#4a5568"
                fontFamily="Arial, Helvetica, 'Noto Sans SC', sans-serif"
              >
                {layer.label}
              </text>
            );
          })}
          <text x={520} y={110} textAnchor="middle" fontSize={11} fontWeight={400} fill="#718096" fontFamily="Arial, Helvetica, 'Noto Sans SC', sans-serif">
            暂无网络数据
          </text>
        </svg>
      </div>
    );
  }

  const nodeMap = new Map(nodes.map((n) => [n.id, n]));
  const maxNodeX = Math.max(...nodes.map((n) => n.x));
  const maxNodeY = Math.max(...nodes.map((n) => n.y));
  const svgWidth = maxNodeX + GRAPH_OFFSET_X + 120;
  const svgHeight = maxNodeY + GRAPH_OFFSET_Y + 130;
  const legendY = maxNodeY + GRAPH_OFFSET_Y + 40;

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
              refX="9"
              refY="5"
              markerWidth="4"
              markerHeight="4"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 10 5 L 0 9 z" fill="#888888" opacity={0.6} />
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

          {/* Layer column headers — publication style: plain text, no background bands */}
          {layers.map((layer, i) => {
            const x = layerX(i);
            return (
              <text
                key={layer.key}
                x={x}
                y={28}
                textAnchor="middle"
                fontSize={10}
                fontWeight={600}
                fill="#4a5568"
                fontFamily="Arial, Helvetica, 'Noto Sans SC', sans-serif"
              >
                {layer.label}
              </text>
            );
          })}

          {/* Focus indicator text */}
          {focusedNode ? (
            <text
              x={24}
              y={16}
              fontSize={9}
              fill="#4a5568"
              fontWeight={500}
              fontFamily="Arial, Helvetica, 'Noto Sans SC', sans-serif"
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
                effectiveStroke = isFocusedEdge ? "#333333" : "#555555";
                effectiveStrokeWidth = style.strokeWidth + 0.4;
                effectiveOpacity = 0.85;
              } else {
                effectiveOpacity = 0.06;
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
              effectiveNodeOpacity = isRelated ? 1 : 0.2;
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
                    r={nodeRadius + 4}
                    fill="none"
                    stroke="#333333"
                    strokeWidth={1.2}
                    strokeDasharray="3 2"
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
                  y={y - (lines.length - 1) * 5}
                  textAnchor="start"
                  dominantBaseline="central"
                  fontSize={lines.length > 1 ? 8 : 9}
                  fill="#2d3748"
                  fontWeight={400}
                  fontFamily="Arial, Helvetica, 'Noto Sans SC', sans-serif"
                  opacity={effectiveNodeOpacity}
                >
                  {lines.map((line, index) => (
                    <tspan key={`${node.id}-line-${index}`} x={labelX} dy={index === 0 ? 0 : 11}>
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
              y={legendY - 14}
              width={svgWidth - 52}
              height={70}
              rx={2}
              fill="#ffffff"
              stroke="#cccccc"
              strokeWidth={0.5}
            />
            <text x={38} y={legendY} fontSize={9} fill="#4a5568" fontWeight={600} fontFamily="Arial, Helvetica, 'Noto Sans SC', sans-serif">
              {"图例: 节点形状/颜色表示类别，节点符号大小表示 degree，连线粗细表示置信度"}
            </text>
            {layers.map((layer, index) => {
              const visual = getLayerVisual(layer.key);
              const lx = 38 + index * 105;
              return (
                <g key={`legend-${layer.key}`}>
                  {renderLegendShape(visual, lx, legendY + 18, 6)}
                  <text x={lx + 10} y={legendY + 21} fontSize={8} fill="#4a5568" fontWeight={500} fontFamily="Arial, Helvetica, 'Noto Sans SC', sans-serif">
                    {visual.label}
                  </text>
                </g>
              );
            })}
            <text x={38} y={legendY + 42} fontSize={8} fill="#4a5568" fontWeight={500} fontFamily="Arial, Helvetica, sans-serif">
              {"置信度:"}
            </text>
            <line
              x1={82}
              y1={legendY + 39}
              x2={110}
              y2={legendY + 39}
              stroke="#666666"
              strokeWidth={1.6}
              opacity={0.7}
            />
            <text x={114} y={legendY + 42} fontSize={8} fill="#4a5568" fontWeight={500}>
              {"≥0.9"}
            </text>
            <line
              x1={144}
              y1={legendY + 39}
              x2={172}
              y2={legendY + 39}
              stroke="#999999"
              strokeWidth={1.1}
              opacity={0.5}
            />
            <text x={176} y={legendY + 42} fontSize={8} fill="#4a5568" fontWeight={500}>
              {"≥0.7"}
            </text>
            <line
              x1={206}
              y1={legendY + 39}
              x2={234}
              y2={legendY + 39}
              stroke="#bbbbbb"
              strokeWidth={0.7}
              opacity={0.38}
            />
            <text x={238} y={legendY + 42} fontSize={8} fill="#4a5568" fontWeight={500}>
              {"<0.7"}
            </text>
            <circle cx={284} cy={legendY + 39} r={4} fill="#cccccc" opacity={0.6} />
            <text x={292} y={legendY + 42} fontSize={8} fill="#4a5568" fontWeight={500}>
              {"小 = 低 degree"}
            </text>
            <circle cx={368} cy={legendY + 39} r={8} fill="#cccccc" opacity={0.6} />
            <text x={380} y={legendY + 42} fontSize={8} fill="#4a5568" fontWeight={500}>
              {"大 = 高 degree"}
            </text>
          </g>

          {/* Figure caption */}
          <text
            x={svgWidth / 2}
            y={svgHeight - 8}
            textAnchor="middle"
            fontSize={9}
            fill="#4a5568"
            fontWeight={400}
            fontFamily="Arial, Helvetica, 'Noto Sans SC', sans-serif"
          >
            {`Fig. 「中药-成分-靶点-通路-疾病」网络 (Nodes: ${nodes.length}, Edges: ${edges.length})`}
          </text>
        </svg>
      </div>
    </div>
  );
}
