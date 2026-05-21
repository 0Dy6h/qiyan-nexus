"""Tests for the X-Access-Token middleware.

A2 minimum access control: when ``QIYAN_ACCESS_TOKENS`` is empty the API is
open (dev default). When it is configured to a comma-separated allowlist, every
non-trivial path must present a matching ``X-Access-Token`` header or get 401.
``/health`` and CORS preflight (``OPTIONS``) are always allowed through.
"""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def reload_app(monkeypatch):
    """Reload app.main after env mutation so the middleware re-reads tokens."""

    def _reload() -> TestClient:
        import app.main as main_module

        importlib.reload(main_module)
        return TestClient(main_module.app)

    yield _reload

    # restore module state for downstream tests: clear env first so the reload
    # picks up an empty allowlist (open mode), then reload.
    monkeypatch.delenv("QIYAN_ACCESS_TOKENS", raising=False)
    import app.main as main_module

    importlib.reload(main_module)


def test_access_control_open_when_tokens_env_unset(monkeypatch, reload_app):
    monkeypatch.delenv("QIYAN_ACCESS_TOKENS", raising=False)
    client = reload_app()

    response = client.get("/api/literature/search", params={"q": "特应性皮炎"})

    assert response.status_code == 200


def test_access_control_returns_401_when_token_missing(monkeypatch, reload_app):
    monkeypatch.setenv("QIYAN_ACCESS_TOKENS", "alpha,beta")
    client = reload_app()

    response = client.get("/api/literature/search", params={"q": "特应性皮炎"})

    assert response.status_code == 401
    payload = response.json()
    assert payload["detail"] == "missing or invalid X-Access-Token"


def test_access_control_returns_401_when_token_invalid(monkeypatch, reload_app):
    monkeypatch.setenv("QIYAN_ACCESS_TOKENS", "alpha,beta")
    client = reload_app()

    response = client.get(
        "/api/literature/search",
        params={"q": "特应性皮炎"},
        headers={"X-Access-Token": "gamma"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "missing or invalid X-Access-Token"


def test_access_control_returns_200_with_matching_token(monkeypatch, reload_app):
    monkeypatch.setenv("QIYAN_ACCESS_TOKENS", "alpha,beta")
    client = reload_app()

    response = client.get(
        "/api/literature/search",
        params={"q": "特应性皮炎"},
        headers={"X-Access-Token": "beta"},
    )

    assert response.status_code == 200


def test_access_control_skips_health_endpoint(monkeypatch, reload_app):
    monkeypatch.setenv("QIYAN_ACCESS_TOKENS", "alpha")
    client = reload_app()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_access_control_allows_cors_preflight_without_token(monkeypatch, reload_app):
    monkeypatch.setenv("QIYAN_ACCESS_TOKENS", "alpha")
    client = reload_app()

    response = client.options(
        "/api/literature/search?q=特应性皮炎",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_access_control_strips_whitespace_in_token_list(monkeypatch, reload_app):
    monkeypatch.setenv("QIYAN_ACCESS_TOKENS", " alpha ,  beta , ")
    client = reload_app()

    ok = client.get(
        "/api/literature/search",
        params={"q": "特应性皮炎"},
        headers={"X-Access-Token": "alpha"},
    )
    bad = client.get(
        "/api/literature/search",
        params={"q": "特应性皮炎"},
        headers={"X-Access-Token": " alpha "},
    )

    assert ok.status_code == 200
    assert bad.status_code == 401
