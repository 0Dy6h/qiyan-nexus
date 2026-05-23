import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const testFilePath = fileURLToPath(import.meta.url);

function getSource(relativePath: string) {
  return readFileSync(resolve(testFilePath, "..", "..", relativePath), "utf8");
}

test("network analysis client reads focus param from URL via useSearchParams", () => {
  const clientSource = getSource("components/NetworkAnalysisClient.tsx");

  assert.match(clientSource, /import \{ useSearchParams \} from "next\/navigation"/);
  assert.match(clientSource, /const searchParams = useSearchParams\(\)/);
  assert.match(clientSource, /searchParams\.get\("focus"\)/);
});

test("network analysis client prefills query and analysis type from focus entity then auto-runs analysis", () => {
  const clientSource = getSource("components/NetworkAnalysisClient.tsx");

  assert.match(clientSource, /fetchNetworkEntities\(\)/);
  // herb entities prefill as herb analysis; everything else falls back to formula
  assert.match(clientSource, /entity\?\.kind === "herb" \? "herb" : "formula"/);
  // one-shot guard: appliedFocusRef prevents re-submit on re-renders
  assert.match(clientSource, /appliedFocusRef\.current === focusEntityId/);
  // runAnalysis is invoked with the resolved entity values, not the stale state
  assert.match(clientSource, /void runAnalysis\(nextQuery, nextType\)/);
});

test("network page wraps the client in Suspense so useSearchParams can prerender", () => {
  const pageSource = getSource("app/network/page.tsx");

  assert.match(pageSource, /import \{ Suspense \} from "react"/);
  assert.match(pageSource, /<Suspense[\s\S]*<NetworkAnalysisClient \/>/);
});
