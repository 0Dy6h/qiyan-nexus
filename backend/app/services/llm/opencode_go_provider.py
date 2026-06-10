"""OpenCode Go provider for OpenAI-compatible chat completions."""

from __future__ import annotations

import json
import logging

import httpx

from app.core.config import Settings, get_settings
from app.schemas.rag import CitationCard, GroundedClaim
from app.services.llm.prompting import (
    EMPTY_CITATIONS_FALLBACK,
    GROUNDING_SYSTEM_PROMPT,
    GROUNDING_TOOL_NAME,
    build_citation_text,
)
from app.services.llm.provider import AnswerDraft, DeterministicProvider

_LOGGER = logging.getLogger(__name__)

GROUNDING_FUNCTION_SCHEMA = {
    "type": "function",
    "function": {
        "name": GROUNDING_TOOL_NAME,
        "description": "Record short grounded evidence claims using only the provided evidence IDs.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "claims": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 3,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "text": {"type": "string", "minLength": 1},
                            "evidence_refs": {
                                "type": "array",
                                "minItems": 1,
                                "maxItems": 1,
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
    },
}


def _parse_grounding_tool_arguments(arguments: object) -> list[GroundedClaim] | None:
    if not isinstance(arguments, str):
        return None
    try:
        tool_input = json.loads(arguments)
    except json.JSONDecodeError:
        return None
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


def _usage_value(usage: dict[str, object], key: str) -> int | None:
    value = usage.get(key)
    return value if isinstance(value, int) else None


def _message_text(message: dict[str, object]) -> str:
    content = message.get("content")
    return content if isinstance(content, str) else ""


def _extract_message_and_usage(
    data: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    raw_choices = data["choices"]
    if not isinstance(raw_choices, list) or not raw_choices:
        raise ValueError("missing choices")
    first_choice = raw_choices[0]
    if not isinstance(first_choice, dict):
        raise ValueError("invalid choice")
    message = first_choice["message"]
    if not isinstance(message, dict):
        raise ValueError("invalid message")
    usage = data.get("usage") or {}
    if not isinstance(usage, dict):
        usage = {}
    return message, usage


def _draft_from_tool_calls(message: object, usage: dict[str, object]) -> AnswerDraft | None:
    if not isinstance(message, dict):
        return None
    tool_calls = message.get("tool_calls")
    if not isinstance(tool_calls, list) or not tool_calls:
        return None

    tool_name: str | None = None
    for raw_tool_call in tool_calls:
        if not isinstance(raw_tool_call, dict):
            continue
        function = raw_tool_call.get("function")
        if not isinstance(function, dict):
            continue
        current_tool_name = function.get("name")
        if isinstance(current_tool_name, str) and tool_name is None:
            tool_name = current_tool_name
        if current_tool_name != GROUNDING_TOOL_NAME:
            continue
        claims = _parse_grounding_tool_arguments(function.get("arguments"))
        blocked_reason = None if claims is not None else "tool_input_schema_error"
        return AnswerDraft(
            text=_message_text(message),
            provider_name=OpenCodeGoProvider.name,
            input_tokens=_usage_value(usage, "prompt_tokens"),
            output_tokens=_usage_value(usage, "completion_tokens"),
            structured_claims=claims,
            grounding_policy="opencode_go_tool_use_v1",
            provider_native_grounding=True,
            tool_name=tool_name,
            tool_call_count=len(tool_calls),
            grounding_blocked_reason=blocked_reason,
        )

    return AnswerDraft(
        text=_message_text(message),
        provider_name=OpenCodeGoProvider.name,
        input_tokens=_usage_value(usage, "prompt_tokens"),
        output_tokens=_usage_value(usage, "completion_tokens"),
        structured_claims=None,
        grounding_policy="opencode_go_tool_use_v1",
        provider_native_grounding=True,
        tool_name=tool_name,
        tool_call_count=len(tool_calls),
        grounding_blocked_reason="tool_name_mismatch",
    )


def _build_completion_payload(
    settings: Settings, question: str, citations: list[CitationCard], *, include_tools: bool
) -> dict[str, object]:
    payload: dict[str, object] = {
        "model": settings.opencode_go_model,
        "max_tokens": settings.opencode_go_max_tokens,
        "temperature": settings.opencode_go_temperature,
        "messages": [
            {"role": "system", "content": GROUNDING_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"问题：{question}\n\n引用片段：\n\n{build_citation_text(citations)}",
            },
        ],
    }
    if include_tools:
        payload["tools"] = [GROUNDING_FUNCTION_SCHEMA]
        payload["tool_choice"] = {"type": "function", "function": {"name": GROUNDING_TOOL_NAME}}
    return payload


def _is_tool_payload_rejection(exc: Exception) -> bool:
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in {400, 422}


class OpenCodeGoProvider:
    name = "opencode_go"

    def __init__(
        self,
        http_client: httpx.Client | None = None,
        fallback: DeterministicProvider | None = None,
    ) -> None:
        # When an http_client is injected (tests), the caller owns its lifecycle.
        # When none is provided, lazily create one on first use and keep it for
        # the provider's lifetime so connection pooling is reused.
        self._http_client = http_client
        self._fallback = fallback or DeterministicProvider()

    def _ensure_http_client(self) -> httpx.Client:
        if self._http_client is None:
            self._http_client = httpx.Client(timeout=30.0)
        return self._http_client

    def generate_answer(self, question: str, citations: list[CitationCard]) -> AnswerDraft:
        settings = get_settings()

        if not citations:
            return AnswerDraft(
                text=EMPTY_CITATIONS_FALLBACK,
                provider_name=self.name,
            )

        if not settings.opencode_go_api_key:
            _LOGGER.warning(
                "OpenCodeGoProvider falling back to %s: missing API key",
                self._fallback.name,
            )
            return self._fallback.generate_answer(question, citations)

        return self._request_completion(self._ensure_http_client(), settings, question, citations)

    def _request_completion(
        self,
        http_client: httpx.Client,
        settings: Settings,
        question: str,
        citations: list[CitationCard],
    ) -> AnswerDraft:
        url = f"{settings.opencode_go_base_url.rstrip('/')}/chat/completions"

        try:
            data = self._post_completion(
                http_client,
                url,
                settings,
                _build_completion_payload(settings, question, citations, include_tools=True),
            )
            message, usage = _extract_message_and_usage(data)
            tool_draft = _draft_from_tool_calls(message, usage)
            if tool_draft is not None:
                return tool_draft
            text = message["content"]
            if not isinstance(text, str) or not text.strip():
                raise ValueError("empty message content")
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            if _is_tool_payload_rejection(exc):
                try:
                    return self._request_legacy_structured_completion(
                        http_client, url, settings, question, citations
                    )
                except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as legacy_exc:
                    exc = legacy_exc
            status_code = None
            if isinstance(exc, httpx.HTTPStatusError):
                status_code = exc.response.status_code
            _LOGGER.warning(
                "OpenCodeGoProvider falling back to %s: %s status=%s",
                self._fallback.name,
                type(exc).__name__,
                status_code,
            )
            return self._fallback.generate_answer(question, citations)

        return AnswerDraft(
            text=text,
            provider_name=self.name,
            input_tokens=_usage_value(usage, "prompt_tokens"),
            output_tokens=_usage_value(usage, "completion_tokens"),
        )

    def _post_completion(
        self,
        http_client: httpx.Client,
        url: str,
        settings: Settings,
        payload: dict[str, object],
    ) -> dict[str, object]:
        response = http_client.post(
            url,
            headers={
                "Authorization": f"Bearer {settings.opencode_go_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("invalid response json")
        return data

    def _request_legacy_structured_completion(
        self,
        http_client: httpx.Client,
        url: str,
        settings: Settings,
        question: str,
        citations: list[CitationCard],
    ) -> AnswerDraft:
        data = self._post_completion(
            http_client,
            url,
            settings,
            _build_completion_payload(settings, question, citations, include_tools=False),
        )
        message, usage = _extract_message_and_usage(data)
        text = message["content"]
        if not isinstance(text, str) or not text.strip():
            raise ValueError("empty message content")
        return AnswerDraft(
            text=text,
            provider_name=self.name,
            input_tokens=_usage_value(usage, "prompt_tokens"),
            output_tokens=_usage_value(usage, "completion_tokens"),
        )
