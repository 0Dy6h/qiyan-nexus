from pathlib import Path
from typing import Any

from app.schemas.eval import (
    RagEvalItemResult,
    RagEvalReport,
    RagEvalSummary,
    RealAnswerPair,
    load_grounding_semantic_pairs,
    load_rag_eval_dataset,
    load_real_answer_pairs,
)
from app.services.grounding import score_claim_support
from app.services.llm.provider import DEFAULT_PROVIDER_NAME
from app.services.rag import DISCLAIMER, answer_question
from app.services.retrieval.embedding import select_embedding_backend
from app.services.retrieval.provider import DEFAULT_RETRIEVAL_PROVIDER_NAME

_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "evals" / "rag_ad_eval_questions.json"
_SEMANTIC_PAIRS_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "evals" / "grounding_semantic_pairs.json"
)
# Harder real-LLM-style fixture (faithful claims lifted from the 2026-05-31 live
# smoke, paired with on-topic hard negatives) used only for threshold-recalibration
# analysis on the bge backend; not part of the locked hashing-default invariants.
SEMANTIC_PAIRS_BGE_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "evals" / "grounding_semantic_pairs_bge.json"
)
# Real-answer validation set (Slice 2): 20 pairs from live smoke claims + authored
# hard negatives, labeled with support_label ∈ {supported, partial, unsupported}.
REAL_ANSWER_PAIRS_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "evals" / "grounding_real_answer_pairs.json"
)


def get_rag_eval_questions() -> list[dict[str, Any]]:
    return [item.model_dump() for item in load_rag_eval_dataset(_DATA_PATH)]


def run_rag_ad_eval_report(strategy: str | None = None) -> dict[str, Any]:
    results: list[RagEvalItemResult] = []
    run_provider_name = DEFAULT_PROVIDER_NAME
    applied_strategy = strategy or DEFAULT_RETRIEVAL_PROVIDER_NAME
    for question in load_rag_eval_dataset(_DATA_PATH):
        response = answer_question(
            question.question,
            source=question.source_preference,
            top_k=3,
            llm_provider_name=DEFAULT_PROVIDER_NAME,
            retrieval_provider_name=strategy,
        )
        run_provider_name = response.provider_name
        applied_strategy = response.retrieval.strategy
        citation_text = "\n".join(
            "\n".join(
                [
                    citation.title,
                    citation.source,
                    citation.snippet,
                    citation.quote or "",
                    citation.reason or "",
                ]
            )
            for citation in response.citations
        )
        response_text = f"{response.answer}\n{response.disclaimer}\n{citation_text}".lower()
        citation_literature_ids = [citation.literature_id for citation in response.citations]
        citation_chunk_ids = [
            citation.chunk_id for citation in response.citations if citation.chunk_id
        ]
        expected_literature_hits = [
            literature_id
            for literature_id in question.expected_literature_ids
            if literature_id in citation_literature_ids
        ]
        expected_chunk_hits = [
            chunk_id for chunk_id in question.expected_chunk_ids if chunk_id in citation_chunk_ids
        ]
        missing_must_include = [
            term for term in question.must_include if term.lower() not in response_text
        ]
        violated_must_not_include = [
            term for term in question.must_not_include if term.lower() in response_text
        ]
        disclaimer_present = response.disclaimer == DISCLAIMER
        literature_passed = bool(expected_literature_hits)
        chunk_passed = not question.expected_chunk_ids or bool(expected_chunk_hits)
        passed = (
            literature_passed
            and chunk_passed
            and disclaimer_present
            and not missing_must_include
            and not violated_must_not_include
        )
        results.append(
            RagEvalItemResult(
                id=question.id,
                question=question.question,
                source_preference=question.source_preference,
                difficulty=question.difficulty,
                expected_literature_ids=question.expected_literature_ids,
                expected_literature_hits=expected_literature_hits,
                expected_chunk_ids=question.expected_chunk_ids,
                expected_chunk_hits=expected_chunk_hits,
                missing_must_include=missing_must_include,
                violated_must_not_include=violated_must_not_include,
                disclaimer_present=disclaimer_present,
                citation_count=len(response.citations),
                provider_name=response.provider_name,
                grounding_status=response.grounding.status,
                passed=passed,
            )
        )

    total_questions = len(results)
    passed_questions = sum(1 for item in results if item.passed)
    report = RagEvalReport(
        summary=RagEvalSummary(
            total_questions=total_questions,
            passed_questions=passed_questions,
            pass_rate=round(passed_questions / total_questions, 3) if total_questions else 0,
            citation_hit_count=sum(1 for item in results if item.expected_literature_hits),
            chunk_hit_count=sum(1 for item in results if item.expected_chunk_hits),
            disclaimer_coverage_count=sum(1 for item in results if item.disclaimer_present),
            must_not_violation_count=sum(1 for item in results if item.violated_must_not_include),
            grounding_blocked_count=sum(
                1 for item in results if item.grounding_status == "blocked"
            ),
            provider_name=run_provider_name,
            retrieval_strategy=applied_strategy,
        ),
        items=results,
    )
    return report.model_dump()


def run_grounding_semantic_separation(
    threshold: float,
    backend_name: str | None = None,
    pairs_path: Path | None = None,
) -> dict[str, Any]:
    """Score the labeled (claim, chunk, supported) fixture at a given threshold.

    Reports the confusion matrix plus score-distribution bounds so the gate's
    separation is measurable. On the default ``hashing`` backend the score is a
    lexical-overlap proxy: faithful claims separate cleanly from their *paired*
    hallucinations, but a high-lexical-overlap fabrication can still outscore an
    unrelated faithful claim — hence ``paired_separation`` is reported alongside
    the global confusion matrix.

    ``pairs_path`` defaults to the curated easy-negative fixture. Pass the
    ``grounding_semantic_pairs_bge.json`` path to score the harder real-LLM-style
    set used for threshold recalibration (see
    ``docs/evaluations/2026-06-01-threshold-recalibration.md``).
    """

    backend = select_embedding_backend(backend_name)
    pairs = load_grounding_semantic_pairs(pairs_path or _SEMANTIC_PAIRS_PATH)
    scored = [(pair, score_claim_support(pair.claim, pair.chunk_text, backend)) for pair in pairs]
    faithful = [(pair, score) for pair, score in scored if pair.supported]
    hallucinated = [(pair, score) for pair, score in scored if not pair.supported]

    accepted_faithful = sum(1 for _, score in faithful if score >= threshold)
    rejected_hallucinated = sum(1 for _, score in hallucinated if score < threshold)
    score_by_id = {pair.id: score for pair, score in scored}
    paired_separation = sum(
        1
        for pair, score in faithful
        if (counterpart := score_by_id.get(pair.id.replace("-faithful", "-hallucinated")))
        is not None
        and score > counterpart
    )

    return {
        "threshold": threshold,
        "backend_name": backend.name,
        "faithful_total": len(faithful),
        "hallucinated_total": len(hallucinated),
        "accepted_faithful": accepted_faithful,
        "rejected_hallucinated": rejected_hallucinated,
        "false_rejected_faithful": len(faithful) - accepted_faithful,
        "false_accepted_hallucinated": len(hallucinated) - rejected_hallucinated,
        "min_faithful_score": round(min(score for _, score in faithful), 3),
        "max_hallucinated_score": round(max(score for _, score in hallucinated), 3),
        "paired_separation": paired_separation,
        "paired_total": len(faithful),
    }


def run_nli_real_distribution_eval(
    threshold: float = 0.5,
    pairs_path: Path | None = None,
) -> dict[str, Any]:
    """Evaluate the NLI entailment gate on the real-answer labeled validation set.

    Loads ``grounding_real_answer_pairs.json`` (the Slice 2 fixture), scores each
    claim-premise pair with the NLI entailment backend, and returns a confusion
    matrix at the given threshold.

    The `partial` label is tracked separately from `supported` / `unsupported`:
    partial claims are excluded from strict false-accept/false-reject counts
    (they are borderline by definition).

    Requires ``QIYAN_NLI_BACKEND=transformers`` to be set; otherwise raises
    ``ValueError``. The NLI model is lazily loaded on first call.

    Returns a dict with:
    - threshold, total_pairs
    - label_counts: {"supported", "partial", "unsupported"}
    - strict: confusion matrix (supported vs unsupported only)
    - per_pair: list of (support_label, entailment_score, accepted) for all pairs
    - per_label_stats: min/max/mean entailment per label
    """
    from app.services.nli import select_nli_backend

    nli = select_nli_backend()
    if nli is None:
        raise ValueError(
            "NLI backend not configured. Set QIYAN_NLI_BACKEND=transformers "
            "to enable NLI entailment evaluation. (Default: no NLI backend, "
            "the gate is off.)"
        )

    path = pairs_path or REAL_ANSWER_PAIRS_PATH
    pairs = load_real_answer_pairs(path)

    scored: list[tuple[RealAnswerPair, float]] = []
    for pair in pairs:
        score = nli.entailment(pair.premise, pair.claim)
        scored.append((pair, score))

    # Partition by label
    by_label: dict[str, list[tuple[RealAnswerPair, float]]] = {
        "supported": [],
        "partial": [],
        "unsupported": [],
    }
    for pair, score in scored:
        by_label[pair.support_label].append((pair, score))

    # Strict confusion matrix (supported vs unsupported, partial excluded)
    strict_accepted_supported = sum(1 for _, score in by_label["supported"] if score >= threshold)
    strict_rejected_unsupported = sum(
        1 for _, score in by_label["unsupported"] if score < threshold
    )
    false_rejects = len(by_label["supported"]) - strict_accepted_supported
    false_accepts = len(by_label["unsupported"]) - strict_rejected_unsupported

    # Partial: accepted vs rejected (informational only)
    partial_accepted = sum(1 for _, score in by_label["partial"] if score >= threshold)
    partial_rejected = len(by_label["partial"]) - partial_accepted

    def _score_stats(
        entries: list[tuple[RealAnswerPair, float]],
    ) -> dict[str, float | None]:
        scores = [s for _, s in entries]
        if not scores:
            return {"min": None, "max": None, "mean": None}
        return {
            "min": round(min(scores), 4),
            "max": round(max(scores), 4),
            "mean": round(sum(scores) / len(scores), 4),
        }

    per_pair = [
        {
            "support_label": pair.support_label,
            "source": pair.source,
            "entailment_score": round(score, 4),
            "accepted": score >= threshold,
            "claim_preview": pair.claim[:80],
            "premise_preview": pair.premise[:80],
        }
        for pair, score in scored
    ]

    return {
        "threshold": threshold,
        "total_pairs": len(pairs),
        "label_counts": {label: len(entries) for label, entries in by_label.items()},
        "strict": {
            "supported_total": len(by_label["supported"]),
            "unsupported_total": len(by_label["unsupported"]),
            "accepted_supported": strict_accepted_supported,
            "rejected_unsupported": strict_rejected_unsupported,
            "false_rejects": false_rejects,
            "false_accepts": false_accepts,
            "accuracy": round(
                (strict_accepted_supported + strict_rejected_unsupported)
                / max(len(by_label["supported"]) + len(by_label["unsupported"]), 1),
                4,
            ),
        },
        "partial": {
            "total": len(by_label["partial"]),
            "accepted": partial_accepted,
            "rejected": partial_rejected,
        },
        "per_label_stats": {
            "supported": _score_stats(by_label["supported"]),
            "partial": _score_stats(by_label["partial"]),
            "unsupported": _score_stats(by_label["unsupported"]),
        },
        "per_pair": per_pair,
    }
