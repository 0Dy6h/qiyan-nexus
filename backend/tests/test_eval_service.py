from pathlib import Path

import pytest

from app.schemas.eval import load_rag_eval_dataset
from app.services import eval as eval_service
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


def test_run_rag_ad_eval_report_allows_questions_without_expected_chunks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    synthetic_dataset = tmp_path / "synthetic_eval.json"
    synthetic_dataset.write_text(
        """[
          {
            "id": "synthetic-no-chunks",
            "question": "特应性皮炎和肠-脑-皮肤轴之间有什么关系？",
            "source_preference": "all",
            "difficulty": "easy",
            "expected_literature_ids": ["cn-ad-gbs-001"],
            "expected_chunk_ids": [],
            "must_include": ["肠道菌群"],
            "must_not_include": ["确诊建议"],
            "compliance_notes": "synthetic question covers the empty-chunk branch."
          }
        ]""",
        encoding="utf-8",
    )
    monkeypatch.setattr(eval_service, "_DATA_PATH", synthetic_dataset)

    report = run_rag_ad_eval_report()

    assert len(report["items"]) == 1
    item = report["items"][0]
    assert item["expected_chunk_ids"] == []
    assert item["passed"] is True


def test_run_rag_ad_eval_report_meets_baseline_pass_rate():
    report = run_rag_ad_eval_report()

    assert report["summary"]["passed_questions"] == 20, (
        "RAG eval baseline must hold at 20/20 — see docs/plans/2026-05-10-rag-eval-slice.md."
        f" Current failing items: "
        f"{[item['id'] for item in report['items'] if not item['passed']]}"
    )
    assert report["summary"]["citation_hit_count"] == 20
    assert report["summary"]["disclaimer_coverage_count"] == 20
    assert report["summary"]["must_not_violation_count"] == 0


def test_run_rag_ad_eval_report_chunk_hit_count_meets_target():
    report = run_rag_ad_eval_report()

    assert report["summary"]["chunk_hit_count"] == 20, (
        "chunk_hit_count must stay at 20/20 after the chunk dataset expansion."
        f" Current value: {report['summary']['chunk_hit_count']}."
        " Questions without chunk_hit but with expected_chunk_ids: "
        f"{[item['id'] for item in report['items'] if item['expected_chunk_ids'] and not item['expected_chunk_hits']]}"
    )


def test_rag_eval_q019_returns_all_expected_molecular_research_literature_hits():
    report = run_rag_ad_eval_report()
    q019 = next(item for item in report["items"] if item["id"] == "rag-eval-019")

    assert q019["expected_literature_hits"] == [
        "cn-ad-network-007",
        "pmid-40100008",
        "pmid-40100005",
    ]
