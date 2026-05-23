"""Retrieval provider abstraction (C3 slice 1/5).

Mirrors the ``LLMProvider`` pattern in ``app.services.llm.provider``: a single
``RetrievalProvider`` Protocol with concrete keyword/vector/hybrid implementations
and an env-driven ``select_retrieval_provider`` selector. The default stays
``keyword`` so every existing test sees byte-identical ranking.

Ranking policy (i.e. ``network``-token re-sort and the cross-language top-3 swap)
remains in ``answer_question``; this module only owns the per-candidate score.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from app.schemas.chunk import LiteratureChunk
from app.schemas.literature import LiteratureItem

_LOGGER = logging.getLogger(__name__)

RETRIEVAL_PROVIDER_ENV_VAR = "QIYAN_RETRIEVAL_PROVIDER"
DEFAULT_RETRIEVAL_PROVIDER_NAME = "keyword"

CONFIDENCE_BY_SOURCE_TYPE: dict[str, float] = {
    "cn_literature": 0.86,
    "pubmed": 0.74,
}

_KEYWORD_ALIASES: dict[str, list[str]] = {
    "gut": ["肠", "肠道", "gut", "microbiome", "菌群"],
    "skin_barrier": ["屏障", "barrier", "filaggrin"],
    "immune": ["免疫", "inflammation", "immune", "th2", "jak", "cytokine"],
    "targeted_therapy": ["后续", "线索", "therapeutic target", "targeted therapy"],
    "pruritus": ["瘙痒", "itch", "il-31"],
    "formula": ["复方", "方剂", "formula", "herbal"],
    "network": [
        "网络药理学",
        "network pharmacology",
        "分子对接",
        "分子模拟",
        "molecular docking",
        "molecular simulation",
        "靶点",
        "通路",
        "target",
        "pathway",
    ],
    "pediatric": ["儿童", "pediatric"],
}


def tokenize_query(question: str) -> list[str]:
    normalized = question.lower().strip()
    tokens = set(re.findall(r"[a-z0-9\-]+", normalized))
    for alias, keywords in _KEYWORD_ALIASES.items():
        if any(keyword in normalized for keyword in keywords):
            tokens.add(alias)
    for char in normalized:
        if "一" <= char <= "鿿":
            tokens.add(char)
    return sorted(tokens)


def score_item(item: LiteratureItem, chunk: LiteratureChunk | None, query_tokens: list[str]) -> int:
    haystacks = [
        item.title.lower(),
        item.snippet.lower(),
        (item.abstract or "").lower(),
        " ".join(item.keywords).lower(),
        " ".join(item.evidence_tags).lower(),
        chunk.text.lower() if chunk else "",
        " ".join(chunk.evidence_tags).lower() if chunk else "",
    ]
    score = 0
    for token in query_tokens:
        if any(token in haystack for haystack in haystacks if haystack):
            score += 1
    return score


def alias_tag_bonus(tags: list[str], query_tokens: list[str], weight: int) -> int:
    if not tags:
        return 0
    matched = 0
    for token in query_tokens:
        if token in _KEYWORD_ALIASES and any(token in tag for tag in tags):
            matched += 1
    return matched * weight


@dataclass(frozen=True)
class ScoredCandidate:
    """One ``(item, chunk)`` ranking candidate.

    ``score`` is an integer so hybrid providers can synthesise a value
    consistent with the keyword path's integer counts; ``language_bonus`` is
    0 or 1 and is honoured by ``answer_question`` when composing the answer.
    """

    score: int
    language_bonus: int
    item: LiteratureItem
    chunk: LiteratureChunk | None


@runtime_checkable
class RetrievalProvider(Protocol):
    name: str

    def rank(
        self,
        query: str,
        items: list[LiteratureItem],
        chunks_by_item: dict[str, list[LiteratureChunk]],
        preferred_source_type: str,
    ) -> list[ScoredCandidate]: ...


class KeywordRetrievalProvider:
    """Deterministic keyword + alias-table ranker (current behaviour).

    Iterates ``(item, chunk)`` pairs, computes the integer score, applies the
    ``score (desc) → language_bonus (desc) → year (desc)`` ordering. Items
    with no chunks contribute a single ``(item, None)`` candidate so the
    fallback path still works.
    """

    name = "keyword"

    def rank(
        self,
        query: str,
        items: list[LiteratureItem],
        chunks_by_item: dict[str, list[LiteratureChunk]],
        preferred_source_type: str,
    ) -> list[ScoredCandidate]:
        tokens = tokenize_query(query)
        ranked: list[ScoredCandidate] = []
        for item in items:
            chunks: list[LiteratureChunk | None] = list(chunks_by_item.get(item.id, []))
            if not chunks:
                chunks = [None]
            for chunk in chunks:
                base = score_item(item, chunk, tokens)
                base += alias_tag_bonus(item.evidence_tags, tokens, 2)
                if chunk:
                    base += alias_tag_bonus(chunk.evidence_tags, tokens, 7)
                language_bonus = 1 if item.source_type == preferred_source_type else 0
                ranked.append(
                    ScoredCandidate(
                        score=base,
                        language_bonus=language_bonus,
                        item=item,
                        chunk=chunk,
                    )
                )
        ranked.sort(
            key=lambda c: (c.language_bonus, c.score, c.item.year),
            reverse=True,
        )
        return ranked


_PROVIDERS: dict[str, type[RetrievalProvider]] = {
    KeywordRetrievalProvider.name: KeywordRetrievalProvider,
}


def select_retrieval_provider(name: str | None = None) -> RetrievalProvider:
    """Return the configured retrieval provider, falling back to keyword on misconfig.

    Precedence: explicit ``name`` argument → ``QIYAN_RETRIEVAL_PROVIDER`` env →
    ``KeywordRetrievalProvider``. Unknown names log a warning and fall back
    rather than raise, mirroring ``select_provider`` in ``llm.provider``.
    """

    raw = name if name is not None else os.getenv(RETRIEVAL_PROVIDER_ENV_VAR, "")
    candidate = raw.strip().lower()
    if not candidate:
        return KeywordRetrievalProvider()
    provider_cls = _PROVIDERS.get(candidate)
    if provider_cls is None:
        _LOGGER.warning(
            "Unknown %s=%r; falling back to %s",
            RETRIEVAL_PROVIDER_ENV_VAR,
            raw,
            DEFAULT_RETRIEVAL_PROVIDER_NAME,
        )
        return KeywordRetrievalProvider()
    return provider_cls()
