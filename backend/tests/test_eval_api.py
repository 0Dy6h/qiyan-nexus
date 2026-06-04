from fastapi.testclient import TestClient

from app.main import app


def test_rag_ad_eval_endpoint_returns_50_items():
    client = TestClient(app)

    response = client.get("/api/evals/rag-ad")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 50
    assert payload["items"][0]["id"] == "rag-eval-001"
    assert payload["items"][-1]["id"] == "rag-eval-050"


def test_rag_ad_eval_endpoint_exposes_expected_contract_fields():
    client = TestClient(app)

    response = client.get("/api/evals/rag-ad")

    assert response.status_code == 200
    first = response.json()["items"][0]
    assert first["expected_literature_ids"] == [
        "cn-ad-gbs-001",
        "cn-ad-microbiome-003",
        "pmid-40100002",
    ]
    assert "肠道菌群" in first["must_include"]
    assert "替代医生诊断" in first["must_not_include"]


def test_rag_ad_eval_report_endpoint_returns_reproducible_summary():
    client = TestClient(app)

    response = client.get("/api/evals/rag-ad/report")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total_questions"] == 50
    assert payload["summary"]["corpus"] == "seed"
    assert payload["summary"]["disclaimer_coverage_count"] == 50
    assert payload["summary"]["must_not_violation_count"] == 0
    assert payload["summary"]["grounding_blocked_count"] == 0
    assert len(payload["items"]) == 50

    first = payload["items"][0]
    assert first["id"] == "rag-eval-001"
    assert first["disclaimer_present"] is True
    assert first["grounding_status"] == "skipped"
    assert "cn-ad-gbs-001" in first["expected_literature_hits"]


def test_rag_ad_eval_report_endpoint_returns_503_when_report_generation_fails(monkeypatch):
    from app.api import eval as eval_api

    def broken_report(**_kwargs) -> dict:
        raise RuntimeError("boom")

    monkeypatch.setattr(eval_api, "run_rag_ad_eval_report", broken_report)
    client = TestClient(app)

    response = client.get("/api/evals/rag-ad/report")

    assert response.status_code == 503
    assert response.json() == {"detail": "RAG eval report unavailable"}


def test_rag_ad_eval_report_endpoint_honours_strategy_query_param(monkeypatch):
    monkeypatch.setenv("QIYAN_EMBEDDING_BACKEND", "hashing")
    client = TestClient(app)

    response = client.get("/api/evals/rag-ad/report", params={"strategy": "hybrid"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["retrieval_strategy"] == "hybrid"


def test_rag_ad_eval_report_endpoint_honours_corpus_query_param():
    client = TestClient(app)

    response = client.get("/api/evals/rag-ad/report", params={"corpus": "runtime"})

    assert response.status_code == 200
    assert response.json()["summary"]["corpus"] == "runtime"


def test_rag_ad_eval_report_endpoint_rejects_unknown_corpus():
    client = TestClient(app)

    response = client.get("/api/evals/rag-ad/report", params={"corpus": "demo"})

    assert response.status_code == 422


def test_rag_ad_eval_report_endpoint_rejects_unknown_strategy():
    client = TestClient(app)

    response = client.get("/api/evals/rag-ad/report", params={"strategy": "bogus"})

    assert response.status_code == 422
