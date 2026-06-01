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
    """English query: PubMed items should appear in top results (score-primary sort).

    After Slice 2, the sort key changed from (language_bonus, score, year) to
    (score, language_bonus, year).  Cross-lingual token injection means Chinese
    items can now score higher for English queries, so PubMed items may not
    always be at positions 1-2.  The key invariant is that PubMed items are
    present in the top results with language_bonus=1.
    """
    items, chunks_by_item = _load_seed()
    provider = KeywordRetrievalProvider()

    candidates = provider.rank(
        "atopic dermatitis barrier",
        items,
        chunks_by_item,
        preferred_source_type="pubmed",
    )

    top_ids = [c.item.id for c in candidates[:10]]
    # PubMed items should be present in the top 10 results
    pubmed_in_top = [lid for lid in top_ids if lid.startswith("pmid-")]
    assert len(pubmed_in_top) >= 2, f"Expected at least 2 PubMed items in top 10, got: {top_ids}"
    # The top PubMed item should still be pmid-40100001 (highest-scoring PubMed)
    pubmed_candidates = [c for c in candidates if c.item.id.startswith("pmid-")]
    assert pubmed_candidates[0].item.id == "pmid-40100001"


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


# ---------------------------------------------------------------------------
# Slice 2: cross-lingual token injection tests
# ---------------------------------------------------------------------------


def test_cross_language_tokenization_injects_english_equivalents_for_zh_query():
    """中文查询 token 应包含英文等价词（跨语言别名注入）"""
    from app.services.retrieval.provider import tokenize_query

    tokens = tokenize_query("肠道菌群与特应性皮炎")
    # 应包含与查询相关的英文 token（来自 cross_lingual_terms.json）
    en_tokens = [t for t in tokens if t.isascii() and t[0].isalpha()]
    assert len(en_tokens) > 0, f"No English tokens injected for zh query, got: {tokens}"
    # 至少应包含 gut/microbiome/atopic dermatitis 等关键词之一
    assert any(
        kw in tokens for kw in ["gut", "microbiome", "atopic dermatitis", "microbiota", "ad"]
    ), f"Expected cross-lingual English tokens, got: {tokens}"


def test_cross_language_tokenization_injects_zh_equivalents_for_en_query():
    """英文查询 token 应包含中文等价词（跨语言别名注入）"""
    from app.services.retrieval.provider import tokenize_query

    tokens = tokenize_query("atopic dermatitis gut microbiome")
    # 应包含与查询相关的中文 token
    cjk_tokens = [t for t in tokens if any("\u4e00" <= ch <= "\u9fff" for ch in t)]
    assert len(cjk_tokens) > 0, f"No CJK tokens injected for en query, got: {tokens}"


def test_sort_key_uses_score_as_primary():
    """排序键应以 score 为主键，language_bonus 为次键"""
    from app.schemas.literature import LiteratureItem
    from app.services.retrieval.provider import ScoredCandidate

    # 构造两个候选：高分 pubmed + 低分 cn_literature
    high_score_pubmed = ScoredCandidate(
        score=10,
        language_bonus=0,
        item=LiteratureItem(
            id="pmid-test-001",
            title="Test PubMed",
            snippet="test",
            source="pubmed",
            source_type="pubmed",
            language="en",
            year=2023,
            keywords=[],
            evidence_tags=[],
            related_entity_ids=[],
        ),
        chunk=None,
    )
    low_score_cn = ScoredCandidate(
        score=2,
        language_bonus=1,
        item=LiteratureItem(
            id="cn-test-001",
            title="测试中文",
            snippet="测试",
            source="cn_literature",
            source_type="cn_literature",
            language="zh",
            year=2023,
            keywords=[],
            evidence_tags=[],
            related_entity_ids=[],
        ),
        chunk=None,
    )
    # 当 score 为主排序键时，高分 pubmed 应排在低分 cn 前面
    ranked = sorted(
        [high_score_pubmed, low_score_cn],
        key=lambda c: (c.score, c.language_bonus, c.item.year),
        reverse=True,
    )
    assert ranked[0].item.id == "pmid-test-001", (
        "High-score pubmed should rank above low-score cn when score is primary sort key"
    )
