import assert from "node:assert/strict";
import { test } from "node:test";

import { buildLiteratureSearchUrl } from "../lib/api/literature.mjs";

test("buildLiteratureSearchUrl encodes query with default backend base URL", () => {
  const url = buildLiteratureSearchUrl("特应性皮炎");

  assert.equal(
    url,
    "http://127.0.0.1:8000/api/literature/search?q=%E7%89%B9%E5%BA%94%E6%80%A7%E7%9A%AE%E7%82%8E",
  );
});

test("buildLiteratureSearchUrl trims query", () => {
  const url = buildLiteratureSearchUrl("  AD  ");

  assert.equal(url, "http://127.0.0.1:8000/api/literature/search?q=AD");
});

test("buildLiteratureSearchUrl appends source when provided", () => {
  const url = buildLiteratureSearchUrl("AD", "pubmed");

  assert.equal(url, "http://127.0.0.1:8000/api/literature/search?q=AD&source=pubmed");
});
