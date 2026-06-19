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
import os
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from app.schemas.rag import CitationCard, GroundedClaim, GroundingPolicy

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
        question_trim = question.strip()
        if not citations:
            return AnswerDraft(
                text=(
                    "当前特应性皮炎（AD）证据样本库中没有检索到足够匹配的证据片段。"
                    "本工作台仅覆盖 AD 中医药相关文献，请确认问题属于该领域，"
                    "或调整问题关键词、切换来源后重试。"
                ),
                provider_name=self.name,
            )

        lead = f"针对「{question_trim}」，" if question_trim else ""
        evidence_lines: list[str] = []
        for index, citation in enumerate(citations):
            evidence = (citation.quote or citation.snippet or "").strip()
            evidence_lines.append(
                f"{index + 1}.《{citation.title}》（{citation.source}）：{evidence}"
            )
        evidence_block = "\n".join(evidence_lines)
        topics = collect_topic_phrases(citations)
        topics_text = "、".join(topics) if topics else "暂无主题映射"
        text = (
            f"{lead}在当前样本文献中检索到 {len(citations)} 条相关证据片段，按相关度排序：\n"
            f"{evidence_block}\n"
            f"涉及主题：{topics_text}。"
            f"以上为系统检索命中的原文证据片段，未经真实模型综合改写"
            f"（deterministic retrieval）；请结合引用来源逐条核对，"
            f"相关结论仍属非诊断结论、需结合临床。"
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

    Precedence: explicit ``name`` argument → ``QIYAN_LLM_PROVIDER`` env →
    ``DeterministicProvider``. Unknown names log a warning and fall back rather
    than raise, so a typo in env never breaks the answer endpoint.
    """

    raw = name if name is not None else os.getenv(PROVIDER_ENV_VAR, "")
    candidate = raw.strip().lower()
    if not candidate:
        return DeterministicProvider()
    provider_cls = _PROVIDERS.get(candidate) or _resolve_extra_provider_class(candidate)
    if provider_cls is None:
        _LOGGER.warning(
            "Unknown %s=%r; falling back to %s",
            PROVIDER_ENV_VAR,
            raw,
            DEFAULT_PROVIDER_NAME,
        )
        return DeterministicProvider()
    return provider_cls()
