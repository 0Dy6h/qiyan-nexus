const ACCESS_TOKEN_HEADER = "X-Access-Token";

export function getAccessToken() {
  return (process.env.NEXT_PUBLIC_QIYAN_ACCESS_TOKEN ?? "").trim();
}

function canonicalHeaderName(name: string) {
  const lowerName = name.toLowerCase();
  if (lowerName === "content-type") {
    return "Content-Type";
  }
  if (lowerName === "accept") {
    return "Accept";
  }
  if (lowerName === "x-access-token") {
    return ACCESS_TOKEN_HEADER;
  }
  return name;
}

export function buildApiHeaders(extra?: HeadersInit): Record<string, string> {
  const headers: Record<string, string> = {};
  new Headers(extra).forEach((value, key) => {
    headers[canonicalHeaderName(key)] = value;
  });
  const token = getAccessToken();
  if (token) {
    headers[ACCESS_TOKEN_HEADER] = token;
  }
  return headers;
}

export function apiFetch(input: URL | RequestInfo, init: RequestInit = {}): Promise<Response> {
  return fetch(input, {
    ...init,
    headers: buildApiHeaders(init.headers),
  });
}
