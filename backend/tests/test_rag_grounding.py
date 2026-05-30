from app.schemas.rag import CitationCard, GroundedClaim
from app.services.grounding import BLOCKED_ANSWER_TEXT, evaluate_answer_grounding


def _sample_citations() -> list[CitationCard]:
    return [
        CitationCard(
            literature_id="cn-ad-gbs-001",
            chunk_id="chunk-cn-ad-gbs-001-abstract",
            title="肠-脑-皮肤轴与特应性皮炎中医证候研究",
            source="CNKI curated AD sample",
            snippet="围绕特应性皮炎、肠-脑-皮肤轴与中医证候关联进行综述。",
            reason="gut_skin_axis, tcm_syndrome",
            confidence=0.86,
        ),
        CitationCard(
            literature_id="pmid-40100002",
            chunk_id="chunk-pmid-40100002-microbiome",
            title="Gut microbiome alterations and atopic dermatitis severity",
            source="PubMed curated AD sample",
            snippet="Short-chain fatty acid metabolism and immune balance are reviewed.",
            reason="microbiome, severity",
            confidence=0.74,
        ),
    ]


def test_external_answer_passes_when_it_uses_allowed_evidence_ref():
    answer = (
        '{"claims":['
        '{"text":"证据提示肠道菌群与皮肤屏障异常之间存在关联",'
        '"evidence_refs":["chunk-cn-ad-gbs-001-abstract"]},'
        '{"text":"短链脂肪酸代谢和免疫平衡可能与严重度有关",'
        '"evidence_refs":["chunk-pmid-40100002-microbiome"]}'
        "]}"
    )

    grounded_answer, metadata = evaluate_answer_grounding(
        provider_name="opencode_go",
        answer_text=answer,
        citations=_sample_citations(),
    )

    assert grounded_answer == (
        "证据提示肠道菌群与皮肤屏障异常之间存在关联 [chunk-cn-ad-gbs-001-abstract]。"
        "短链脂肪酸代谢和免疫平衡可能与严重度有关 [chunk-pmid-40100002-microbiome]。"
    )
    assert metadata.status == "passed"
    assert metadata.policy == "structured_claim_refs_v3"
    assert metadata.checked is True
    assert metadata.allowed_evidence_refs == [
        "chunk-cn-ad-gbs-001-abstract",
        "chunk-pmid-40100002-microbiome",
    ]
    assert metadata.matched_evidence_refs == [
        "chunk-cn-ad-gbs-001-abstract",
        "chunk-pmid-40100002-microbiome",
    ]
    assert metadata.unsupported_evidence_refs == []
    assert metadata.blocked_reason is None
    assert metadata.claim_count == 2
    assert metadata.cited_claim_count == 2
    assert [claim.text for claim in metadata.structured_claims] == [
        "证据提示肠道菌群与皮肤屏障异常之间存在关联",
        "短链脂肪酸代谢和免疫平衡可能与严重度有关",
    ]


def test_anthropic_native_tool_claims_pass_when_they_use_allowed_evidence_refs():
    grounded_answer, metadata = evaluate_answer_grounding(
        provider_name="anthropic",
        answer_text="this free text must not be shown",
        citations=_sample_citations(),
        structured_claims=[
            GroundedClaim(
                text="证据提示肠道菌群与皮肤屏障异常之间存在关联",
                evidence_refs=["chunk-cn-ad-gbs-001-abstract"],
            )
        ],
        policy="anthropic_tool_use_v1",
        provider_native_grounding=True,
        tool_name="record_grounded_claims",
        tool_call_count=1,
    )

    assert (
        grounded_answer
        == "证据提示肠道菌群与皮肤屏障异常之间存在关联 [chunk-cn-ad-gbs-001-abstract]。"
    )
    assert metadata.status == "passed"
    assert metadata.policy == "anthropic_tool_use_v1"
    assert metadata.checked is True
    assert metadata.provider_native_grounding is True
    assert metadata.tool_name == "record_grounded_claims"
    assert metadata.tool_call_count == 1
    assert metadata.matched_evidence_refs == ["chunk-cn-ad-gbs-001-abstract"]
    assert metadata.unsupported_evidence_refs == []
    assert metadata.claim_count == 1
    assert metadata.cited_claim_count == 1


def test_external_answer_accepts_fenced_structured_claims_json():
    answer = (
        "```json\n"
        '{"claims":[{"text":"中文模型可能输出结构化证据声明",'
        '"evidence_refs":["chunk-cn-ad-gbs-001-abstract"]}]}\n'
        "```"
    )

    grounded_answer, metadata = evaluate_answer_grounding(
        provider_name="opencode_go",
        answer_text=answer,
        citations=_sample_citations(),
    )

    assert grounded_answer == "中文模型可能输出结构化证据声明 [chunk-cn-ad-gbs-001-abstract]。"
    assert metadata.status == "passed"
    assert metadata.matched_evidence_refs == ["chunk-cn-ad-gbs-001-abstract"]
    assert metadata.claim_count == 1
    assert metadata.cited_claim_count == 1


def test_external_answer_is_hard_blocked_when_it_uses_no_evidence_ref():
    grounded_answer, metadata = evaluate_answer_grounding(
        provider_name="anthropic",
        answer_text="模型给出了没有证据 ID 的医学总结。",
        citations=_sample_citations(),
    )

    assert grounded_answer == BLOCKED_ANSWER_TEXT
    assert metadata.status == "blocked"
    assert metadata.checked is True
    assert metadata.blocked_reason == "structured_claims_parse_error"
    assert metadata.matched_evidence_refs == []
    assert metadata.unsupported_evidence_refs == []
    assert metadata.claim_count == 0
    assert metadata.cited_claim_count == 0


def test_external_answer_is_hard_blocked_when_structured_claims_json_cannot_parse():
    grounded_answer, metadata = evaluate_answer_grounding(
        provider_name="opencode_go",
        answer_text="模型用普通自然语言引用了允许证据 [chunk-cn-ad-gbs-001-abstract]。",
        citations=_sample_citations(),
    )

    assert grounded_answer == BLOCKED_ANSWER_TEXT
    assert metadata.status == "blocked"
    assert metadata.policy == "structured_claim_refs_v3"
    assert metadata.blocked_reason == "structured_claims_parse_error"
    assert metadata.claim_count == 0
    assert metadata.cited_claim_count == 0


def test_external_answer_is_hard_blocked_when_structured_claims_are_empty():
    grounded_answer, metadata = evaluate_answer_grounding(
        provider_name="opencode_go",
        answer_text='{"claims":[]}',
        citations=_sample_citations(),
    )

    assert grounded_answer == BLOCKED_ANSWER_TEXT
    assert metadata.status == "blocked"
    assert metadata.blocked_reason == "empty_structured_claims"
    assert metadata.claim_count == 0
    assert metadata.cited_claim_count == 0


def test_external_answer_is_hard_blocked_when_structured_claim_has_no_evidence_ref():
    grounded_answer, metadata = evaluate_answer_grounding(
        provider_name="opencode_go",
        answer_text='{"claims":[{"text":"一条没有证据 ID 的结构化声明","evidence_refs":[]}]}',
        citations=_sample_citations(),
    )

    assert grounded_answer == BLOCKED_ANSWER_TEXT
    assert metadata.status == "blocked"
    assert metadata.blocked_reason == "claim_without_evidence_ref"
    assert metadata.claim_count == 1
    assert metadata.cited_claim_count == 0


def test_external_answer_is_hard_blocked_when_structured_claim_text_is_blank():
    grounded_answer, metadata = evaluate_answer_grounding(
        provider_name="opencode_go",
        answer_text=(
            '{"claims":[{"text":"   ","evidence_refs":["chunk-cn-ad-gbs-001-abstract"]}]}'
        ),
        citations=_sample_citations(),
    )

    assert grounded_answer == BLOCKED_ANSWER_TEXT
    assert metadata.status == "blocked"
    assert metadata.blocked_reason == "blank_claim_text"
    assert metadata.claim_count == 1
    assert metadata.cited_claim_count == 1
    assert metadata.matched_evidence_refs == ["chunk-cn-ad-gbs-001-abstract"]


def test_external_answer_is_hard_blocked_when_a_claim_sentence_has_no_allowed_ref():
    grounded_answer, metadata = evaluate_answer_grounding(
        provider_name="opencode_go",
        answer_text=(
            "肠道菌群与皮肤屏障异常存在关联 [chunk-cn-ad-gbs-001-abstract]。"
            "模型又补充了一个没有证据 ID 的事实判断。"
        ),
        citations=_sample_citations(),
    )

    assert grounded_answer == BLOCKED_ANSWER_TEXT
    assert metadata.status == "blocked"
    assert metadata.checked is True
    assert metadata.blocked_reason == "structured_claims_parse_error"
    assert metadata.matched_evidence_refs == []
    assert metadata.unsupported_evidence_refs == []
    assert metadata.claim_count == 0
    assert metadata.cited_claim_count == 0


def test_external_answer_is_hard_blocked_when_it_uses_unknown_evidence_ref():
    grounded_answer, metadata = evaluate_answer_grounding(
        provider_name="opencode_go",
        answer_text=(
            '{"claims":[{"text":"回答引用了不存在的证据","evidence_refs":["chunk-unknown-ref"]}]}'
        ),
        citations=_sample_citations(),
    )

    assert grounded_answer == BLOCKED_ANSWER_TEXT
    assert metadata.status == "blocked"
    assert metadata.checked is True
    assert metadata.blocked_reason == "unsupported_evidence_ref"
    assert metadata.matched_evidence_refs == []
    assert metadata.unsupported_evidence_refs == ["chunk-unknown-ref"]
    assert metadata.claim_count == 1
    assert metadata.cited_claim_count == 0


def test_deterministic_answer_skips_grounding_gate():
    answer = "deterministic retrieval keeps the existing answer shape."

    grounded_answer, metadata = evaluate_answer_grounding(
        provider_name="deterministic",
        answer_text=answer,
        citations=_sample_citations(),
    )

    assert grounded_answer == answer
    assert metadata.status == "skipped"
    assert metadata.policy == "structured_claim_refs_v3"
    assert metadata.checked is False
    assert metadata.blocked_reason is None
    assert metadata.claim_count == 0
    assert metadata.cited_claim_count == 0
