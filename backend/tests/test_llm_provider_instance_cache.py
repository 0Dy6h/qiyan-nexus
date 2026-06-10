"""Test that select_provider caches instances and reuses http_client / anthropic.Client."""

from app.services.llm.provider import select_provider


def test_select_provider_caches_instances_across_calls(monkeypatch):
    """Repeated calls to select_provider with the same name return the same instance."""
    monkeypatch.setenv("QIYAN_LLM_PROVIDER", "deterministic")

    first = select_provider()
    second = select_provider()

    assert first is second


def test_select_provider_caches_opencode_go_provider(monkeypatch):
    """OpenCodeGoProvider is cached so its http_client is reused."""
    monkeypatch.setenv("QIYAN_LLM_PROVIDER", "opencode_go")

    first = select_provider("opencode_go")
    second = select_provider("opencode_go")

    assert first is second


def test_select_provider_caches_anthropic_provider(monkeypatch):
    """AnthropicProvider is cached so its client is reused."""
    monkeypatch.setenv("QIYAN_LLM_PROVIDER", "anthropic")

    first = select_provider("anthropic")
    second = select_provider("anthropic")

    assert first is second


def test_opencode_go_lazy_http_client_creation(monkeypatch):
    """OpenCodeGoProvider without injected http_client creates one on first use."""
    from app.services.llm.opencode_go_provider import OpenCodeGoProvider

    provider = OpenCodeGoProvider()

    # No client initially
    assert provider._http_client is None

    # First call to _ensure_http_client creates it
    client1 = provider._ensure_http_client()
    assert client1 is not None

    # Second call returns the same client
    client2 = provider._ensure_http_client()
    assert client1 is client2


def test_anthropic_lazy_client_creation(monkeypatch):
    """AnthropicProvider without injected client creates one on first use."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    from app.core.config import get_settings

    get_settings.cache_clear()

    try:
        from app.services.llm.anthropic_provider import AnthropicProvider

        provider = AnthropicProvider()

        # No client initially
        assert provider._client is None

        # First call to _ensure_client creates it
        client1 = provider._ensure_client(get_settings())
        assert client1 is not None

        # Second call returns the same client
        client2 = provider._ensure_client(get_settings())
        assert client1 is client2
    finally:
        get_settings.cache_clear()
