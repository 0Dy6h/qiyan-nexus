export type LiteratureItem = {
  id: string;
  title: string;
  language: "zh" | "en";
  source_type: "cn_literature" | "pubmed";
  source: string;
  year: number;
  snippet: string;
};

export type LiteratureSource = "all" | "cn_literature" | "pubmed";

export type LiteratureSearchResponse = {
  query: string;
  total: number;
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

export function buildLiteratureSearchUrl(query: string, source: LiteratureSource = "all") {
  const url = new URL("/api/literature/search", getBackendBaseUrl());
  url.searchParams.set("q", query.trim());
  if (source !== "all") {
    url.searchParams.set("source", source);
  }
  return url.toString();
}

export async function searchLiterature(
  query: string,
  source: LiteratureSource = "all",
): Promise<LiteratureSearchResponse> {
  const response = await fetch(buildLiteratureSearchUrl(query, source));

  if (!response.ok) {
    throw new Error("Literature search failed");
  }

  return response.json();
}
