export type LiteratureItem = {
  id: string;
  title: string;
  language: "zh" | "en";
  source_type: "cn_literature" | "pubmed";
  source: string;
  year: number;
  snippet: string;
};

export type LiteratureSearchResponse = {
  query: string;
  total: number;
  items: LiteratureItem[];
};

export function getBackendBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
}

export function buildLiteratureSearchUrl(query: string) {
  const url = new URL("/api/literature/search", getBackendBaseUrl());
  url.searchParams.set("q", query.trim());
  return url.toString();
}

export async function searchLiterature(query: string): Promise<LiteratureSearchResponse> {
  const response = await fetch(buildLiteratureSearchUrl(query));

  if (!response.ok) {
    throw new Error("Literature search failed");
  }

  return response.json();
}
