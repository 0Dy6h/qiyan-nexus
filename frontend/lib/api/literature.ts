export type LiteratureItem = {
  id: string;
  title: string;
  language: "zh" | "en";
  source_type: "cn_literature" | "pubmed";
  source: string;
  year: number;
  snippet: string;
  pdf_upload_id?: string | null;
  pdf_file_name?: string | null;
  pdf_parse_status?: "pending" | "parsed" | "failed" | null;
  pdf_parse_message?: string | null;
  pdf_parse_started_at?: string | null;
  pdf_parse_finished_at?: string | null;
  pdf_parse_result?: {
    file_name: string;
    storage_path: string;
    file_size: number;
    preview_text: string;
    extraction_method: string;
  } | null;
  last_parse_trigger?: "auto" | "manual" | null;
  parse_attempt_count?: number | null;
};

export type LiteratureSource = "all" | "cn_literature" | "pubmed";
export type LiteratureSearchSort = "relevance" | "year_desc" | "year_asc";
export type PdfParseStatus = "pending" | "parsed" | "failed";

export type LiteratureSearchResponse = {
  query: string;
  source: LiteratureSource;
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  sort: LiteratureSearchSort;
  items: LiteratureItem[];
};

export type PdfUploadResponse = {
  literature_id: string;
  pdf_upload_id: string;
  file_name: string;
  content_type: string;
  file_size: number;
  storage_path: string;
  pdf_parse_status: PdfParseStatus;
};

export type LiteratureSyncRequest = {
  source: "pubmed";
  q: string;
  max_results: number;
};

export type LiteratureSyncResponse = {
  source: "pubmed";
  query: string;
  fetched: number;
  created: number;
  updated: number;
  items: LiteratureItem[];
};

export function getBackendBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
}

export function getLiteratureSourceLabel(source: LiteratureSource) {
  if (source === "cn_literature") {
    return "中文文献";
  }
  if (source === "pubmed") {
    return "PubMed";
  }
  return "全部";
}

export function getParseTriggerLabel(trigger: LiteratureItem["last_parse_trigger"]) {
  if (trigger === "auto") {
    return "自动触发";
  }
  if (trigger === "manual") {
    return "手动触发";
  }
  return null;
}

export function getParseAttemptLabel(count: LiteratureItem["parse_attempt_count"]) {
  if (count === null || count === undefined) {
    return null;
  }
  return `尝试 ${count} 次`;
}

export function getPdfParseStatusLabel(status: LiteratureItem["pdf_parse_status"]) {
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

export function buildLiteratureSearchUrl(
  query: string,
  source: LiteratureSource = "all",
  page = 1,
  pageSize = 10,
  sort: LiteratureSearchSort = "relevance",
) {
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

export function buildLiteratureDetailUrl(itemId: string) {
  const encodedItemId = encodeURIComponent(itemId);
  return new URL(`/api/literature/${encodedItemId}`, getBackendBaseUrl()).toString();
}

export function buildPdfUploadUrl() {
  return new URL("/api/uploads/pdf", getBackendBaseUrl()).toString();
}

export function buildPdfDownloadUrl(pdfUploadId: string) {
  const encodedPdfUploadId = encodeURIComponent(pdfUploadId);
  return new URL(`/api/uploads/pdf/${encodedPdfUploadId}`, getBackendBaseUrl()).toString();
}

export function buildPdfParseStatusRequest(literatureId: string, status: Exclude<PdfParseStatus, "pending">) {
  return {
    literature_id: literatureId,
    pdf_parse_status: status,
  };
}

export function buildFakePdfAutoParseRequest(literatureId: string, fileName: string) {
  return {
    literature_id: literatureId,
    file_name: fileName,
  };
}

export async function searchLiterature(
  query: string,
  source: LiteratureSource = "all",
  page = 1,
  pageSize = 10,
  sort: LiteratureSearchSort = "relevance",
): Promise<LiteratureSearchResponse> {
  const response = await fetch(buildLiteratureSearchUrl(query, source, page, pageSize, sort));

  if (!response.ok) {
    throw new Error("Literature search failed");
  }

  return response.json();
}

export async function getLiteratureDetail(itemId: string): Promise<LiteratureItem> {
  const response = await fetch(buildLiteratureDetailUrl(itemId));

  if (!response.ok) {
    throw new Error("Literature detail request failed");
  }

  return response.json();
}

export async function uploadLiteraturePdf(
  literatureId: string,
  file: File,
): Promise<PdfUploadResponse> {
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

export async function runFakePdfAutoParse(literatureId: string, fileName: string): Promise<LiteratureItem> {
  const response = await fetch(new URL("/api/uploads/pdf/auto-parse", getBackendBaseUrl()).toString(), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(buildFakePdfAutoParseRequest(literatureId, fileName)),
  });

  if (!response.ok) {
    throw new Error("Fake PDF auto parse failed");
  }

  return response.json();
}

export async function updatePdfParseStatus(
  literatureId: string,
  status: Exclude<PdfParseStatus, "pending">,
): Promise<LiteratureItem> {
  const response = await fetch(new URL("/api/literature/pdf-parse-status", getBackendBaseUrl()).toString(), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(buildPdfParseStatusRequest(literatureId, status)),
  });

  if (!response.ok) {
    throw new Error("PDF parse status update failed");
  }

  return response.json();
}

export const LITERATURE_SYNC_MAX_RESULTS_CAP = 50;

export function buildLiteratureSyncUrl() {
  return new URL("/api/literature/sync", getBackendBaseUrl()).toString();
}

export function buildLiteratureSyncRequest(query: string, maxResults: number): LiteratureSyncRequest {
  const trimmed = query.trim();
  const bounded = Math.max(1, Math.min(LITERATURE_SYNC_MAX_RESULTS_CAP, Math.floor(maxResults)));
  return {
    source: "pubmed",
    q: trimmed,
    max_results: bounded,
  };
}

export async function syncLiteratureFromPubmed(
  query: string,
  maxResults: number,
): Promise<LiteratureSyncResponse> {
  const response = await fetch(buildLiteratureSyncUrl(), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(buildLiteratureSyncRequest(query, maxResults)),
  });

  if (!response.ok) {
    throw new Error("Literature sync failed");
  }

  return response.json();
}
