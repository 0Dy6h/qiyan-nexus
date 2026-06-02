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
    assert payload["retrieval"]["applied_source"] == "all"
    assert payload["retrieval"]["applied_top_k"] == 2
    assert payload["retrieval"]["strategy"] == "keyword"
    # After Slice 2 (score-primary sort + cross-lingual token injection),
    # available_citation_count increased because more items now match.
    assert payload["retrieval"]["available_citation_count"] >= 17
    # Slice 7: microbiome-003 edges out gbs-001 as top-1 (see test_rag_service.py for
    # the +14-vs-+7 alias_tag_bonus rationale).
    assert payload["citations"][0]["literature_id"] == "cn-ad-microbiome-003"
    assert payload["citations"][1]["literature_id"] == "cn-ad-gbs-001"
    assert payload["citations"][0]["chunk_id"] == "chunk-cn-ad-microbiome-003-abstract"
    assert "deterministic retrieval" in payload["answer"]
    assert payload["provider_name"] == "deterministic"
    assert payload["grounding"] == {
        "status": "skipped",
        "policy": "structured_claim_refs_v3",
        "checked": False,
        "blocked_reason": None,
        "allowed_evidence_refs": [
            "chunk-cn-ad-microbiome-003-abstract",
            "chunk-cn-ad-gbs-001-abstract",
        ],
        "matched_evidence_refs": [],
        "unsupported_evidence_refs": [],
        "claim_count": 0,
        "cited_claim_count": 0,
        "structured_claims": [],
        "provider_native_grounding": False,
        "tool_name": None,
        "tool_call_count": 0,
        "semantic_threshold": None,
        "min_semantic_score": None,
        "nli_threshold": None,
        "min_entailment_score": None,
    }
    assert payload["input_tokens"] is None
    assert payload["output_tokens"] is None
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
    # After Slice 2, score-primary sort + cross-lingual token injection changes
    # which item ranks first for a bare Chinese query. Pin the deterministic top
    # result (against the seed dataset) so a ranking regression is caught.
    assert response.json()["citations"][0]["literature_id"] == "cn-ad-microbiome-003"


def test_rag_answer_endpoint_filters_citations_by_source():
    client = TestClient(app)

    response = client.post(
        "/api/rag/answer",
        json={"question": "特应性皮炎 肠道菌群", "source": "pubmed"},
    )

    assert response.status_code == 200
    citations = response.json()["citations"]
    assert len(citations) == 2
    # Deterministic order after Slice 2 cross-lingual token injection.
    citation_ids = [citation["literature_id"] for citation in citations]
    assert citation_ids == ["pmid-40100007", "pmid-40100002"]


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
    assert response.json()["retrieval"]["applied_source"] == "pubmed"
    assert response.json()["retrieval"]["applied_top_k"] == 1
    # After Slice 2, cross-lingual token injection increases available_citation_count
    # because more PubMed items now match Chinese query tokens.
    assert response.json()["retrieval"]["available_citation_count"] >= 2
    assert response.json()["retrieval"]["strategy"] == "keyword"
