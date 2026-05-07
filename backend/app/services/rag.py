from pathlib import Path

from app.repositories.literature import InMemoryLiteratureRepository
from app.schemas.rag import CitationCard, RagAnswerResponse
from app.services.literature import detect_query_language

DISCLAIMER = "非诊断结论、需结合临床。"
MOCK_ANSWER = "基于当前样本文献，特应性皮炎（AD）可从肠-脑-皮肤轴、皮肤屏障功能和免疫通路三个角度组织证据。此接口目前只返回 mock RAG 结果，用于验证引用卡片与合规文案。"
_SAMPLE_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "literature" / "sample_ad_literature.json"
_REPOSITORY = InMemoryLiteratureRepository(_SAMPLE_DATA_PATH)
_CONFIDENCE_BY_SOURCE_TYPE = {
    "cn_literature": 0.86,
    "pubmed": 0.74,
}


def answer_question(question: str) -> RagAnswerResponse:
    normalized_question = question.strip()
    preferred_source_type = "cn_literature" if detect_query_language(normalized_question) == "zh" else "pubmed"
    items = sorted(
        _REPOSITORY.list_items(),
        key=lambda item: item.source_type != preferred_source_type,
    )
    citations = [
        CitationCard(
            literature_id=item.id,
            title=item.title,
            source=item.source,
            snippet=item.snippet,
            confidence=_CONFIDENCE_BY_SOURCE_TYPE[item.source_type],
        )
        for item in items
    ]
    return RagAnswerResponse(
        question=normalized_question,
        answer=MOCK_ANSWER,
        disclaimer=DISCLAIMER,
        citations=citations,
    )
