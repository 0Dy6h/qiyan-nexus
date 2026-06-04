"""Integration tests for POST /api/rag/answer/export endpoint."""

from fastapi.testclient import TestClient

from app.main import app

DISCLAIMER = "非诊断结论、需结合临床。"

_SAMPLE_ANSWER_PAYLOAD: dict[str, object] = {
    "question": "特应性皮炎和肠-脑-皮肤轴有什么关系？",
    "answer": "基于当前检索到的证据片段，已优先返回与问题最相关的文献。",
    "disclaimer": DISCLAIMER,
    "answered_at": "2026-06-04T07:42:11.123456+00:00",
    "provider_name": "deterministic",
    "input_tokens": None,
    "output_tokens": None,
    "retrieval": {
        "applied_source": "all",
        "applied_top_k": 2,
        "available_citation_count": 16,
        "strategy": "keyword",
    },
    "grounding": {
        "status": "skipped",
        "policy": "structured_claim_refs_v3",
        "checked": False,
        "blocked_reason": None,
        "allowed_evidence_refs": ["chunk-cn-ad-gbs-001-abstract"],
        "matched_evidence_refs": [],
        "unsupported_evidence_refs": [],
        "claim_count": 0,
        "cited_claim_count": 0,
        "structured_claims": [],
        "provider_native_grounding": False,
        "tool_name": None,
        "tool_call_count": 0,
    },
    "citations": [
        {
            "literature_id": "cn-ad-gbs-001",
            "chunk_id": "chunk-cn-ad-gbs-001-abstract",
            "title": "肠-脑-皮肤轴与特应性皮炎中医证候研究",
            "source": "CNKI curated AD sample",
            "snippet": "围绕特应性皮炎、肠-脑-皮肤轴与中医证候关联进行综述。",
            "quote": None,
            "reason": "gut_skin_axis, tcm_syndrome",
            "confidence": 0.86,
            "source_type": "sample",
            "pdf_upload_id": None,
            "related_entity_ids": [],
        }
    ],
    "sli": None,
}


def test_rag_answer_export_endpoint_returns_plain_text_markdown() -> None:
    client = TestClient(app)

    response = client.post("/api/rag/answer/export", json=_SAMPLE_ANSWER_PAYLOAD)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "charset=utf-8" in response.headers["content-type"]

    body = response.text
    assert body.startswith("# Qiyan Nexus RAG 答案导出")
    assert DISCLAIMER in body
    assert "特应性皮炎和肠-脑-皮肤轴有什么关系？" in body
    assert "literature_id：cn-ad-gbs-001" in body
    assert "2026-06-04T07:42:11.123456+00:00" in body
    assert "应用来源：全部文献" in body
    assert "应用 top_k：2" in body
    assert "Provider：deterministic" in body


def test_rag_answer_export_endpoint_handles_empty_citations() -> None:
    client = TestClient(app)

    payload = dict(_SAMPLE_ANSWER_PAYLOAD)
    payload["citations"] = []

    response = client.post("/api/rag/answer/export", json=payload)

    assert response.status_code == 200
    body = response.text
    assert "（当前回答没有可核对的引用证据。）" in body
    assert DISCLAIMER in body


def test_rag_answer_export_endpoint_rejects_malformed_payload() -> None:
    client = TestClient(app)

    response = client.post("/api/rag/answer/export", json={"question": "incomplete"})

    assert response.status_code == 422
