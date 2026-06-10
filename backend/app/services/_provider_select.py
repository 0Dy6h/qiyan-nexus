"""Unified provider selection logic (fixes #5 backend selector duplication).

All three provider/backend selectors (LLM, retrieval, embedding) share the same
pattern: env var → explicit name → fallback to default, with case normalization,
lazy import for heavy dependencies, and log-warning-then-fallback on misconfig.
This module extracts that shared logic so each caller site shrinks to 3-5 lines.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from typing import TypeVar

_LOGGER = logging.getLogger(__name__)

T = TypeVar("T")


def select_from_registry(
    env_var: str,
    registry: dict[str, type[T]],
    default_cls: type[T],
    *,
    normalizer: Callable[[str], str] | None = None,
    lazy_resolver: Callable[[str], type[T] | None] | None = None,
    explicit_name: str | None = None,
) -> T:
    """Select a provider/backend class from registry, with env/explicit precedence.

    Precedence: ``explicit_name`` → ``os.getenv(env_var)`` → ``default_cls``.
    Unknown names log a warning and fall back to ``default_cls()``.

    Args:
        env_var: Environment variable name (e.g. ``QIYAN_LLM_PROVIDER``).
        registry: Dict of known provider classes (e.g. ``{"deterministic": DeterministicProvider}``).
        default_cls: Fallback class when env is empty or invalid.
        normalizer: Optional candidate normalization (e.g. ``.lower().strip()``).
        lazy_resolver: Optional callback to resolve candidates not in registry (e.g. heavy imports).
        explicit_name: Explicit name overriding env (e.g. for tests or explicit calls).

    Returns:
        An instance of the selected class.
    """
    raw = explicit_name if explicit_name is not None else os.getenv(env_var, "")
    candidate = raw.strip()
    if normalizer:
        candidate = normalizer(candidate)

    if not candidate:
        return default_cls()

    provider_cls = registry.get(candidate)
    if provider_cls is None and lazy_resolver:
        provider_cls = lazy_resolver(candidate)
    if provider_cls is None:
        _LOGGER.warning(
            "Unknown %s=%r; falling back to %s",
            env_var,
            raw,
            default_cls.__name__,
        )
        return default_cls()

    return provider_cls()
