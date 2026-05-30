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

export type NetworkAnalysisResult = {
  task_id: string;
  query: string;
  analysis_type: NetworkAnalysisType;
  chains: NetworkChain[];
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

export function getNetworkAnalysisTypeLabel(type: NetworkAnalysisType) {
  return type === "herb" ? "单味中药" : "复方";
}

export async function submitNetworkAnalysis(
  query: string,
  analysisType: NetworkAnalysisType,
): Promise<NetworkAnalyzeAccepted> {
  const response = await fetch(buildNetworkAnalyzeUrl(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query: query.trim(), analysis_type: analysisType }),
  });

  if (!response.ok) {
    throw new Error("Network analyze request failed");
  }

  return response.json();
}

export async function fetchNetworkResult(taskId: string): Promise<NetworkResultResponse> {
  const response = await fetch(buildNetworkResultUrl(taskId));

  if (!response.ok) {
    throw new Error("Network result request failed");
  }

  return response.json();
}
