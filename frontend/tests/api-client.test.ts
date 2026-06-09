import assert from "node:assert/strict";
import { afterEach, test } from "node:test";

const ORIGINAL_TOKEN = process.env.NEXT_PUBLIC_QIYAN_ACCESS_TOKEN;

afterEach(() => {
  if (ORIGINAL_TOKEN === undefined) {
    delete process.env.NEXT_PUBLIC_QIYAN_ACCESS_TOKEN;
  } else {
    process.env.NEXT_PUBLIC_QIYAN_ACCESS_TOKEN = ORIGINAL_TOKEN;
  }
});

async function importClient() {
  return import(`../lib/api/client?ts=${Date.now()}`);
}

test("getAccessToken trims NEXT_PUBLIC_QIYAN_ACCESS_TOKEN and treats blank as open mode", async () => {
  const { getAccessToken } = await importClient();

  delete process.env.NEXT_PUBLIC_QIYAN_ACCESS_TOKEN;
  assert.equal(getAccessToken(), "");

  process.env.NEXT_PUBLIC_QIYAN_ACCESS_TOKEN = "   ";
  assert.equal(getAccessToken(), "");

  process.env.NEXT_PUBLIC_QIYAN_ACCESS_TOKEN = "  dev-token  ";
  assert.equal(getAccessToken(), "dev-token");
});

test("buildApiHeaders preserves caller headers and appends X-Access-Token when configured", async () => {
  process.env.NEXT_PUBLIC_QIYAN_ACCESS_TOKEN = "dev-token";
  const { buildApiHeaders } = await importClient();

  const headers = buildApiHeaders({
    "Content-Type": "application/json",
    Accept: "text/markdown",
  });

  assert.equal(headers["Content-Type"], "application/json");
  assert.equal(headers.Accept, "text/markdown");
  assert.equal(headers["X-Access-Token"], "dev-token");
});

test("buildApiHeaders accepts Headers input and omits token in open mode", async () => {
  delete process.env.NEXT_PUBLIC_QIYAN_ACCESS_TOKEN;
  const { buildApiHeaders } = await importClient();

  const headers = buildApiHeaders(new Headers({ Accept: "application/json" }));

  assert.equal(headers.Accept, "application/json");
  assert.equal("X-Access-Token" in headers, false);
});

test("apiFetch merges token header without changing fetch response semantics", async () => {
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
    assert.equal(headers["X-Access-Token"], "dev-token");
  } finally {
    globalThis.fetch = originalFetch;
  }
});
