from pathlib import Path
import re

from app.repositories.chunk import InMemoryChunkRepository
from app.repositories.literature import InMemoryLiteratureRepository
from app.schemas.rag import CitationCard, RagAnswerResponse, RetrievalMetadata
from app.services.literature import detect_query_language

DISCLAIMER = "非诊断结论、需结合临床。"
_SAMPLE_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "literature" / "sample_ad_literature.json"
_CHUNK_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "literature" / "sample_ad_chunks.json"
_REPOSITORY = InMemoryLiteratureRepository(_SAMPLE_DATA_PATH)
_CHUNK_REPOSITORY = InMemoryChunkRepository(_CHUNK_DATA_PATH)
_CONFIDENCE_BY_SOURCE_TYPE = {
    "cn_literature": 0.86,
    "pubmed": 0.74,
}

_KEYWORD_ALIASES = {
    "gut": ["肠", "肠道", "gut", "microbiome", "菌群"],
    "skin_barrier": ["屏障", "barrier", "filaggrin"],
    "immune": ["免疫", "inflammation", "immune", "th2", "jak", "cytokine"],
    "pruritus": ["瘙痒", "itch", "il-31"],
    "formula": ["复方", "方剂", "formula", "herbal"],
    "network": ["网络药理学", "network pharmacology", "靶点", "通路", "target", "pathway"],
    "pediatric": ["儿童", "pediatric"],
}


def tokenize_query(question: str) -> list[str]:
    normalized = question.lower().strip()
    tokens = set(re.findall(r"[a-z0-9\-]+", normalized))
    for alias, keywords in _KEYWORD_ALIASES.items():
        if any(keyword in normalized for keyword in keywords):
            tokens.add(alias)
    for char in normalized:
        if "\u4e00" <= char <= "\u9fff":
            tokens.add(char)
    return sorted(tokens)


def score_item(item, chunk, query_tokens: list[str]) -> int:
    haystacks = [
        item.title.lower(),
        item.snippet.lower(),
        (item.abstract or "").lower(),
        " ".join(item.keywords).lower(),
        " ".join(item.evidence_tags).lower(),
        chunk.text.lower() if chunk else "",
        " ".join(chunk.evidence_tags).lower() if chunk else "",
    ]
    score = 0
    for token in query_tokens:
        if any(token in haystack for haystack in haystacks if haystack):
            score += 1
    return score


def build_answer(citations: list[CitationCard]) -> str:
    if not citations:
        return "当前样本文献中没有检索到足够匹配的证据片段。请调整问题关键词或切换来源后重试。"

    top_reasons = [citation.reason for citation in citations if citation.reason]
    top_reasons_text = "；".join(top_reasons[:2]) if top_reasons else "当前命中的证据片段"
    titles = "；".join(citation.title for citation in citations[:2])
    return (
        f"基于当前检索到的证据片段，已优先返回与问题最相关的文献。"
        f"主要证据线索包括：{top_reasons_text}。"
        f"代表性文献：{titles}。"
        f"此回答仍是基于样本文献的 deterministic retrieval 结果，用于验证引用卡片、证据片段与合规文案。"
    )


def answer_question(question: str, source: str = "all", top_k: int = 2) -> RagAnswerResponse:
    normalized_question = question.strip()
    preferred_source_type = "cn_literature" if detect_query_language(normalized_question) == "zh" else "pubmed"
    query_tokens = tokenize_query(normalized_question)

    items = _REPOSITORY.list_items()
    if source != "all":
        items = [item for item in items if item.source_type == source]

    ranked_items: list[tuple[int, int, object, object]] = []
    for item in items:
        chunk = next(iter(_CHUNK_REPOSITORY.list_chunks_by_literature_id(item.id)), None)
        score = score_item(item, chunk, query_tokens)
        language_bonus = 1 if item.source_type == preferred_source_type else 0
        ranked_items.append((score, language_bonus, item, chunk))

    ranked_items.sort(key=lambda row: (row[0], row[1], row[2].year), reverse=True)
    available_citation_count = sum(1 for score, _, _, _ in ranked_items if score > 0)
    if available_citation_count == 0:
        available_citation_count = len(ranked_items)

    selected = [row for row in ranked_items if row[0] > 0][:top_k]
    if not selected:
        selected = ranked_items[:top_k]

    citations = []
    for _, _, item, chunk in selected:
        citations.append(
            CitationCard(
                literature_id=item.id,
                chunk_id=chunk.chunk_id if chunk else None,
                title=item.title,
                source=item.source,
                snippet=item.snippet,
                quote=chunk.source_quote if chunk else None,
                reason=(", ".join(chunk.evidence_tags[:2]) if chunk and chunk.evidence_tags else None),
                confidence=_CONFIDENCE_BY_SOURCE_TYPE[item.source_type],
            )
        )

    return RagAnswerResponse(
        question=normalized_question,
        answer=build_answer(citations),
        disclaimer=DISCLAIMER,
        retrieval=RetrievalMetadata(
            applied_source=source,
            applied_top_k=top_k,
            available_citation_count=available_citation_count,
        ),
        citations=citations,
    )
