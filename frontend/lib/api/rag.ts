export type RagSource = "all" | "cn_literature" | "pubmed";

export type CitationCard = {
  literature_id: string;
  chunk_id?: string | null;
  title: string;
  source: string;
  snippet: string;
  quote?: string | null;
  reason?: string | null;
  confidence: number;
  source_type?: string | null;
  pdf_upload_id?: string | null;
  related_entity_ids?: string[];
};

export type RetrievalMetadata = {
  applied_source: RagSource;
  applied_top_k: number;
  available_citation_count: number;
  strategy: string;
};

export type GroundedClaim = {
  text: string;
  evidence_refs: string[];
  semantic_score?: number | null;
};

export type GroundingMetadata = {
  status: "skipped" | "passed" | "blocked";
  policy: "structured_claim_refs_v3" | "anthropic_tool_use_v1" | "opencode_go_tool_use_v1";
  checked: boolean;
  blocked_reason?: string | null;
  allowed_evidence_refs: string[];
  matched_evidence_refs: string[];
  unsupported_evidence_refs: string[];
  claim_count: number;
  cited_claim_count: number;
  structured_claims: GroundedClaim[];
  provider_native_grounding: boolean;
  tool_name?: string | null;
  tool_call_count: number;
  semantic_threshold?: number | null;
  min_semantic_score?: number | null;
};

export type ProviderSli = {
  provider_latency_ms?: number | null;
  estimated_cost_usd?: number | null;
};

export type RagAnswerResponse = {
  question: string;
  answer: string;
  disclaimer: string;
  retrieval: RetrievalMetadata;
  citations: CitationCard[];
  answered_at: string;
  provider_name: string;
  grounding: GroundingMetadata;
  input_tokens?: number | null;
  output_tokens?: number | null;
  sli?: ProviderSli | null;
};

export function getBackendBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
}

export function buildRagAnswerUrl() {
  return new URL("/api/rag/answer", getBackendBaseUrl()).toString();
}

export function buildRagAnswerRequest(question: string, source: RagSource = "all", topK = 2) {
  return {
    question: question.trim(),
    source,
    top_k: topK,
  };
}

export function getRagSourceLabel(source: RagSource) {
  if (source === "cn_literature") {
    return "中文文献";
  }
  if (source === "pubmed") {
    return "PubMed";
  }
  return "全部文献";
}

export async function answerRagQuestion(
  question: string,
  source: RagSource = "all",
  topK = 2,
): Promise<RagAnswerResponse> {
  const response = await fetch(buildRagAnswerUrl(), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(buildRagAnswerRequest(question, source, topK)),
  });

  if (!response.ok) {
    throw new Error("RAG answer request failed");
  }

  return response.json();
}
