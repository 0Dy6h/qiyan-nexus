from fastapi.testclient import TestClient

from app.main import app


def test_cors_allows_local_frontend_origin():
    client = TestClient(app)

    response = client.options(
        "/api/literature/search?q=特应性皮炎",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_allows_internal_preview_frontend_port():
    """换端口试用（run-internal-preview.ps1 -FrontendPort 3100）也要能直连后端。"""
    client = TestClient(app)

    response = client.options(
        "/api/literature/search?q=特应性皮炎",
        headers={
            "Origin": "http://127.0.0.1:3100",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3100"


def test_cors_rejects_unknown_origin():
    client = TestClient(app)

    response = client.options(
        "/api/literature/search?q=特应性皮炎",
        headers={
            "Origin": "http://evil.example.com:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.headers.get("access-control-allow-origin") != "http://evil.example.com:3000"
