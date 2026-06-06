import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const testFilePath = fileURLToPath(import.meta.url);

function getSource(relativePath: string) {
  return readFileSync(resolve(testFilePath, "..", "..", relativePath), "utf8");
}

test("ErrorBoundary component is a class component with error state", () => {
  const source = getSource("components/ErrorBoundary.tsx");

  assert.match(source, /class ErrorBoundary extends Component/);
  assert.match(source, /getDerivedStateFromError/);
  assert.match(source, /componentDidCatch/);
  assert.match(source, /hasError: boolean/);
});

test("ErrorBoundary supports custom fallback prop", () => {
  const source = getSource("components/ErrorBoundary.tsx");

  assert.match(source, /fallback\?: ReactNode/);
  assert.match(source, /this\.props\.fallback/);
});

test("ErrorBoundary default fallback uses brand-compliant page padding", () => {
  const source = getSource("components/ErrorBoundary.tsx");

  // Must match the locked page padding token
  assert.match(source, /clamp\(20px, 4vw, 48px\)/);
});

test("ErrorBoundary default fallback offers reload and home navigation", () => {
  const source = getSource("components/ErrorBoundary.tsx");

  assert.match(source, /window\.location\.reload\(\)/);
  assert.match(source, /刷新页面/);
  assert.match(source, /返回首页/);
});

test("ErrorBoundary logs errors via componentDidCatch", () => {
  const source = getSource("components/ErrorBoundary.tsx");

  assert.match(source, /console\.error/);
});

test("app/error.tsx is a client component with reset handler", () => {
  const source = getSource("app/error.tsx");

  assert.match(source, /"use client"/);
  assert.match(source, /reset: \(\) => void/);
  assert.match(source, /onClick=\{reset\}/);
});

test("app/error.tsx surfaces error digest and recovery actions", () => {
  const source = getSource("app/error.tsx");

  assert.match(source, /error\.digest/);
  assert.match(source, /重试/);
  assert.match(source, /返回首页/);
  assert.match(source, /clamp\(20px, 4vw, 48px\)/);
});

test("app/error.tsx logs error in useEffect", () => {
  const source = getSource("app/error.tsx");

  assert.match(source, /useEffect/);
  assert.match(source, /console\.error/);
});

test("app/global-error.tsx renders its own html and body tags", () => {
  const source = getSource("app/global-error.tsx");

  assert.match(source, /"use client"/);
  assert.match(source, /<html lang="zh-CN">/);
  assert.match(source, /<body>/);
});

test("app/global-error.tsx offers reload recovery", () => {
  const source = getSource("app/global-error.tsx");

  assert.match(source, /onClick=\{reset\}/);
  assert.match(source, /重新加载/);
  assert.match(source, /应用加载出错/);
});
