import assert from "node:assert/strict";
import { test } from "node:test";

import { formatLocalDateTimeMinutes, toLocalDateInputValue } from "../lib/format-date";

function pad2(value: number) {
  return String(value).padStart(2, "0");
}

test("toLocalDateInputValue returns the local calendar date rather than the UTC date", () => {
  // 2026-09-03T23:30Z is 2026-09-04 in UTC+8 but still 2026-09-03 in UTC; the
  // expectation is derived with local getters so the assertion holds in every TZ.
  const instant = new Date("2026-09-03T23:30:00+00:00");
  const expected = `${instant.getFullYear()}-${pad2(instant.getMonth() + 1)}-${pad2(instant.getDate())}`;
  assert.equal(toLocalDateInputValue(instant), expected);
});

test("toLocalDateInputValue keeps the zero-padded YYYY-MM-DD input format", () => {
  const instant = new Date(2026, 8, 4, 7, 34);
  assert.equal(toLocalDateInputValue(instant), "2026-09-04");
});

test("formatLocalDateTimeMinutes renders local wall clock to minutes", () => {
  const instant = new Date(2026, 8, 4, 7, 34, 52);
  assert.equal(formatLocalDateTimeMinutes(instant), "2026-09-04 07:34");
});
