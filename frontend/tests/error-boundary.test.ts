import { test } from "node:test";
import assert from "node:assert/strict";
import { ErrorBoundary } from "../components/ErrorBoundary";

test("ErrorBoundary component is exported and constructable", () => {
  assert.ok(ErrorBoundary);
  assert.equal(typeof ErrorBoundary, "function");
  assert.ok(ErrorBoundary.prototype.render);
});

test("ErrorBoundary has required lifecycle methods", () => {
  assert.ok(ErrorBoundary.getDerivedStateFromError);
  assert.ok(ErrorBoundary.prototype.componentDidCatch);
  assert.equal(typeof ErrorBoundary.getDerivedStateFromError, "function");
  assert.equal(typeof ErrorBoundary.prototype.componentDidCatch, "function");
});

test("ErrorBoundary.getDerivedStateFromError returns error state", () => {
  const testError = new Error("Test error");
  const state = ErrorBoundary.getDerivedStateFromError(testError);
  assert.ok(state.hasError);
  assert.equal(state.error, testError);
});
