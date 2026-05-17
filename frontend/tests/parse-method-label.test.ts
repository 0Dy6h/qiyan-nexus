import assert from "node:assert/strict";
import { test } from "node:test";

import { getParseMethodLabel } from "../lib/literature/parseMethodLabel";

test("getParseMethodLabel translates pypdf-text-preview to Chinese label", () => {
  assert.strictEqual(getParseMethodLabel("pypdf-text-preview"), "pypdf 文本预览");
});

test("getParseMethodLabel translates file-metadata-placeholder to Chinese label", () => {
  assert.strictEqual(getParseMethodLabel("file-metadata-placeholder"), "文件级占位");
});

test("getParseMethodLabel returns unknown method as-is for future enums", () => {
  assert.strictEqual(getParseMethodLabel("some-future-method"), "some-future-method");
});
