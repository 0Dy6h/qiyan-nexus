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

RESEARCH_PROTOCOL = {
    "disease": "atopic_dermatitis",
    "phenotype": "特应性皮炎伴 2 型炎症与皮肤屏障异常",
    "species": "Homo sapiens",
    "evidence_policy": "direct_human_first",
    "query_date": "2026-07-11",
}


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


def test_protected_network_task_creation_requires_reviewer_identity(monkeypatch, reload_app):
    monkeypatch.setenv("QIYAN_ACCESS_TOKENS", "alpha")
    client = reload_app()

    response = client.post(
        "/api/network/analyze",
        json={"query": "黄芪", "analysis_type": "herb", "research_protocol": RESEARCH_PROTOCOL},
        headers={"X-Access-Token": "alpha"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "missing or invalid X-Qiyan-Reviewer"}


def test_protected_network_task_is_visible_only_to_its_reviewer(monkeypatch, reload_app):
    monkeypatch.setenv("QIYAN_ACCESS_TOKENS", "alpha")
    client = reload_app()
    reviewer_a_headers = {
        "X-Access-Token": "alpha",
        "X-Qiyan-Reviewer": "reviewer-a",
    }
    reviewer_b_headers = {
        "X-Access-Token": "alpha",
        "X-Qiyan-Reviewer": "reviewer-b",
    }

    create_response = client.post(
        "/api/network/analyze",
        json={"query": "黄芪", "analysis_type": "herb", "research_protocol": RESEARCH_PROTOCOL},
        headers=reviewer_a_headers,
    )
    assert create_response.status_code == 202
    task_id = create_response.json()["task_id"]

    foreign_response = client.get(
        f"/api/network/result/{task_id}",
        headers=reviewer_b_headers,
    )
    foreign_report_response = client.get(
        f"/api/network/result/{task_id}/report",
        headers=reviewer_b_headers,
    )
    owner_response = client.get(
        f"/api/network/result/{task_id}",
        headers=reviewer_a_headers,
    )

    assert foreign_response.status_code == 404
    assert foreign_response.json() == {"detail": "Network analysis task not found"}
    assert foreign_report_response.status_code == 404
    assert foreign_report_response.json() == {"detail": "Network analysis task not found"}
    assert owner_response.status_code == 200
    assert owner_response.json()["task_id"] == task_id


def test_protected_reviewer_identity_must_already_be_canonical(monkeypatch, reload_app):
    monkeypatch.setenv("QIYAN_ACCESS_TOKENS", "alpha")
    client = reload_app()

    response = client.post(
        "/api/network/analyze",
        json={"query": "黄芪", "analysis_type": "herb", "research_protocol": RESEARCH_PROTOCOL},
        headers={
            "X-Access-Token": "alpha",
            "X-Qiyan-Reviewer": "Reviewer-A",
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "missing or invalid X-Qiyan-Reviewer"}


def test_open_mode_ignores_untrusted_reviewer_header(monkeypatch, reload_app):
    monkeypatch.delenv("QIYAN_ACCESS_TOKENS", raising=False)
    client = reload_app()

    create_response = client.post(
        "/api/network/analyze",
        json={"query": "黄芪", "analysis_type": "herb", "research_protocol": RESEARCH_PROTOCOL},
        headers={"X-Qiyan-Reviewer": "reviewer-a"},
    )
    assert create_response.status_code == 202
    task_id = create_response.json()["task_id"]

    response = client.get(
        f"/api/network/result/{task_id}",
        headers={"X-Qiyan-Reviewer": "reviewer-b"},
    )

    assert response.status_code == 200
    assert response.json()["task_id"] == task_id


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


def test_access_control_401_response_carries_cors_headers_for_browser_origin(
    monkeypatch, reload_app
):
    """W1 from security review: a 401 from the access-control middleware must
    still carry Access-Control-Allow-Origin when the request came from an
    allowed Origin. Otherwise the browser turns the rejection into an opaque
    CORS error instead of a readable 401, blocking closed-beta debugging."""

    monkeypatch.setenv("QIYAN_ACCESS_TOKENS", "alpha")
    client = reload_app()

    response = client.get(
        "/api/literature/search",
        params={"q": "AD"},
        headers={"Origin": "http://localhost:3000"},
    )

    assert response.status_code == 401
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_install_access_token_middleware_logs_open_mode_when_env_unset(monkeypatch, caplog):
    """W2 from security review: deploying with QIYAN_ACCESS_TOKENS unset must
    leave a startup log line, so a forgotten env doesn't silently open the API."""

    import importlib
    import logging

    monkeypatch.delenv("QIYAN_ACCESS_TOKENS", raising=False)

    with caplog.at_level(logging.INFO, logger="app.core.access_control"):
        import app.main as main_module

        importlib.reload(main_module)

    messages = [record.getMessage() for record in caplog.records]
    assert any("disabled" in m.lower() and "open" in m.lower() for m in messages), messages

    importlib.reload(main_module)


def test_install_access_token_middleware_logs_token_count_when_env_set(monkeypatch, caplog):
    """W2 from security review: when tokens are configured, the startup log
    should make that clear without leaking the actual token values."""

    import importlib
    import logging

    monkeypatch.setenv("QIYAN_ACCESS_TOKENS", "alpha,beta,gamma")

    with caplog.at_level(logging.INFO, logger="app.core.access_control"):
        import app.main as main_module

        importlib.reload(main_module)

    messages = [record.getMessage() for record in caplog.records]
    assert any("3" in m and "enabled" in m.lower() for m in messages), messages
    # token values must never appear in the log line
    assert not any("alpha" in m or "beta" in m or "gamma" in m for m in messages), messages

    monkeypatch.delenv("QIYAN_ACCESS_TOKENS", raising=False)
    importlib.reload(main_module)
