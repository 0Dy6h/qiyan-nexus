from pathlib import Path

from app.schemas.eval import load_rag_eval_dataset
from app.services.eval import get_rag_eval_questions


def test_load_rag_eval_dataset_returns_20_questions():
    data_path = Path(__file__).resolve().parents[1] / "data" / "evals" / "rag_ad_eval_questions.json"

    items = load_rag_eval_dataset(data_path)

    assert len(items) == 20
    assert items[0].id == "rag-eval-001"
    assert items[-1].id == "rag-eval-020"


def test_rag_eval_questions_cover_literature_and_compliance_fields():
    data_path = Path(__file__).resolve().parents[1] / "data" / "evals" / "rag_ad_eval_questions.json"

    items = load_rag_eval_dataset(data_path)
    first = items[0]

    assert first.expected_literature_ids == ["cn-ad-gbs-001", "cn-ad-microbiome-003", "pmid-40100002"]
    assert "肠道菌群" in first.must_include
    assert "替代医生诊断" in first.must_not_include
    assert "不能给出诊断结论" in first.compliance_notes


def test_get_rag_eval_questions_returns_serializable_payload():
    items = get_rag_eval_questions()

    assert len(items) == 20
    assert items[16]["id"] == "rag-eval-017"
    assert items[16]["source_preference"] == "pubmed"
