export type RagSource = "all" | "cn_literature" | "pubmed";

export type CitationCard = {
  literature_id: string;
  title: string;
  source: string;
  snippet: string;
  confidence: number;
};

export type RetrievalMetadata = {
  applied_source: RagSource;
  applied_top_k: number;
  available_citation_count: number;
};

export type RagAnswerResponse = {
  question: string;
  answer: string;
  disclaimer: string;
  retrieval: RetrievalMetadata;
  citations: CitationCard[];
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
