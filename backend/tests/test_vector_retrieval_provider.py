"""Slice 3 tests for VectorRetrievalProvider.

Mirrors the keyword provider test shape but uses a deterministic in-test
``SubstringEmbeddingBackend`` so we can assert on semantic-style rankings
without depending on bge weights or hashing collisions.
"""

import numpy as np
import numpy.typing as npt

from app.schemas.chunk import LiteratureChunk
from app.schemas.literature import LiteratureItem
from app.services.retrieval.provider import RetrievalProvider, select_retrieval_provider
from app.services.retrieval.vector_index import (
    ChunkVectorIndex,
    reset_chunk_vector_index_cache,
)
from app.services.retrieval.vector_provider import VectorRetrievalProvider


class SubstringEmbeddingBackend:
    name = "substring-test"
    dim = 8
    _KEYWORDS = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta"]

    def encode(self, texts: list[str]) -> npt.NDArray[np.float32]:
        vectors = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            lo = text.lower()
            for i, keyword in enumerate(self._KEYWORDS):
                if keyword in lo:
                    vectors[row, i] = 1.0
            norm = float(np.linalg.norm(vectors[row]))
            if norm == 0.0:
                vectors[row, 0] = 1.0
            else:
                vectors[row] /= norm
        return vectors


def _make_item(item_id: str, source_type: str = "cn_literature") -> LiteratureItem:
    return LiteratureItem(
        id=item_id,
        title=f"Title {item_id}",
        language="zh",
        source="seed",
        source_type=source_type,
        year=2024,
        authors=["author"],
        snippet="snippet",
        keywords=[],
        evidence_tags=[],
        related_entity_ids=[],
    )


def _make_chunk(chunk_id: str, literature_id: str, text: str) -> LiteratureChunk:
    return LiteratureChunk(
        chunk_id=chunk_id,
        literature_id=literature_id,
        section="abstract",
        text=text,
        source_quote=text,
    )


def test_vector_provider_satisfies_retrieval_provider_protocol():
    reset_chunk_vector_index_cache()
    backend = SubstringEmbeddingBackend()
    provider = VectorRetrievalProvider(backend=backend, cache_path=None)
    assert isinstance(provider, RetrievalProvider)
    assert provider.name == "vector"


def test_vector_provider_ranks_more_similar_chunks_higher():
    reset_chunk_vector_index_cache()
    backend = SubstringEmbeddingBackend()
    items = [_make_item("lit-a"), _make_item("lit-b")]
    chunks_by_item = {
        "lit-a": [_make_chunk("ca", "lit-a", "alpha and beta")],
        "lit-b": [_make_chunk("cb", "lit-b", "gamma far away")],
    }
    index = ChunkVectorIndex(backend, cache_path=None)
    provider = VectorRetrievalProvider(backend=backend, cache_path=None, index=index)

    candidates = provider.rank(
        "alpha", items, chunks_by_item, preferred_source_type="cn_literature"
    )

    assert candidates[0].item.id == "lit-a"
    assert candidates[0].chunk is not None and candidates[0].chunk.chunk_id == "ca"
    assert candidates[0].score > candidates[1].score


def test_vector_provider_fallback_for_chunkless_items():
    reset_chunk_vector_index_cache()
    backend = SubstringEmbeddingBackend()
    items = [_make_item("lit-a"), _make_item("lit-b")]
    chunks_by_item: dict[str, list[LiteratureChunk]] = {
        "lit-a": [_make_chunk("ca", "lit-a", "alpha")],
        "lit-b": [],
    }
    index = ChunkVectorIndex(backend, cache_path=None)
    provider = VectorRetrievalProvider(backend=backend, cache_path=None, index=index)

    candidates = provider.rank(
        "alpha", items, chunks_by_item, preferred_source_type="cn_literature"
    )

    ids = [c.item.id for c in candidates]
    assert "lit-b" in ids
    fallback = next(c for c in candidates if c.item.id == "lit-b")
    assert fallback.chunk is None
    assert fallback.score == 0


def test_select_retrieval_provider_returns_vector_for_env_value(monkeypatch):
    reset_chunk_vector_index_cache()
    monkeypatch.setenv("QIYAN_RETRIEVAL_PROVIDER", "vector")
    monkeypatch.setenv("QIYAN_EMBEDDING_BACKEND", "hashing")
    provider = select_retrieval_provider()
    assert isinstance(provider, VectorRetrievalProvider)
    assert provider.name == "vector"
