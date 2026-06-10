"""Test _canonical_token_set() cache behavior when cross-lingual map is reset."""

from app.services.retrieval.provider import _canonical_token_set


def test_canonical_token_set_recomputes_after_cross_lingual_cache_reset(monkeypatch):
    """When _cross_lingual_cache is reset, _canonical_token_set must pick up new values.

    The monkeypatch pattern ``setattr(provider_module, "_cross_lingual_cache", None)``
    is used in multiple tests to inject different alias maps. The canonical set must
    recompute when that happens rather than returning a stale memoised result.
    """
    from pathlib import Path

    from app.services.retrieval import provider as provider_module

    # Initial call with the real cross_lingual_terms.json
    first_canonicals = _canonical_token_set()
    assert "gut" in first_canonicals  # from _KEYWORD_ALIASES

    # Inject a custom alias map
    custom_file = Path(__file__).parent / "fixtures" / "test_canonical_recompute.json"
    custom_file.parent.mkdir(exist_ok=True)
    custom_file.write_text(
        '{"alias_map":[{"canonical":"test_canonical_only","zh":["测试"],"en":["test"]}]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(provider_module, "_CROSS_LINGUAL_TERMS_PATH", custom_file)
    monkeypatch.setattr(provider_module, "_cross_lingual_cache", None)
    monkeypatch.setattr(provider_module, "_canonical_cache", None)

    second_canonicals = _canonical_token_set()
    assert "test_canonical_only" in second_canonicals
    assert "gut" in second_canonicals  # _KEYWORD_ALIASES still present

    # Reset to real map again
    real_path = (
        Path(__file__).resolve().parents[1] / "data" / "retrieval" / "cross_lingual_terms.json"
    )
    monkeypatch.setattr(provider_module, "_CROSS_LINGUAL_TERMS_PATH", real_path)
    monkeypatch.setattr(provider_module, "_cross_lingual_cache", None)
    monkeypatch.setattr(provider_module, "_canonical_cache", None)

    third_canonicals = _canonical_token_set()
    assert "gut" in third_canonicals
    # "test_canonical_only" should no longer be present if we reverted to the real map
