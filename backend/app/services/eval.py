from pathlib import Path
from typing import Any

from app.schemas.eval import (
    RagEvalItemResult,
    RagEvalReport,
    RagEvalSummary,
    load_grounding_semantic_pairs,
    load_rag_eval_dataset,
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
    threshold: float, backend_name: str | None = None
) -> dict[str, Any]:
    """Score the labeled (claim, chunk, supported) fixture at a given threshold.

    Reports the confusion matrix plus score-distribution bounds so the gate's
    separation is measurable. On the default ``hashing`` backend the score is a
    lexical-overlap proxy: faithful claims separate cleanly from their *paired*
    hallucinations, but a high-lexical-overlap fabrication can still outscore an
    unrelated faithful claim — hence ``paired_separation`` is reported alongside
    the global confusion matrix.
    """

    backend = select_embedding_backend(backend_name)
    pairs = load_grounding_semantic_pairs(_SEMANTIC_PAIRS_PATH)
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
