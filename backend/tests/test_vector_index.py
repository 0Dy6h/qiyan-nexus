"""Slice 3 tests for ChunkVectorIndex.

Uses an in-test ``SubstringEmbeddingBackend`` that encodes keyword presence
in 8 fixed dims so faiss search returns predictable rankings — the hashing
backend has too much collision noise for assertions over a 3-chunk corpus.
"""

import numpy as np
import numpy.typing as npt

from app.schemas.chunk import LiteratureChunk
from app.services.retrieval.vector_index import ChunkVectorIndex


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


def _make_chunk(chunk_id: str, text: str) -> LiteratureChunk:
    return LiteratureChunk(
        chunk_id=chunk_id,
        literature_id="lit-a",
        section="abstract",
        text=text,
        source_quote=text,
    )


def test_build_creates_index_with_ntotal_equal_to_chunk_count():
    backend = SubstringEmbeddingBackend()
    index = ChunkVectorIndex(backend, cache_path=None)
    chunks = [
        _make_chunk("c1", "alpha and beta"),
        _make_chunk("c2", "gamma alone"),
        _make_chunk("c3", "delta epsilon"),
    ]

    index.build(chunks)

    assert index.ntotal == 3
    assert index.chunk_ids == ["c1", "c2", "c3"]


def test_search_returns_chunks_ranked_by_semantic_similarity():
    backend = SubstringEmbeddingBackend()
    index = ChunkVectorIndex(backend, cache_path=None)
    chunks = [
        _make_chunk("c1", "alpha and beta together"),
        _make_chunk("c2", "gamma alone in a corner"),
        _make_chunk("c3", "alpha appears here too"),
    ]
    index.build(chunks)

    hits = index.search("alpha", top_k=3)

    assert [chunk_id for chunk_id, _ in hits[:2]] == ["c1", "c3"] or [
        chunk_id for chunk_id, _ in hits[:2]
    ] == ["c3", "c1"]
    assert hits[2][0] == "c2"
    assert hits[2][1] < hits[0][1]


def test_load_or_build_uses_cache_when_fingerprint_matches(tmp_path):
    backend = SubstringEmbeddingBackend()
    cache_path = tmp_path / "vector_index_state.npy"
    chunks = [_make_chunk("c1", "alpha"), _make_chunk("c2", "beta")]

    first = ChunkVectorIndex(backend, cache_path=cache_path)
    first.build(chunks)
    original_fingerprint = first.fingerprint

    assert cache_path.exists()
    assert cache_path.with_suffix(".meta.json").exists()

    second = ChunkVectorIndex(backend, cache_path=cache_path)
    second.load_or_build(chunks)

    assert second.fingerprint == original_fingerprint
    assert second.chunk_ids == first.chunk_ids
    assert second.ntotal == 2


def test_load_or_build_rebuilds_when_chunk_text_changes(tmp_path):
    backend = SubstringEmbeddingBackend()
    cache_path = tmp_path / "vector_index_state.npy"

    first = ChunkVectorIndex(backend, cache_path=cache_path)
    first.build([_make_chunk("c1", "alpha"), _make_chunk("c2", "beta")])
    old_fingerprint = first.fingerprint

    second = ChunkVectorIndex(backend, cache_path=cache_path)
    second.load_or_build([_make_chunk("c1", "alpha"), _make_chunk("c2", "gamma")])

    assert second.fingerprint != old_fingerprint
    assert second.ntotal == 2
