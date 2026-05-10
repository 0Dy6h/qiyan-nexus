export function getBackendBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
}

export function buildRagAdEvalReportUrl() {
  return new URL("/api/evals/rag-ad/report", getBackendBaseUrl()).toString();
}

export function formatEvalPassRate(passRate) {
  return `${Math.round(passRate * 100)}%`;
}

export function getEvalItemStatusLabel(passed) {
  return passed ? "通过" : "需复核";
}

export async function getRagAdEvalReport() {
  const response = await fetch(buildRagAdEvalReportUrl());

  if (!response.ok) {
    throw new Error("RAG AD eval report request failed");
  }

  return response.json();
}
