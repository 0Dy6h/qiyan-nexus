import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

async function importClient() {
  return import(`../lib/api/client?ts=${Date.now()}`);
}

test("browser API client source does not read a public access-token environment variable", () => {
  const source = readFileSync(
    resolve(fileURLToPath(import.meta.url), "..", "..", "lib", "api", "client.ts"),
    "utf8",
  );

  assert.doesNotMatch(source, /NEXT_PUBLIC_QIYAN_ACCESS_TOKEN/);
});

test("buildApiHeaders preserves caller headers without exposing the browser access token", async () => {
  process.env.NEXT_PUBLIC_QIYAN_ACCESS_TOKEN = "dev-token";
  const { buildApiHeaders } = await importClient();

  const headers = buildApiHeaders({
    "Content-Type": "application/json",
    Accept: "text/markdown",
  });

  assert.equal(headers["Content-Type"], "application/json");
  assert.equal(headers.Accept, "text/markdown");
  assert.equal("X-Access-Token" in headers, false);
});

test("buildApiHeaders accepts Headers input without adding authentication headers", async () => {
  const { buildApiHeaders } = await importClient();

  const headers = buildApiHeaders(new Headers({ Accept: "application/json" }));

  assert.equal(headers.Accept, "application/json");
  assert.equal("X-Access-Token" in headers, false);
});

test("buildApiHeaders strips a backend access token supplied by browser code", async () => {
  const { buildApiHeaders } = await importClient();

  const headers = new Headers(
    buildApiHeaders({
      Accept: "application/json",
      "X-Access-Token": "must-stay-server-side",
    }),
  );

  assert.equal(headers.get("Accept"), "application/json");
  assert.equal(headers.has("X-Access-Token"), false);
});

test("apiFetch attaches the non-public internal token for server-side requests", async () => {
  process.env.QIYAN_INTERNAL_API_TOKEN = "  server-only-token  ";
  process.env.QIYAN_INTERNAL_API_BASE_URL = "http://127.0.0.1:8000";
  const originalFetch = globalThis.fetch;
  let capturedHeaders: HeadersInit | undefined;
  globalThis.fetch = (async (_url: URL | RequestInfo, init?: RequestInit) => {
    capturedHeaders = init?.headers;
    return { ok: true } as Response;
  }) as typeof globalThis.fetch;

  try {
    const { apiFetch } = await importClient();
    await apiFetch("http://127.0.0.1:8000/api/literature/item-1");

    assert.equal(new Headers(capturedHeaders).get("X-Access-Token"), "server-only-token");
  } finally {
    globalThis.fetch = originalFetch;
    delete process.env.QIYAN_INTERNAL_API_TOKEN;
    delete process.env.QIYAN_INTERNAL_API_BASE_URL;
  }
});

test("apiFetch does not send the internal token to a different server-side origin", async () => {
  process.env.QIYAN_INTERNAL_API_TOKEN = "server-only-token";
  process.env.QIYAN_INTERNAL_API_BASE_URL = "http://127.0.0.1:8000";
  const originalFetch = globalThis.fetch;
  let capturedHeaders: HeadersInit | undefined;
  globalThis.fetch = (async (_url: URL | RequestInfo, init?: RequestInit) => {
    capturedHeaders = init?.headers;
    return { ok: true } as Response;
  }) as typeof globalThis.fetch;

  try {
    const { apiFetch } = await importClient();
    await apiFetch("https://third-party.example/api");

    assert.equal(new Headers(capturedHeaders).has("X-Access-Token"), false);
  } finally {
    globalThis.fetch = originalFetch;
    delete process.env.QIYAN_INTERNAL_API_TOKEN;
    delete process.env.QIYAN_INTERNAL_API_BASE_URL;
  }
});

test("apiFetch never exposes the internal token from a browser request", async () => {
  process.env.QIYAN_INTERNAL_API_TOKEN = "server-only-token";
  const originalWindowDescriptor = Object.getOwnPropertyDescriptor(globalThis, "window");
  const originalFetch = globalThis.fetch;
  let capturedHeaders: HeadersInit | undefined;
  Object.defineProperty(globalThis, "window", { configurable: true, value: {} });
  globalThis.fetch = (async (_url: URL | RequestInfo, init?: RequestInit) => {
    capturedHeaders = init?.headers;
    return { ok: true } as Response;
  }) as typeof globalThis.fetch;

  try {
    const { apiFetch } = await importClient();
    await apiFetch("https://trial.example/api/literature/item-1");

    assert.equal(new Headers(capturedHeaders).has("X-Access-Token"), false);
  } finally {
    globalThis.fetch = originalFetch;
    delete process.env.QIYAN_INTERNAL_API_TOKEN;
    if (originalWindowDescriptor) {
      Object.defineProperty(globalThis, "window", originalWindowDescriptor);
    } else {
      Reflect.deleteProperty(globalThis, "window");
    }
  }
});

test("apiFetch forwards caller headers without injecting a browser access token", async () => {
  process.env.NEXT_PUBLIC_QIYAN_ACCESS_TOKEN = "dev-token";
  const originalFetch = globalThis.fetch;
  const captured: { url: URL | RequestInfo; init?: RequestInit }[] = [];
  globalThis.fetch = (async (url: URL | RequestInfo, init?: RequestInit) => {
    captured.push({ url, init });
    return {
      ok: true,
      async text() {
        return "ok";
      },
    } as Response;
  }) as typeof globalThis.fetch;

  try {
    const { apiFetch } = await importClient();
    const response = await apiFetch("http://127.0.0.1:8000/api/rag/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });

    assert.equal(await response.text(), "ok");
    assert.equal(captured.length, 1);
    const headers = captured[0].init?.headers as Record<string, string>;
    assert.equal(headers["Content-Type"], "application/json");
    assert.equal("X-Access-Token" in headers, false);
  } finally {
    globalThis.fetch = originalFetch;
    delete process.env.NEXT_PUBLIC_QIYAN_ACCESS_TOKEN;
  }
});
