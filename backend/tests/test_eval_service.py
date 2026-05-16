from pathlib import Path

from app.schemas.eval import load_rag_eval_dataset
from app.services.eval import get_rag_eval_questions, run_rag_ad_eval_report


def test_load_rag_eval_dataset_returns_20_questions():
    data_path = (
        Path(__file__).resolve().parents[1] / "data" / "evals" / "rag_ad_eval_questions.json"
    )

    items = load_rag_eval_dataset(data_path)

    assert len(items) == 20
    assert items[0].id == "rag-eval-001"
    assert items[-1].id == "rag-eval-020"


def test_rag_eval_questions_cover_literature_and_compliance_fields():
    data_path = (
        Path(__file__).resolve().parents[1] / "data" / "evals" / "rag_ad_eval_questions.json"
    )

    items = load_rag_eval_dataset(data_path)
    first = items[0]

    assert first.expected_literature_ids == [
        "cn-ad-gbs-001",
        "cn-ad-microbiome-003",
        "pmid-40100002",
    ]
    assert "肠道菌群" in first.must_include
    assert "替代医生诊断" in first.must_not_include
    assert "不能给出诊断结论" in first.compliance_notes


def test_get_rag_eval_questions_returns_serializable_payload():
    items = get_rag_eval_questions()

    assert len(items) == 20
    assert items[16]["id"] == "rag-eval-017"
    assert items[16]["source_preference"] == "pubmed"


def test_run_rag_ad_eval_report_returns_summary_and_item_results():
    report = run_rag_ad_eval_report()

    assert report["summary"]["total_questions"] == 20
    assert report["summary"]["disclaimer_coverage_count"] == 20
    assert report["summary"]["must_not_violation_count"] == 0
    assert 0 <= report["summary"]["pass_rate"] <= 1
    assert len(report["items"]) == 20

    first = report["items"][0]
    assert first["id"] == "rag-eval-001"
    assert first["source_preference"] == "all"
    assert "cn-ad-gbs-001" in first["expected_literature_hits"]
    assert "chunk-cn-ad-gbs-001-abstract" in first["expected_chunk_hits"]
    assert first["disclaimer_present"] is True
    assert first["violated_must_not_include"] == []


def test_run_rag_ad_eval_report_allows_questions_without_expected_chunks():
    report = run_rag_ad_eval_report()

    item = next(
        result
        for result in report["items"]
        if not result["expected_chunk_ids"]
        and result["expected_literature_hits"]
        and not result["missing_must_include"]
        and not result["violated_must_not_include"]
        and result["disclaimer_present"]
    )

    assert item["expected_chunk_ids"] == []
    assert item["passed"] is True


def test_run_rag_ad_eval_report_meets_baseline_pass_rate():
    report = run_rag_ad_eval_report()

    assert report["summary"]["passed_questions"] >= 19, (
        "RAG eval baseline must hold at >=19/20 — see docs/plans/2026-05-10-rag-eval-slice.md."
        f" Current failing items: "
        f"{[item['id'] for item in report['items'] if not item['passed']]}"
    )
    assert report["summary"]["citation_hit_count"] == 20
    assert report["summary"]["disclaimer_coverage_count"] == 20
    assert report["summary"]["must_not_violation_count"] == 0
