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

from app.schemas.rag import CitationCard
from app.services.llm.provider import AnswerDraft


class AnthropicProvider:
    name = "anthropic"

    def generate_answer(self, question: str, citations: list[CitationCard]) -> AnswerDraft:
        raise NotImplementedError("AnthropicProvider.generate_answer lands in C1 slice 2")
