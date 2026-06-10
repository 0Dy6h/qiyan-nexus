"""Slice 2 tests for the ``EmbeddingBackend`` Protocol and its two implementations.

Mirrors ``test_retrieval_provider.py``'s shape: protocol satisfaction, env-driven
selection with fallback, and behaviour assertions. The bge backend test only
checks construction is lazy — CI never downloads the ~95MB model.
"""

import logging
from unittest.mock import patch

import numpy as np

from app.services.retrieval.embedding import (
    DEFAULT_EMBEDDING_BACKEND_NAME,
    EMBEDDING_BACKEND_ENV_VAR,
    BgeM3EmbeddingBackend,
    EmbeddingBackend,
    HashingEmbeddingBackend,
    MultilingualE5LargeEmbeddingBackend,
    SentenceTransformerEmbeddingBackend,
    encode_with_role,
    select_embedding_backend,
)


class RecordingSentenceTransformer:
    def __init__(self, dim: int) -> None:
        self.dim = dim
        self.calls: list[list[str]] = []

    def encode(
        self,
        texts: list[str],
        *,
        normalize_embeddings: bool,
        convert_to_numpy: bool,
    ) -> np.ndarray:
        self.calls.append(list(texts))
        assert normalize_embeddings is True
        assert convert_to_numpy is True
        return np.ones((len(texts), self.dim), dtype=np.float32)


def test_hashing_backend_produces_unit_vectors():
    backend = HashingEmbeddingBackend()
    vectors = backend.encode(["特应性皮炎", "atopic dermatitis"])

    assert vectors.shape == (2, backend.dim)
    norms = np.linalg.norm(vectors, axis=1)
    np.testing.assert_allclose(norms, np.ones(2), atol=1e-5)


def test_hashing_backend_is_deterministic():
    backend = HashingEmbeddingBackend()
    first = backend.encode(["肠-脑-皮肤轴"])
    second = backend.encode(["肠-脑-皮肤轴"])

    np.testing.assert_array_equal(first, second)


def test_hashing_backend_distinguishes_different_inputs():
    backend = HashingEmbeddingBackend()
    vectors = backend.encode(["atopic dermatitis barrier", "network pharmacology"])

    cosine = float(vectors[0] @ vectors[1])
    assert cosine < 0.95


def test_hashing_backend_satisfies_protocol():
    backend = HashingEmbeddingBackend()
    assert isinstance(backend, EmbeddingBackend)
    assert backend.name == "hashing"


def test_select_embedding_backend_defaults_to_hashing(monkeypatch):
    monkeypatch.delenv(EMBEDDING_BACKEND_ENV_VAR, raising=False)
    backend = select_embedding_backend()
    assert backend.name == DEFAULT_EMBEDDING_BACKEND_NAME
    assert isinstance(backend, HashingEmbeddingBackend)


def test_select_embedding_backend_falls_back_for_invalid_value(monkeypatch, caplog):
    monkeypatch.setenv(EMBEDDING_BACKEND_ENV_VAR, "nonexistent-backend")
    with caplog.at_level(logging.WARNING):
        backend = select_embedding_backend()
    assert isinstance(backend, HashingEmbeddingBackend)
    assert any(
        "nonexistent-backend" in record.message or "Unknown" in record.message
        for record in caplog.records
    )


def test_bge_backend_does_not_load_model_on_construction():
    """Constructing the bge backend must not import sentence_transformers.

    The plan calls for lazy import inside the first encode() call so CI never
    downloads the ~95MB model just because the class is imported.
    """

    with patch(
        "app.services.retrieval.embedding._load_sentence_transformer",
    ) as loader:
        backend = SentenceTransformerEmbeddingBackend()
        assert backend.name == "bge"
        assert backend.dim == 512
        loader.assert_not_called()


def test_multilingual_sentence_transformer_backends_are_lazy():
    with patch(
        "app.services.retrieval.embedding._load_sentence_transformer",
    ) as loader:
        bge_m3 = BgeM3EmbeddingBackend()
        e5 = MultilingualE5LargeEmbeddingBackend()

        assert bge_m3.name == "bge-m3"
        assert bge_m3.model_name == "BAAI/bge-m3"
        assert bge_m3.dim == 1024
        assert e5.name == "multilingual-e5-large"
        assert e5.model_name == "intfloat/multilingual-e5-large"
        assert e5.dim == 1024
        loader.assert_not_called()


def test_multilingual_e5_applies_query_and_document_prefixes():
    model = RecordingSentenceTransformer(dim=MultilingualE5LargeEmbeddingBackend.dim)

    with patch(
        "app.services.retrieval.embedding._load_sentence_transformer",
        return_value=model,
    ):
        backend = MultilingualE5LargeEmbeddingBackend()
        backend.encode(["肠道菌群"], role="document")
        backend.encode(["肠道菌群"], role="query")
        backend.encode(["query: already-prefixed"], role="query")

    assert model.calls == [
        ["passage: 肠道菌群"],
        ["query: 肠道菌群"],
        ["query: already-prefixed"],
    ]


def test_encode_with_role_falls_back_for_legacy_test_backends():
    class LegacyBackend:
        name = "legacy-test"
        dim = 2

        def encode(self, texts: list[str]) -> np.ndarray:
            return np.ones((len(texts), self.dim), dtype=np.float32)

    vectors = encode_with_role(LegacyBackend(), ["alpha"], role="query")

    assert vectors.shape == (1, 2)


def test_select_embedding_backend_accepts_explicit_name_overriding_env(monkeypatch):
    monkeypatch.setenv(EMBEDDING_BACKEND_ENV_VAR, "nonexistent")
    backend = select_embedding_backend("hashing")
    assert isinstance(backend, HashingEmbeddingBackend)


def test_select_embedding_backend_accepts_multilingual_candidates(monkeypatch):
    monkeypatch.setenv(EMBEDDING_BACKEND_ENV_VAR, "bge_m3")
    backend = select_embedding_backend()
    assert isinstance(backend, BgeM3EmbeddingBackend)
    assert backend.name == "bge-m3"

    e5 = select_embedding_backend("multilingual-e5")
    assert isinstance(e5, MultilingualE5LargeEmbeddingBackend)
    assert e5.name == "multilingual-e5-large"
