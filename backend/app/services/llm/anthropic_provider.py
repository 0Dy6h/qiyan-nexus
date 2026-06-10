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
from typing import TYPE_CHECKING, cast

from app.core.config import Settings, get_settings
from app.schemas.rag import CitationCard, GroundedClaim
from app.services.llm.prompting import (
    EMPTY_CITATIONS_FALLBACK,
    GROUNDING_SYSTEM_PROMPT,
    GROUNDING_TOOL_NAME,
    build_citation_text,
)
from app.services.llm.provider import AnswerDraft

if TYPE_CHECKING:
    from anthropic import Anthropic
    from anthropic.types import MessageParam, ToolChoiceToolParam, ToolParam

    from app.services.llm.provider import LLMProvider

_LOGGER = logging.getLogger(__name__)


GROUNDING_TOOL_SCHEMA = {
    "name": GROUNDING_TOOL_NAME,
    "description": "Record short grounded evidence claims using only the provided evidence IDs.",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "claims": {
                "type": "array",
                "minItems": 1,
                "maxItems": 4,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "text": {"type": "string", "minLength": 1},
                        "evidence_refs": {
                            "type": "array",
                            "minItems": 1,
                            "items": {"type": "string", "minLength": 1},
                        },
                    },
                    "required": ["text", "evidence_refs"],
                },
            }
        },
        "required": ["claims"],
    },
    "strict": True,
}


def _extract_text_from_response(response: object) -> str:
    text_parts: list[str] = []
    for block in response.content:  # type: ignore[attr-defined]
        if getattr(block, "type", None) == "text":
            block_text: str = getattr(block, "text", "")
            text_parts.append(block_text)
    return "".join(text_parts)


def _parse_grounding_tool_input(tool_input: object) -> list[GroundedClaim] | None:
    if not isinstance(tool_input, dict):
        return None
    raw_claims = tool_input.get("claims")
    if not isinstance(raw_claims, list):
        return None

    claims: list[GroundedClaim] = []
    for raw_claim in raw_claims:
        if not isinstance(raw_claim, dict):
            return None
        text = raw_claim.get("text")
        evidence_refs = raw_claim.get("evidence_refs")
        if not isinstance(text, str) or not isinstance(evidence_refs, list):
            return None

        refs: list[str] = []
        for raw_ref in evidence_refs:
            if not isinstance(raw_ref, str):
                return None
            if raw_ref not in refs:
                refs.append(raw_ref)
        claims.append(GroundedClaim(text=text.strip(), evidence_refs=refs))

    return claims


def _extract_grounding_tool_claims(
    response: object,
) -> tuple[list[GroundedClaim] | None, str | None, int, str | None]:
    tool_name: str | None = None
    tool_call_count = 0
    for block in response.content:  # type: ignore[attr-defined]
        if getattr(block, "type", None) != "tool_use":
            continue
        tool_call_count += 1
        current_tool_name = getattr(block, "name", None)
        if isinstance(current_tool_name, str) and tool_name is None:
            tool_name = current_tool_name
        if current_tool_name != GROUNDING_TOOL_NAME:
            continue
        claims = _parse_grounding_tool_input(getattr(block, "input", None))
        if claims is None:
            return None, tool_name, tool_call_count, "tool_input_schema_error"
        return claims, tool_name, tool_call_count, None
    blocked_reason = "missing_tool_use" if tool_call_count == 0 else "tool_name_mismatch"
    return None, tool_name, tool_call_count, blocked_reason


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

    def _ensure_client(self, settings: Settings) -> Anthropic:
        if self._client is None:
            from anthropic import Anthropic as _Anthropic

            self._client = _Anthropic(api_key=settings.anthropic_api_key)
        return self._client

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
                text=EMPTY_CITATIONS_FALLBACK,
                provider_name=self.name,
            )

        if self._client is None and not settings.anthropic_api_key:
            return self._log_and_fallback(
                question,
                citations,
                "MissingCredentials",
                "missing API key",
            )

        try:
            response = self._ensure_client(settings).messages.create(
                model=settings.anthropic_model,
                max_tokens=settings.anthropic_max_tokens,
                system=GROUNDING_SYSTEM_PROMPT,
                tools=cast("list[ToolParam]", [GROUNDING_TOOL_SCHEMA]),
                tool_choice=cast(
                    "ToolChoiceToolParam", {"type": "tool", "name": GROUNDING_TOOL_NAME}
                ),
                messages=cast(
                    "list[MessageParam]",
                    [
                        {
                            "role": "user",
                            "content": (
                                f"问题：{question}\n\n引用片段：\n\n"
                                f"{build_citation_text(citations)}"
                            ),
                        },
                    ],
                ),
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
        structured_claims, tool_name, tool_call_count, blocked_reason = (
            _extract_grounding_tool_claims(response)
        )

        return AnswerDraft(
            text=_extract_text_from_response(response),
            provider_name=self.name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            structured_claims=structured_claims,
            grounding_policy="anthropic_tool_use_v1",
            provider_native_grounding=True,
            tool_name=tool_name,
            tool_call_count=tool_call_count,
            grounding_blocked_reason=blocked_reason,
        )
