import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const testFilePath = fileURLToPath(import.meta.url);

function getSource(relativePath: string) {
  return readFileSync(resolve(testFilePath, "..", "..", relativePath), "utf8");
}

test("LiteratureDataSourceBanner renders view-aware copy and tone roles", () => {
  const bannerSource = getSource("components/LiteratureDataSourceBanner.tsx");

  // accepts a view prop and pulls copy from the lib helper instead of inlining strings
  assert.match(bannerSource, /import \{[\s\S]*getLiteratureDataSourceBanner[\s\S]*\} from "\.\.\/lib\/api\/literature"/);
  assert.match(bannerSource, /view: LiteratureDataSourceView/);
  // aria-label distinguishes it from the generic DemoDataBanner so screen-reader users get the data-source context
  assert.match(bannerSource, /aria-label="数据来源说明"/);
  // tone-keyed visual differentiation so PubMed/CNKI/upload chips look distinct
  assert.match(bannerSource, /banner\.tone/);
});

test("LiteratureSearchClient drives the 4-option data-source view selector", () => {
  const clientSource = getSource("components/LiteratureSearchClient.tsx");

  // form holds a view (not raw source) so the UI and backend filter contract are decoupled
  assert.match(clientSource, /LiteratureDataSourceView/);
  assert.match(clientSource, /<option value="all">全部来源<\/option>/);
  assert.match(clientSource, /<option value="pubmed_live">PubMed 记录<\/option>/);
  assert.match(clientSource, /<option value="cnki_sample">CNKI sample<\/option>/);
  assert.match(clientSource, /<option value="uploaded_pdf">上传 PDF<\/option>/);
  assert.match(clientSource, /记录来源 \$\{getLiteratureRecordOriginLabel\(item\.record_origin\)\}/);

  // legacy 3-option source dropdown values are gone — fail loud if someone re-adds them
  assert.doesNotMatch(clientSource, /<option value="cn_literature">/);
  assert.doesNotMatch(clientSource, /<option value="pubmed">/);

  // submit path translates view -> {source, hasPdfUpload} via the shared lib helper
  assert.match(clientSource, /getLiteratureDataSourceFilter\(/);
  assert.match(clientSource, /searchLiterature\([\s\S]*hasPdfUpload/);

  // banner is mounted inside the search client so its copy switches with the form selection
  assert.match(clientSource, /<LiteratureDataSourceBanner view=\{state\.view\} \/>/);
});

test("literature page keeps DemoDataBanner above the search client (banner stacking contract)", () => {
  const pageSource = getSource("app/literature/page.tsx");

  assert.match(pageSource, /<DemoDataBanner \/>/);
  // DemoDataBanner remains site-level; the new view-aware banner is mounted INSIDE LiteratureSearchClient
  assert.doesNotMatch(pageSource, /<LiteratureDataSourceBanner/);
});
