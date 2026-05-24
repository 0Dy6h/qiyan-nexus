"""Slice 1 tests for the RetrievalProvider Protocol + KeywordRetrievalProvider.

Mirrors the test shape of ``tests/test_llm_provider.py``: env-driven selection,
fallback on misconfig, and a behaviour-parity check against the production
seed data so the keyword path reproduces the pre-refactor ranking.
"""

import logging

from app.repositories.chunk import InMemoryChunkRepository
from app.repositories.literature import InMemoryLiteratureRepository
from app.repositories.runtime_storage import (
    resolve_chunk_storage_path,
    resolve_literature_storage_path,
)
from app.services.retrieval.provider import (
    DEFAULT_RETRIEVAL_PROVIDER_NAME,
    RETRIEVAL_PROVIDER_ENV_VAR,
    KeywordRetrievalProvider,
    RetrievalProvider,
    select_retrieval_provider,
)


def _load_seed():
    items = InMemoryLiteratureRepository(resolve_literature_storage_path()).list_items()
    chunk_repo = InMemoryChunkRepository(resolve_chunk_storage_path())
    chunks_by_item = {item.id: chunk_repo.list_chunks_by_literature_id(item.id) for item in items}
    return items, chunks_by_item


def test_keyword_provider_reproduces_existing_ranking_for_zh_question():
    items, chunks_by_item = _load_seed()
    provider = KeywordRetrievalProvider()

    candidates = provider.rank(
        "特应性皮炎和肠-脑-皮肤轴有什么关系？",
        items,
        chunks_by_item,
        preferred_source_type="cn_literature",
    )

    top_two = [(c.item.id, c.chunk.chunk_id if c.chunk else None) for c in candidates[:2]]
    assert top_two[0] == ("cn-ad-gbs-001", "chunk-cn-ad-gbs-001-abstract")
    assert top_two[1][0] == "cn-ad-microbiome-003"


def test_keyword_provider_reproduces_pubmed_priority_for_english_question():
    items, chunks_by_item = _load_seed()
    provider = KeywordRetrievalProvider()

    candidates = provider.rank(
        "atopic dermatitis barrier",
        items,
        chunks_by_item,
        preferred_source_type="pubmed",
    )

    top_two_ids = [c.item.id for c in candidates[:2]]
    assert top_two_ids[0] == "pmid-40100001"
    assert top_two_ids[1] == "pmid-40100006"


def test_keyword_provider_satisfies_retrieval_provider_protocol():
    provider = KeywordRetrievalProvider()
    assert isinstance(provider, RetrievalProvider)
    assert provider.name == "keyword"


def test_select_retrieval_provider_defaults_to_keyword(monkeypatch):
    monkeypatch.delenv(RETRIEVAL_PROVIDER_ENV_VAR, raising=False)
    provider = select_retrieval_provider()
    assert provider.name == DEFAULT_RETRIEVAL_PROVIDER_NAME
    assert isinstance(provider, KeywordRetrievalProvider)


def test_select_retrieval_provider_falls_back_for_invalid_value(monkeypatch, caplog):
    monkeypatch.setenv(RETRIEVAL_PROVIDER_ENV_VAR, "nonexistent-strategy")
    with caplog.at_level(logging.WARNING):
        provider = select_retrieval_provider()
    assert isinstance(provider, KeywordRetrievalProvider)
    assert any(
        "nonexistent-strategy" in record.message or "Unknown" in record.message
        for record in caplog.records
    )


def test_select_retrieval_provider_accepts_explicit_name_overriding_env(monkeypatch):
    monkeypatch.setenv(RETRIEVAL_PROVIDER_ENV_VAR, "nonexistent")
    provider = select_retrieval_provider("keyword")
    assert isinstance(provider, KeywordRetrievalProvider)
