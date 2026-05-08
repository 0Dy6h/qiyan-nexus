export function getBackendBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
}

export function buildRagAnswerUrl() {
  return new URL("/api/rag/answer", getBackendBaseUrl()).toString();
}

export function buildRagAnswerRequest(question, source = "all", topK = 2) {
  return {
    question: question.trim(),
    source,
    top_k: topK,
  };
}

export function getRagSourceLabel(source) {
  if (source === "cn_literature") {
    return "中文文献";
  }
  if (source === "pubmed") {
    return "PubMed";
  }
  return "全部文献";
}
