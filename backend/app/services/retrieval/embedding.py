"""Embedding backend abstraction (C3 slice 2/5).

Mirrors the ``LLMProvider`` / ``RetrievalProvider`` env-selection pattern. The
default ``HashingEmbeddingBackend`` is deterministic, offline, and dim=128. All
``sentence-transformers`` backends are thin lazy wrappers: CI and the default
path never import the heavy dependency or download model weights unless a real
``encode`` call is made for an explicitly selected backend.

The hashing scheme: lowercase token → md5 → 16 bytes interpreted as a ±1 sign
pattern across the 128 dims, summed across tokens, then L2 normalised. Empty
texts collapse to ``e_0`` so downstream code never sees a zero vector.
"""

from __future__ import annotations

import hashlib
import logging
import re
from functools import cache, cached_property
from inspect import signature
from typing import Any, Literal, Protocol, runtime_checkable

import numpy as np
import numpy.typing as npt

_LOGGER = logging.getLogger(__name__)

EMBEDDING_BACKEND_ENV_VAR = "QIYAN_EMBEDDING_BACKEND"
DEFAULT_EMBEDDING_BACKEND_NAME = "hashing"

EmbeddingMatrix = npt.NDArray[np.float32]
EmbeddingTextRole = Literal["document", "query"]

_TOKEN_PATTERN = re.compile(r"[\w]+")


def _tokenize_for_hashing(text: str) -> list[str]:
    normalized = text.lower().strip()
    tokens = _TOKEN_PATTERN.findall(normalized)
    for char in normalized:
        if "一" <= char <= "鿿":
            tokens.append(char)
    return tokens


@runtime_checkable
class EmbeddingBackend(Protocol):
    name: str
    dim: int

    def encode(
        self,
        texts: list[str],
        *,
        role: EmbeddingTextRole = "document",
    ) -> EmbeddingMatrix: ...


class HashingEmbeddingBackend:
    """Deterministic md5 → ±1 → L2-normalised embedding (zero downloads)."""

    name = "hashing"
    dim = 128

    def encode(
        self,
        texts: list[str],
        *,
        role: EmbeddingTextRole = "document",
    ) -> EmbeddingMatrix:
        vectors = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            tokens = _tokenize_for_hashing(text)
            vec = vectors[row]
            if not tokens:
                vec[0] = 1.0
                continue
            for token in tokens:
                digest = hashlib.md5(token.encode("utf-8")).digest()
                for i in range(self.dim):
                    byte = digest[i % 16]
                    bit = (byte >> (i % 8)) & 1
                    vec[i] += 1.0 if bit else -1.0
            norm = float(np.linalg.norm(vec))
            if norm == 0.0:
                vec[0] = 1.0
            else:
                vec /= norm
        return vectors


@cache
def _load_sentence_transformer(model_name: str) -> Any:
    """Import sentence-transformers lazily and return a loaded model.

    Memoised per process so per-request backend construction (``rag.answer_question``
    calls ``select_embedding_backend()`` each time) never reloads model weights.
    Patched out in tests so constructing ``SentenceTransformerEmbeddingBackend``
    never imports or downloads the model.
    """

    from sentence_transformers import (  # type: ignore[import-untyped, import-not-found, unused-ignore]
        SentenceTransformer,
    )

    return SentenceTransformer(model_name)


@cache
def _encode_accepts_role(backend_type: type[Any]) -> bool:
    try:
        parameters = signature(backend_type.encode).parameters
    except (AttributeError, TypeError, ValueError):
        return False
    return "role" in parameters


def encode_with_role(
    backend: EmbeddingBackend,
    texts: list[str],
    *,
    role: EmbeddingTextRole = "document",
) -> EmbeddingMatrix:
    """Encode texts with query/document intent when the backend supports it.

    Production backends now accept a ``role`` keyword, but several tiny in-test
    fake backends intentionally keep the old ``encode(texts)`` shape. Inspecting
    the concrete method avoids forcing those fakes to grow production-only
    details while still letting E5-style backends apply query/passage prefixes.
    """

    if _encode_accepts_role(type(backend)):
        return backend.encode(texts, role=role)
    return backend.encode(texts)


class SentenceTransformerEmbeddingBackend:
    """Lazy ``BAAI/bge-small-zh-v1.5`` wrapper for dev/prod embeddings.

    Construction stays cheap (no import / download) so ``select_embedding_backend``
    never pays the model cost; the model materialises on first ``encode`` via
    ``cached_property`` and the process-level ``_load_sentence_transformer`` memo,
    so neither the per-encode ``is None`` branch nor repeated weight loads remain.
    """

    name = "bge"
    dim = 512
    model_name = "BAAI/bge-small-zh-v1.5"
    document_prefix = ""
    query_prefix = ""

    @cached_property
    def _model(self) -> Any:
        return _load_sentence_transformer(self.model_name)

    def _prepare_texts(self, texts: list[str], role: EmbeddingTextRole) -> list[str]:
        prefix = self.query_prefix if role == "query" else self.document_prefix
        if not prefix:
            return texts
        return [text if text.startswith(prefix) else f"{prefix}{text}" for text in texts]

    def encode(
        self,
        texts: list[str],
        *,
        role: EmbeddingTextRole = "document",
    ) -> EmbeddingMatrix:
        prepared_texts = self._prepare_texts(texts, role)
        raw = self._model.encode(
            prepared_texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return np.asarray(raw, dtype=np.float32)


class BgeM3EmbeddingBackend(SentenceTransformerEmbeddingBackend):
    """Lazy ``BAAI/bge-m3`` backend for multilingual retrieval spikes."""

    name = "bge-m3"
    dim = 1024
    model_name = "BAAI/bge-m3"


class MultilingualE5LargeEmbeddingBackend(SentenceTransformerEmbeddingBackend):
    """Lazy ``intfloat/multilingual-e5-large`` backend.

    The E5 family expects retrieval inputs to be prefixed by role, so document
    chunks are encoded as ``passage: ...`` and search queries/claims as
    ``query: ...``.
    """

    name = "multilingual-e5-large"
    dim = 1024
    model_name = "intfloat/multilingual-e5-large"
    document_prefix = "passage: "
    query_prefix = "query: "


_BACKENDS: dict[str, type[EmbeddingBackend]] = {
    HashingEmbeddingBackend.name: HashingEmbeddingBackend,
    SentenceTransformerEmbeddingBackend.name: SentenceTransformerEmbeddingBackend,
    BgeM3EmbeddingBackend.name: BgeM3EmbeddingBackend,
    MultilingualE5LargeEmbeddingBackend.name: MultilingualE5LargeEmbeddingBackend,
    "e5-large": MultilingualE5LargeEmbeddingBackend,
    "multilingual-e5": MultilingualE5LargeEmbeddingBackend,
}


def select_embedding_backend(name: str | None = None) -> EmbeddingBackend:
    """Return the configured embedding backend, falling back to hashing."""
    from app.services._provider_select import select_from_registry

    return select_from_registry(
        EMBEDDING_BACKEND_ENV_VAR,
        _BACKENDS,
        HashingEmbeddingBackend,
        normalizer=lambda s: s.lower().replace("_", "-"),
        explicit_name=name,
    )
