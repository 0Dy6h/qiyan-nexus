import assert from "node:assert/strict";
import { test } from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import DemoDataBanner from "../components/DemoDataBanner";

test("DemoDataBanner renders without error (default)", () => {
  const html = renderToStaticMarkup(createElement(DemoDataBanner));
  assert.ok(html.includes("演示数据"));
  assert.ok(html.includes("数据边界提示"));
  // 三类来源分开说清楚，不得再声称「未对接 PubMed 真实库」——pubmed_live 同步已存在
  assert.ok(html.includes("NCBI E-utilities 实时同步"));
  assert.ok(html.includes("未对接知网/万方"));
  assert.doesNotMatch(html, /未对接知网\/PubMed/);
});

test("DemoDataBanner renders without error (compact)", () => {
  const html = renderToStaticMarkup(createElement(DemoDataBanner, { compact: true }));
  assert.ok(html.includes("演示数据"));
  assert.ok(html.includes("数据边界提示"));
});
