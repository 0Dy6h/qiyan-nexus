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
    """After Slice 7, alias_tag_bonus also recognises cross-lingual canonicals
    (microbiome, atopic_dermatitis, ...). The query "特应性皮炎和肠-脑-皮肤轴..." injects
    both ``gut`` (legacy) and ``microbiome`` (cross-lingual) canonicals; chunk-microbiome-003
    has both tags so it edges ahead of chunk-gbs-001 (only ``gut_skin_axis`` matches).
    Both docs remain top-2 — the change is a tie-break swap.
    """
    items, chunks_by_item = _load_seed()
    provider = KeywordRetrievalProvider()

    candidates = provider.rank(
        "特应性皮炎和肠-脑-皮肤轴有什么关系？",
        items,
        chunks_by_item,
        preferred_source_type="cn_literature",
    )

    top_two = [(c.item.id, c.chunk.chunk_id if c.chunk else None) for c in candidates[:2]]
    assert top_two[0] == ("cn-ad-microbiome-003", "chunk-cn-ad-microbiome-003-abstract")
    assert top_two[1][0] == "cn-ad-gbs-001"


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


def test_single_gut_character_does_not_inject_gut_aliases():
    """肠 by itself is too broad; 肠道/肠-脑 remain valid AD gut-axis signals."""
    from app.services.retrieval.provider import tokenize_query

    obstruction_tokens = set(tokenize_query("肠梗阻怎么治疗"))
    assert "gut" not in obstruction_tokens
    assert "microbiome" not in obstruction_tokens

    gut_axis_tokens = set(tokenize_query("肠道菌群与特应性皮炎"))
    assert {"gut", "microbiome"} <= gut_axis_tokens


def test_tokenization_injects_formula_and_herb_entity_ids():
    """Network seed entity names should bridge RAG queries to related_entity_ids."""
    from app.services.retrieval.provider import tokenize_query

    formula_tokens = set(tokenize_query("消风散的组成有哪些"))
    assert {"formula-xiaofengsan", "herb-jingjie", "herb-fangfeng"} <= formula_tokens

    herb_tokens = set(tokenize_query("黄芪的功效"))
    assert {"herb-huangqi", "formula-danggui-yinzi"} <= herb_tokens


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


# ---------------------------------------------------------------------------
# Short-token word-boundary matching (prevents "ad" substring false positives)
# ---------------------------------------------------------------------------


def test_short_ascii_token_matches_on_word_boundary_only():
    """The 2-char "ad" abbreviation must not substring-match inside common words.

    Before this guard, ``"ad" in haystack`` matched *adult, adverse, gradient,
    leading*… adding a spurious +1 to nearly every English candidate. Matching
    short ASCII tokens on a word boundary keeps the standalone "AD" signal while
    dropping those false positives.
    """
    from app.services.retrieval.provider import _token_matches

    assert _token_matches("ad", "ad is atopic dermatitis") is True
    assert _token_matches("ad", "study of ad. patients") is True
    assert _token_matches("ad", "advanced therapy for adult patients") is False
    assert _token_matches("ad", "concentration gradient") is False
    # Longer tokens keep plain substring matching.
    assert _token_matches("barrier", "skin barrier dysfunction") is True
    assert _token_matches("il-4", "role of il-4 cytokine") is True


def test_short_token_does_not_inject_cross_lingual_terms_from_substring():
    """An English word merely containing "ad" must not inject the AD Chinese terms."""
    from app.services.retrieval.provider import tokenize_query

    ad_zh_terms = {"特应性皮炎", "异位性皮炎", "湿疹"}

    # "advanced" contains the substring "ad" but is not the AD abbreviation.
    advanced_tokens = set(tokenize_query("advanced therapy"))
    assert ad_zh_terms.isdisjoint(advanced_tokens), (
        f"'advanced' should not inject AD Chinese terms, got: {sorted(ad_zh_terms & advanced_tokens)}"
    )

    # Standalone "AD" still injects the Chinese equivalents.
    standalone_tokens = set(tokenize_query("AD barrier"))
    assert ad_zh_terms.issubset(standalone_tokens), (
        f"Standalone 'AD' should inject AD Chinese terms, got: {sorted(standalone_tokens)}"
    )


def test_load_cross_lingual_aliases_falls_back_on_malformed_json(monkeypatch, tmp_path, caplog):
    """Malformed JSON must fall back to an empty map, not crash every retrieval call."""
    import logging

    from app.services.retrieval import provider as provider_module

    bad_file = tmp_path / "cross_lingual_terms.json"
    bad_file.write_text("{ this is not valid json", encoding="utf-8")
    monkeypatch.setattr(provider_module, "_CROSS_LINGUAL_TERMS_PATH", bad_file)
    monkeypatch.setattr(provider_module, "_cross_lingual_cache", None)

    with caplog.at_level(logging.WARNING):
        result = provider_module._load_cross_lingual_aliases()

    assert result == {"alias_map": []}
    # tokenize_query must still work (no exception propagates).
    assert isinstance(provider_module.tokenize_query("特应性皮炎"), list)


def test_load_cross_lingual_aliases_falls_back_on_non_dict_json(monkeypatch, tmp_path):
    """A JSON file that parses to a non-dict (e.g. a list) must fall back safely."""
    from app.services.retrieval import provider as provider_module

    list_file = tmp_path / "cross_lingual_terms.json"
    list_file.write_text("[1, 2, 3]", encoding="utf-8")
    monkeypatch.setattr(provider_module, "_CROSS_LINGUAL_TERMS_PATH", list_file)
    monkeypatch.setattr(provider_module, "_cross_lingual_cache", None)

    result = provider_module._load_cross_lingual_aliases()

    assert result == {"alias_map": []}


# ---------------------------------------------------------------------------
# Slice 7: alias_tag_bonus recognises cross-lingual canonicals
# ---------------------------------------------------------------------------


def test_alias_tag_bonus_honours_cross_lingual_canonicals():
    """alias_tag_bonus must honour canonicals declared only in cross_lingual_terms.json.

    Previously the eligibility check was ``token in _KEYWORD_ALIASES`` (the in-code
    8-entry dict), so canonicals injected by the cross-lingual bridge — ``microbiome``,
    ``atopic_dermatitis``, ``tcm_syndrome``, ... — silently failed to earn the +2/+7
    bonus even when the document's evidence_tags carried the canonical string. That
    structurally underweighted cross-lingual hits (closes rag-eval-035/047).
    """
    from app.services.retrieval.provider import alias_tag_bonus

    # ``microbiome`` is a cross-lingual-only canonical (not in _KEYWORD_ALIASES).
    # A chunk tag containing "microbiome" must contribute one match.
    bonus = alias_tag_bonus(
        tags=["microbiome", "severity"],
        query_tokens=["microbiome"],
        weight=7,
    )
    assert bonus == 7, f"Expected +7 for microbiome canonical match, got {bonus}"

    # ``atopic_dermatitis`` is also cross-lingual-only — same contract.
    bonus = alias_tag_bonus(
        tags=["atopic_dermatitis"],
        query_tokens=["atopic_dermatitis"],
        weight=2,
    )
    assert bonus == 2

    # Tokens not in either alias set → no bonus.
    bonus = alias_tag_bonus(
        tags=["microbiome"],
        query_tokens=["unrelated_token"],
        weight=7,
    )
    assert bonus == 0

    # The legacy _KEYWORD_ALIASES path must keep working.
    bonus = alias_tag_bonus(
        tags=["gut_skin_axis"],
        query_tokens=["gut"],
        weight=7,
    )
    assert bonus == 7

    # Mixed: one legacy canonical + one cross-lingual canonical, two matches → 2×weight.
    bonus = alias_tag_bonus(
        tags=["gut_skin_axis", "microbiome"],
        query_tokens=["gut", "microbiome"],
        weight=7,
    )
    assert bonus == 14


# ---------------------------------------------------------------------------
# Pillar ②: synthetic seed records must not suppress real evidence
# ---------------------------------------------------------------------------


def test_real_records_outrank_synthetic_seed_in_mixed_corpus():
    """Synthetic ``seed_sample`` demo records must not outrank real ``pubmed_live``
    evidence in a mixed corpus.

    Seed records carry curated ``evidence_tags`` (earning the +2 item / +7 chunk
    ``alias_tag_bonus``) and, being bilingual, match many cross-lingual tokens; a
    real PubMed record has empty tags, no chunk, and matches fewer tokens. Before
    the origin-aware sort a broad Chinese microbiome seed outscored a specific real
    JAK paper for a JAK query (the real paper fell to rank #8 on the live corpus).
    In any corpus that contains real evidence, real records rank ahead of the
    synthetic demo scaffolding.
    """
    from app.schemas.chunk import LiteratureChunk
    from app.schemas.literature import LiteratureItem
    from app.services.retrieval.provider import KeywordRetrievalProvider

    real = LiteratureItem(
        id="pmid-99999999",
        title="Targeting the JAK/STAT pathway in atopic dermatitis",
        snippet="JAK inhibitors modulate the JAK-STAT axis in atopic dermatitis.",
        source="PubMed live sync",
        source_type="pubmed",
        language="en",
        record_origin="pubmed_live",
        year=2025,
        keywords=["JAK", "atopic dermatitis", "inhibitor"],
    )
    seed = LiteratureItem(
        id="cn-ad-microbiome-003",
        title="肠道菌群失衡与特应性皮炎发病关系研究进展",
        snippet="肠道菌群 免疫 炎症 皮肤屏障 特应性皮炎",
        source="CNKI curated AD sample",
        source_type="cn_literature",
        language="zh",
        record_origin="seed_sample",
        year=2024,
        evidence_tags=["gut_skin_axis", "microbiome", "immune_pathway"],
    )
    seed_chunk = LiteratureChunk(
        chunk_id="chunk-cn-ad-microbiome-003-abstract",
        literature_id="cn-ad-microbiome-003",
        section="abstract",
        text="肠道菌群 免疫 皮肤屏障 特应性皮炎",
        source_quote="肠道菌群失衡与特应性皮炎相关。",
        evidence_tags=["gut_skin_axis", "microbiome", "immune_pathway"],
    )

    ranked = KeywordRetrievalProvider().rank(
        "atopic dermatitis JAK inhibitor",
        [seed, real],
        {"cn-ad-microbiome-003": [seed_chunk]},
        preferred_source_type="pubmed",
    )

    assert ranked[0].item.record_origin == "pubmed_live"
    assert ranked[0].item.id == "pmid-99999999"
