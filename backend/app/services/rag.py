import re
from datetime import UTC, datetime

from app.repositories.chunk import InMemoryChunkRepository
from app.repositories.literature import InMemoryLiteratureRepository
from app.repositories.runtime_storage import (
    resolve_chunk_storage_path,
    resolve_literature_storage_path,
)
from app.schemas.chunk import LiteratureChunk
from app.schemas.literature import LiteratureItem, LiteratureSource
from app.schemas.rag import CitationCard, RagAnswerResponse, RetrievalMetadata
from app.services.literature import detect_query_language
from app.services.llm.provider import DeterministicProvider, select_provider

DISCLAIMER = "非诊断结论、需结合临床。"
_REPOSITORY = InMemoryLiteratureRepository(resolve_literature_storage_path())
_CHUNK_REPOSITORY = InMemoryChunkRepository(resolve_chunk_storage_path())
_CONFIDENCE_BY_SOURCE_TYPE = {
    "cn_literature": 0.86,
    "pubmed": 0.74,
}

_KEYWORD_ALIASES = {
    "gut": ["肠", "肠道", "gut", "microbiome", "菌群"],
    "skin_barrier": ["屏障", "barrier", "filaggrin"],
    "immune": ["免疫", "inflammation", "immune", "th2", "jak", "cytokine"],
    "targeted_therapy": ["后续", "线索", "therapeutic target", "targeted therapy"],
    "pruritus": ["瘙痒", "itch", "il-31"],
    "formula": ["复方", "方剂", "formula", "herbal"],
    "network": [
        "网络药理学",
        "network pharmacology",
        "分子对接",
        "分子模拟",
        "molecular docking",
        "molecular simulation",
        "靶点",
        "通路",
        "target",
        "pathway",
    ],
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


def score_item(item: LiteratureItem, chunk: LiteratureChunk | None, query_tokens: list[str]) -> int:
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


def _alias_tag_bonus(tags: list[str], query_tokens: list[str], weight: int) -> int:
    if not tags:
        return 0
    matched = 0
    for token in query_tokens:
        if token in _KEYWORD_ALIASES and any(token in tag for tag in tags):
            matched += 1
    return matched * weight


def build_answer(citations: list[CitationCard], question: str = "") -> str:
    """Backward-compatible thin wrapper over ``DeterministicProvider``.

    Existing tests and callers reference ``build_answer(citations)``; this
    delegates to the deterministic provider so behaviour is byte-identical.
    """

    return DeterministicProvider().generate_answer(question, citations).text


def answer_question(
    question: str, source: LiteratureSource = "all", top_k: int = 2
) -> RagAnswerResponse:
    normalized_question = question.strip()
    preferred_source_type = (
        "cn_literature" if detect_query_language(normalized_question) == "zh" else "pubmed"
    )
    query_tokens = tokenize_query(normalized_question)

    items = _REPOSITORY.list_items()
    if source != "all":
        items = [item for item in items if item.source_type == source]

    ranked_items: list[tuple[int, int, LiteratureItem, LiteratureChunk | None]] = []
    for item in items:
        chunks: list[LiteratureChunk | None] = list(
            _CHUNK_REPOSITORY.list_chunks_by_literature_id(item.id)
        )
        if not chunks:
            chunks = [None]
        for chunk in chunks:
            score = score_item(item, chunk, query_tokens)
            score += _alias_tag_bonus(item.evidence_tags, query_tokens, 2)
            if chunk:
                score += _alias_tag_bonus(chunk.evidence_tags, query_tokens, 7)
            language_bonus = 1 if item.source_type == preferred_source_type else 0
            ranked_items.append((score, language_bonus, item, chunk))

    ranked_items.sort(key=lambda row: (row[1], row[0], row[2].year), reverse=True)
    if source == "all" and "network" in query_tokens:
        ranked_items.sort(
            key=lambda row: (
                "network_pharmacology" in row[2].evidence_tags,
                "targeted_therapy" in row[2].evidence_tags,
                row[1],
                row[0],
                row[2].year,
            ),
            reverse=True,
        )
    available_citation_count = sum(1 for score, _, _, _ in ranked_items if score > 0)
    if available_citation_count == 0:
        available_citation_count = len(ranked_items)

    selected = [row for row in ranked_items if row[0] > 0][:top_k]
    if not selected:
        selected = ranked_items[:top_k]

    if (
        top_k >= 3
        and source == "all"
        and len(selected) == top_k
        and all(row[1] == 1 for row in selected)
    ):
        cross_chunk = next(
            (
                row
                for row in ranked_items
                if row[0] > 0 and row[1] == 0 and row[3] is not None and row not in selected
            ),
            None,
        )
        if cross_chunk is not None:
            selected = selected[:-1] + [cross_chunk]

    citations = []
    for _, _, item, chunk in selected:
        chunk_tags = chunk.evidence_tags if chunk and chunk.evidence_tags else []
        reason_tags = chunk_tags or item.evidence_tags
        citations.append(
            CitationCard(
                literature_id=item.id,
                chunk_id=chunk.chunk_id if chunk else None,
                title=item.title,
                source=item.source,
                snippet=item.snippet,
                quote=chunk.source_quote if chunk else None,
                reason=(", ".join(reason_tags[:2]) if reason_tags else None),
                confidence=_CONFIDENCE_BY_SOURCE_TYPE[item.source_type],
                source_type=chunk.source_type if chunk else None,
                pdf_upload_id=chunk.pdf_upload_id if chunk else None,
            )
        )

    provider = select_provider()
    draft = provider.generate_answer(normalized_question, citations)
    return RagAnswerResponse(
        question=normalized_question,
        answer=draft.text,
        disclaimer=DISCLAIMER,
        retrieval=RetrievalMetadata(
            applied_source=source,
            applied_top_k=top_k,
            available_citation_count=available_citation_count,
        ),
        citations=citations,
        answered_at=datetime.now(UTC).isoformat(),
    )
