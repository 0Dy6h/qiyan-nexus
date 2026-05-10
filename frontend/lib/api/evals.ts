import { getBackendBaseUrl, type RagSource } from "./rag";

export type RagEvalSummary = {
  total_questions: number;
  passed_questions: number;
  pass_rate: number;
  citation_hit_count: number;
  chunk_hit_count: number;
  disclaimer_coverage_count: number;
  must_not_violation_count: number;
};

export type RagEvalItemResult = {
  id: string;
  question: string;
  source_preference: RagSource;
  difficulty: string;
  expected_literature_ids: string[];
  expected_literature_hits: string[];
  expected_chunk_ids: string[];
  expected_chunk_hits: string[];
  missing_must_include: string[];
  violated_must_not_include: string[];
  disclaimer_present: boolean;
  citation_count: number;
  passed: boolean;
};

export type RagEvalReport = {
  summary: RagEvalSummary;
  items: RagEvalItemResult[];
};

export function buildRagAdEvalReportUrl() {
  return new URL("/api/evals/rag-ad/report", getBackendBaseUrl()).toString();
}

export function formatEvalPassRate(passRate: number) {
  return `${Math.round(passRate * 100)}%`;
}

export function getEvalItemStatusLabel(passed: boolean) {
  return passed ? "通过" : "需复核";
}

export async function getRagAdEvalReport(): Promise<RagEvalReport> {
  const response = await fetch(buildRagAdEvalReportUrl());

  if (!response.ok) {
    throw new Error("RAG AD eval report request failed");
  }

  return response.json();
}
