import assert from "node:assert/strict";
import { test } from "node:test";

import { readFileSync } from "node:fs";

const detailPageSource = readFileSync(new URL("../app/literature/[id]/page.tsx", import.meta.url), "utf8");
const uploadClientSource = readFileSync(new URL("../components/LiteraturePdfUploadClient.tsx", import.meta.url), "utf8");

test("literature detail metadata line stays concise and labeled", () => {
  assert.match(detailPageSource, /语言 \$\{item\.language === "zh" \? "中文" : "英文"\}/);
  assert.match(detailPageSource, /来源 \$\{getLiteratureSourceLabel\(item\.source_type\)\}/);
  assert.match(detailPageSource, /文献 ID \$\{item\.id\}/);
});

test("pdf upload panel uses unified review-first labels for file identity and parse process metadata", () => {
  assert.match(uploadClientSource, /当前文件 \$\{currentFileName\}/);
  assert.doesNotMatch(uploadClientSource, /结果文件 \$\{currentParseResult\.file_name\}/);
  assert.match(uploadClientSource, /解析方式 \$\{getParseMethodLabel\(currentParseResult\.extraction_method\)\}/);
  assert.match(uploadClientSource, /预览说明 \$\{currentParseResult\.preview_text\}/);
  assert.match(uploadClientSource, /当前仅展示文件级信息与预览提示，正文抽取与 OCR 能力将在后续接入/);
});
