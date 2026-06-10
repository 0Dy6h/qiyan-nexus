import { expect, test } from "@playwright/test";

/**
 * RAG regression suite: covers key regression scenarios beyond the main path.
 */

test("RAG citation cards link to literature detail", async ({ page }) => {
  await page.goto("/rag");
  await page.waitForLoadState("networkidle");

  await page.getByRole("textbox", { name: "RAG 问题" }).fill("特应性皮炎");
  await page.getByRole("button", { name: /生成回答|生成中/ }).click();

  await expect(page.getByRole("heading", { name: "引用卡片" })).toBeVisible({ timeout: 15_000 });

  // Click first citation detail link
  const firstCitationLink = page.getByRole("link", { name: /查看文献详情/ }).first();
  await expect(firstCitationLink).toBeVisible();
  await firstCitationLink.click();

  // Should navigate to literature detail page
  await expect(page).toHaveURL(/\/literature\/.+/);
  await expect(page.getByRole("navigation", { name: "工作台导航" })).toBeVisible();
});

test("RAG export markdown button is present after answer", async ({ page }) => {
  await page.goto("/rag");
  await page.waitForLoadState("networkidle");

  await page.getByRole("textbox", { name: "RAG 问题" }).fill("特应性皮炎");
  await page.getByRole("button", { name: /生成回答|生成中/ }).click();

  await expect(page.getByRole("heading", { name: "回答结果" })).toBeVisible({ timeout: 15_000 });

  // Export button should be visible
  const exportButton = page.getByRole("button", { name: "导出答案为 Markdown" });
  await expect(exportButton).toBeVisible();
});

test("RAG always displays disclaimer", async ({ page }) => {
  await page.goto("/rag");
  await page.waitForLoadState("networkidle");

  await page.getByRole("textbox", { name: "RAG 问题" }).fill("肠皮轴");
  await page.getByRole("button", { name: /生成回答|生成中/ }).click();

  await expect(page.getByRole("heading", { name: "回答结果" })).toBeVisible({ timeout: 15_000 });

  // Byte-identical disclaimer must be present
  await expect(page.getByText("非诊断结论、需结合临床。", { exact: true })).toBeVisible();
});
