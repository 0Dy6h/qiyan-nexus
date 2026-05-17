import assert from "node:assert/strict";
import { test } from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import DemoDataBanner from "../components/DemoDataBanner";

test("DemoDataBanner renders without error (default)", () => {
  const html = renderToStaticMarkup(createElement(DemoDataBanner));
  assert.ok(html.includes("演示数据"));
  assert.ok(html.includes("示例数据集"));
});

test("DemoDataBanner renders without error (compact)", () => {
  const html = renderToStaticMarkup(createElement(DemoDataBanner, { compact: true }));
  assert.ok(html.includes("演示数据"));
  assert.ok(html.includes("示例数据集"));
});
