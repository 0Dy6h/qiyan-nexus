"""OpenCode Go provider for OpenAI-compatible chat completions."""

from __future__ import annotations

import logging

import httpx

from app.core.config import Settings, get_settings
from app.schemas.rag import CitationCard
from app.services.llm.prompting import GROUNDING_SYSTEM_PROMPT, build_citation_text
from app.services.llm.provider import AnswerDraft, DeterministicProvider

_LOGGER = logging.getLogger(__name__)

_EMPTY_CITATIONS_FALLBACK = (
    "当前样本文献中没有检索到足够匹配的证据片段。请调整问题关键词或切换来源后重试。"
)


class OpenCodeGoProvider:
    name = "opencode_go"

    def __init__(
        self,
        http_client: httpx.Client | None = None,
        fallback: DeterministicProvider | None = None,
    ) -> None:
        # Keep an injected client as-is (caller owns its lifecycle). When none is
        # injected we open a short-lived client per request and close it, so the
        # per-call instantiation in select_provider() never leaks a pool.
        self._http_client = http_client
        self._fallback = fallback or DeterministicProvider()

    def generate_answer(self, question: str, citations: list[CitationCard]) -> AnswerDraft:
        settings = get_settings()

        if not citations:
            return AnswerDraft(
                text=_EMPTY_CITATIONS_FALLBACK,
                provider_name=self.name,
            )

        if not settings.opencode_go_api_key:
            _LOGGER.warning(
                "OpenCodeGoProvider falling back to %s: missing API key",
                self._fallback.name,
            )
            return self._fallback.generate_answer(question, citations)

        if self._http_client is not None:
            return self._request_completion(self._http_client, settings, question, citations)
        with httpx.Client(timeout=30.0) as client:
            return self._request_completion(client, settings, question, citations)

    def _request_completion(
        self,
        http_client: httpx.Client,
        settings: Settings,
        question: str,
        citations: list[CitationCard],
    ) -> AnswerDraft:
        url = f"{settings.opencode_go_base_url.rstrip('/')}/chat/completions"
        payload = {
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

        try:
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
            text = data["choices"][0]["message"]["content"]
            if not isinstance(text, str) or not text.strip():
                raise ValueError("empty message content")
            usage = data.get("usage") or {}
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
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
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
        )
