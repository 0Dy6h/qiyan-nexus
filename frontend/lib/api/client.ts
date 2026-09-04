function canonicalHeaderName(name: string) {
  const lowerName = name.toLowerCase();
  if (lowerName === "content-type") {
    return "Content-Type";
  }
  if (lowerName === "accept") {
    return "Accept";
  }
  return name;
}

export function buildApiHeaders(extra?: HeadersInit): Record<string, string> {
  const headers: Record<string, string> = {};
  new Headers(extra).forEach((value, key) => {
    if (key.toLowerCase() === "x-access-token") {
      return;
    }
    headers[canonicalHeaderName(key)] = value;
  });
  return headers;
}

function isInternalApiTarget(input: URL | RequestInfo, internalBaseUrl: string) {
  try {
    const inputUrl =
      input instanceof URL ? input.toString() : typeof input === "string" ? input : input.url;
    return new URL(inputUrl, internalBaseUrl).origin === new URL(internalBaseUrl).origin;
  } catch {
    return false;
  }
}

// 带 HTTP 状态码的请求错误：让 UI 能区分 404（资源不存在/不可见）与网络/服务故障，
// 而不是把所有失败折叠成「后端未启动」。
export class ApiStatusError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiStatusError";
    this.status = status;
  }
}

export function apiFetch(input: URL | RequestInfo, init: RequestInit = {}): Promise<Response> {
  const headers = buildApiHeaders(init.headers);
  if (typeof window === "undefined") {
    const internalToken = (process.env.QIYAN_INTERNAL_API_TOKEN ?? "").trim();
    const internalBaseUrl = (process.env.QIYAN_INTERNAL_API_BASE_URL ?? "").trim();
    if (internalToken && internalBaseUrl && isInternalApiTarget(input, internalBaseUrl)) {
      headers["X-Access-Token"] = internalToken;
    }
  }
  return fetch(input, {
    ...init,
    headers,
  });
}
