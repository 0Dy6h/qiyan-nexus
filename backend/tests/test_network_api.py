from fastapi.testclient import TestClient

from app.main import app


def test_network_analyze_endpoint_creates_task():
    client = TestClient(app)

    response = client.post(
        "/api/network/analyze",
        json={
            "query": "消风散",
            "analysis_type": "formula",
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["progress"] == 0
    assert payload["task_id"].startswith("network-")


def test_network_result_endpoint_returns_progress_then_completed_result():
    client = TestClient(app)

    create_response = client.post(
        "/api/network/analyze",
        json={
            "query": "黄芪",
            "analysis_type": "herb",
        },
    )
    assert create_response.status_code == 202
    task_id = create_response.json()["task_id"]

    first_poll = client.get(f"/api/network/result/{task_id}")
    assert first_poll.status_code == 200
    first_payload = first_poll.json()
    assert first_payload["status"] == "running"
    assert first_payload["progress"] == 60
    assert first_payload["result"] is None

    second_poll = client.get(f"/api/network/result/{task_id}")
    assert second_poll.status_code == 200
    second_payload = second_poll.json()
    assert second_payload["status"] == "completed"
    assert second_payload["progress"] == 100
    assert second_payload["result"] is not None
    assert second_payload["result"]["analysis_type"] == "herb"
    assert second_payload["result"]["query"] == "黄芪"
    assert len(second_payload["result"]["chains"]) >= 1


def test_network_result_endpoint_keeps_returning_completed_mock_result_after_completion():
    client = TestClient(app)

    create_response = client.post(
        "/api/network/analyze",
        json={
            "query": "白鲜皮",
            "analysis_type": "herb",
        },
    )
    assert create_response.status_code == 202
    task_id = create_response.json()["task_id"]

    client.get(f"/api/network/result/{task_id}")
    completed_response = client.get(f"/api/network/result/{task_id}")
    repeated_response = client.get(f"/api/network/result/{task_id}")

    assert completed_response.status_code == 200
    assert repeated_response.status_code == 200
    assert completed_response.json()["status"] == "completed"
    assert repeated_response.json()["status"] == "completed"
    assert repeated_response.json()["result"]["query"] == "白鲜皮"


def test_network_result_endpoint_returns_404_for_unknown_task():
    client = TestClient(app)

    response = client.get("/api/network/result/network-missing-task")

    assert response.status_code == 404
    assert response.json() == {"detail": "Network analysis task not found"}


def test_network_analyze_endpoint_rejects_empty_query():
    client = TestClient(app)

    response = client.post(
        "/api/network/analyze",
        json={
            "query": "",
            "analysis_type": "formula",
        },
    )

    assert response.status_code == 422
