import { expect, test } from "@playwright/test";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

function createMinimalPdf() {
  const dir = mkdtempSync(join(tmpdir(), "qiyan-e2e-pdf-"));
  const path = join(dir, "internal-preview.pdf");
  writeFileSync(
    path,
    [
      "%PDF-1.4",
      "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
      "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj",
      "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] >> endobj",
      "xref",
      "0 4",
      "0000000000 65535 f ",
      "0000000009 00000 n ",
      "0000000058 00000 n ",
      "0000000115 00000 n ",
      "trailer << /Size 4 /Root 1 0 R >>",
      "startxref",
      "190",
      "%%EOF",
      "",
    ].join("\n"),
  );
  return path;
}

test("internal preview: pdf upload, rag eval, and network mock paths", async ({ page }) => {
  await page.goto("/literature/cn-ad-gbs-001");
  await page.waitForLoadState("networkidle");
  await expect(page.getByRole("heading", { name: "文献详情" })).toBeVisible();

  const pdfPath = createMinimalPdf();
  await page.getByLabel("上传 PDF").setInputFiles(pdfPath);
  const uploadResponse = page.waitForResponse(
    (response) => response.url().includes("/api/uploads/pdf") && response.status() === 201,
  );
  await page.getByText("上传 PDF", { exact: true }).click();
  await uploadResponse;
  await expect(page.getByText("Mock parser completed successfully")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText(/解析方式/)).toBeVisible();
  await expect(page.getByRole("link", { name: "预览 PDF" })).toBeVisible();

  await page.goto("/evals/rag-ad");
  await page.waitForLoadState("networkidle");
  const evalResponse = page.waitForResponse(
    (response) => response.url().includes("/api/evals/rag-ad/report") && response.status() === 200,
  );
  await page.getByRole("button", { name: /^运行 RAG 评估$|^正在运行评估$/ }).click();
  await evalResponse;
  await expect(page.getByText("通过问题")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("50", { exact: false }).first()).toBeVisible();
  await expect(page.getByText("免责声明覆盖", { exact: true })).toBeVisible();
  await expect(page.getByText("禁用语违规", { exact: true })).toBeVisible();

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
  await expect(page.getByText("链 #1")).toBeVisible();
  await expect(page.getByRole("button", { name: "导出报告为 Markdown" })).toBeVisible();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "导出报告为 Markdown" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(
    /^qiyan-network-report-network-[a-z0-9]+-\d{8}-\d{4}\.md$/,
  );
  await expect(page.getByText("非诊断结论、需结合临床。", { exact: true })).toBeVisible();
});
