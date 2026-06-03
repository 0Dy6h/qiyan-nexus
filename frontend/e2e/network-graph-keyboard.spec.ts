import { expect, test } from "@playwright/test";

/**
 * Regression coverage for NetworkGraph keyboard a11y (Slice 10 + 11). Slice 11
 * handoff explicitly called out the missing e2e — this spec closes that loop by
 * driving the real keyboard against a real chromium, instead of grep'ing source
 * strings the way `tests/network-graph-ui.test.ts` does.
 *
 * Backed by the deterministic mock chain seed for default 消风散 (formula) which
 * yields multiple compound + target nodes, so within-layer ArrowDown is safe.
 */
test("network graph keyboard a11y: focus → enter/space toggle → escape clear → arrow nav", async ({ page }) => {
  // Run the default mock analysis to render the NetworkGraph with real nodes.
  await page.goto("/network");
  await page.waitForLoadState("networkidle");
  const analyzeResponse = page.waitForResponse(
    (response) => response.url().includes("/api/network/analyze") && response.status() === 202,
  );
  await page.getByRole("button", { name: /^开始分析$|^提交中\.\.\.$|^运行中\.\.\. \d+%$/ }).click();
  await analyzeResponse;
  await expect(page.getByRole("heading", { name: "「成分-靶点-通路-疾病」链" })).toBeVisible({
    timeout: 20_000,
  });

  // Grab the first herb-layer node (aria-label format: "中药/复方: <name>").
  const herbNode = page.getByRole("button", { name: /^中药\/复方: / }).first();
  await expect(herbNode).toBeVisible();
  await expect(herbNode).toHaveAttribute("aria-pressed", "false");

  // Programmatic focus stands in for Tab arrival; the keyboard handler is what we're verifying.
  await herbNode.focus();
  await expect(herbNode).toBeFocused();

  // Enter toggles focus on → aria-pressed flips + 聚焦：indicator text appears.
  await page.keyboard.press("Enter");
  await expect(herbNode).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByText(/^聚焦：中药\/复方:/)).toBeVisible();

  // Enter again toggles off.
  await page.keyboard.press("Enter");
  await expect(herbNode).toHaveAttribute("aria-pressed", "false");
  await expect(page.getByText(/^聚焦：/)).toHaveCount(0);

  // Space behaves the same as Enter for the toggle.
  await page.keyboard.press("Space");
  await expect(herbNode).toHaveAttribute("aria-pressed", "true");

  // Escape clears focus + indicator regardless of current focus state.
  await page.keyboard.press("Escape");
  await expect(herbNode).toHaveAttribute("aria-pressed", "false");
  await expect(page.getByText(/^聚焦：/)).toHaveCount(0);

  // ArrowRight from herb → compound layer (closest-Y match across layers).
  await page.keyboard.press("ArrowRight");
  const focusedAfterRight = page.locator(":focus");
  await expect(focusedAfterRight).toHaveAttribute("aria-label", /^化合物: /);

  // ArrowDown within compound layer → focus stays in compound but moves to a different node.
  const compoundLabelBefore = await focusedAfterRight.getAttribute("aria-label");
  await page.keyboard.press("ArrowDown");
  const focusedAfterDown = page.locator(":focus");
  await expect(focusedAfterDown).toHaveAttribute("aria-label", /^化合物: /);
  const compoundLabelAfter = await focusedAfterDown.getAttribute("aria-label");
  expect(compoundLabelAfter).not.toBe(compoundLabelBefore);

  // ArrowLeft from compound → herb layer (symmetric to ArrowRight).
  await page.keyboard.press("ArrowLeft");
  await expect(page.locator(":focus")).toHaveAttribute("aria-label", /^中药\/复方: /);
});
