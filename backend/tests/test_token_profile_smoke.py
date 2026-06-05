import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def token_client(monkeypatch):
    monkeypatch.setenv("QIYAN_ACCESS_TOKENS", "dev-token")
    import app.main as main_module

    importlib.reload(main_module)
    client = TestClient(main_module.app)
    yield client

    monkeypatch.delenv("QIYAN_ACCESS_TOKENS", raising=False)
    importlib.reload(main_module)


def test_token_profile_blocks_missing_header_and_allows_core_preview_flows(token_client):
    unauthorized = token_client.get("/api/literature/search", params={"q": "特应性皮炎"})
    assert unauthorized.status_code == 401

    headers = {"X-Access-Token": "dev-token"}

    literature = token_client.get(
        "/api/literature/search",
        params={"q": "特应性皮炎", "source": "all"},
        headers=headers,
    )
    assert literature.status_code == 200
    assert literature.json()["total"] > 0

    rag = token_client.post(
        "/api/rag/answer",
        json={"question": "特应性皮炎和皮肤屏障有什么关系？", "source": "all", "top_k": 2},
        headers=headers,
    )
    assert rag.status_code == 200
    rag_payload = rag.json()
    assert rag_payload["provider_name"] == "deterministic"
    assert rag_payload["disclaimer"] == "非诊断结论、需结合临床。"

    rag_export = token_client.post(
        "/api/rag/answer/export",
        json=rag_payload,
        headers=headers,
    )
    assert rag_export.status_code == 200
    assert rag_export.text.startswith("# Qiyan Nexus RAG 答案导出")

    accepted = token_client.post(
        "/api/network/analyze",
        json={"query": "消风散", "analysis_type": "formula"},
        headers=headers,
    )
    assert accepted.status_code == 202
    task_id = accepted.json()["task_id"]

    first_poll = token_client.get(f"/api/network/result/{task_id}", headers=headers)
    assert first_poll.status_code == 200
    assert first_poll.json()["status"] == "running"

    result = token_client.get(f"/api/network/result/{task_id}", headers=headers)
    assert result.status_code == 200
    assert result.json()["result"]["disclaimer"] == "非诊断结论、需结合临床。"

    report = token_client.get(f"/api/network/result/{task_id}/report", headers=headers)
    assert report.status_code == 200
    assert report.text.startswith("# Qiyan Nexus 网络药理学报告导出")
