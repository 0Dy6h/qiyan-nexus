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
    EmbeddingBackend,
    HashingEmbeddingBackend,
    SentenceTransformerEmbeddingBackend,
    select_embedding_backend,
)


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


def test_select_embedding_backend_accepts_explicit_name_overriding_env(monkeypatch):
    monkeypatch.setenv(EMBEDDING_BACKEND_ENV_VAR, "nonexistent")
    backend = select_embedding_backend("hashing")
    assert isinstance(backend, HashingEmbeddingBackend)
