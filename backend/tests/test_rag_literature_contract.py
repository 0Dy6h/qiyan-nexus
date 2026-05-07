from fastapi.testclient import TestClient

from app.main import app


def test_rag_citation_literature_ids_resolve_to_literature_detail():
    client = TestClient(app)

    rag_response = client.post(
        "/api/rag/answer",
        json={"question": "特应性皮炎和肠-脑-皮肤轴有什么关系？"},
    )

    assert rag_response.status_code == 200
    citations = rag_response.json()["citations"]
    assert citations
    for citation in citations:
        detail_response = client.get(f"/api/literature/{citation['literature_id']}")

        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["id"] == citation["literature_id"]
        assert detail["title"] == citation["title"]
        assert detail["source"] == citation["source"]
        assert detail["snippet"] == citation["snippet"]
