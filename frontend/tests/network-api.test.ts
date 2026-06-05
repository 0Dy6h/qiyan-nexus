import assert from "node:assert/strict";
import { test } from "node:test";

import {
  buildNetworkAnalyzeUrl,
  buildNetworkReportUrl,
  buildNetworkResultUrl,
  getNetworkAnalysisTypeLabel,
} from "../lib/api/network";

test("buildNetworkAnalyzeUrl returns the analyze endpoint", () => {
  assert.equal(buildNetworkAnalyzeUrl(), "http://127.0.0.1:8000/api/network/analyze");
});

test("buildNetworkResultUrl encodes task id and points at result endpoint", () => {
  assert.equal(
    buildNetworkResultUrl("network-abc123"),
    "http://127.0.0.1:8000/api/network/result/network-abc123",
  );
});

test("getNetworkAnalysisTypeLabel maps formula and herb to display labels", () => {
  assert.equal(getNetworkAnalysisTypeLabel("formula"), "复方");
  assert.equal(getNetworkAnalysisTypeLabel("herb"), "单味中药");
});

test("submitNetworkAnalysis posts trimmed query and analysis_type, returns task id", async () => {
  process.env.NEXT_PUBLIC_QIYAN_ACCESS_TOKEN = "dev-token";
  const originalFetch = globalThis.fetch;
  const captured: { url: URL | RequestInfo; init?: RequestInit }[] = [];
  globalThis.fetch = (async (url: URL | RequestInfo, init?: RequestInit) => {
    captured.push({ url, init });
    return {
      ok: true,
      async json() {
        return { task_id: "network-abc123", status: "queued", progress: 0 };
      },
    } as Response;
  }) as typeof globalThis.fetch;

  try {
    const { submitNetworkAnalysis } = await import(`../lib/api/network?ts=${Date.now()}`);
    const accepted = await submitNetworkAnalysis("  消风散  ", "formula");

    assert.equal(captured.length, 1);
    assert.equal(captured[0].url, "http://127.0.0.1:8000/api/network/analyze");
    assert.equal(captured[0].init?.method, "POST");
    const headers = captured[0].init?.headers as Record<string, string>;
    assert.equal(headers["Content-Type"], "application/json");
    assert.equal(headers["X-Access-Token"], "dev-token");
    assert.deepEqual(JSON.parse(String(captured[0].init?.body ?? "{}")), {
      query: "消风散",
      analysis_type: "formula",
    });
    assert.equal(accepted.task_id, "network-abc123");
    assert.equal(accepted.status, "queued");
  } finally {
    globalThis.fetch = originalFetch;
    delete process.env.NEXT_PUBLIC_QIYAN_ACCESS_TOKEN;
  }
});

test("fetchNetworkResult returns the polled response shape", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = (async () => {
    return {
      ok: true,
      async json() {
        return {
          task_id: "network-abc123",
          status: "completed",
          progress: 100,
          result: {
            task_id: "network-abc123",
            query: "消风散",
            analysis_type: "formula",
            chains: [
              {
                herb: "消风散",
                compound: "槲皮素",
                target: "IL6",
                pathway: "PI3K-Akt signaling pathway",
                disease: "Atopic dermatitis",
                score: 0.87,
                related_entity_ids: [
                  "herb-jingjie",
                  "compound-quercetin",
                  "target-il6",
                  "pathway-pi3k-akt",
                ],
              },
            ],
            disclaimer: "非诊断结论、需结合临床。",
          },
        };
      },
    } as Response;
  }) as typeof globalThis.fetch;

  try {
    const { fetchNetworkResult } = await import(`../lib/api/network?ts=${Date.now()}`);
    const polled = await fetchNetworkResult("network-abc123");

    assert.equal(polled.status, "completed");
    assert.equal(polled.result?.chains[0].target, "IL6");
    assert.deepEqual(polled.result?.chains[0].related_entity_ids, [
      "herb-jingjie",
      "compound-quercetin",
      "target-il6",
      "pathway-pi3k-akt",
    ]);
    assert.equal(polled.result?.disclaimer, "非诊断结论、需结合临床。");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("fetchNetworkResult throws when the response is not ok", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = (async () => {
    return {
      ok: false,
      async json() {
        return { detail: "Network analysis task not found" };
      },
    } as Response;
  }) as typeof globalThis.fetch;

  try {
    const { fetchNetworkResult } = await import(`../lib/api/network?ts=${Date.now()}`);
    await assert.rejects(fetchNetworkResult("network-missing-task"), /Network result request failed/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("buildNetworkReportUrl encodes task id and points at report endpoint", () => {
  assert.equal(
    buildNetworkReportUrl("network-abc123"),
    "http://127.0.0.1:8000/api/network/result/network-abc123/report",
  );
});

test("fetchNetworkReportMarkdown returns markdown text on 200", async () => {
  process.env.NEXT_PUBLIC_QIYAN_ACCESS_TOKEN = "dev-token";
  const originalFetch = globalThis.fetch;
  const captured: { url: URL | RequestInfo; init?: RequestInit }[] = [];
  globalThis.fetch = (async (url: URL | RequestInfo, init?: RequestInit) => {
    captured.push({ url, init });
    return {
      ok: true,
      async text() {
        return "# Qiyan Nexus 网络药理学报告导出\n\n- task_id：network-abc123\n";
      },
    } as Response;
  }) as typeof globalThis.fetch;

  try {
    const { fetchNetworkReportMarkdown } = await import(`../lib/api/network?ts=${Date.now()}`);
    const markdown = await fetchNetworkReportMarkdown("network-abc123");

    assert.equal(captured.length, 1);
    assert.equal(captured[0].url, "http://127.0.0.1:8000/api/network/result/network-abc123/report");
    const headers = captured[0].init?.headers as Record<string, string>;
    assert.equal(headers["X-Access-Token"], "dev-token");
    assert.ok(markdown.startsWith("# Qiyan Nexus"));
  } finally {
    globalThis.fetch = originalFetch;
    delete process.env.NEXT_PUBLIC_QIYAN_ACCESS_TOKEN;
  }
});

test("fetchNetworkReportMarkdown throws when the response is not ok", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = (async () => {
    return {
      ok: false,
      async json() {
        return { detail: "Network analysis task not found" };
      },
    } as Response;
  }) as typeof globalThis.fetch;

  try {
    const { fetchNetworkReportMarkdown } = await import(`../lib/api/network?ts=${Date.now()}`);
    await assert.rejects(
      fetchNetworkReportMarkdown("network-missing-task"),
      /Network report request failed/,
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});
