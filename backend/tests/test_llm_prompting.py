from app.schemas.rag import CitationCard
from app.services.llm.prompting import build_citation_text


def test_build_citation_text_includes_chunk_quote_when_present():
    citation = CitationCard(
        literature_id="uploaded-ad-pdf-001",
        chunk_id="chunk-uploaded-ad-pdf-001-page-2",
        title="上传 PDF 解析片段",
        source="local reviewer PDF",
        snippet="文件级摘要只说明这是一段 AD 相关证据。",
        quote="PDF 第 2 页原文指出皮肤屏障受损与瘙痒反复发作相关。",
        reason="uploaded_pdf, pdf_parse",
        confidence=0.86,
    )

    citation_text = build_citation_text([citation])

    assert "证据ID：chunk-uploaded-ad-pdf-001-page-2" in citation_text
    assert "片段：文件级摘要只说明这是一段 AD 相关证据。" in citation_text
    assert "证据原文：PDF 第 2 页原文指出皮肤屏障受损与瘙痒反复发作相关。" in citation_text
    assert "[1]" not in citation_text
