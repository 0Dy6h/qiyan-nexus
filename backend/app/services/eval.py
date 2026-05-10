from pathlib import Path

from app.schemas.eval import RagEvalItemResult, RagEvalReport, RagEvalSummary, load_rag_eval_dataset
from app.services.rag import DISCLAIMER, answer_question


_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "evals" / "rag_ad_eval_questions.json"


def get_rag_eval_questions() -> list[dict]:
    return [item.dict() for item in load_rag_eval_dataset(_DATA_PATH)]


def run_rag_ad_eval_report() -> dict:
    results: list[RagEvalItemResult] = []
    for question in load_rag_eval_dataset(_DATA_PATH):
        response = answer_question(question.question, source=question.source_preference, top_k=3)
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
        citation_chunk_ids = [citation.chunk_id for citation in response.citations if citation.chunk_id]
        expected_literature_hits = [
            literature_id
            for literature_id in question.expected_literature_ids
            if literature_id in citation_literature_ids
        ]
        expected_chunk_hits = [chunk_id for chunk_id in question.expected_chunk_ids if chunk_id in citation_chunk_ids]
        missing_must_include = [term for term in question.must_include if term.lower() not in response_text]
        violated_must_not_include = [term for term in question.must_not_include if term.lower() in response_text]
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
        ),
        items=results,
    )
    return report.dict()
