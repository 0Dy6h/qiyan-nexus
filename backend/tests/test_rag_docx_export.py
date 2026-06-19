import io
import xml.etree.ElementTree as ET
import zipfile

from app.schemas.rag import (
    CitationCard,
    GroundingMetadata,
    ProviderSli,
    RagAnswerResponse,
    RetrievalMetadata,
)
from app.services.rag_docx import build_answer_docx

DISCLAIMER = "非诊断结论、需结合临床。"


def _sample_answer() -> RagAnswerResponse:
    return RagAnswerResponse(
        question="特应性皮炎和肠-脑-皮肤轴有什么关系？",
        answer="在当前样本文献中检索到 1 条相关证据片段：肠道菌群失衡与特应性皮炎存在关联。",
        disclaimer=DISCLAIMER,
        retrieval=RetrievalMetadata(
            applied_source="all",
            applied_top_k=2,
            available_citation_count=1,
            strategy="keyword",
        ),
        citations=[
            CitationCard(
                literature_id="cn-ad-microbiome-003",
                chunk_id="chunk-cn-ad-microbiome-003-abstract",
                title="肠道菌群失衡与特应性皮炎发病关系研究进展",
                source="VIP curated AD sample",
                snippet="聚焦双歧杆菌、乳酸杆菌下降与炎症偏移。",
                quote="讨论菌群干预在免疫稳态恢复中的可能作用。",
                reason="microbiome, gut_skin_axis",
                confidence=0.86,
            )
        ],
        answered_at="2026-06-19T01:00:00+00:00",
        provider_name="deterministic",
        grounding=GroundingMetadata(
            status="skipped", policy="structured_claim_refs_v3", checked=False
        ),
        sli=ProviderSli(provider_latency_ms=0, estimated_cost_usd=None),
    )


def test_build_answer_docx_is_a_valid_openxml_package():
    data = build_answer_docx(_sample_answer())

    assert data[:2] == b"PK"  # ZIP magic
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = set(archive.namelist())
        assert {"[Content_Types].xml", "_rels/.rels", "word/document.xml"} <= names
        document = archive.read("word/document.xml").decode("utf-8")

    # document.xml must be well-formed XML (Word/WPS reject malformed parts).
    ET.fromstring(document)


def test_build_answer_docx_embeds_question_answer_and_disclaimer():
    answer = _sample_answer()
    data = build_answer_docx(answer)

    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        document = archive.read("word/document.xml").decode("utf-8")

    assert answer.question in document
    assert "肠道菌群失衡与特应性皮炎存在关联" in document
    assert DISCLAIMER in document
    assert "肠道菌群失衡与特应性皮炎发病关系研究进展" in document  # citation title
    assert "讨论菌群干预在免疫稳态恢复中的可能作用。" in document  # citation quote


def test_build_answer_docx_handles_zero_citations():
    answer = _sample_answer()
    answer = answer.model_copy(update={"citations": []})
    data = build_answer_docx(answer)

    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        document = archive.read("word/document.xml").decode("utf-8")

    assert "（当前回答没有可核对的引用证据。）" in document


def test_build_answer_docx_escapes_xml_special_characters():
    answer = _sample_answer()
    answer = answer.model_copy(update={"question": 'AD & <屏障> 与 "轴" 的关系？'})
    data = build_answer_docx(answer)

    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        document = archive.read("word/document.xml").decode("utf-8")

    # Raw '&' / '<' would corrupt the package; they must be entity-escaped.
    assert "AD &amp; &lt;屏障&gt;" in document
    ET.fromstring(document)


def test_build_answer_docx_preserves_newlines_as_word_breaks():
    answer = _sample_answer()
    answer = answer.model_copy(update={"answer": "第一行证据\n第二行证据\r\n第三行证据"})
    data = build_answer_docx(answer)

    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        document = archive.read("word/document.xml").decode("utf-8")

    assert "第一行证据" in document
    assert "第二行证据" in document
    assert "第三行证据" in document
    assert document.count("<w:br/>") >= 2
    ET.fromstring(document)


def test_build_answer_docx_strips_xml_illegal_control_characters():
    answer = _sample_answer()
    answer = answer.model_copy(
        update={
            "answer": "合法文本\x00混入\x08控制字符",
            "question": "问题\x1f仍可打开",
        }
    )
    data = build_answer_docx(answer)

    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        document = archive.read("word/document.xml").decode("utf-8")

    assert "\x00" not in document
    assert "\x08" not in document
    assert "\x1f" not in document
    assert "合法文本混入控制字符" in document
    ET.fromstring(document)
