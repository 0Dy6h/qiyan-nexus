from fastapi.testclient import TestClient

from app.main import app

DISCLAIMER = "非诊断结论、需结合临床。"


def test_rag_answer_endpoint_returns_ranked_citations_for_gut_skin_axis_question():
    client = TestClient(app)

    response = client.post(
        "/api/rag/answer",
        json={"question": "特应性皮炎和肠-脑-皮肤轴有什么关系？"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["question"] == "特应性皮炎和肠-脑-皮肤轴有什么关系？"
    assert payload["disclaimer"] == DISCLAIMER
    assert payload["retrieval"] == {
        "applied_source": "all",
        "applied_top_k": 2,
        "available_citation_count": 17,
    }
    assert payload["citations"][0]["literature_id"] == "cn-ad-gbs-001"
    assert payload["citations"][1]["literature_id"] == "cn-ad-microbiome-003"
    assert payload["citations"][0]["chunk_id"] == "chunk-cn-ad-gbs-001-abstract"
    assert "deterministic retrieval" in payload["answer"]
    assert isinstance(payload["answered_at"], str)
    assert payload["answered_at"].endswith("+00:00")


def test_rag_answer_endpoint_rejects_empty_question():
    client = TestClient(app)

    response = client.post("/api/rag/answer", json={"question": ""})

    assert response.status_code == 422


def test_rag_answer_endpoint_limits_citations_by_top_k():
    client = TestClient(app)

    response = client.post(
        "/api/rag/answer",
        json={"question": "特应性皮炎", "top_k": 1},
    )

    assert response.status_code == 200
    assert len(response.json()["citations"]) == 1
    assert response.json()["citations"][0]["literature_id"] == "cn-ad-gbs-001"


def test_rag_answer_endpoint_filters_citations_by_source():
    client = TestClient(app)

    response = client.post(
        "/api/rag/answer",
        json={"question": "特应性皮炎 肠道菌群", "source": "pubmed"},
    )

    assert response.status_code == 200
    citations = response.json()["citations"]
    assert len(citations) == 2
    assert [citation["literature_id"] for citation in citations] == [
        "pmid-40100002",
        "pmid-40100007",
    ]


def test_rag_answer_endpoint_rejects_invalid_source():
    client = TestClient(app)

    response = client.post(
        "/api/rag/answer",
        json={"question": "特应性皮炎", "source": "invalid"},
    )

    assert response.status_code == 422


def test_rag_answer_endpoint_rejects_zero_top_k():
    client = TestClient(app)

    response = client.post(
        "/api/rag/answer",
        json={"question": "特应性皮炎", "top_k": 0},
    )

    assert response.status_code == 422


def test_rag_answer_endpoint_returns_retrieval_metadata_for_positive_matches():
    client = TestClient(app)

    response = client.post(
        "/api/rag/answer",
        json={"question": "特应性皮炎 肠道菌群", "source": "pubmed", "top_k": 1},
    )

    assert response.status_code == 200
    assert response.json()["retrieval"] == {
        "applied_source": "pubmed",
        "applied_top_k": 1,
        "available_citation_count": 2,
    }
