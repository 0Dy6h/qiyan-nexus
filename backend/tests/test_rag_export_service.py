"""Unit tests for build_answer_markdown service function.

Field order and labels mirror frontend/lib/rag-export.ts:buildAnswerMarkdown
so the server-rendered export is byte-identical to the legacy client build.
"""

from app.schemas.rag import (
    CitationCard,
    GroundedClaim,
    GroundingMetadata,
    ProviderSli,
    RagAnswerResponse,
    RetrievalMetadata,
)
from app.services.rag import build_answer_markdown

DISCLAIMER = "非诊断结论、需结合临床。"


def _sample_answer(**overrides: object) -> RagAnswerResponse:
    defaults: dict[str, object] = {
        "question": "特应性皮炎和肠-脑-皮肤轴有什么关系？",
        "answer": "基于当前检索到的证据片段，已优先返回与问题最相关的文献。",
        "disclaimer": DISCLAIMER,
        "answered_at": "2026-05-21T07:42:11.123456+00:00",
        "provider_name": "deterministic",
        "input_tokens": None,
        "output_tokens": None,
        "retrieval": RetrievalMetadata(
            applied_source="all",
            applied_top_k=2,
            available_citation_count=16,
            strategy="keyword",
        ),
        "grounding": GroundingMetadata(
            status="skipped",
            policy="structured_claim_refs_v3",
            checked=False,
            blocked_reason=None,
            allowed_evidence_refs=[
                "chunk-cn-ad-gbs-001-abstract",
                "chunk-pdf-cn-ad-uploaded-007-uploaded",
            ],
            matched_evidence_refs=[],
            unsupported_evidence_refs=[],
            claim_count=0,
            cited_claim_count=0,
            structured_claims=[
                GroundedClaim(
                    text="证据提示肠道菌群与皮肤屏障异常之间存在关联",
                    evidence_refs=["chunk-cn-ad-gbs-001-abstract"],
                    semantic_score=0.76,
                    entailment_score=0.99,
                )
            ],
            provider_native_grounding=False,
            tool_name=None,
            tool_call_count=0,
        ),
        "citations": [
            CitationCard(
                literature_id="cn-ad-gbs-001",
                chunk_id="chunk-cn-ad-gbs-001-abstract",
                title="肠-脑-皮肤轴与特应性皮炎中医证候研究",
                source="CNKI curated AD sample",
                snippet="围绕特应性皮炎、肠-脑-皮肤轴与中医证候关联进行综述。",
                quote="脾虚湿蕴、血虚风燥与肠道微生态失衡的可解释关联",
                reason="gut_skin_axis, tcm_syndrome",
                confidence=0.86,
                source_type="sample",
                pdf_upload_id=None,
            ),
            CitationCard(
                literature_id="cn-ad-uploaded-007",
                chunk_id="chunk-pdf-cn-ad-uploaded-007-uploaded",
                title="上传 PDF：ad-evidence.pdf",
                source="Uploaded PDF",
                snippet="上传 PDF ad-evidence.pdf 已完成解析。",
                quote="Mock parser 提取了特应性皮炎证据片段",
                reason="uploaded_pdf, pdf_parse",
                confidence=0.86,
                source_type="uploaded_pdf",
                pdf_upload_id="pdf-cn-ad-uploaded-007-ad-evidence-pdf",
            ),
        ],
        "sli": None,
    }
    defaults.update(overrides)
    return RagAnswerResponse(**defaults)  # type: ignore[arg-type]


def test_build_answer_markdown_includes_header_and_metadata() -> None:
    md = build_answer_markdown(_sample_answer())

    assert md.startswith("# Qiyan Nexus RAG 答案导出")
    assert "特应性皮炎和肠-脑-皮肤轴有什么关系？" in md
    assert "基于当前检索到的证据片段" in md
    assert "2026-05-21T07:42:11.123456+00:00" in md
    assert "应用来源：全部文献" in md
    assert "应用 top_k：2" in md
    assert "可用引用数：16" in md
    assert "Provider：deterministic" in md
    assert "检索策略：keyword" in md
    assert "Grounding 状态：skipped" in md
    assert "Grounding 策略：structured_claim_refs_v3" in md
    assert "Provider-native grounding：false" in md
    assert "Grounding Tool：无" in md
    assert "Tool 调用数：0" in md
    assert "NLI 阈值：未启用" in md
    assert "最小蕴含支持度：未计算" in md
    assert "句级引用覆盖：0/0" in md
    assert "Token 输入：未返回" in md
    assert "Token 输出：未返回" in md


def test_build_answer_markdown_includes_reviewer_ready_evidence_brief_sections() -> None:
    md = build_answer_markdown(_sample_answer())

    assert "## 证据简报" in md
    assert "- 回答模式：deterministic / keyword" in md
    assert "- 证据范围：全部文献" in md
    assert "- 引用卡片：2" in md
    assert "- 可用引用数：16" in md
    assert "- 句级引用覆盖：0/0" in md
    assert "## 使用边界" in md
    assert "## Reviewer 核对清单" in md
    assert f"- [ ] 已核对免责声明：{DISCLAIMER}" in md
    assert "- [ ] 已逐条打开引用文献详情或原文 PDF" in md
    assert "- [ ] 已确认 seed / PubMed / 上传 PDF 来源边界" in md
    assert "- [ ] 已确认当前回答不作为诊断或处方建议" in md
    assert "## 技术审计信息" in md
    assert md.index("## 证据简报") < md.index("## 问题") < md.index("## 回答")
    assert md.index("## Reviewer 核对清单") < md.index("## 技术审计信息")


def test_build_answer_markdown_includes_structured_claim_block() -> None:
    md = build_answer_markdown(_sample_answer())

    assert "## 结构化声明" in md
    assert "### Claim 1" in md
    assert "证据提示肠道菌群与皮肤屏障异常之间存在关联" in md
    assert "evidence_refs：chunk-cn-ad-gbs-001-abstract" in md
    assert "semantic_score：76%" in md
    assert "entailment_score：99%" in md


def test_build_answer_markdown_includes_citation_blocks() -> None:
    md = build_answer_markdown(_sample_answer())

    assert "## 引用证据" in md
    assert "### 引用 1 — 肠-脑-皮肤轴与特应性皮炎中医证候研究" in md
    assert "literature_id：cn-ad-gbs-001" in md
    assert "chunk_id：chunk-cn-ad-gbs-001-abstract" in md
    assert "置信度：86%" in md
    assert "命中证据标签：gut_skin_axis, tcm_syndrome" in md
    assert "### 引用 2 — 上传 PDF：ad-evidence.pdf" in md
    assert "source_type：uploaded_pdf" in md
    assert "pdf_upload_id：pdf-cn-ad-uploaded-007-ad-evidence-pdf" in md
    assert DISCLAIMER in md


def test_build_answer_markdown_includes_token_usage_when_present() -> None:
    md = build_answer_markdown(
        _sample_answer(
            provider_name="opencode_go",
            input_tokens=128,
            output_tokens=64,
            retrieval=RetrievalMetadata(
                applied_source="all",
                applied_top_k=2,
                available_citation_count=16,
                strategy="hybrid",
            ),
        )
    )

    assert "Provider：opencode_go" in md
    assert "检索策略：hybrid" in md
    assert "Token 输入：128" in md
    assert "Token 输出：64" in md


def test_build_answer_markdown_shows_provider_latency_and_cost_when_sli_present() -> None:
    md = build_answer_markdown(
        _sample_answer(
            provider_name="opencode_go",
            input_tokens=517,
            output_tokens=1087,
            sli=ProviderSli(provider_latency_ms=8423, estimated_cost_usd=0.001234),
        )
    )

    assert "Provider 延迟：8423 ms" in md
    assert "预估成本：$0.001234" in md


def test_build_answer_markdown_shows_sli_placeholders_when_absent() -> None:
    md = build_answer_markdown(_sample_answer())

    assert "Provider 延迟：未返回" in md
    assert "预估成本：未估算" in md


def test_build_answer_markdown_includes_opencode_go_native_grounding_metadata() -> None:
    md = build_answer_markdown(
        _sample_answer(
            provider_name="opencode_go",
            grounding=GroundingMetadata(
                status="skipped",
                policy="opencode_go_tool_use_v1",
                checked=False,
                blocked_reason=None,
                allowed_evidence_refs=["chunk-cn-ad-gbs-001-abstract"],
                matched_evidence_refs=[],
                unsupported_evidence_refs=[],
                claim_count=0,
                cited_claim_count=0,
                structured_claims=[],
                provider_native_grounding=True,
                tool_name="record_grounded_claims",
                tool_call_count=1,
            ),
        )
    )

    assert "Provider：opencode_go" in md
    assert "Grounding 策略：opencode_go_tool_use_v1" in md
    assert "Provider-native grounding：true" in md
    assert "Grounding Tool：record_grounded_claims" in md
    assert "Tool 调用数：1" in md


def test_build_answer_markdown_includes_blocked_grounding_details() -> None:
    md = build_answer_markdown(
        _sample_answer(
            provider_name="opencode_go",
            answer="当前模型草稿未通过引用证据校验，系统已拦截展示。",
            grounding=GroundingMetadata(
                status="blocked",
                policy="structured_claim_refs_v3",
                checked=True,
                blocked_reason="unsupported_evidence_ref",
                allowed_evidence_refs=["chunk-cn-ad-gbs-001-abstract"],
                matched_evidence_refs=[],
                unsupported_evidence_refs=["chunk-unknown-ref"],
                claim_count=2,
                cited_claim_count=1,
                structured_claims=[],
                provider_native_grounding=False,
                tool_name=None,
                tool_call_count=0,
            ),
        )
    )

    assert "Grounding 状态：blocked" in md
    assert "Grounding 拦截原因：unsupported_evidence_ref" in md
    assert "句级引用覆盖：1/2" in md
    assert "Grounding 异常证据：chunk-unknown-ref" in md


def test_build_answer_markdown_includes_semantic_gate_details() -> None:
    md = build_answer_markdown(
        _sample_answer(
            provider_name="opencode_go",
            grounding=GroundingMetadata(
                status="blocked",
                policy="structured_claim_refs_v3",
                checked=True,
                blocked_reason="semantic_low_support",
                allowed_evidence_refs=["chunk-cn-ad-gbs-001-abstract"],
                matched_evidence_refs=[],
                unsupported_evidence_refs=[],
                claim_count=0,
                cited_claim_count=0,
                structured_claims=[],
                provider_native_grounding=False,
                tool_name=None,
                tool_call_count=0,
                semantic_threshold=0.4,
                min_semantic_score=0.12,
            ),
        )
    )

    assert "Grounding 拦截原因：semantic_low_support" in md
    assert "语义阈值：0.40" in md
    assert "最小语义支持度：12%" in md


def test_build_answer_markdown_includes_nli_gate_details() -> None:
    md = build_answer_markdown(
        _sample_answer(
            provider_name="opencode_go",
            grounding=GroundingMetadata(
                status="blocked",
                policy="structured_claim_refs_v3",
                checked=True,
                blocked_reason="nli_low_entailment",
                allowed_evidence_refs=["chunk-cn-ad-gbs-001-abstract"],
                matched_evidence_refs=[],
                unsupported_evidence_refs=[],
                claim_count=0,
                cited_claim_count=0,
                structured_claims=[],
                provider_native_grounding=False,
                tool_name=None,
                tool_call_count=0,
                nli_threshold=0.5,
                min_entailment_score=0.004,
            ),
        )
    )

    assert "Grounding 拦截原因：nli_low_entailment" in md
    assert "NLI 阈值：0.50" in md
    assert "最小蕴含支持度：0%" in md


def test_build_answer_markdown_empty_citations_uses_placeholder() -> None:
    md = build_answer_markdown(_sample_answer(citations=[]))

    assert "（当前回答没有可核对的引用证据。）" in md
    assert DISCLAIMER in md


def test_build_answer_markdown_empty_structured_claims_uses_placeholder() -> None:
    md = build_answer_markdown(
        _sample_answer(
            grounding=GroundingMetadata(
                status="skipped",
                policy="structured_claim_refs_v3",
                checked=False,
                blocked_reason=None,
                allowed_evidence_refs=[],
                matched_evidence_refs=[],
                unsupported_evidence_refs=[],
                claim_count=0,
                cited_claim_count=0,
                structured_claims=[],
                provider_native_grounding=False,
                tool_name=None,
                tool_call_count=0,
            )
        )
    )

    assert "（当前回答没有结构化声明。）" in md


def test_build_answer_markdown_disclaimer_is_byte_identical() -> None:
    """The disclaimer is referenced by tests/eval/frontend; must be byte-stable."""
    md = build_answer_markdown(_sample_answer())
    assert DISCLAIMER in md


def test_build_answer_markdown_uses_server_disclaimer_constant() -> None:
    md = build_answer_markdown(_sample_answer(disclaimer="不要使用这个客户端传入文案"))

    assert DISCLAIMER in md
    assert "不要使用这个客户端传入文案" not in md
