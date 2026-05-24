"""Hybrid retrieval provider via Reciprocal Rank Fusion (C3 slice 4/5).

RRF fuses keyword and vector rankings without normalising scores —
candidates are scored by ``Σ 1/(k + rank)`` across the two lists with
``k = 60`` (Cormack's original constant). Candidates only one side ranks
still surface, and language_bonus is preserved from whichever side ranked
the candidate.

Downstream code keeps treating the fused score as an integer (``pool_size
- final_rank``) so the ``score > 0`` filter in ``answer_question`` works
unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.chunk import LiteratureChunk
from app.schemas.literature import LiteratureItem
from app.services.retrieval.provider import (
    KeywordRetrievalProvider,
    RetrievalProvider,
    ScoredCandidate,
)
from app.services.retrieval.vector_provider import VectorRetrievalProvider

RRF_K = 60
SUB_PROVIDER_TOP_K = 50


@dataclass
class _FusionEntry:
    rrf: float
    language_bonus: int
    candidate: ScoredCandidate


class HybridRetrievalProvider:
    """RRF fusion of keyword + vector rankings."""

    name = "hybrid"

    def __init__(
        self,
        keyword_provider: RetrievalProvider | None = None,
        vector_provider: RetrievalProvider | None = None,
    ) -> None:
        self._keyword = (
            keyword_provider if keyword_provider is not None else KeywordRetrievalProvider()
        )
        self._vector = vector_provider if vector_provider is not None else VectorRetrievalProvider()

    def rank(
        self,
        query: str,
        items: list[LiteratureItem],
        chunks_by_item: dict[str, list[LiteratureChunk]],
        preferred_source_type: str,
    ) -> list[ScoredCandidate]:
        keyword_hits = self._keyword.rank(query, items, chunks_by_item, preferred_source_type)
        vector_hits = self._vector.rank(query, items, chunks_by_item, preferred_source_type)

        scored_keyword = [c for c in keyword_hits if c.score > 0]
        if not scored_keyword:
            scored_keyword = keyword_hits
        scored_vector = [c for c in vector_hits if c.score > 0]
        if not scored_vector:
            scored_vector = vector_hits

        fused: dict[tuple[str, str], _FusionEntry] = {}
        for rank, candidate in enumerate(scored_keyword[:SUB_PROVIDER_TOP_K]):
            self._merge_candidate(fused, candidate, rank)
        for rank, candidate in enumerate(scored_vector[:SUB_PROVIDER_TOP_K]):
            self._merge_candidate(fused, candidate, rank)

        ordered = sorted(
            fused.values(),
            key=lambda entry: (entry.rrf, entry.language_bonus, entry.candidate.item.year),
            reverse=True,
        )
        pool_size = len(ordered)
        ranked: list[ScoredCandidate] = []
        for final_rank, entry in enumerate(ordered):
            ranked.append(
                ScoredCandidate(
                    score=pool_size - final_rank,
                    language_bonus=entry.language_bonus,
                    item=entry.candidate.item,
                    chunk=entry.candidate.chunk,
                )
            )
        return ranked

    @staticmethod
    def _composite_key(candidate: ScoredCandidate) -> tuple[str, str]:
        chunk_id = candidate.chunk.chunk_id if candidate.chunk is not None else "_"
        return (candidate.item.id, chunk_id)

    def _merge_candidate(
        self,
        fused: dict[tuple[str, str], _FusionEntry],
        candidate: ScoredCandidate,
        rank: int,
    ) -> None:
        key = self._composite_key(candidate)
        contribution = 1.0 / (RRF_K + rank + 1)
        existing = fused.get(key)
        if existing is None:
            fused[key] = _FusionEntry(
                rrf=contribution,
                language_bonus=candidate.language_bonus,
                candidate=candidate,
            )
            return
        existing.rrf += contribution
        existing.language_bonus = max(existing.language_bonus, candidate.language_bonus)
