import { expect, test } from "@playwright/test";

/**
 * A4 baseline E2E: the single "main path" required by the roadmap to gate
 * closed-beta readiness. Touches literature search → detail → rag answer →
 * citation → exported markdown affordance, plus the load-bearing disclaimer.
 *
 * The dev servers are wired up by playwright.config.ts `webServer`. Backend
 * is started with isolated LITERATURE_RUNTIME_STATE_PATH so this test does
 * not pollute developer-local runtime state, and with QIYAN_ACCESS_TOKENS
 * intentionally empty so the middleware is in open mode.
 */
test("main path: literature search → detail → rag answer with citations + disclaimer", async ({ page }) => {
  // 1. /literature loads with default query and renders shell + nav.
  await page.goto("/literature");
  await page.waitForLoadState("networkidle");
  await expect(page.getByRole("navigation", { name: "工作台导航" })).toBeVisible();
  await expect(page.getByRole("textbox", { name: "检索关键词", exact: true })).toHaveValue("特应性皮炎");

  // 2. Trigger the search; deterministic seed always returns the cn-ad-gbs-001 card.
  const literatureSearchResponse = page.waitForResponse(
    (response) => response.url().includes("/api/literature/search") && response.status() === 200,
  );
  await page.getByRole("button", { name: /^开始检索$|^检索中$/ }).click();
  await literatureSearchResponse;
  const firstDetailLink = page.getByRole("link", { name: /查看详情/ }).first();
  await expect(firstDetailLink).toBeVisible({ timeout: 15_000 });

  // 3. Click into the literature detail; URL contains the literature id.
  await firstDetailLink.click();
  await expect(page).toHaveURL(/\/literature\/.+/);
  await expect(page.getByRole("navigation", { name: "工作台导航" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "文献详情" })).toBeVisible();
  await expect(page.getByText("文献 ID cn-ad-gbs-001")).toBeVisible();

  // 4. Navigate to /rag and submit the seed AD question.
  await page.goto("/rag");
  await page.waitForLoadState("networkidle");
  await expect(page.getByRole("textbox", { name: "RAG 问题" })).toBeVisible();
  await page.getByRole("textbox", { name: "RAG 问题" }).fill("特应性皮炎 肠皮轴");
  await page.getByRole("button", { name: /生成回答|生成中/ }).click();

  // 5. Evidence brief renders with disclaimer (byte-identical) and at least one citation card.
  await expect(page.getByRole("heading", { name: "证据简报" })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("非诊断结论、需结合临床。", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "引用卡片" })).toBeVisible();
  await expect(page.getByRole("link", { name: /查看文献详情/ }).first()).toBeVisible();

  // 6. Export and reviewer closeout actions stay visible.
  await expect(page.getByRole("button", { name: "导出答案为 Markdown" })).toBeVisible();
  await expect(page.getByRole("link", { name: "运行 RAG 评估" })).toBeVisible();
  await expect(page.getByRole("link", { name: "核对合规边界" })).toBeVisible();
});
