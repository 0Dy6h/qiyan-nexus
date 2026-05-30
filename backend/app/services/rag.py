from datetime import UTC, datetime

from app.repositories.chunk import InMemoryChunkRepository
from app.repositories.literature import InMemoryLiteratureRepository
from app.repositories.runtime_storage import (
    resolve_chunk_storage_path,
    resolve_literature_storage_path,
)
from app.schemas.literature import LiteratureSource
from app.schemas.rag import CitationCard, RagAnswerResponse, RetrievalMetadata
from app.services.grounding import evaluate_answer_grounding
from app.services.literature import detect_query_language
from app.services.llm.provider import DeterministicProvider, select_provider
from app.services.retrieval.provider import (
    CONFIDENCE_BY_SOURCE_TYPE,
    ScoredCandidate,
    select_retrieval_provider,
    tokenize_query,
)

DISCLAIMER = "非诊断结论、需结合临床。"
_REPOSITORY = InMemoryLiteratureRepository(resolve_literature_storage_path())
_CHUNK_REPOSITORY = InMemoryChunkRepository(resolve_chunk_storage_path())


def build_answer(citations: list[CitationCard], question: str = "") -> str:
    """Backward-compatible thin wrapper over ``DeterministicProvider``.

    Existing tests and callers reference ``build_answer(citations)``; this
    delegates to the deterministic provider so behaviour is byte-identical.
    """

    return DeterministicProvider().generate_answer(question, citations).text


def answer_question(
    question: str,
    source: LiteratureSource = "all",
    top_k: int = 2,
    *,
    llm_provider_name: str | None = None,
    retrieval_provider_name: str | None = None,
) -> RagAnswerResponse:
    normalized_question = question.strip()
    preferred_source_type = (
        "cn_literature" if detect_query_language(normalized_question) == "zh" else "pubmed"
    )

    items = _REPOSITORY.list_items()
    if source != "all":
        items = [item for item in items if item.source_type == source]

    chunks_by_item = {
        item.id: _CHUNK_REPOSITORY.list_chunks_by_literature_id(item.id) for item in items
    }

    retrieval_provider = select_retrieval_provider(retrieval_provider_name)
    ranked: list[ScoredCandidate] = retrieval_provider.rank(
        normalized_question, items, chunks_by_item, preferred_source_type
    )

    if source == "all" and "network" in tokenize_query(normalized_question):
        ranked = sorted(
            ranked,
            key=lambda c: (
                "network_pharmacology" in c.item.evidence_tags,
                "targeted_therapy" in c.item.evidence_tags,
                c.language_bonus,
                c.score,
                c.item.year,
            ),
            reverse=True,
        )

    available_citation_count = sum(1 for c in ranked if c.score > 0)
    if available_citation_count == 0:
        available_citation_count = len(ranked)

    selected = [c for c in ranked if c.score > 0][:top_k]
    if not selected:
        selected = ranked[:top_k]

    if (
        top_k >= 3
        and source == "all"
        and len(selected) == top_k
        and all(c.language_bonus == 1 for c in selected)
    ):
        cross_chunk = next(
            (
                c
                for c in ranked
                if c.score > 0
                and c.language_bonus == 0
                and c.chunk is not None
                and c not in selected
            ),
            None,
        )
        if cross_chunk is not None:
            selected = selected[:-1] + [cross_chunk]

    citations: list[CitationCard] = []
    for candidate in selected:
        item = candidate.item
        chunk = candidate.chunk
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
                confidence=CONFIDENCE_BY_SOURCE_TYPE[item.source_type],
                source_type=chunk.source_type if chunk else None,
                pdf_upload_id=chunk.pdf_upload_id if chunk else None,
                related_entity_ids=list(item.related_entity_ids),
            )
        )

    provider = select_provider(llm_provider_name)
    draft = provider.generate_answer(normalized_question, citations)
    grounded_answer, grounding = evaluate_answer_grounding(
        draft.provider_name,
        draft.text,
        citations,
        structured_claims=draft.structured_claims,
        policy=draft.grounding_policy,
        provider_native_grounding=draft.provider_native_grounding,
        tool_name=draft.tool_name,
        tool_call_count=draft.tool_call_count,
        blocked_reason=draft.grounding_blocked_reason,
    )
    return RagAnswerResponse(
        question=normalized_question,
        answer=grounded_answer,
        disclaimer=DISCLAIMER,
        retrieval=RetrievalMetadata(
            applied_source=source,
            applied_top_k=top_k,
            available_citation_count=available_citation_count,
            strategy=retrieval_provider.name,
        ),
        citations=citations,
        answered_at=datetime.now(UTC).isoformat(),
        provider_name=draft.provider_name,
        grounding=grounding,
        input_tokens=draft.input_tokens,
        output_tokens=draft.output_tokens,
    )
