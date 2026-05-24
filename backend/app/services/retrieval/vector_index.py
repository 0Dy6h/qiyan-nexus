"""Chunk-level faiss vector index (C3 slice 3/5).

A thin wrapper around ``faiss.IndexFlatIP`` keyed by chunk_id. Persistence
uses ``numpy.save`` for the vectors + a side-car JSON for chunk ids and a
fingerprint over ``(chunk_id, text[:64], backend.name, backend.dim)``. The
fingerprint is recomputed on every ``load_or_build`` so a seed-data change
(or backend swap) transparently rebuilds the cache rather than serving stale
hits — this is the same class of bug that bit B5 and B6
([[runtime-state-bootstrap-stale-on-seed-change]]).

Public surface returns ``list[tuple[str, float]]`` ranked best-first so the
provider layer doesn't have to know about faiss arrays.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import faiss  # type: ignore[import-untyped, import-not-found, unused-ignore]
import numpy as np

from app.schemas.chunk import LiteratureChunk
from app.services.retrieval.embedding import EmbeddingBackend, EmbeddingMatrix

_META_SUFFIX = ".meta.json"
_FINGERPRINT_TEXT_PREFIX = 64


class ChunkVectorIndex:
    """Dense vector index over chunk texts, persisted next to the runtime state.

    The index is rebuilt whenever the chunk set, the chunk texts, or the
    embedding backend identity change. Empty chunk lists are allowed — search
    on an empty index returns ``[]`` and ``load_or_build`` is a no-op.
    """

    def __init__(self, backend: EmbeddingBackend, cache_path: Path | None = None) -> None:
        self._backend = backend
        self._cache_path = cache_path
        self._index: Any = None
        self._chunk_ids: list[str] = []
        self._fingerprint: str = ""

    @property
    def backend(self) -> EmbeddingBackend:
        return self._backend

    @property
    def chunk_ids(self) -> list[str]:
        return list(self._chunk_ids)

    @property
    def fingerprint(self) -> str:
        return self._fingerprint

    @property
    def ntotal(self) -> int:
        if self._index is None:
            return 0
        total = self._index.ntotal
        return int(total)

    def compute_fingerprint(self, chunks: list[LiteratureChunk]) -> str:
        records = sorted(
            f"{c.chunk_id}|{c.text[:_FINGERPRINT_TEXT_PREFIX]}|{self._backend.name}|{self._backend.dim}"
            for c in chunks
        )
        payload = "\n".join(records).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def build(self, chunks: list[LiteratureChunk]) -> None:
        if not chunks:
            self._index = faiss.IndexFlatIP(self._backend.dim)
            self._chunk_ids = []
            self._fingerprint = ""
            self._save_to_cache(None)
            return

        texts = [chunk.text for chunk in chunks]
        vectors = self._backend.encode(texts)
        index = faiss.IndexFlatIP(self._backend.dim)
        index.add(vectors)
        self._index = index
        self._chunk_ids = [chunk.chunk_id for chunk in chunks]
        self._fingerprint = self.compute_fingerprint(chunks)
        self._save_to_cache(vectors)

    def load_or_build(self, chunks: list[LiteratureChunk], rebuild: bool = False) -> None:
        expected = self.compute_fingerprint(chunks)
        if not rebuild and self._load_from_cache() and self._fingerprint == expected:
            return
        self.build(chunks)

    def search(self, query: str, top_k: int) -> list[tuple[str, float]]:
        if self._index is None or self._index.ntotal == 0 or top_k <= 0:
            return []
        query_vec = self._backend.encode([query])
        effective = min(top_k, int(self._index.ntotal))
        scores, indices = self._index.search(query_vec, effective)
        results: list[tuple[str, float]] = []
        for rank in range(effective):
            raw_idx = int(indices[0][rank])
            if raw_idx < 0:
                continue
            chunk_id = self._chunk_ids[raw_idx]
            results.append((chunk_id, float(scores[0][rank])))
        return results

    def _save_to_cache(self, vectors: EmbeddingMatrix | None) -> None:
        if self._cache_path is None:
            return
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path = self._cache_path.with_suffix(_META_SUFFIX)
        if vectors is None or vectors.size == 0:
            if self._cache_path.exists():
                self._cache_path.unlink()
            if meta_path.exists():
                meta_path.unlink()
            return
        np.save(self._cache_path, vectors)
        meta = {
            "backend_name": self._backend.name,
            "dim": self._backend.dim,
            "chunk_ids": self._chunk_ids,
            "fingerprint": self._fingerprint,
        }
        meta_path.write_text(json.dumps(meta), encoding="utf-8")

    def _load_from_cache(self) -> bool:
        if self._cache_path is None or not self._cache_path.exists():
            return False
        meta_path = self._cache_path.with_suffix(_META_SUFFIX)
        if not meta_path.exists():
            return False
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        if meta.get("backend_name") != self._backend.name:
            return False
        if meta.get("dim") != self._backend.dim:
            return False
        try:
            vectors = np.load(self._cache_path)
        except (OSError, ValueError):
            return False
        if vectors.dtype != np.float32:
            vectors = vectors.astype(np.float32)
        if vectors.ndim != 2 or vectors.shape[1] != self._backend.dim:
            return False
        index = faiss.IndexFlatIP(self._backend.dim)
        index.add(vectors)
        self._index = index
        self._chunk_ids = list(meta.get("chunk_ids", []))
        self._fingerprint = str(meta.get("fingerprint", ""))
        return True


_INDEX_SINGLETONS: dict[str, ChunkVectorIndex] = {}


def get_chunk_vector_index(backend: EmbeddingBackend, cache_path: Path | None) -> ChunkVectorIndex:
    """Module-level cache: one index per ``backend.name``.

    Switching the embedding backend (e.g. hashing → bge) creates a fresh
    index for that backend; the fingerprint check inside ``load_or_build``
    handles seed-data drift within the same backend.
    """

    cached = _INDEX_SINGLETONS.get(backend.name)
    if cached is None:
        cached = ChunkVectorIndex(backend, cache_path)
        _INDEX_SINGLETONS[backend.name] = cached
    return cached


def reset_chunk_vector_index_cache() -> None:
    """Drop the module-level singleton cache (test helper)."""

    _INDEX_SINGLETONS.clear()
