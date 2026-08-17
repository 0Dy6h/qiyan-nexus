"""Retrieval provider abstraction (C3 slice 1/5).

Mirrors the ``LLMProvider`` pattern in ``app.services.llm.provider``: a single
``RetrievalProvider`` Protocol with concrete keyword/vector/hybrid implementations
and an env-driven ``select_retrieval_provider`` selector. The default stays
``keyword`` so every existing test sees byte-identical ranking.

Ranking policy (i.e. ``network``-token re-sort and the cross-language top-3 swap)
remains in ``answer_question``; this module only owns the per-candidate score.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

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
    "gut": ["肠道", "gut", "microbiome", "菌群"],
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

# ---------------------------------------------------------------------------
# Multi-character CJK medical term dictionary with cross-lingual mapping
# ---------------------------------------------------------------------------

_CJK_MEDICAL_TERMS_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "retrieval" / "cjk_medical_terms.json"
)

_cjk_medical_terms_cache: list[dict[str, Any]] | None = None


def _load_cjk_medical_terms() -> list[dict[str, Any]]:
    """Load the multi-character CJK medical term dictionary.

    Each entry has ``zh`` (Chinese term), ``en`` (list of English equivalents),
    and ``canonical`` (a canonical token).  Terms are sorted by ``zh`` length
    descending so that longest-match-first recognition prevents
    ``神经酰胺`` from being split into single characters.
    """
    global _cjk_medical_terms_cache
    if _cjk_medical_terms_cache is not None:
        return _cjk_medical_terms_cache
    try:
        raw = _CJK_MEDICAL_TERMS_PATH.read_text(encoding="utf-8")
        parsed = json.loads(raw)
    except (FileNotFoundError, OSError, ValueError) as exc:
        _LOGGER.warning("cjk_medical_terms.json unreadable (%s); using empty list", exc)
        _cjk_medical_terms_cache = []
        return _cjk_medical_terms_cache
    terms = parsed.get("terms", []) if isinstance(parsed, dict) else []
    if not isinstance(terms, list):
        _LOGGER.warning("cjk_medical_terms.json has unexpected shape; using empty list")
        _cjk_medical_terms_cache = []
        return _cjk_medical_terms_cache
    # Sort by zh length descending for longest-match-first
    terms.sort(key=lambda e: len(str(e.get("zh", ""))), reverse=True)
    _cjk_medical_terms_cache = terms
    return _cjk_medical_terms_cache


# Short ASCII abbreviation tokens (e.g. "ad") substring-match inside many
# unrelated English words (adult, adverse, gradient, leading...). Matching them
# on a word boundary keeps the legitimate "AD" abbreviation signal without the
# spurious match those words would otherwise contribute, both when injecting
# cross-lingual tokens and when scoring candidates. CJK keywords never hit this
# branch (the pattern only matches 1-2 ASCII chars), so single-char CJK matching
# is unaffected.
_SHORT_ASCII_TOKEN = re.compile(r"^[a-z0-9]{1,2}$")


def _token_matches(token: str, haystack: str) -> bool:
    if _SHORT_ASCII_TOKEN.match(token):
        return re.search(rf"\b{re.escape(token)}\b", haystack) is not None
    return token in haystack


# ---------------------------------------------------------------------------
# Cross-lingual alias loading (Slice 2)
# ---------------------------------------------------------------------------

_CROSS_LINGUAL_TERMS_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "retrieval" / "cross_lingual_terms.json"
)
_NETWORK_DATA_ROOT = Path(__file__).resolve().parents[3] / "data" / "network"

_cross_lingual_cache: dict[str, Any] | None = None
_network_entity_alias_cache: list[dict[str, Any]] | None = None


def _load_cross_lingual_aliases() -> dict[str, Any]:
    """Load cross-lingual term map from JSON, with fallback to empty map.

    Any failure to produce a usable ``{"alias_map": [...]}`` dict — missing
    file, malformed JSON, or a non-dict top-level value — falls back to an
    empty map and logs, rather than propagating out through ``tokenize_query``
    and breaking every retrieval call.
    """
    global _cross_lingual_cache
    if _cross_lingual_cache is not None:
        return _cross_lingual_cache
    fallback: dict[str, Any] = {"alias_map": []}
    try:
        raw = _CROSS_LINGUAL_TERMS_PATH.read_text(encoding="utf-8")
        parsed = json.loads(raw)
    except FileNotFoundError:
        _LOGGER.debug("cross_lingual_terms.json not found; using empty alias map")
        _cross_lingual_cache = fallback
        return _cross_lingual_cache
    except (OSError, ValueError) as exc:
        _LOGGER.warning("cross_lingual_terms.json unreadable (%s); using empty alias map", exc)
        _cross_lingual_cache = fallback
        return _cross_lingual_cache
    if not isinstance(parsed, dict) or not isinstance(parsed.get("alias_map"), list):
        _LOGGER.warning("cross_lingual_terms.json has unexpected shape; using empty alias map")
        _cross_lingual_cache = fallback
        return _cross_lingual_cache
    _cross_lingual_cache = parsed
    return _cross_lingual_cache


def _load_network_entity_aliases() -> list[dict[str, Any]]:
    """Load formula/herb entity aliases used by retrieval.

    RAG still answers only from literature chunks; these aliases simply let a
    query such as "消风散" or "黄芪" match curated literature entity links instead
    of being treated as off-topic CJK character noise.
    """

    global _network_entity_alias_cache
    if _network_entity_alias_cache is not None:
        return _network_entity_alias_cache

    try:
        formulas_raw = json.loads(
            (_NETWORK_DATA_ROOT / "sample_formulas.json").read_text(encoding="utf-8")
        )
        herbs_raw = json.loads(
            (_NETWORK_DATA_ROOT / "sample_herbs.json").read_text(encoding="utf-8")
        )
    except (FileNotFoundError, OSError, ValueError) as exc:
        _LOGGER.warning("network entity aliases unreadable (%s); using empty alias map", exc)
        _network_entity_alias_cache = []
        return _network_entity_alias_cache

    formulas = formulas_raw if isinstance(formulas_raw, list) else []
    herbs = herbs_raw if isinstance(herbs_raw, list) else []

    herb_to_formula_ids: dict[str, list[str]] = {}
    for formula in formulas:
        if not isinstance(formula, dict):
            continue
        formula_id = str(formula.get("id", "")).strip()
        if not formula_id:
            continue
        for herb_id in formula.get("herb_ids", []):
            if isinstance(herb_id, str) and herb_id:
                herb_to_formula_ids.setdefault(herb_id, []).append(formula_id)

    aliases: list[dict[str, Any]] = []
    for formula in formulas:
        if not isinstance(formula, dict):
            continue
        formula_id = str(formula.get("id", "")).strip()
        name = str(formula.get("name", "")).strip()
        pinyin = str(formula.get("pinyin", "")).strip().lower()
        if not formula_id or not name:
            continue
        tokens = {formula_id, "formula"}
        tokens.update(str(herb_id).strip() for herb_id in formula.get("herb_ids", []) if herb_id)
        aliases.append({"terms": {name, pinyin}, "tokens": tokens})

    for herb in herbs:
        if not isinstance(herb, dict):
            continue
        herb_id = str(herb.get("id", "")).strip()
        name = str(herb.get("name", "")).strip()
        pinyin = str(herb.get("pinyin", "")).strip().lower()
        latin_name = str(herb.get("latin_name", "")).strip().lower()
        if not herb_id or not name:
            continue
        tokens = {herb_id, "herb"}
        tokens.update(herb_to_formula_ids.get(herb_id, []))
        aliases.append({"terms": {name, pinyin, latin_name}, "tokens": tokens})

    _network_entity_alias_cache = aliases
    return _network_entity_alias_cache


def tokenize_query(question: str) -> list[str]:
    normalized = question.lower().strip()
    tokens = set(re.findall(r"[a-z0-9\-]+", normalized))

    # Step 1: existing alias injection (canonical keys)
    for alias, keywords in _KEYWORD_ALIASES.items():
        if any(_token_matches(keyword, normalized) for keyword in keywords):
            tokens.add(alias)

    # Step 2: multi-character CJK medical term recognition + cross-lingual mapping
    # Longest-match-first: recognize multi-char terms BEFORE single-char
    # extraction so that e.g. "神经酰胺" is treated as one unit and its
    # English equivalents (ceramide) are injected, rather than being split
    # into 神/经/酰/胺 which cannot match English PubMed text.
    remaining = normalized
    for entry in _load_cjk_medical_terms():
        zh_term = str(entry.get("zh", ""))
        if zh_term and zh_term in remaining:
            en_terms = entry.get("en", [])
            canonical = entry.get("canonical", "")
            for en_kw in en_terms:
                tokens.add(en_kw)
            if canonical:
                tokens.add(canonical)
            # Remove matched substring so its chars aren't extracted as singles
            remaining = remaining.replace(zh_term, " ", 1)

    # Step 3: CJK char extraction (on remaining text after multi-char removal)
    for char in remaining:
        if "一" <= char <= "鿿":
            tokens.add(char)

    # Step 4: cross-lingual token injection (Slice 2)
    # For each alias entry, if ANY zh keyword appears in the query,
    # inject ALL en tokens from that entry (and vice versa for en→zh).
    cross_map = _load_cross_lingual_aliases()
    for entry in cross_map.get("alias_map", []):
        zh_keywords: list[str] = entry.get("zh", [])
        en_keywords: list[str] = entry.get("en", [])
        cross_canonical: str = entry.get("canonical", "")

        # zh keywords matched → inject en tokens
        if any(_token_matches(kw, normalized) for kw in zh_keywords):
            for en_kw in en_keywords:
                tokens.add(en_kw)
            if cross_canonical:
                tokens.add(cross_canonical)

        # en keywords matched → inject zh tokens
        if any(_token_matches(kw, normalized) for kw in en_keywords):
            for zh_kw in zh_keywords:
                tokens.add(zh_kw)
            if cross_canonical:
                tokens.add(cross_canonical)

    # Step 5: TCM formula/herb entity injection from the network seed.
    for entry in _load_network_entity_aliases():
        terms = [term for term in entry.get("terms", set()) if term]
        if any(_token_matches(term, normalized) for term in terms):
            tokens.update(entry.get("tokens", set()))

    return sorted(tokens)


# Field weights for weighted scoring: title > keywords/evidence_tags/entity_ids > snippet/abstract/chunk_text
# Per-token scoring takes the MAX weight across all fields where it matches,
# not the sum, so a token matching both title and abstract earns 3 (not 4).
_FIELD_WEIGHTS: list[tuple[int, str]] = [
    (3, "title"),
    (2, "keywords"),
    (2, "evidence_tags"),
    (2, "related_entity_ids"),
    (1, "snippet"),
    (1, "abstract"),
    (1, "chunk_text"),
    (2, "chunk_evidence_tags"),
    (2, "chunk_related_entity_ids"),
]


def _build_haystacks(item: LiteratureItem, chunk: LiteratureChunk | None) -> dict[str, str]:
    return {
        "title": item.title.lower(),
        "keywords": " ".join(item.keywords).lower(),
        "evidence_tags": " ".join(item.evidence_tags).lower(),
        "related_entity_ids": " ".join(item.related_entity_ids).lower(),
        "snippet": item.snippet.lower(),
        "abstract": (item.abstract or "").lower(),
        "chunk_text": chunk.text.lower() if chunk else "",
        "chunk_evidence_tags": " ".join(chunk.evidence_tags).lower() if chunk else "",
        "chunk_related_entity_ids": " ".join(chunk.related_entity_ids).lower() if chunk else "",
    }


def score_item(item: LiteratureItem, chunk: LiteratureChunk | None, query_tokens: list[str]) -> int:
    haystacks = _build_haystacks(item, chunk)
    score = 0
    for token in query_tokens:
        best_weight = 0
        for weight, field_name in _FIELD_WEIGHTS:
            haystack = haystacks.get(field_name, "")
            if haystack and _token_matches(token, haystack):
                if weight > best_weight:
                    best_weight = weight
        score += best_weight
    return score


def _canonical_token_set() -> set[str]:
    """Tokens eligible for the ``alias_tag_bonus`` substring-against-tag bonus.

    Union of the in-code ``_KEYWORD_ALIASES`` keys and every ``canonical`` declared
    in ``cross_lingual_terms.json``. Recomputed each call — the set is ~25 items so
    cost is negligible, and skipping memoisation keeps the existing monkeypatch
    pattern (``setattr(provider_module, "_cross_lingual_cache", None)``) sufficient
    for cache invalidation in tests.
    """
    canonicals: set[str] = set(_KEYWORD_ALIASES.keys())
    cross_map = _load_cross_lingual_aliases()
    for entry in cross_map.get("alias_map", []):
        canonical = entry.get("canonical", "")
        if canonical:
            canonicals.add(canonical)
    return canonicals


def domain_vocabulary() -> set[str]:
    """Tokens that signal an in-domain (AD) query.

    Union of the in-code ``_KEYWORD_ALIASES`` keys, every cross-lingual
    term/canonical, and multi-character CJK medical term canonicals/en tokens.
    ``tokenize_query`` only emits these when a real domain term
    matched, so their presence in a tokenized query separates an AD question
    from off-topic input that merely accumulates single-CJK-char noise (e.g. a
    hypertension question whose only "matches" are common characters like 的/是/药).
    Used by ``answer_question`` to answer off-topic queries with an honest
    "no evidence" message instead of confidently mismatched citations.
    """

    vocab: set[str] = {key.lower() for key in _KEYWORD_ALIASES}
    cross_map = _load_cross_lingual_aliases()
    for entry in cross_map.get("alias_map", []):
        for keyword in entry.get("zh", []):
            vocab.add(keyword.lower())
        for keyword in entry.get("en", []):
            vocab.add(keyword.lower())
        canonical = entry.get("canonical", "")
        if canonical:
            vocab.add(canonical.lower())
    for entry in _load_cjk_medical_terms():
        for keyword in entry.get("en", []):
            vocab.add(str(keyword).lower())
        canonical = entry.get("canonical", "")
        if canonical:
            vocab.add(str(canonical).lower())
        zh = entry.get("zh", "")
        if zh:
            vocab.add(str(zh).lower())
    for entry in _load_network_entity_aliases():
        for term in entry.get("terms", set()):
            if term:
                vocab.add(str(term).lower())
        for token in entry.get("tokens", set()):
            if token:
                vocab.add(str(token).lower())
    return vocab


def alias_tag_bonus(tags: list[str], query_tokens: list[str], weight: int) -> int:
    if not tags:
        return 0
    canonical_tokens = _canonical_token_set()
    matched = 0
    for token in query_tokens:
        if token in canonical_tokens and any(token in tag for tag in tags):
            matched += 1
    return matched * weight


def _is_real_evidence(item: LiteratureItem) -> bool:
    """Whether ``item`` is real ingested literature rather than synthetic seed data.

    The seed corpus is hand-authored demo / offline-test data whose curated
    ``evidence_tags`` earn the +2/+7 ``alias_tag_bonus``; in a mixed corpus that
    lets a broad synthetic record outscore a specific real paper. In any corpus
    that contains real records, real evidence must rank ahead of the demo
    scaffolding. A seed-only corpus is unaffected — every candidate shares the
    origin, so this key is constant and the ordering is unchanged.
    """

    return item.record_origin != "seed_sample"


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
            key=lambda c: (_is_real_evidence(c.item), c.score, c.language_bonus, c.item.year),
            reverse=True,
        )
        return ranked


_PROVIDERS: dict[str, type[RetrievalProvider]] = {
    KeywordRetrievalProvider.name: KeywordRetrievalProvider,
}


def _resolve_provider_class(candidate: str) -> type[RetrievalProvider] | None:
    """Resolve a provider class, lazy-importing heavy ones (vector, hybrid)."""

    if candidate in _PROVIDERS:
        return _PROVIDERS[candidate]
    if candidate == "vector":
        from app.services.retrieval.vector_provider import VectorRetrievalProvider

        return VectorRetrievalProvider
    if candidate == "hybrid":
        from app.services.retrieval.hybrid_provider import HybridRetrievalProvider

        return HybridRetrievalProvider
    return None


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
    provider_cls = _resolve_provider_class(candidate)
    if provider_cls is None:
        _LOGGER.warning(
            "Unknown %s=%r; falling back to %s",
            RETRIEVAL_PROVIDER_ENV_VAR,
            raw,
            DEFAULT_RETRIEVAL_PROVIDER_NAME,
        )
        return KeywordRetrievalProvider()
    return provider_cls()
