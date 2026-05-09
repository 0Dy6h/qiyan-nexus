from fastapi.testclient import TestClient

from app.main import app


def test_rag_ad_eval_endpoint_returns_20_items():
    client = TestClient(app)

    response = client.get("/api/evals/rag-ad")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 20
    assert payload["items"][0]["id"] == "rag-eval-001"
    assert payload["items"][-1]["id"] == "rag-eval-020"


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
