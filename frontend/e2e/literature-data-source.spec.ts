import { expect, test, type Page } from "@playwright/test";

type ExpectedSearchParams = {
  source?: string;
  hasPdfUpload?: string;
};

async function submitSearchForSource(
  page: Page,
  option: string,
  expectedParams: ExpectedSearchParams,
) {
  await page.getByLabel("文献来源").selectOption(option);

  const searchResponse = page.waitForResponse((response) => {
    if (!response.url().includes("/api/literature/search") || response.status() !== 200) {
      return false;
    }

    const params = new URL(response.url()).searchParams;
    const sourceMatches =
      expectedParams.source === undefined
        ? !params.has("source")
        : params.get("source") === expectedParams.source;
    const pdfMatches =
      expectedParams.hasPdfUpload === undefined
        ? !params.has("has_pdf_upload")
        : params.get("has_pdf_upload") === expectedParams.hasPdfUpload;

    return sourceMatches && pdfMatches;
  });

  await page.getByRole("button", { name: /^开始检索$|^检索中$/ }).click();
  await searchResponse;
}

test("literature data-source switcher sends scoped search params and updates compliance banner", async ({
  page,
}) => {
  await page.goto("/literature");
  await page.waitForLoadState("networkidle");

  await expect(page.getByRole("note", { name: "数据来源说明" })).toContainText("全部来源");

  await submitSearchForSource(page, "pubmed_live", { source: "pubmed" });
  await expect(page.getByRole("note", { name: "数据来源说明" })).toContainText("PubMed 记录（含演示 seed）");

  await submitSearchForSource(page, "cnki_sample", { source: "cn_literature" });
  await expect(page.getByRole("note", { name: "数据来源说明" })).toContainText("CNKI sample（演示）");

  await submitSearchForSource(page, "uploaded_pdf", { hasPdfUpload: "true" });
  await expect(page.getByRole("note", { name: "数据来源说明" })).toContainText("上传 PDF（仅本地）");
});
