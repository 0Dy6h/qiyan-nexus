"""OpenCode Go provider for OpenAI-compatible chat completions."""

from __future__ import annotations

import logging

import httpx

from app.core.config import get_settings
from app.schemas.rag import CitationCard
from app.services.llm.provider import AnswerDraft, DeterministicProvider

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
    for i, citation in enumerate(citations, 1):
        parts = [
            f"[{i}] 标题：{citation.title}",
            f"来源：{citation.source}",
            f"片段：{citation.snippet}",
        ]
        if citation.reason:
            parts.append(f"匹配依据：{citation.reason}")
        parts.append(f"置信度：{citation.confidence:.2f}")
        parts.append(f"文献ID：{citation.literature_id}")
        blocks.append("\n".join(parts))
    return "\n\n".join(blocks)


class OpenCodeGoProvider:
    name = "opencode_go"

    def __init__(
        self,
        http_client: httpx.Client | None = None,
        fallback: DeterministicProvider | None = None,
    ) -> None:
        self._http_client = http_client or httpx.Client(timeout=30.0)
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

        url = f"{settings.opencode_go_base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": settings.opencode_go_model,
            "max_tokens": settings.opencode_go_max_tokens,
            "temperature": settings.opencode_go_temperature,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"问题：{question}\n\n引用片段：\n\n{_build_citation_text(citations)}",
                },
            ],
        }

        try:
            response = self._http_client.post(
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
