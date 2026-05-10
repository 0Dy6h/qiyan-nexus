import assert from "node:assert/strict";
import { test } from "node:test";

import { buildLiteratureSearchUrl, getLiteratureSourceLabel } from "../lib/api/literature.mjs";

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

test("buildLiteratureSearchUrl appends non-default search contract params", () => {
  const url = buildLiteratureSearchUrl("AD", "pubmed", 2, 5, "year_asc");

  assert.equal(
    url,
    "http://127.0.0.1:8000/api/literature/search?q=AD&source=pubmed&page=2&page_size=5&sort=year_asc",
  );
});

test("getLiteratureSourceLabel returns display text", () => {
  assert.equal(getLiteratureSourceLabel("all"), "全部");
  assert.equal(getLiteratureSourceLabel("cn_literature"), "中文文献");
  assert.equal(getLiteratureSourceLabel("pubmed"), "PubMed");
});
