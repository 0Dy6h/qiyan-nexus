export function getBackendBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
}

export function getLiteratureSourceLabel(source) {
  if (source === "cn_literature") {
    return "中文文献";
  }
  if (source === "pubmed") {
    return "PubMed";
  }
  return "全部";
}

export function getParseTriggerLabel(trigger) {
  if (trigger === "auto") {
    return "自动触发";
  }
  if (trigger === "manual") {
    return "手动触发";
  }
  return null;
}

export function getParseAttemptLabel(count) {
  if (count === null || count === undefined) {
    return null;
  }
  return `尝试 ${count} 次`;
}

export function buildLiteratureSearchUrl(query, source = "all") {
  const url = new URL("/api/literature/search", getBackendBaseUrl());
  url.searchParams.set("q", query.trim());
  if (source !== "all") {
    url.searchParams.set("source", source);
  }
  return url.toString();
}

export function buildLiteratureDetailUrl(itemId) {
  const encodedItemId = encodeURIComponent(itemId);
  return new URL(`/api/literature/${encodedItemId}`, getBackendBaseUrl()).toString();
}

export function buildPdfUploadUrl() {
  return new URL("/api/uploads/pdf", getBackendBaseUrl()).toString();
}

export function buildPdfParseStatusRequest(literatureId, status) {
  return {
    literature_id: literatureId,
    pdf_parse_status: status,
  };
}

export function buildFakePdfAutoParseRequest(literatureId, fileName) {
  return {
    literature_id: literatureId,
    file_name: fileName,
  };
}

export async function uploadLiteraturePdf(literatureId, file) {
  const formData = new FormData();
  formData.set("literature_id", literatureId);
  formData.set("file", file);

  const response = await fetch(buildPdfUploadUrl(), {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error("PDF upload failed");
  }

  return response.json();
}
