"""Vector-only retrieval provider (C3 slice 3/5).

Flattens chunks across the (already source-filtered) item list, builds or
loads the cached chunk vector index, queries it, and maps results back to
``ScoredCandidate`` rows. The integer ``score`` is ``pool_size - rank`` so
downstream code (``answer_question`` thresholds, RRF fusion in slice 4) can
treat keyword and vector scores on the same integer axis.
"""

from __future__ import annotations

from pathlib import Path

from app.repositories.runtime_storage import resolve_vector_index_cache_path
from app.schemas.chunk import LiteratureChunk
from app.schemas.literature import LiteratureItem
from app.services.retrieval.embedding import EmbeddingBackend, select_embedding_backend
from app.services.retrieval.provider import ScoredCandidate
from app.services.retrieval.vector_index import ChunkVectorIndex, get_chunk_vector_index


class VectorRetrievalProvider:
    """faiss-backed ranker; chunkless items contribute a zero-score fallback row."""

    name = "vector"

    def __init__(
        self,
        backend: EmbeddingBackend | None = None,
        cache_path: Path | None = None,
        index: ChunkVectorIndex | None = None,
    ) -> None:
        self._backend = backend if backend is not None else select_embedding_backend()
        self._cache_path = (
            cache_path if cache_path is not None else resolve_vector_index_cache_path()
        )
        self._override_index = index

    def rank(
        self,
        query: str,
        items: list[LiteratureItem],
        chunks_by_item: dict[str, list[LiteratureChunk]],
        preferred_source_type: str,
    ) -> list[ScoredCandidate]:
        all_chunks: list[LiteratureChunk] = []
        for item in items:
            all_chunks.extend(chunks_by_item.get(item.id, []))

        items_by_id = {item.id: item for item in items}
        chunks_by_id = {chunk.chunk_id: chunk for chunk in all_chunks}

        index = (
            self._override_index
            if self._override_index is not None
            else get_chunk_vector_index(self._backend, self._cache_path)
        )
        index.load_or_build(all_chunks)

        hits = index.search(query, top_k=len(all_chunks)) if all_chunks else []
        pool_size = len(hits)

        ranked: list[ScoredCandidate] = []
        seen_pairs: set[tuple[str, str]] = set()
        for rank, (chunk_id, _score) in enumerate(hits):
            chunk = chunks_by_id.get(chunk_id)
            if chunk is None:
                continue
            owning_item = items_by_id.get(chunk.literature_id)
            if owning_item is None:
                continue
            score = pool_size - rank
            language_bonus = 1 if owning_item.source_type == preferred_source_type else 0
            ranked.append(
                ScoredCandidate(
                    score=score,
                    language_bonus=language_bonus,
                    item=owning_item,
                    chunk=chunk,
                )
            )
            seen_pairs.add((owning_item.id, chunk_id))

        for item in items:
            chunks = chunks_by_item.get(item.id, [])
            if not chunks:
                if (item.id, "_") not in seen_pairs:
                    ranked.append(
                        ScoredCandidate(
                            score=0,
                            language_bonus=1 if item.source_type == preferred_source_type else 0,
                            item=item,
                            chunk=None,
                        )
                    )
                    seen_pairs.add((item.id, "_"))
        return ranked
