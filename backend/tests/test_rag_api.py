from fastapi.testclient import TestClient

from app.main import app


DISCLAIMER = "非诊断结论、需结合临床。"


def test_rag_answer_endpoint_returns_mock_answer_with_citations():
    client = TestClient(app)

    response = client.post(
        "/api/rag/answer",
        json={"question": "特应性皮炎和肠-脑-皮肤轴有什么关系？"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "question": "特应性皮炎和肠-脑-皮肤轴有什么关系？",
        "answer": "基于当前样本文献，特应性皮炎（AD）可从肠-脑-皮肤轴、皮肤屏障功能和免疫通路三个角度组织证据。此接口目前只返回 mock RAG 结果，用于验证引用卡片与合规文案。",
        "disclaimer": DISCLAIMER,
        "citations": [
            {
                "literature_id": "cn-ad-gbs-001",
                "title": "肠-脑-皮肤轴与特应性皮炎中医证候研究",
                "source": "中文本地样本文献库",
                "snippet": "围绕特应性皮炎、肠-脑-皮肤轴与中医证候关联进行综述。",
                "confidence": 0.86,
            },
            {
                "literature_id": "en-ad-barrier-001",
                "title": "Atopic dermatitis, skin barrier dysfunction, and immune pathways",
                "source": "PubMed sample",
                "snippet": "A sample English literature record for AD barrier and immune pathway retrieval.",
                "confidence": 0.74,
            },
        ],
    }


def test_rag_answer_endpoint_rejects_empty_question():
    client = TestClient(app)

    response = client.post("/api/rag/answer", json={"question": ""})

    assert response.status_code == 422
