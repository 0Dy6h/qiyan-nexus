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

from typing import TYPE_CHECKING

from app.schemas.rag import CitationCard
from app.services.llm.provider import AnswerDraft

if TYPE_CHECKING:
    from anthropic import Anthropic


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


class AnthropicProvider:
    name = "anthropic"
    MODEL = "claude-haiku-4-5"
    MAX_TOKENS = 1024

    def __init__(self, client: Anthropic | None = None) -> None:
        if client is None:
            from anthropic import Anthropic as _Anthropic

            client = _Anthropic()
        self._client = client

    def generate_answer(self, question: str, citations: list[CitationCard]) -> AnswerDraft:
        if not citations:
            return AnswerDraft(
                text=_EMPTY_CITATIONS_FALLBACK,
                provider_name=self.name,
            )

        response = self._client.messages.create(
            model=self.MODEL,
            max_tokens=self.MAX_TOKENS,
            system=_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"问题：{question}\n\n引用片段：\n\n{_build_citation_text(citations)}",
                },
            ],
        )

        return AnswerDraft(
            text=_extract_text_from_response(response),
            provider_name=self.name,
        )
