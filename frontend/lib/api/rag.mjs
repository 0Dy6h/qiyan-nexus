export function getBackendBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
}

export function buildRagAnswerUrl() {
  return new URL("/api/rag/answer", getBackendBaseUrl()).toString();
}

export function buildRagExportUrl() {
  return new URL("/api/rag/export", getBackendBaseUrl()).toString();
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

export function getCitationSourceTypeLabel(sourceType) {
  if (sourceType === "cn_literature") {
    return "中文文献";
  }
  return "PubMed";
}

export function buildRagMarkdownDownloadName(fileName) {
  const trimmed = fileName.trim();
  return trimmed.endsWith(".md") ? trimmed : "qiyan-rag-report.md";
}

export async function answerRagQuestion(question, source = "all", topK = 2) {
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

export async function exportRagMarkdown(question, source = "all", topK = 2) {
  const response = await fetch(buildRagExportUrl(), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      ...buildRagAnswerRequest(question, source, topK),
      format: "markdown",
    }),
  });

  if (!response.ok) {
    throw new Error("RAG export request failed");
  }

  return response.json();
}
