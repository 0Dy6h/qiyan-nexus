"""Slice 4 tests for HybridRetrievalProvider (RRF fusion).

Uses tiny stub sub-providers so we can pin the RRF arithmetic without
depending on the real keyword/vector pipelines. The protocol-conformance
and fallback tests give the integration handshake.
"""

from app.schemas.chunk import LiteratureChunk
from app.schemas.literature import LiteratureItem
from app.services.retrieval.hybrid_provider import (
    RRF_K,
    HybridRetrievalProvider,
)
from app.services.retrieval.provider import RetrievalProvider, ScoredCandidate


def _make_item(item_id: str, year: int = 2024) -> LiteratureItem:
    return LiteratureItem(
        id=item_id,
        title=f"T-{item_id}",
        language="zh",
        source="seed",
        source_type="cn_literature",
        year=year,
        authors=["a"],
        snippet="s",
        keywords=[],
        evidence_tags=[],
        related_entity_ids=[],
    )


def _make_chunk(chunk_id: str, literature_id: str) -> LiteratureChunk:
    return LiteratureChunk(
        chunk_id=chunk_id,
        literature_id=literature_id,
        section="abstract",
        text="t",
        source_quote="t",
    )


class _StubProvider:
    def __init__(self, name: str, hits: list[ScoredCandidate]):
        self.name = name
        self._hits = hits

    def rank(self, query, items, chunks_by_item, preferred_source_type):
        return list(self._hits)


def test_hybrid_provider_satisfies_protocol():
    provider = HybridRetrievalProvider(
        keyword_provider=_StubProvider("kw", []),
        vector_provider=_StubProvider("vec", []),
    )
    assert isinstance(provider, RetrievalProvider)
    assert provider.name == "hybrid"


def test_hybrid_rrf_arithmetic_two_lists_one_shared_candidate():
    item_a = _make_item("lit-a")
    item_b = _make_item("lit-b")
    item_c = _make_item("lit-c")
    chunk_a = _make_chunk("ca", "lit-a")
    chunk_b = _make_chunk("cb", "lit-b")
    chunk_c = _make_chunk("cc", "lit-c")

    keyword_hits = [
        ScoredCandidate(score=5, language_bonus=1, item=item_a, chunk=chunk_a),
        ScoredCandidate(score=3, language_bonus=1, item=item_b, chunk=chunk_b),
    ]
    vector_hits = [
        ScoredCandidate(score=2, language_bonus=1, item=item_b, chunk=chunk_b),
        ScoredCandidate(score=1, language_bonus=1, item=item_c, chunk=chunk_c),
    ]
    provider = HybridRetrievalProvider(
        keyword_provider=_StubProvider("kw", keyword_hits),
        vector_provider=_StubProvider("vec", vector_hits),
    )

    fused = provider.rank("q", [item_a, item_b, item_c], {}, "cn_literature")

    expected_rrf = {
        "lit-a": 1 / (RRF_K + 1),
        "lit-b": 1 / (RRF_K + 2) + 1 / (RRF_K + 1),
        "lit-c": 1 / (RRF_K + 2),
    }
    top_order = [c.item.id for c in fused]
    assert top_order[0] == "lit-b"
    assert expected_rrf["lit-b"] > expected_rrf["lit-a"] > expected_rrf["lit-c"]
    assert set(top_order) == {"lit-a", "lit-b", "lit-c"}
    pool_size = len(fused)
    assert fused[0].score == pool_size
    assert fused[-1].score == 1


def test_hybrid_falls_back_to_keyword_when_vector_returns_nothing():
    item_a = _make_item("lit-a")
    chunk_a = _make_chunk("ca", "lit-a")
    keyword_hits = [ScoredCandidate(score=5, language_bonus=1, item=item_a, chunk=chunk_a)]
    provider = HybridRetrievalProvider(
        keyword_provider=_StubProvider("kw", keyword_hits),
        vector_provider=_StubProvider("vec", []),
    )

    fused = provider.rank("q", [item_a], {}, "cn_literature")

    assert len(fused) == 1
    assert fused[0].item.id == "lit-a"
    assert fused[0].score > 0


def test_hybrid_surfaces_candidates_unique_to_each_side():
    item_a = _make_item("lit-a")
    item_b = _make_item("lit-b")
    chunk_a = _make_chunk("ca", "lit-a")
    chunk_b = _make_chunk("cb", "lit-b")
    keyword_hits = [ScoredCandidate(score=5, language_bonus=1, item=item_a, chunk=chunk_a)]
    vector_hits = [ScoredCandidate(score=2, language_bonus=1, item=item_b, chunk=chunk_b)]
    provider = HybridRetrievalProvider(
        keyword_provider=_StubProvider("kw", keyword_hits),
        vector_provider=_StubProvider("vec", vector_hits),
    )

    fused = provider.rank("q", [item_a, item_b], {}, "cn_literature")

    ids = {c.item.id for c in fused}
    assert ids == {"lit-a", "lit-b"}
