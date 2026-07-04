import logging
import time
from datetime import UTC, datetime

from app.core.config import get_settings
from app.repositories.protocols import ChunkRepository, LiteratureRepository
from app.repositories.runtime_storage import (
    get_chunk_repository,
    get_literature_repository,
)
from app.schemas.literature import LiteratureSource
from app.schemas.rag import (
    CitationCard,
    GroundingMetadata,
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
    domain_vocabulary,
    select_retrieval_provider,
    tokenize_query,
)

DISCLAIMER = "非诊断结论、需结合临床。"
_LOGGER = logging.getLogger(__name__)
_REPOSITORY = get_literature_repository()
_CHUNK_REPOSITORY = get_chunk_repository()

# Off-topic guard: the sample corpus is atopic-dermatitis-scoped. A positive
# top score alone is not enough (single common CJK chars like 的/是/药 match many
# AD docs), so an on-topic query must also carry a recognized, non-generic
# domain/entity term.
RELEVANCE_MIN_TOP_SCORE = 3
_GENERIC_INTENT_TOKENS = {
    "therapy",
    "treatment",
    "intervention",
    "acupuncture",
    "topical",
    "external",
}
_ENTITY_TOKEN_PREFIXES = ("formula-", "herb-", "compound-", "target-", "pathway-")


def _query_entity_tokens(query_tokens: set[str]) -> set[str]:
    return {token for token in query_tokens if token.startswith(_ENTITY_TOKEN_PREFIXES)}


def _entity_token_variants(entity_token: str) -> set[str]:
    variants = {entity_token}
    prefix, separator, rest = entity_token.partition("-")
    if separator and rest:
        variants.add(f"{prefix}:{rest}")
    return variants


def _candidate_entity_ids(candidate: ScoredCandidate) -> set[str]:
    entity_ids = {entity_id.lower() for entity_id in candidate.item.related_entity_ids}
    if candidate.chunk is not None:
        entity_ids.update(entity_id.lower() for entity_id in candidate.chunk.related_entity_ids)
    return entity_ids


def _candidate_matches_query_entity(candidate: ScoredCandidate, entity_tokens: set[str]) -> bool:
    candidate_ids = _candidate_entity_ids(candidate)
    for entity_token in entity_tokens:
        if candidate_ids & _entity_token_variants(entity_token):
            return True
    return False


def _query_has_topical_signal(question: str, ranked: list[ScoredCandidate]) -> bool:
    """Whether ``question`` is in-domain for the AD evidence corpus.

    True iff retrieval found a positive top match AND the query contains at
    least one domain-vocabulary token. Off-topic queries (e.g. a hypertension
    or weather question) only accumulate single-CJK-char noise — no domain
    token and a near-zero top score — so ``answer_question`` returns an honest
    "no matching evidence" answer instead of confidently surfacing mismatched
    AD literature (product fix P0-1).
    """

    if not ranked:
        return False
    if max(candidate.score for candidate in ranked) < RELEVANCE_MIN_TOP_SCORE:
        return False
    query_tokens = set(tokenize_query(question))
    topical_tokens = query_tokens & domain_vocabulary()
    strong_topical_tokens = topical_tokens - _GENERIC_INTENT_TOKENS
    return bool(strong_topical_tokens)


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
    literature_repository: LiteratureRepository | None = None,
    chunk_repository: ChunkRepository | None = None,
    request_id: str | None = None,
) -> RagAnswerResponse:
    normalized_question = question.strip()
    preferred_source_type = (
        "cn_literature" if detect_query_language(normalized_question) == "zh" else "pubmed"
    )
    active_literature_repository = literature_repository or _REPOSITORY
    active_chunk_repository = chunk_repository or _CHUNK_REPOSITORY

    items = active_literature_repository.list_items()
    if source != "all":
        items = [item for item in items if item.source_type == source]

    chunks_by_item = {
        item.id: active_chunk_repository.list_chunks_by_literature_id(item.id) for item in items
    }

    retrieval_provider = select_retrieval_provider(retrieval_provider_name)
    ranked: list[ScoredCandidate] = retrieval_provider.rank(
        normalized_question, items, chunks_by_item, preferred_source_type
    )

    if source == "all" and "network" in tokenize_query(normalized_question):
        ranked = sorted(
            ranked,
            key=lambda c: (
                c.item.record_origin != "seed_sample",
                "network_pharmacology" in c.item.evidence_tags,
                "targeted_therapy" in c.item.evidence_tags,
                c.language_bonus,
                c.score,
                c.item.year,
            ),
            reverse=True,
        )

    available_citation_count: int
    selected: list[ScoredCandidate]
    if _query_has_topical_signal(normalized_question, ranked):
        query_tokens = set(tokenize_query(normalized_question))
        entity_tokens = _query_entity_tokens(query_tokens)
        positive_ranked = [c for c in ranked if c.score > 0]
        entity_ranked = [
            c for c in positive_ranked if _candidate_matches_query_entity(c, entity_tokens)
        ]
        citation_pool = entity_ranked or positive_ranked
        available_citation_count = len(citation_pool)
        if available_citation_count == 0:
            available_citation_count = len(ranked)

        selected = citation_pool[:top_k]
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
    else:
        # Off-topic query (P0-1): the sample corpus is AD-scoped, so an
        # off-topic question only accumulates single-CJK-char noise. Return an
        # honest "no matching evidence" answer with zero citations instead of
        # confidently surfacing mismatched AD literature.
        selected = []
        available_citation_count = 0

    citations: list[CitationCard] = []
    # Borrow ② (ADR-0016): expose a transparent, computed relevance instead of
    # only the constant source-type prior. match_score normalises each selected
    # candidate's real retrieval score against the best score in this result
    # set, so the top hit saturates at 1.0. It is a relevance signal, NOT a
    # probability or efficacy estimate.
    max_selected_score = max((candidate.score for candidate in selected), default=0)
    for candidate in selected:
        item = candidate.item
        chunk = candidate.chunk
        chunk_tags = chunk.evidence_tags if chunk and chunk.evidence_tags else []
        reason_tags = chunk_tags or item.evidence_tags
        match_score = (
            round(candidate.score / max_selected_score, 4) if max_selected_score > 0 else 0.0
        )
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
                match_score=match_score,
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
        "output_tokens=%s cost_usd=%s strategy=%s request_id=%s",
        draft.provider_name,
        grounding.status,
        provider_latency_ms,
        draft.input_tokens,
        draft.output_tokens,
        estimated_cost_usd,
        retrieval_provider.name,
        request_id,
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


_RAG_SOURCE_LABELS: dict[str, str] = {
    "all": "全部文献",
    "cn_literature": "中文文献",
    "pubmed": "PubMed",
}


def _rag_source_label(source: str) -> str:
    return _RAG_SOURCE_LABELS.get(source, source)


def _join_or_fallback(items: list[str], fallback: str) -> str:
    return "、".join(items) if items else fallback


def _format_latency_ms(sli: ProviderSli | None) -> str:
    if sli is None or sli.provider_latency_ms is None:
        return "未返回"
    return f"{sli.provider_latency_ms} ms"


def _format_estimated_cost(sli: ProviderSli | None) -> str:
    if sli is None or sli.estimated_cost_usd is None:
        return "未估算"
    return f"${sli.estimated_cost_usd:.6f}"


def _format_semantic_threshold(value: float | None) -> str:
    return "未启用" if value is None else f"{value:.2f}"


def _format_semantic_score(value: float | None) -> str:
    return "未计算" if value is None else f"{round(value * 100)}%"


def _format_nli_threshold(value: float | None) -> str:
    return "未启用" if value is None else f"{value:.2f}"


def _format_nli_score(value: float | None) -> str:
    return "未计算" if value is None else f"{round(value * 100)}%"


def _format_token_usage(value: int | None) -> str:
    return "未返回" if value is None else str(value)


def _format_match_score(value: float | None) -> str:
    return "未计算" if value is None else f"{round(value * 100)}%"


def _format_citation_block(citation: CitationCard, index: int) -> str:
    lines: list[str] = []
    lines.append(f"### 引用 {index + 1} — {citation.title}")
    meta = [
        f"来源：{citation.source}",
        f"literature_id：{citation.literature_id}",
        f"检索匹配度：{_format_match_score(citation.match_score)}",
        f"来源类型先验：{round(citation.confidence * 100)}%",
    ]
    if citation.chunk_id:
        meta.append(f"chunk_id：{citation.chunk_id}")
    if citation.source_type:
        meta.append(f"source_type：{citation.source_type}")
    if citation.pdf_upload_id:
        meta.append(f"pdf_upload_id：{citation.pdf_upload_id}")
    lines.append(" · ".join(meta))
    lines.append("")
    lines.append(f"> {citation.snippet}")
    if citation.quote:
        lines.append("")
        lines.append(f"证据片段引文：{citation.quote}")
    if citation.reason:
        lines.append("")
        lines.append(f"命中证据标签：{citation.reason}")
    return "\n".join(lines)


def build_answer_markdown(answer: RagAnswerResponse) -> str:
    """Build a Markdown export string for a RAG answer payload.

    The export is reviewer-facing first, while preserving the previous metadata
    labels for API smoke tests and technical auditability.
    """

    sections: list[str] = []
    grounding: GroundingMetadata = answer.grounding
    source_label = _rag_source_label(answer.retrieval.applied_source)
    cited_claim_coverage = f"{grounding.cited_claim_count}/{grounding.claim_count}"
    sections.append("# Qiyan Nexus RAG 答案导出")
    sections.append("")
    sections.append("## 证据简报")
    sections.append("")
    sections.append(f"- 导出时间（UTC）：{answer.answered_at}")
    sections.append(f"- 回答模式：{answer.provider_name} / {answer.retrieval.strategy}")
    sections.append(f"- 证据范围：{source_label}")
    sections.append(f"- 引用卡片：{len(answer.citations)}")
    sections.append(f"- 可用引用数：{answer.retrieval.available_citation_count}")
    sections.append(f"- 句级引用覆盖：{cited_claim_coverage}")
    sections.append(f"- 结构化声明：{len(grounding.structured_claims)}")
    sections.append("")
    sections.append("## 问题")
    sections.append("")
    sections.append(answer.question)
    sections.append("")
    sections.append("## 回答")
    sections.append("")
    sections.append(answer.answer)
    sections.append("")
    sections.append("## 使用边界")
    sections.append("")
    sections.append(f"- 本导出仅用于 AD 中医药证据整理和 reviewer 走查：{DISCLAIMER}")
    sections.append("- 引用证据可能来自演示 seed、PubMed 同步记录或用户上传 PDF；请逐条核对来源。")
    sections.append(
        "- 当前网络/机制相关内容如被引用，应按探索性线索理解，不等同正式网络药理学结论。"
    )
    sections.append(
        "- 引用「检索匹配度」为按检索得分归一的相对相关度启发式，非概率、非疗效或置信判断；"
        "「来源类型先验」是按来源类型的固定基线权重。"
    )
    sections.append("")
    sections.append("## 结构化声明")
    sections.append("")
    if not grounding.structured_claims:
        sections.append("（当前回答没有结构化声明。）")
    else:
        for idx, claim in enumerate(grounding.structured_claims):
            sections.append(f"### Claim {idx + 1}")
            sections.append("")
            sections.append(claim.text)
            sections.append("")
            sections.append(f"evidence_refs：{_join_or_fallback(claim.evidence_refs, '无')}")
            sections.append(f"semantic_score：{_format_semantic_score(claim.semantic_score)}")
            sections.append(f"entailment_score：{_format_nli_score(claim.entailment_score)}")
            sections.append("")
    sections.append("")
    sections.append("## 引用证据")
    sections.append("")
    if not answer.citations:
        sections.append("（当前回答没有可核对的引用证据。）")
    else:
        for idx, citation in enumerate(answer.citations):
            sections.append(_format_citation_block(citation, idx))
            sections.append("")
    sections.append("## Reviewer 核对清单")
    sections.append("")
    sections.append(f"- [ ] 已核对免责声明：{DISCLAIMER}")
    sections.append("- [ ] 已逐条打开引用文献详情或原文 PDF")
    sections.append("- [ ] 已确认 seed / PubMed / 上传 PDF 来源边界")
    sections.append("- [ ] 已确认当前回答不作为诊断或处方建议")
    sections.append("")
    sections.append("## 技术审计信息")
    sections.append("")
    sections.append(f"- 导出时间（UTC）：{answer.answered_at}")
    sections.append(f"- 应用来源：{source_label}")
    sections.append(f"- 应用 top_k：{answer.retrieval.applied_top_k}")
    sections.append(f"- 可用引用数：{answer.retrieval.available_citation_count}")
    sections.append(f"- Provider：{answer.provider_name}")
    sections.append(f"- 检索策略：{answer.retrieval.strategy}")
    sections.append(f"- Grounding 状态：{grounding.status}")
    sections.append(f"- Grounding 策略：{grounding.policy}")
    sections.append(
        f"- Provider-native grounding：{'true' if grounding.provider_native_grounding else 'false'}"
    )
    sections.append(f"- Grounding Tool：{grounding.tool_name or '无'}")
    sections.append(f"- Tool 调用数：{grounding.tool_call_count}")
    sections.append(f"- 语义阈值：{_format_semantic_threshold(grounding.semantic_threshold)}")
    sections.append(f"- 最小语义支持度：{_format_semantic_score(grounding.min_semantic_score)}")
    sections.append(f"- NLI 阈值：{_format_nli_threshold(grounding.nli_threshold)}")
    sections.append(f"- 最小蕴含支持度：{_format_nli_score(grounding.min_entailment_score)}")
    sections.append(f"- Grounding 拦截原因：{grounding.blocked_reason or '无'}")
    sections.append(f"- 句级引用覆盖：{cited_claim_coverage}")
    sections.append(
        f"- Grounding 命中证据：{_join_or_fallback(grounding.matched_evidence_refs, '无')}"
    )
    sections.append(
        f"- Grounding 异常证据：{_join_or_fallback(grounding.unsupported_evidence_refs, '无')}"
    )
    sections.append(f"- 结构化声明数：{len(grounding.structured_claims)}")
    sections.append(f"- Token 输入：{_format_token_usage(answer.input_tokens)}")
    sections.append(f"- Token 输出：{_format_token_usage(answer.output_tokens)}")
    sections.append(f"- Provider 延迟：{_format_latency_ms(answer.sli)}")
    sections.append(f"- 预估成本：{_format_estimated_cost(answer.sli)}")
    sections.append("---")
    sections.append("")
    sections.append(DISCLAIMER)
    sections.append("")
    return "\n".join(sections)
