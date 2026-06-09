"""Cross-lingual retrieval evaluation harness.

Pure retrieval evaluation (no LLM): measures recall@k, MRR, language
diversity for bilingual questions.  Uses the existing 50-question
rag_ad_eval_questions.json dataset, filtering to bilingual questions
(those whose expected_literature_ids contain both cn-* and pmid-* ids).

Design principle: this module calls ``retrieval_provider.rank()``
directly, bypassing ``answer_question()``, so it measures retrieval
quality in isolation without confounds from LLM generation, grounding,
or disclaimer checks.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.repositories.chunk import InMemoryChunkRepository
from app.repositories.literature import InMemoryLiteratureRepository
from app.repositories.runtime_storage import (
    resolve_chunk_storage_path,
    resolve_literature_storage_path,
)
from app.schemas.chunk import LiteratureChunk
from app.schemas.eval import (
    CrossLingualRetrievalItem,
    CrossLingualRetrievalReport,
    CrossLingualRetrievalSummary,
    EvalCorpus,
    load_rag_eval_dataset,
)
from app.services.retrieval.provider import select_retrieval_provider

_CN_PATTERN = re.compile(r"[\u4e00-\u9fff]")
_SEED_LITERATURE_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "literature" / "sample_ad_literature.json"
)
_SEED_CHUNK_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "literature" / "sample_ad_chunks.json"
)


def _identify_question_language(question: str) -> str:
    """Heuristic: if any CJK char present → zh, else en."""
    if _CN_PATTERN.search(question):
        return "zh"
    return "en"


def _classify_id(lit_id: str) -> str:
    """Map a literature_id to its source language: cn / pubmed / unknown."""
    if lit_id.startswith("cn-"):
        return "cn"
    if lit_id.startswith("pmid-"):
        return "pubmed"
    return "unknown"


def _compute_item_metrics(
    *,
    id: str,
    question: str,
    source_preference: str,
    question_language: str,
    expected_cn_ids: list[str],
    expected_pubmed_ids: list[str],
    top_k: int,
    retrieved_ids: list[str],
) -> CrossLingualRetrievalItem:
    """Compute per-question cross-lingual metrics from retrieval results."""
    # Count hits by language
    cn_hits = sum(1 for rid in retrieved_ids if _classify_id(rid) == "cn")
    pubmed_hits = sum(1 for rid in retrieved_ids if _classify_id(rid) == "pubmed")

    # Monolingual recall: the question language's expected IDs
    if question_language == "zh":
        total_mono = len(expected_cn_ids)
        mono_hits = sum(1 for rid in retrieved_ids if rid in expected_cn_ids)
    else:
        total_mono = len(expected_pubmed_ids)
        mono_hits = sum(1 for rid in retrieved_ids if rid in expected_pubmed_ids)

    monolingual_recall = mono_hits / total_mono if total_mono > 0 else 0.0

    # Cross-lingual recall: the other language's expected IDs
    if question_language == "zh":
        total_cross = len(expected_pubmed_ids)
        cross_hits = sum(1 for rid in retrieved_ids if rid in expected_pubmed_ids)
    else:
        total_cross = len(expected_cn_ids)
        cross_hits = sum(1 for rid in retrieved_ids if rid in expected_cn_ids)

    cross_lingual_recall = cross_hits / total_cross if total_cross > 0 else 0.0

    # Language diversity
    max_hit = max(cn_hits, pubmed_hits, 1)
    language_diversity = min(cn_hits, pubmed_hits) / max_hit

    # MRR: 1 / rank of first expected ID in retrieved_ids (1-indexed)
    all_expected = set(expected_cn_ids + expected_pubmed_ids)
    mrr = 0.0
    if all_expected:
        for rank, rid in enumerate(retrieved_ids, start=1):
            if rid in all_expected:
                mrr = 1.0 / rank
                break

    # Precision@k
    precision_at_k = (
        sum(1 for rid in retrieved_ids if rid in all_expected) / top_k if top_k > 0 else 0.0
    )

    return CrossLingualRetrievalItem(
        id=id,
        question=question,
        source_preference=source_preference,
        question_language=question_language,
        expected_cn_ids=expected_cn_ids,
        expected_pubmed_ids=expected_pubmed_ids,
        top_k=top_k,
        retrieved_ids=retrieved_ids,
        cn_hit_count=cn_hits,
        pubmed_hit_count=pubmed_hits,
        monolingual_recall=round(monolingual_recall, 4),
        cross_lingual_recall=round(cross_lingual_recall, 4),
        language_diversity=round(language_diversity, 4),
        mean_reciprocal_rank=round(mrr, 4),
        precision_at_k=round(precision_at_k, 4),
    )


def run_cross_lingual_retrieval_eval(
    strategy: str | None = None,
    top_k: int = 10,
    eval_data_path: Path | None = None,
    corpus: EvalCorpus = "seed",
) -> CrossLingualRetrievalReport:
    """Run a retrieval-only cross-lingual evaluation.

    Filters the rag_ad_eval_questions to bilingual questions (those with
    both cn-* and pmid-* expected_literature_ids), calls the retrieval
    provider's ``rank()`` directly, and computes recall@k and MRR metrics.

    Args:
        strategy: retrieval provider name (keyword/vector/hybrid), default keyword
        top_k: number of top candidates to inspect
        eval_data_path: path to eval questions JSON, defaults to dataset
        corpus: seed benchmark corpus or runtime local state corpus

    Returns:
        CrossLingualRetrievalReport with per-item metrics and aggregated summary
    """
    dataset_path = eval_data_path or (
        Path(__file__).resolve().parents[2] / "data" / "evals" / "rag_ad_eval_questions.json"
    )
    dataset = load_rag_eval_dataset(dataset_path)

    # Filter to bilingual questions (both cn-* and pmid-* expected IDs)
    bilingual = [
        q
        for q in dataset
        if any(lit_id.startswith("cn-") for lit_id in q.expected_literature_ids)
        and any(lit_id.startswith("pmid-") for lit_id in q.expected_literature_ids)
    ]

    # Load retrieval provider and data
    provider = select_retrieval_provider(strategy)
    if corpus == "runtime":
        literature_path = resolve_literature_storage_path()
        chunk_path = resolve_chunk_storage_path()
    else:
        literature_path = _SEED_LITERATURE_PATH
        chunk_path = _SEED_CHUNK_PATH
    lit_repo = InMemoryLiteratureRepository(literature_path)
    chunk_repo = InMemoryChunkRepository(chunk_path)
    all_items = lit_repo.list_items()
    chunks_by_item: dict[str, list[LiteratureChunk]] = {}
    for lit_item in all_items:
        chunks_by_item[lit_item.id] = chunk_repo.list_chunks_by_literature_id(lit_item.id)

    items: list[CrossLingualRetrievalItem] = []
    for q in bilingual:
        question_lang = _identify_question_language(q.question)
        preferred_source = "cn_literature" if question_lang == "zh" else "pubmed"

        ranked = provider.rank(
            q.question,
            all_items,
            chunks_by_item,
            preferred_source_type=preferred_source,
        )

        # Deduplicate to unique literature_ids, keeping order
        seen: set[str] = set()
        retrieved_ids: list[str] = []
        for candidate in ranked:
            lit_id = candidate.item.id
            if lit_id not in seen:
                seen.add(lit_id)
                retrieved_ids.append(lit_id)
            if len(retrieved_ids) >= top_k:
                break

        expected_cn = [lid for lid in q.expected_literature_ids if lid.startswith("cn-")]
        expected_pubmed = [lid for lid in q.expected_literature_ids if lid.startswith("pmid-")]

        eval_item = _compute_item_metrics(
            id=q.id,
            question=q.question,
            source_preference=q.source_preference,
            question_language=question_lang,
            expected_cn_ids=expected_cn,
            expected_pubmed_ids=expected_pubmed,
            top_k=top_k,
            retrieved_ids=retrieved_ids,
        )
        items.append(eval_item)

    # Aggregate summary
    n = len(items)
    if n > 0:
        avg_mono = round(sum(i.monolingual_recall for i in items) / n, 4)
        avg_cross = round(sum(i.cross_lingual_recall for i in items) / n, 4)
        avg_div = round(sum(i.language_diversity for i in items) / n, 4)
        avg_pk = round(sum(i.precision_at_k for i in items) / n, 4)
        avg_mrr = round(sum(i.mean_reciprocal_rank for i in items) / n, 4)
    else:
        avg_mono = avg_cross = avg_div = avg_pk = avg_mrr = 0.0

    summary = CrossLingualRetrievalSummary(
        total_questions=n,
        corpus=corpus,
        top_k=top_k,
        retrieval_strategy=provider.name,
        avg_monolingual_recall=avg_mono,
        avg_cross_lingual_recall=avg_cross,
        avg_language_diversity=avg_div,
        avg_precision_at_k=avg_pk,
        avg_mrr=avg_mrr,
    )

    return CrossLingualRetrievalReport(summary=summary, items=items)
