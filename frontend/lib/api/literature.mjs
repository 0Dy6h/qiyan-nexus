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

export function buildLiteratureSearchUrl(query, source = "all") {
  const url = new URL("/api/literature/search", getBackendBaseUrl());
  url.searchParams.set("q", query.trim());
  if (source !== "all") {
    url.searchParams.set("source", source);
  }
  return url.toString();
}
