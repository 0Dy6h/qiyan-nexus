import { fetchJson, fetchText, postJson } from "./http";
import { getBackendBaseUrl } from "./rag";

export type NetworkAnalysisType = "formula" | "herb";

export type NetworkTaskStatus = "queued" | "running" | "completed";

export type NetworkChain = {
  herb: string;
  formula?: string | null;
  compound: string;
  target: string;
  pathway: string;
  disease: string;
  score: number;
  related_entity_ids: string[];
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
  chains: NetworkChain[];
  enrichment?: EnrichmentResult | null;
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
  result: NetworkAnalysisResult | null;
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

export async function submitNetworkAnalysis(
  query: string,
  analysisType: NetworkAnalysisType,
): Promise<NetworkAnalyzeAccepted> {
  return postJson<NetworkAnalyzeAccepted>(buildNetworkAnalyzeUrl(), {
    query: query.trim(),
    analysis_type: analysisType,
  });
}

export async function fetchNetworkResult(taskId: string): Promise<NetworkResultResponse> {
  return fetchJson<NetworkResultResponse>(buildNetworkResultUrl(taskId));
}

export async function fetchNetworkReportMarkdown(taskId: string): Promise<string> {
  return fetchText(buildNetworkReportUrl(taskId));
}
