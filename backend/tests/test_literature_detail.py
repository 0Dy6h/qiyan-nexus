from fastapi.testclient import TestClient

from app.main import app


def test_literature_detail_returns_item_by_id():
    client = TestClient(app)

    response = client.get("/api/literature/cn-ad-gbs-001")

    assert response.status_code == 200
    assert response.json() == {
        "id": "cn-ad-gbs-001",
        "title": "肠-脑-皮肤轴与特应性皮炎中医证候研究",
        "language": "zh",
        "source_type": "cn_literature",
        "source": "中文本地样本文献库",
        "year": 2025,
        "snippet": "围绕特应性皮炎、肠-脑-皮肤轴与中医证候关联进行综述。",
    }


def test_literature_detail_returns_404_for_unknown_id():
    client = TestClient(app)

    response = client.get("/api/literature/unknown")

    assert response.status_code == 404
    assert response.json() == {"detail": "Literature item not found"}
