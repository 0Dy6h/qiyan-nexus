import logging
import time
from datetime import UTC, datetime

from app.core.config import get_settings
from app.repositories.chunk import InMemoryChunkRepository
from app.repositories.literature import InMemoryLiteratureRepository
from app.repositories.runtime_storage import (
    resolve_chunk_storage_path,
    resolve_literature_storage_path,
)
from app.schemas.literature import LiteratureSource
from app.schemas.rag import (
    CitationCard,
    ProviderSli,
    RagAnswerResponse,
    RetrievalMetadata,
)
from app.services.grounding import evaluate_answer_grounding
from app.services.literature import detect_query_language
from app.services.llm.provider import DeterministicProvider, select_provider
from app.services.nli import select_nli_backend
from app.services.retrieval.embedding import select_embedding_backend
from app.services.retrieval.provider import (
    CONFIDENCE_BY_SOURCE_TYPE,
    ScoredCandidate,
    select_retrieval_provider,
    tokenize_query,
)

DISCLAIMER = "非诊断结论、需结合临床。"
_LOGGER = logging.getLogger(__name__)
_REPOSITORY = InMemoryLiteratureRepository(resolve_literature_storage_path())
_CHUNK_REPOSITORY = InMemoryChunkRepository(resolve_chunk_storage_path())


def _estimate_cost_usd(
    input_tokens: int | None,
    output_tokens: int | None,
    price_input_per_mtok: float,
    price_output_per_mtok: float,
) -> float | None:
    """Estimate USD cost from token usage and per-million-token prices.

    Returns ``None`` when no token usage is available or both prices are unset,
    so a guessed price is never surfaced for deterministic / fallback answers.
    """

    if input_tokens is None and output_tokens is None:
        return None
    if price_input_per_mtok <= 0 and price_output_per_mtok <= 0:
        return None
    cost = (input_tokens or 0) / 1_000_000 * price_input_per_mtok
    cost += (output_tokens or 0) / 1_000_000 * price_output_per_mtok
    return round(cost, 6)


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
    provider_started = time.perf_counter()
    draft = provider.generate_answer(normalized_question, citations)
    provider_latency_ms = int((time.perf_counter() - provider_started) * 1000)
    settings = get_settings()
    configured_threshold = settings.grounding_semantic_threshold
    semantic_threshold = configured_threshold if configured_threshold > 0 else None
    semantic_backend = select_embedding_backend() if semantic_threshold is not None else None
    nli_threshold = settings.nli_threshold if settings.nli_threshold > 0 else None
    nli_backend = select_nli_backend(settings.nli_backend) if nli_threshold is not None else None
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
        semantic_backend=semantic_backend,
        semantic_threshold=semantic_threshold,
        nli_backend=nli_backend,
        nli_threshold=nli_threshold,
    )
    estimated_cost_usd = _estimate_cost_usd(
        draft.input_tokens,
        draft.output_tokens,
        settings.opencode_go_price_input_per_mtok,
        settings.opencode_go_price_output_per_mtok,
    )
    sli = ProviderSli(
        provider_latency_ms=provider_latency_ms,
        estimated_cost_usd=estimated_cost_usd,
    )
    # Secret-free structured SLI line for ops observability.
    _LOGGER.info(
        "rag_sli provider=%s grounding=%s latency_ms=%s input_tokens=%s "
        "output_tokens=%s cost_usd=%s strategy=%s",
        draft.provider_name,
        grounding.status,
        provider_latency_ms,
        draft.input_tokens,
        draft.output_tokens,
        estimated_cost_usd,
        retrieval_provider.name,
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
        sli=sli,
    )
