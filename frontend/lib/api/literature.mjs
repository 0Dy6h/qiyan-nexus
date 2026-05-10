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

export function getPdfParseStatusLabel(status) {
  if (status === "pending") {
    return "PDF 待解析";
  }
  if (status === "parsed") {
    return "PDF 已解析";
  }
  if (status === "failed") {
    return "PDF 解析失败";
  }
  return null;
}

export function buildLiteratureSearchUrl(query, source = "all", page = 1, pageSize = 10, sort = "relevance") {
  const url = new URL("/api/literature/search", getBackendBaseUrl());
  url.searchParams.set("q", query.trim());
  if (source !== "all") {
    url.searchParams.set("source", source);
  }
  if (page !== 1) {
    url.searchParams.set("page", String(page));
  }
  if (pageSize !== 10) {
    url.searchParams.set("page_size", String(pageSize));
  }
  if (sort !== "relevance") {
    url.searchParams.set("sort", sort);
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

export function buildPdfDownloadUrl(pdfUploadId) {
  const encodedPdfUploadId = encodeURIComponent(pdfUploadId);
  return new URL(`/api/uploads/pdf/${encodedPdfUploadId}`, getBackendBaseUrl()).toString();
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
