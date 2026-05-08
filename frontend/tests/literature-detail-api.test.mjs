import assert from "node:assert/strict";
import { test } from "node:test";

import { buildLiteratureDetailUrl } from "../lib/api/literature.mjs";

test("buildLiteratureDetailUrl encodes item id with default backend base URL", () => {
  assert.equal(
    buildLiteratureDetailUrl("cn-ad-gbs-001"),
    "http://127.0.0.1:8000/api/literature/cn-ad-gbs-001",
  );
});

test("buildLiteratureDetailUrl encodes reserved characters", () => {
  assert.equal(
    buildLiteratureDetailUrl("pubmed/test id"),
    "http://127.0.0.1:8000/api/literature/pubmed%2Ftest%20id",
  );
});
