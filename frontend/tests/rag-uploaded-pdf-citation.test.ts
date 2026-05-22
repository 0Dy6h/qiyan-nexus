import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import type { CitationCard } from "../lib/api/rag";

const testFilePath = fileURLToPath(import.meta.url);

function getSource(relativePath: string) {
  return readFileSync(resolve(testFilePath, "..", "..", relativePath), "utf8");
}

test("CitationCard exposes optional uploaded_pdf provenance fields", () => {
  // Compile-time check: assigning a citation that carries uploaded_pdf
  // provenance fields must be accepted by the CitationCard type. Build
  // the object via the type to fail tsc --noEmit if the fields go missing.
  const citation: CitationCard = {
    literature_id: "cn-ad-gbs-001",
    title: "肠-脑-皮肤轴与特应性皮炎中医证候研究",
    source: "CNKI curated AD sample",
    snippet: "围绕特应性皮炎、肠-脑-皮肤轴与中医证候关联进行综述。",
    confidence: 0.86,
    source_type: "uploaded_pdf",
    pdf_upload_id: "pdf-cn-ad-gbs-001-ad-evidence-pdf",
    chunk_id: "chunk-pdf-cn-ad-gbs-001-ad-evidence-pdf-uploaded",
  };

  assert.equal(citation.source_type, "uploaded_pdf");
  assert.equal(citation.pdf_upload_id, "pdf-cn-ad-gbs-001-ad-evidence-pdf");
});

test("RagAnswerClient flags uploaded_pdf citations with provenance badge and preview link", () => {
  const source = getSource("components/RagAnswerClient.tsx");

  // Must branch on the new source_type discriminator coming from the
  // backend, not on a hardcoded string somewhere else.
  assert.match(source, /citation\.source_type === "uploaded_pdf"/);

  // Visible provenance label so reviewers can tell at a glance the
  // citation came from an uploaded PDF, not a curated sample chunk.
  assert.match(source, /来自上传 PDF/);

  // When pdf_upload_id is present, the card must offer a preview link
  // built via buildPdfDownloadUrl so reviewers can jump back to the file.
  assert.match(source, /buildPdfDownloadUrl\(citation\.pdf_upload_id\)/);
  assert.match(source, /预览原文 PDF/);
});
