"use client";

import { buildNetworkGraphModel } from "../lib/network-graph";
import type { NetworkChain } from "../lib/api/network";

interface NetworkGraphProps {
  chains: NetworkChain[];
}

const LAYER_FILL: Record<string, string> = {
  herb: "#ccfbf1",
  compound: "#e0e7ff",
  target: "#fef3c7",
  pathway: "#dcfce7",
  disease: "#fce7f3",
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
  return { stroke: "#99f6e4", strokeWidth: 1.5, opacity: 0.45 };
}

export default function NetworkGraph({ chains }: NetworkGraphProps) {
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
          <rect x={0} y={0} width={1000} height={200} fill="#ffffff" />
          {layers.map((layer, i) => (
            <text
              key={layer.key}
              x={START_X + i * LAYER_GAP_X}
              y={START_Y - 12}
              textAnchor="middle"
              fontSize={14}
              fontWeight={700}
              fill="#1e293b"
            >
              {layer.label}
            </text>
          ))}
          <text x={500} y={110} textAnchor="middle" fontSize={16} fill="#64748b">
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

  return (
    <div style={{ overflowX: "auto", marginTop: 24 }}>
      <svg
        viewBox={`0 0 ${svgWidth} ${svgHeight}`}
        role="img"
        aria-label="网络药理学成分-靶点-通路-疾病链图"
        style={{ width: "100%", minWidth: 600 }}
      >
        <rect x={0} y={0} width={svgWidth} height={svgHeight} fill="#ffffff" />

        {/* Layer headers */}
        {layers.map((layer, i) => (
          <text
            key={layer.key}
            x={START_X + i * LAYER_GAP_X}
            y={START_Y - 12}
            textAnchor="middle"
            fontSize={14}
            fontWeight={700}
            fill="#1e293b"
          >
            {layer.label}
          </text>
        ))}

        {/* Edges */}
        {edges.map((edge, index) => {
          const source = nodeMap.get(edge.sourceId);
          const target = nodeMap.get(edge.targetId);
          if (!source || !target) return null;
          const style = getEdgeStyle(edge.score);
          return (
            <line
              key={`${edge.sourceId}->${edge.targetId}#${index}`}
              x1={source.x}
              y1={source.y}
              x2={target.x}
              y2={target.y}
              stroke={style.stroke}
              strokeWidth={style.strokeWidth}
              opacity={style.opacity}
            />
          );
        })}

        {/* Nodes */}
        {nodes.map((node) => (
          <g key={node.id}>
            <circle
              cx={node.x}
              cy={node.y}
              r={20}
              fill={LAYER_FILL[node.layer] ?? "#f1f5f9"}
              stroke="#0d9488"
              strokeWidth={1.5}
            />
            <text
              x={node.x}
              y={node.y}
              textAnchor="middle"
              dominantBaseline="central"
              fontSize={11}
              fill="#1e293b"
              fontWeight={600}
            >
              {node.label}
            </text>
            <title>{`${LAYER_LABEL_MAP[node.layer] ?? node.layer}: ${node.label}`}</title>
          </g>
        ))}

        {/* Legend */}
        <text x={20} y={legendY} fontSize={12} fill="#64748b" fontWeight={600}>
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
        <text x={68} y={legendY + 24} fontSize={11} fill="#64748b">
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
        <text x={168} y={legendY + 24} fontSize={11} fill="#64748b">
          {"≥0.7"}
        </text>
        <line
          x1={220}
          y1={legendY + 20}
          x2={260}
          y2={legendY + 20}
          stroke="#99f6e4"
          strokeWidth={1.5}
          opacity={0.45}
        />
        <text x={268} y={legendY + 24} fontSize={11} fill="#64748b">
          {"<0.7"}
        </text>
      </svg>
    </div>
  );
}