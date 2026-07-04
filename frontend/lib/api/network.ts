import { apiFetch, buildApiHeaders } from "./client";
import { getBackendBaseUrl } from "./rag";

export type NetworkAnalysisType = "formula" | "herb";

export type NetworkTaskStatus = "queued" | "running" | "completed" | "failed";
export type NetworkDataMode = "mock" | "live";
export type NetworkTargetEvidenceType = "mock" | "known_activity" | "predicted" | "mixed";
export type NetworkEvidenceLevel =
  | "mock_inferred"
  | "predicted"
  | "literature_supported"
  | "experimental";
export type NetworkPipelineStepStatus = "completed" | "failed" | "skipped" | "degraded";

export type NetworkChain = {
  herb: string;
  formula?: string | null;
  compound: string;
  target: string;
  pathway: string;
  disease: string;
  score: number;
  related_entity_ids: string[];
  evidence_refs?: string[];
  target_evidence_type?: NetworkTargetEvidenceType;
  evidence_level?: NetworkEvidenceLevel | null;
};

export type NetworkDataSource = {
  name: string;
  source_record_id?: string | null;
  url?: string | null;
  retrieved_at?: string | null;
  license_note?: string | null;
  cache_key?: string | null;
  from_cache?: boolean;
};

export type NetworkPipelineStep = {
  name: string;
  status: NetworkPipelineStepStatus;
  duration_ms: number;
  external_request_count: number;
  cache_hit_count: number;
  warning?: string | null;
};

export type NetworkPpiEdge = {
  source: string;
  target: string;
  score: number;
  source_record_id: string;
};

export type EnrichmentTerm = {
  term_id: string;
  term_name: string;
  term_name_zh?: string | null;
  category: string;
  gene_count: number;
  overlap_count: number;
  p_value: number;
  adjusted_p_value: number;
  genes: string[];
};

export type EnrichmentResult = {
  analysis_type: string;
  input_gene_count: number;
  background_gene_count: number;
  terms: EnrichmentTerm[];
  timestamp: string;
};

export type NetworkAnalysisResult = {
  task_id: string;
  query: string;
  analysis_type: NetworkAnalysisType;
  data_mode?: NetworkDataMode;
  chains: NetworkChain[];
  enrichment?: EnrichmentResult | null;
  pipeline_steps?: NetworkPipelineStep[];
  data_sources?: NetworkDataSource[];
  ppi_edges?: NetworkPpiEdge[];
  warnings?: string[];
  disclaimer: string;
};

export type NetworkAnalyzeAccepted = {
  task_id: string;
  status: NetworkTaskStatus;
  progress: number;
};

export type NetworkResultResponse = {
  task_id: string;
  status: NetworkTaskStatus;
  progress: number;
  data_mode?: NetworkDataMode;
  result: NetworkAnalysisResult | null;
  error?: string | null;
  warnings?: string[];
};

export function buildNetworkAnalyzeUrl() {
  return new URL("/api/network/analyze", getBackendBaseUrl()).toString();
}

export function buildNetworkResultUrl(taskId: string) {
  return new URL(`/api/network/result/${encodeURIComponent(taskId)}`, getBackendBaseUrl()).toString();
}

export function buildNetworkReportUrl(taskId: string) {
  return new URL(
    `/api/network/result/${encodeURIComponent(taskId)}/report`,
    getBackendBaseUrl(),
  ).toString();
}

export function getNetworkAnalysisTypeLabel(type: NetworkAnalysisType) {
  return type === "herb" ? "单味中药" : "复方";
}

export function getNetworkDataModeLabel(mode: NetworkDataMode | undefined) {
  return mode === "live" ? "真实数据 opt-in" : "Mock 演示数据";
}

export function getNetworkTargetEvidenceTypeLabel(type: NetworkTargetEvidenceType | undefined) {
  switch (type) {
    case "known_activity":
      return "已知活性证据";
    case "predicted":
      return "预测靶点";
    case "mixed":
      return "已知+预测";
    default:
      return "Mock";
  }
}

export function getNetworkEvidenceLevelLabel(level: NetworkEvidenceLevel | undefined | null) {
  switch (level) {
    case "experimental":
      return "实验证据";
    case "literature_supported":
      return "文献支撑";
    case "predicted":
      return "预测证据";
    default:
      return "演示推断（未验证）";
  }
}

export async function submitNetworkAnalysis(
  query: string,
  analysisType: NetworkAnalysisType,
): Promise<NetworkAnalyzeAccepted> {
  const response = await apiFetch(buildNetworkAnalyzeUrl(), {
    method: "POST",
    headers: buildApiHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ query: query.trim(), analysis_type: analysisType }),
  });

  if (!response.ok) {
    throw new Error("Network analyze request failed");
  }

  return response.json();
}

export async function fetchNetworkResult(taskId: string): Promise<NetworkResultResponse> {
  const response = await apiFetch(buildNetworkResultUrl(taskId));

  if (!response.ok) {
    throw new Error("Network result request failed");
  }

  return response.json();
}

export async function fetchNetworkReportMarkdown(taskId: string): Promise<string> {
  const response = await apiFetch(buildNetworkReportUrl(taskId));

  if (!response.ok) {
    throw new Error("Network report request failed");
  }

  return response.text();
}
