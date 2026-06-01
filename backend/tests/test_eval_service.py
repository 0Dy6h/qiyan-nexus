import os
from pathlib import Path

import pytest

from app.schemas.eval import load_rag_eval_dataset
from app.services import eval as eval_service
from app.services.eval import (
    get_rag_eval_questions,
    run_grounding_semantic_separation,
    run_rag_ad_eval_report,
)


def test_load_rag_eval_dataset_returns_50_questions():
    data_path = (
        Path(__file__).resolve().parents[1] / "data" / "evals" / "rag_ad_eval_questions.json"
    )

    items = load_rag_eval_dataset(data_path)

    assert len(items) == 50
    assert items[0].id == "rag-eval-001"
    assert items[-1].id == "rag-eval-050"


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

    assert len(items) == 50
    assert items[16]["id"] == "rag-eval-017"
    assert items[16]["source_preference"] == "pubmed"


def test_run_rag_ad_eval_report_returns_summary_and_item_results():
    report = run_rag_ad_eval_report()

    assert report["summary"]["total_questions"] == 50
    assert report["summary"]["disclaimer_coverage_count"] == 50
    assert report["summary"]["must_not_violation_count"] == 0
    assert report["summary"]["grounding_blocked_count"] == 0
    assert 0 <= report["summary"]["pass_rate"] <= 1
    assert len(report["items"]) == 50

    first = report["items"][0]
    assert first["id"] == "rag-eval-001"
    assert first["source_preference"] == "all"
    assert "cn-ad-gbs-001" in first["expected_literature_hits"]
    assert "chunk-cn-ad-gbs-001-abstract" in first["expected_chunk_hits"]
    assert first["disclaimer_present"] is True
    assert first["violated_must_not_include"] == []
    assert first["grounding_status"] == "skipped"


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

    assert report["summary"]["passed_questions"] >= 46, (
        "RAG eval baseline must hold at >=46/50 (>=92% pass rate) — see"
        " docs/handoffs/2026-05-22-b2-prep-notes.md for the 50-question expansion plan."
        f" Current failing items: "
        f"{[item['id'] for item in report['items'] if not item['passed']]}"
    )
    assert report["summary"]["citation_hit_count"] >= 48
    assert report["summary"]["disclaimer_coverage_count"] == 50
    assert report["summary"]["must_not_violation_count"] == 0


def test_run_rag_ad_eval_report_chunk_hit_count_meets_target():
    report = run_rag_ad_eval_report()

    assert report["summary"]["chunk_hit_count"] >= 45, (
        "chunk_hit_count must stay >=45/50 after the 50-question expansion."
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


def test_rag_eval_report_tags_default_provider_name():
    report = run_rag_ad_eval_report()

    assert report["summary"]["provider_name"] == "deterministic"
    assert all(item["provider_name"] == "deterministic" for item in report["items"])
    assert all(item["grounding_status"] == "skipped" for item in report["items"])


def test_rag_eval_report_forces_deterministic_provider_when_live_provider_is_configured(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("QIYAN_LLM_PROVIDER", "opencode_go")
    live_provider_called = False

    def fail_if_live_provider_is_called(*args, **kwargs):
        nonlocal live_provider_called
        live_provider_called = True
        raise AssertionError("eval report must not fan out to the live LLM provider")

    monkeypatch.setattr(
        "app.services.llm.opencode_go_provider.OpenCodeGoProvider.generate_answer",
        fail_if_live_provider_is_called,
    )

    report = run_rag_ad_eval_report()

    assert live_provider_called is False
    assert os.environ["QIYAN_LLM_PROVIDER"] == "opencode_go"
    assert report["summary"]["provider_name"] == "deterministic"
    assert all(item["provider_name"] == "deterministic" for item in report["items"])


def test_rag_eval_report_passes_provider_overrides_without_mutating_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    synthetic_dataset = tmp_path / "synthetic_eval.json"
    synthetic_dataset.write_text(
        """[
          {
            "id": "synthetic-provider-override",
            "question": "特应性皮炎和肠-脑-皮肤轴之间有什么关系？",
            "source_preference": "all",
            "difficulty": "easy",
            "expected_literature_ids": ["cn-ad-gbs-001"],
            "expected_chunk_ids": [],
            "must_include": ["肠道菌群"],
            "must_not_include": ["确诊建议"],
            "compliance_notes": "synthetic question covers provider override wiring."
          }
        ]""",
        encoding="utf-8",
    )
    monkeypatch.setattr(eval_service, "_DATA_PATH", synthetic_dataset)
    monkeypatch.setenv("QIYAN_LLM_PROVIDER", "opencode_go")
    monkeypatch.setenv("QIYAN_RETRIEVAL_PROVIDER", "vector")
    actual_answer_question = eval_service.answer_question

    def fake_answer_question(
        question: str,
        source: str = "all",
        top_k: int = 2,
        *,
        llm_provider_name: str | None,
        retrieval_provider_name: str | None,
    ):
        assert question == "特应性皮炎和肠-脑-皮肤轴之间有什么关系？"
        assert source == "all"
        assert top_k == 3
        assert llm_provider_name == "deterministic"
        assert retrieval_provider_name == "hybrid"
        assert os.environ["QIYAN_LLM_PROVIDER"] == "opencode_go"
        assert os.environ["QIYAN_RETRIEVAL_PROVIDER"] == "vector"
        return actual_answer_question(
            question,
            source=source,
            top_k=top_k,
            llm_provider_name=llm_provider_name,
            retrieval_provider_name=retrieval_provider_name,
        )

    monkeypatch.setattr(eval_service, "answer_question", fake_answer_question)

    report = run_rag_ad_eval_report(strategy="hybrid")

    assert report["summary"]["provider_name"] == "deterministic"
    assert report["summary"]["retrieval_strategy"] == "hybrid"
    assert report["summary"]["total_questions"] == 1


def test_rag_eval_report_default_strategy_is_keyword():
    report = run_rag_ad_eval_report()
    assert report["summary"]["retrieval_strategy"] == "keyword"
    assert report["summary"]["pass_rate"] >= 0.90


def test_rag_eval_report_explicit_keyword_matches_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("QIYAN_RETRIEVAL_PROVIDER", raising=False)
    default_report = run_rag_ad_eval_report()
    explicit_report = run_rag_ad_eval_report(strategy="keyword")
    assert explicit_report["summary"]["pass_rate"] == default_report["summary"]["pass_rate"]
    assert explicit_report["summary"]["retrieval_strategy"] == "keyword"


def test_rag_eval_report_hybrid_with_hashing_backend_meets_relaxed_threshold(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("QIYAN_EMBEDDING_BACKEND", "hashing")
    report = run_rag_ad_eval_report(strategy="hybrid")
    assert report["summary"]["retrieval_strategy"] == "hybrid"
    assert report["summary"]["pass_rate"] >= 0.86, (
        "Hybrid + hashing backend should still clear the relaxed 86% bar (bge"
        " gets the full ≥90%). Failing items:"
        f" {[item['id'] for item in report['items'] if not item['passed']]}"
    )


def test_run_grounding_semantic_separation_reports_confusion_matrix():
    report = run_grounding_semantic_separation(0.40, backend_name="hashing")

    assert report["backend_name"] == "hashing"
    assert report["faithful_total"] == report["hallucinated_total"]
    assert (
        report["accepted_faithful"] + report["false_rejected_faithful"] == report["faithful_total"]
    )
    assert (
        report["rejected_hallucinated"] + report["false_accepted_hallucinated"]
        == report["hallucinated_total"]
    )
    assert report["false_rejected_faithful"] == 0
    assert report["paired_separation"] == report["paired_total"]
