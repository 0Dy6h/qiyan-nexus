from app.schemas.rag import CitationCard
from app.services.llm.prompting import GROUNDING_SYSTEM_PROMPT, build_citation_text


def test_grounding_system_prompt_constrains_claim_scope_to_single_evidence_text():
    assert "每条 claim 只能引用一个证据ID" in GROUNDING_SYSTEM_PROMPT
    assert "只能由该证据ID对应的证据文本直接蕴含" in GROUNDING_SYSTEM_PROMPT
    assert "不要跨引用综合" in GROUNDING_SYSTEM_PROMPT
    assert "不要添加引用片段没有明示的治疗疗效、靶点、生活质量、因果或指南地位" in (
        GROUNDING_SYSTEM_PROMPT
    )


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
    assert "标题（元数据）：上传 PDF 解析片段" in citation_text
    assert "来源（元数据）：local reviewer PDF" in citation_text
    assert "片段摘要（元数据）：文件级摘要只说明这是一段 AD 相关证据。" in citation_text
    assert (
        "证据文本（claim 只能基于此字段）：PDF 第 2 页原文指出皮肤屏障受损与瘙痒反复发作相关。"
        in citation_text
    )
    assert "匹配依据（元数据）：uploaded_pdf, pdf_parse" in citation_text
    assert "[1]" not in citation_text


def test_build_citation_text_uses_snippet_as_supporting_text_when_quote_is_missing():
    citation = CitationCard(
        literature_id="pmid-40100001",
        chunk_id=None,
        title="PubMed sample",
        source="PubMed",
        snippet="Atopic dermatitis studies describe barrier dysfunction and type 2 inflammation.",
        reason="skin_barrier, immune_pathway",
        confidence=0.82,
    )

    citation_text = build_citation_text([citation])

    assert "证据ID：pmid-40100001" in citation_text
    assert (
        "证据文本（claim 只能基于此字段）：Atopic dermatitis studies describe barrier dysfunction and type 2 inflammation."
        in citation_text
    )
    assert "片段摘要（元数据）" not in citation_text
