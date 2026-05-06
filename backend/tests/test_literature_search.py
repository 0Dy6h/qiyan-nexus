from fastapi.testclient import TestClient

from app.main import app


def test_literature_search_returns_mock_results_for_keyword():
    client = TestClient(app)

    response = client.get("/api/literature/search", params={"q": "特应性皮炎"})

    assert response.status_code == 200
    assert response.json() == {
        "query": "特应性皮炎",
        "total": 2,
        "items": [
            {
                "id": "cn-ad-gbs-001",
                "title": "肠-脑-皮肤轴与特应性皮炎中医证候研究",
                "language": "zh",
                "source": "中文本地样本文献库",
                "year": 2025,
                "snippet": "围绕特应性皮炎、肠-脑-皮肤轴与中医证候关联进行综述。",
            },
            {
                "id": "en-ad-barrier-001",
                "title": "Atopic dermatitis, skin barrier dysfunction, and immune pathways",
                "language": "en",
                "source": "PubMed sample",
                "year": 2024,
                "snippet": "A sample English literature record for AD barrier and immune pathway retrieval.",
            },
        ],
    }


def test_literature_search_requires_non_empty_query():
    client = TestClient(app)

    response = client.get("/api/literature/search", params={"q": ""})

    assert response.status_code == 422
