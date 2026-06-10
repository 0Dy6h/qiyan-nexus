"""LLM provider abstraction for RAG answer composition.

The provider returns an ``AnswerDraft`` given the question and the citations
selected by deterministic retrieval. Retrieval/ranking/citation construction
stays in ``app.services.rag``; this module only owns the *text shape* of the
answer.

Two providers ship in MVP-A: ``DeterministicProvider`` preserves the current
inline answer text (existing tests lock that wording), and
``MockClaudeProvider`` returns a stub draft that mimics an LLM hand-off while
still being fully offline. The active provider is chosen by the
``QIYAN_LLM_PROVIDER`` environment variable; invalid/empty values fall back to
``DeterministicProvider`` so the answer endpoint never raises on misconfig.
"""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from app.schemas.rag import CitationCard, GroundedClaim, GroundingPolicy
from app.services._provider_select import select_from_registry

_LOGGER = logging.getLogger(__name__)

PROVIDER_ENV_VAR = "QIYAN_LLM_PROVIDER"
DEFAULT_PROVIDER_NAME = "deterministic"

_EVIDENCE_TAG_TOPIC_CN: dict[str, str] = {
    "skin_barrier": "皮肤屏障",
    "filaggrin": "丝聚蛋白与皮肤屏障",
    "gut_skin_axis": "肠-皮肤轴",
    "microbiome": "肠道菌群与皮肤微生物",
    "immune_pathway": "免疫通路与细胞因子信号",
    "pathway": "信号通路与细胞因子调控",
    "neuroimmune": "神经免疫",
    "pruritus": "瘙痒",
    "formula": "中药复方",
    "network_pharmacology": "网络药理学线索",
    "tcm_syndrome": "中医证候辨证",
    "guideline": "诊疗共识与皮肤屏障维护",
    "clinical_management": "长期临床管理",
    "review": "证据综述",
    "pathogenesis": "发病机制",
    "severity": "严重度关联",
    "flare": "急性发作",
    "targeted_therapy": "靶向治疗",
    "systematic_review": "系统综述",
    "pediatric": "儿童分层",
    "uploaded_pdf": "上传 PDF 解析片段",
    "pdf_parse": "PDF 解析",
    "atopic_dermatitis": "特应性皮炎主题",
}


class AnswerDraft(BaseModel):
    text: str
    provider_name: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    structured_claims: list[GroundedClaim] | None = None
    grounding_policy: GroundingPolicy = "structured_claim_refs_v3"
    provider_native_grounding: bool = False
    tool_name: str | None = None
    tool_call_count: int = 0
    grounding_blocked_reason: str | None = None


@runtime_checkable
class LLMProvider(Protocol):
    name: str

    def generate_answer(self, question: str, citations: list[CitationCard]) -> AnswerDraft: ...


def collect_topic_phrases(citations: list[CitationCard]) -> list[str]:
    seen: list[str] = []
    for citation in citations:
        if not citation.reason:
            continue
        for raw in citation.reason.split(","):
            tag = raw.strip()
            phrase = _EVIDENCE_TAG_TOPIC_CN.get(tag)
            if phrase and phrase not in seen:
                seen.append(phrase)
    return seen


class DeterministicProvider:
    name = "deterministic"

    def generate_answer(self, question: str, citations: list[CitationCard]) -> AnswerDraft:
        del question  # deterministic text is question-agnostic
        if not citations:
            return AnswerDraft(
                text=(
                    "当前样本文献中没有检索到足够匹配的证据片段。请调整问题关键词或切换来源后重试。"
                ),
                provider_name=self.name,
            )

        top_reasons = [citation.reason for citation in citations if citation.reason]
        top_reasons_text = "；".join(top_reasons[:2]) if top_reasons else "当前命中的证据片段"
        titles = "；".join(citation.title for citation in citations[:2])
        topics = collect_topic_phrases(citations)
        topics_text = "、".join(topics) if topics else "暂无主题映射"
        text = (
            f"基于当前检索到的证据片段，已优先返回与问题最相关的文献。"
            f"主要证据线索包括：{top_reasons_text}。"
            f"代表性文献：{titles}。"
            f"涉及的研究主题：{topics_text}。"
            f"请结合引用来源逐条核对，相关结论仍属非诊断结论、需结合临床。"
            f"此回答仍是基于样本文献的 deterministic retrieval 结果，"
            f"用于验证引用卡片、证据片段与合规文案。"
        )
        return AnswerDraft(text=text, provider_name=self.name)


class MockClaudeProvider:
    """Offline stub that imitates a Claude draft for the wiring contract.

    The text shape is intentionally distinct from ``DeterministicProvider`` so
    UI/eval can tell which provider produced the answer. No network call.
    """

    name = "mock_claude"

    def generate_answer(self, question: str, citations: list[CitationCard]) -> AnswerDraft:
        question_trim = question.strip()
        if not citations:
            text = (
                f"【模拟 Claude 草稿】针对「{question_trim}」，暂无可引用的证据片段；"
                f"建议调整关键词或切换来源后重试。本回答未经真实模型生成，"
                f"仍是非诊断结论、需结合临床。"
            )
            return AnswerDraft(text=text, provider_name=self.name)

        titles = "、".join(f"《{citation.title}》" for citation in citations[:2])
        topics = collect_topic_phrases(citations)
        topics_text = "、".join(topics) if topics else "暂未映射主题"
        text = (
            f"【模拟 Claude 草稿】围绕「{question_trim}」的证据综述要点："
            f"代表性文献包括 {titles}；"
            f"涉及主题：{topics_text}。"
            f"请逐条对照引用卡片核验来源；本回答由 MockClaudeProvider 产生，"
            f"用于演示真实模型接入前的草稿形态，"
            f"仍属非诊断结论、需结合临床。"
        )
        return AnswerDraft(text=text, provider_name=self.name)


_PROVIDERS: dict[str, type[LLMProvider]] = {
    DeterministicProvider.name: DeterministicProvider,
    MockClaudeProvider.name: MockClaudeProvider,
}

ANTHROPIC_PROVIDER_NAME = "anthropic"
OPENCODE_GO_PROVIDER_NAME = "opencode_go"

_PROVIDER_INSTANCES: dict[str, LLMProvider] = {}


def clear_provider_cache() -> None:
    """Clear the provider instance cache. Used for test isolation."""
    _PROVIDER_INSTANCES.clear()


def _resolve_extra_provider_class(candidate: str) -> type[LLMProvider] | None:
    if candidate == ANTHROPIC_PROVIDER_NAME:
        from app.services.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider
    if candidate == OPENCODE_GO_PROVIDER_NAME:
        from app.services.llm.opencode_go_provider import OpenCodeGoProvider

        return OpenCodeGoProvider
    return None


def select_provider(name: str | None = None) -> LLMProvider:
    """Return the configured provider, falling back to deterministic on misconfig.

    Provider instances are cached: repeated calls with the same name return the
    same instance so that http_client pooling (OpenCodeGo, Anthropic) is reused.
    """
    import os

    raw = name if name is not None else os.getenv(PROVIDER_ENV_VAR, "")
    candidate = raw.strip().lower() or DEFAULT_PROVIDER_NAME

    if candidate in _PROVIDER_INSTANCES:
        return _PROVIDER_INSTANCES[candidate]

    instance = select_from_registry(
        PROVIDER_ENV_VAR,
        _PROVIDERS,
        DeterministicProvider,
        normalizer=str.lower,
        lazy_resolver=_resolve_extra_provider_class,
        explicit_name=name,
    )
    _PROVIDER_INSTANCES[candidate] = instance
    return instance
