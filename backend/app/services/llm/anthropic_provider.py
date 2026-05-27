"""Real Anthropic Claude provider implementing ``LLMProvider``.

Activated by ``QIYAN_LLM_PROVIDER=anthropic``. Lazy-imported by
``select_provider`` so the deterministic / mock_claude paths never pay the
anthropic SDK import cost. Implementation lands across C1 slices 1-4:

* slice 1 (this commit): registration shape only — ``name`` attribute and a
  ``generate_answer`` that raises ``NotImplementedError``.
* slice 2: prompt assembly + real call + code-level disclaimer append.
* slice 3: failure fallback to deterministic.
* slice 4: token usage / cost estimate observability.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.core.config import get_settings
from app.schemas.rag import CitationCard
from app.services.llm.provider import AnswerDraft

if TYPE_CHECKING:
    from anthropic import Anthropic

    from app.services.llm.provider import LLMProvider

_LOGGER = logging.getLogger(__name__)


_EMPTY_CITATIONS_FALLBACK = (
    "当前样本文献中没有检索到足够匹配的证据片段。请调整问题关键词或切换来源后重试。"
)

_SYSTEM_PROMPT = (
    "你是特应性皮炎（AD）证据综述助理。"
    "输出必须严格基于提供的引用片段；不得编造引用之外的事实。"
    "保持中文学术风格。不要带免责声明。"
)


def _build_citation_text(citations: list[CitationCard]) -> str:
    blocks: list[str] = []
    for i, c in enumerate(citations, 1):
        parts = [
            f"[{i}] 标题：{c.title}",
            f"来源：{c.source}",
            f"片段：{c.snippet}",
        ]
        if c.reason:
            parts.append(f"匹配依据：{c.reason}")
        parts.append(f"置信度：{c.confidence:.2f}")
        parts.append(f"文献ID：{c.literature_id}")
        blocks.append("\n".join(parts))
    return "\n\n".join(blocks)


def _extract_text_from_response(response: object) -> str:
    text_parts: list[str] = []
    for block in response.content:  # type: ignore[attr-defined]
        if getattr(block, "type", None) == "text":
            block_text: str = getattr(block, "text", "")
            text_parts.append(block_text)
    return "".join(text_parts)


def _is_auth_resolution_type_error(exc: Exception) -> bool:
    if not isinstance(exc, TypeError):
        return False
    message = str(exc).lower()
    return "could not resolve authentication method" in message


class AnthropicProvider:
    name = "anthropic"

    def __init__(
        self, client: Anthropic | None = None, fallback: LLMProvider | None = None
    ) -> None:
        self._client = client

        if fallback is None:
            from app.services.llm.provider import DeterministicProvider

            self._fallback: LLMProvider = DeterministicProvider()
        else:
            self._fallback = fallback

    def _log_and_fallback(
        self, question: str, citations: list[CitationCard], error_type: str, message: str
    ) -> AnswerDraft:
        _LOGGER.warning(
            "AnthropicProvider falling back to %s: %s=%s",
            self._fallback.name,
            error_type,
            message[:200],
        )
        return self._fallback.generate_answer(question, citations)

    def generate_answer(self, question: str, citations: list[CitationCard]) -> AnswerDraft:
        settings = get_settings()

        if not citations:
            return AnswerDraft(
                text=_EMPTY_CITATIONS_FALLBACK,
                provider_name=self.name,
            )

        if self._client is None and not settings.anthropic_api_key:
            return self._log_and_fallback(
                question,
                citations,
                "MissingCredentials",
                "missing API key",
            )

        if self._client is None:
            from anthropic import Anthropic as _Anthropic

            self._client = _Anthropic(api_key=settings.anthropic_api_key)

        try:
            response = self._client.messages.create(
                model=settings.anthropic_model,
                max_tokens=settings.anthropic_max_tokens,
                system=_SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": f"问题：{question}\n\n引用片段：\n\n{_build_citation_text(citations)}",
                    },
                ],
            )
        except Exception as exc:
            from anthropic import APIError

            if _is_auth_resolution_type_error(exc):
                return self._log_and_fallback(
                    question,
                    citations,
                    type(exc).__name__,
                    str(exc),
                )
            if not isinstance(exc, APIError):
                raise
            return self._log_and_fallback(
                question,
                citations,
                type(exc).__name__,
                str(exc),
            )

        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "input_tokens", None)
        output_tokens = getattr(usage, "output_tokens", None)

        return AnswerDraft(
            text=_extract_text_from_response(response),
            provider_name=self.name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
