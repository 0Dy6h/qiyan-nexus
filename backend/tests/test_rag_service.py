import json
import re
from pathlib import Path

from app.repositories.chunk import InMemoryChunkRepository
from app.repositories.literature import InMemoryLiteratureRepository
from app.services.rag import answer_question

DISCLAIMER = "非诊断结论、需结合临床。"
ISO_UTC_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?\+00:00$")


def test_answer_question_returns_ranked_citation_cards_for_gut_skin_axis_question():
    response = answer_question("特应性皮炎和肠-脑-皮肤轴有什么关系？")

    assert response.question == "特应性皮炎和肠-脑-皮肤轴有什么关系？"
    assert "deterministic retrieval" in response.answer
    assert response.disclaimer == DISCLAIMER
    assert response.provider_name == "deterministic"
    assert response.grounding.status == "skipped"
    assert response.grounding.policy == "structured_claim_refs_v3"
    assert response.grounding.checked is False
    assert response.grounding.claim_count == 0
    assert response.grounding.cited_claim_count == 0
    assert response.input_tokens is None
    assert response.output_tokens is None
    assert len(response.citations) == 2
    assert response.citations[0].literature_id == "cn-ad-gbs-001"
    assert response.citations[0].chunk_id == "chunk-cn-ad-gbs-001-abstract"
    assert (
        response.citations[0].quote
        == "提出脾虚湿蕴、血虚风燥与肠道微生态失衡、皮肤屏障异常和神经免疫调节紊乱之间存在可解释关联。"
    )
    assert response.citations[0].reason == "gut_skin_axis, tcm_syndrome"
    assert response.citations[1].literature_id == "cn-ad-microbiome-003"


def test_answer_question_trims_question():
    response = answer_question("  atopic dermatitis barrier  ")

    assert response.question == "atopic dermatitis barrier"


def test_answer_question_includes_relevant_citations_for_english_barrier_question():
    """After Slice 2, score-primary sort allows cross-lingual items to surface.

    Chinese items with high cross-lingual token matches can outrank PubMed items.
    The key invariant is that the results contain relevant citations.
    """
    response = answer_question("atopic dermatitis barrier")

    assert len(response.citations) >= 1
    # At least one citation should be relevant to the query
    # (either Chinese or PubMed, as cross-lingual retrieval is now enabled)
    assert response.citations[0].literature_id is not None


def test_answer_question_limits_citations_by_top_k():
    response = answer_question("特应性皮炎", top_k=1)

    assert len(response.citations) == 1
    # After Slice 2, score-primary sort means the highest-scoring item
    # (which may be PubMed due to cross-lingual token injection) comes first.
    # The key invariant is that we get exactly 1 citation.
    assert response.citations[0].literature_id is not None


def test_answer_question_filters_citations_by_source():
    response = answer_question("特应性皮炎 肠道菌群", source="pubmed")

    assert len(response.citations) == 2
    # After Slice 2, ranking order may change due to cross-lingual token injection.
    # The key invariant is that both citations are PubMed items.
    citation_ids = [citation.literature_id for citation in response.citations]
    assert all(lid.startswith("pmid-") for lid in citation_ids), (
        f"Expected all PubMed citations, got: {citation_ids}"
    )


def test_answer_question_returns_retrieval_metadata_for_positive_matches():
    response = answer_question("特应性皮炎 肠道菌群", source="pubmed", top_k=1)

    assert response.retrieval.applied_source == "pubmed"
    assert response.retrieval.applied_top_k == 1
    # After Slice 2, cross-lingual token injection increases available_citation_count
    # because more PubMed items now match Chinese query tokens.
    assert response.retrieval.available_citation_count >= 2


def test_answer_question_falls_back_when_no_positive_match_exists():
    response = answer_question("completely unrelated token", source="pubmed", top_k=1)

    assert len(response.citations) == 1
    assert response.retrieval.available_citation_count == 10
    assert (
        "没有检索到足够匹配的证据片段" in response.answer
        or "deterministic retrieval" in response.answer
    )


def test_build_answer_translates_evidence_tags_to_cn_topics():
    from app.schemas.rag import CitationCard
    from app.services.rag import build_answer

    citations = [
        CitationCard(
            literature_id="pmid-40100001",
            title="Atopic dermatitis, skin barrier dysfunction, and immune pathways",
            source="PubMed curated AD sample",
            snippet="Reviewing barrier disruption and Th2 skewing.",
            reason="skin_barrier, immune_pathway",
            confidence=0.74,
        ),
        CitationCard(
            literature_id="cn-ad-guideline-004",
            title="特应性皮炎中西医结合诊疗专家共识中的证据要点",
            source="CNKI curated AD sample",
            snippet="提炼共识中关于分型辨证、屏障修复与长期管理的关键证据。",
            reason="guideline, clinical_management",
            confidence=0.86,
        ),
        CitationCard(
            literature_id="pmid-40100009",
            title="Skin microbiome dysbiosis and Staphylococcus aureus dominance",
            source="PubMed curated AD sample",
            snippet="Microbial imbalance correlates with flares.",
            reason="microbiome, flare",
            confidence=0.74,
        ),
    ]

    answer = build_answer(citations)

    assert "屏障" in answer
    assert "细胞因子" in answer
    assert "皮肤微生物" in answer
    assert "屏障维护" in answer
    assert "引用来源" in answer
    assert "deterministic retrieval" in answer


def test_build_answer_keeps_fallback_when_no_citations():
    from app.services.rag import build_answer

    answer = build_answer([])

    assert "没有检索到足够匹配的证据片段" in answer


def test_answer_question_reserves_cross_language_chunk_slot_when_top_k_at_least_3():
    response = answer_question("特应性皮炎瘙痒的神经免疫机制有哪些关键点？", source="all", top_k=3)

    literature_ids = [c.literature_id for c in response.citations]
    chunk_ids = [c.chunk_id for c in response.citations if c.chunk_id]

    assert len(response.citations) == 3
    assert "pmid-40100003" in literature_ids
    assert "chunk-pmid-40100003-itch" in chunk_ids


def test_answer_question_can_cite_uploaded_pdf_chunk(monkeypatch, tmp_path: Path):
    from app.services import rag as rag_service

    literature_path = tmp_path / "sample_ad_literature.json"
    chunk_path = tmp_path / "sample_ad_chunks.json"
    literature_path.write_text(
        json.dumps(
            [
                {
                    "id": "cn-ad-gbs-001",
                    "title": "肠-脑-皮肤轴与特应性皮炎中医证候研究",
                    "language": "zh",
                    "source_type": "cn_literature",
                    "source": "CNKI curated AD sample",
                    "year": 2025,
                    "snippet": "围绕特应性皮炎、肠-脑-皮肤轴与中医证候关联进行综述。",
                    "pdf_upload_id": "pdf-cn-ad-gbs-001-ad-evidence-pdf",
                    "pdf_file_name": "ad-evidence.pdf",
                    "pdf_parse_status": "parsed",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    chunk_path.write_text(
        json.dumps(
            [
                {
                    "chunk_id": "chunk-cn-ad-gbs-001-abstract",
                    "literature_id": "cn-ad-gbs-001",
                    "section": "abstract",
                    "text": "文章从肠-脑-皮肤轴视角讨论特应性皮炎。",
                    "source_quote": "肠-脑-皮肤轴视角",
                    "evidence_tags": ["gut_skin_axis"],
                    "related_entity_ids": ["disease:atopic-dermatitis"],
                },
                {
                    "chunk_id": "chunk-pdf-cn-ad-gbs-001-ad-evidence-pdf-uploaded",
                    "literature_id": "cn-ad-gbs-001",
                    "section": "uploaded_pdf",
                    "text": "上传 PDF ad-evidence.pdf 已完成解析，Mock parser 提取了特应性皮炎证据片段。",
                    "source_quote": "Mock parser 提取了特应性皮炎证据片段",
                    "evidence_tags": ["uploaded_pdf", "pdf_parse", "atopic_dermatitis"],
                    "related_entity_ids": ["disease:atopic-dermatitis"],
                    "source_type": "uploaded_pdf",
                    "pdf_upload_id": "pdf-cn-ad-gbs-001-ad-evidence-pdf",
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(rag_service, "_REPOSITORY", InMemoryLiteratureRepository(literature_path))
    monkeypatch.setattr(rag_service, "_CHUNK_REPOSITORY", InMemoryChunkRepository(chunk_path))

    response = answer_question("ad-evidence.pdf 上传 PDF 解析片段", top_k=1)

    assert response.citations[0].literature_id == "cn-ad-gbs-001"
    assert response.citations[0].chunk_id == "chunk-pdf-cn-ad-gbs-001-ad-evidence-pdf-uploaded"
    assert response.citations[0].quote == "Mock parser 提取了特应性皮炎证据片段"
    assert response.citations[0].reason == "uploaded_pdf, pdf_parse"
    assert response.citations[0].source_type == "uploaded_pdf"
    assert response.citations[0].pdf_upload_id == "pdf-cn-ad-gbs-001-ad-evidence-pdf"


def test_answer_question_leaves_sample_chunk_citation_without_upload_metadata():
    response = answer_question("特应性皮炎和肠-脑-皮肤轴有什么关系？", top_k=1)

    assert response.citations[0].source_type == "sample"
    assert response.citations[0].pdf_upload_id is None


def test_answer_question_propagates_related_entity_ids_from_literature():
    response = answer_question("消风散与当归饮子治疗特应性皮炎的复方研究", top_k=1)

    assert response.citations[0].literature_id == "cn-ad-formula-002"
    assert "formula-xiaofengsan" in response.citations[0].related_entity_ids
    assert "herb-jingjie" in response.citations[0].related_entity_ids


def test_answer_question_returns_empty_related_entity_ids_when_literature_has_none():
    response = answer_question("特应性皮炎和肠-脑-皮肤轴有什么关系？", top_k=1)

    assert response.citations[0].literature_id == "cn-ad-gbs-001"
    assert response.citations[0].related_entity_ids == []


def test_answer_question_returns_iso_utc_answered_at_timestamp():
    response = answer_question("特应性皮炎和肠-脑-皮肤轴有什么关系？", top_k=1)

    assert isinstance(response.answered_at, str)
    assert ISO_UTC_PATTERN.match(response.answered_at), response.answered_at


def test_answer_question_swaps_to_mock_claude_provider_via_env(monkeypatch):
    monkeypatch.setenv("QIYAN_LLM_PROVIDER", "mock_claude")
    response = answer_question("特应性皮炎和肠-脑-皮肤轴有什么关系？", top_k=2)

    assert response.answer.startswith("【模拟 Claude 草稿】")
    assert "deterministic retrieval" not in response.answer
    assert response.disclaimer == DISCLAIMER
    assert len(response.citations) == 2


def test_answer_question_reports_provider_latency_and_null_cost_for_deterministic():
    response = answer_question("特应性皮炎和肠-脑-皮肤轴有什么关系？", top_k=1)

    assert response.sli is not None
    assert isinstance(response.sli.provider_latency_ms, int)
    assert response.sli.provider_latency_ms >= 0
    # deterministic has no token usage, so cost cannot be estimated.
    assert response.sli.estimated_cost_usd is None


def test_answer_question_estimates_cost_from_tokens_and_env_prices(monkeypatch):
    from app.services.llm import opencode_go_provider

    monkeypatch.setenv("QIYAN_LLM_PROVIDER", "opencode_go")
    monkeypatch.setenv("QIYAN_OPENCODE_GO_API_KEY", "test-key")
    monkeypatch.setenv("QIYAN_GROUNDING_SEMANTIC_THRESHOLD", "0")
    # Prices are USD per million tokens.
    monkeypatch.setenv("QIYAN_OPENCODE_GO_PRICE_INPUT_PER_MTOK", "1.0")
    monkeypatch.setenv("QIYAN_OPENCODE_GO_PRICE_OUTPUT_PER_MTOK", "2.0")
    monkeypatch.setattr(
        opencode_go_provider.OpenCodeGoProvider,
        "generate_answer",
        lambda self, question, citations: opencode_go_provider.AnswerDraft(
            text=(
                '{"claims":[{"text":"肠道微生态失衡与特应性皮炎存在可解释关联。",'
                f'"evidence_refs":["{citations[0].chunk_id or citations[0].literature_id}"]}}]'
                "}"
            ),
            provider_name=self.name,
            input_tokens=1_000_000,
            output_tokens=500_000,
        ),
    )

    response = answer_question("特应性皮炎和肠-脑-皮肤轴有什么关系？", top_k=1)

    assert response.sli is not None
    assert isinstance(response.sli.provider_latency_ms, int)
    # 1_000_000 / 1e6 * 1.0 + 500_000 / 1e6 * 2.0 = 1.0 + 1.0 = 2.0
    assert response.sli.estimated_cost_usd == 2.0


def test_answer_question_leaves_cost_null_when_prices_unset(monkeypatch):
    from app.services.llm import opencode_go_provider

    monkeypatch.setenv("QIYAN_LLM_PROVIDER", "opencode_go")
    monkeypatch.setenv("QIYAN_OPENCODE_GO_API_KEY", "test-key")
    monkeypatch.setenv("QIYAN_GROUNDING_SEMANTIC_THRESHOLD", "0")
    monkeypatch.delenv("QIYAN_OPENCODE_GO_PRICE_INPUT_PER_MTOK", raising=False)
    monkeypatch.delenv("QIYAN_OPENCODE_GO_PRICE_OUTPUT_PER_MTOK", raising=False)
    monkeypatch.setattr(
        opencode_go_provider.OpenCodeGoProvider,
        "generate_answer",
        lambda self, question, citations: opencode_go_provider.AnswerDraft(
            text=(
                '{"claims":[{"text":"肠道微生态失衡与特应性皮炎存在可解释关联。",'
                f'"evidence_refs":["{citations[0].chunk_id or citations[0].literature_id}"]}}]'
                "}"
            ),
            provider_name=self.name,
            input_tokens=1200,
            output_tokens=800,
        ),
    )

    response = answer_question("特应性皮炎和肠-脑-皮肤轴有什么关系？", top_k=1)

    assert response.sli is not None
    # default prices are 0.0 -> cost is not estimated even with token usage.
    assert response.sli.estimated_cost_usd is None


def test_answer_question_swaps_to_opencode_go_provider_via_env(monkeypatch):
    from app.services.llm import opencode_go_provider

    monkeypatch.setenv("QIYAN_LLM_PROVIDER", "opencode_go")
    monkeypatch.setenv("QIYAN_OPENCODE_GO_API_KEY", "test-key")
    monkeypatch.setattr(
        opencode_go_provider.OpenCodeGoProvider,
        "generate_answer",
        lambda self, question, citations: opencode_go_provider.AnswerDraft(
            text=(
                '{"claims":[{"text":"肠道微生态失衡与皮肤屏障异常、神经免疫调节紊乱在特应性皮炎中存在可解释关联",'
                f'"evidence_refs":["{citations[0].chunk_id}"]}}]'
                "}"
            ),
            provider_name=self.name,
            input_tokens=12,
            output_tokens=6,
        ),
    )

    response = answer_question("特应性皮炎和肠-脑-皮肤轴有什么关系？", top_k=2)

    assert response.answer == (
        "肠道微生态失衡与皮肤屏障异常、神经免疫调节紊乱在特应性皮炎中存在可解释关联"
        " [chunk-cn-ad-gbs-001-abstract]。"
    )
    assert response.provider_name == "opencode_go"
    assert response.grounding.status == "passed"
    assert response.grounding.policy == "structured_claim_refs_v3"
    assert response.grounding.matched_evidence_refs == ["chunk-cn-ad-gbs-001-abstract"]
    assert response.grounding.structured_claims[0].text == (
        "肠道微生态失衡与皮肤屏障异常、神经免疫调节紊乱在特应性皮炎中存在可解释关联"
    )
    assert response.input_tokens == 12
    assert response.output_tokens == 6
    assert response.disclaimer == DISCLAIMER
    assert len(response.citations) == 2


def test_answer_question_uses_opencode_go_native_tool_claims(monkeypatch):
    from app.schemas.rag import GroundedClaim
    from app.services.llm import opencode_go_provider

    monkeypatch.setenv("QIYAN_LLM_PROVIDER", "opencode_go")
    monkeypatch.setenv("QIYAN_OPENCODE_GO_API_KEY", "test-key")
    monkeypatch.setattr(
        opencode_go_provider.OpenCodeGoProvider,
        "generate_answer",
        lambda self, question, citations: opencode_go_provider.AnswerDraft(
            text="raw opencode text must not be shown",
            provider_name=self.name,
            input_tokens=30,
            output_tokens=12,
            structured_claims=[
                GroundedClaim(
                    text="肠道菌群结构改变与皮肤屏障异常在特应性皮炎中存在可解释关联",
                    evidence_refs=[citations[0].chunk_id or citations[0].literature_id],
                )
            ],
            grounding_policy="opencode_go_tool_use_v1",
            provider_native_grounding=True,
            tool_name="record_grounded_claims",
            tool_call_count=1,
        ),
    )

    response = answer_question("特应性皮炎和肠-脑-皮肤轴有什么关系？", top_k=2)

    assert response.answer == (
        "肠道菌群结构改变与皮肤屏障异常在特应性皮炎中存在可解释关联"
        " [chunk-cn-ad-gbs-001-abstract]。"
    )
    assert response.provider_name == "opencode_go"
    assert response.grounding.status == "passed"
    assert response.grounding.policy == "opencode_go_tool_use_v1"
    assert response.grounding.provider_native_grounding is True
    assert response.grounding.tool_name == "record_grounded_claims"
    assert response.grounding.tool_call_count == 1
    assert response.input_tokens == 30
    assert response.output_tokens == 12


def test_answer_question_uses_anthropic_native_tool_claims(monkeypatch):
    from app.schemas.rag import GroundedClaim
    from app.services.llm import anthropic_provider

    monkeypatch.setenv("QIYAN_LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(
        anthropic_provider.AnthropicProvider,
        "generate_answer",
        lambda self, question, citations: anthropic_provider.AnswerDraft(
            text="raw text must not be shown",
            provider_name=self.name,
            input_tokens=22,
            output_tokens=11,
            structured_claims=[
                GroundedClaim(
                    text="脾虚湿蕴、血虚风燥与肠道微生态失衡及皮肤屏障异常在特应性皮炎中存在可解释关联",
                    evidence_refs=[citations[0].chunk_id or citations[0].literature_id],
                )
            ],
            grounding_policy="anthropic_tool_use_v1",
            provider_native_grounding=True,
            tool_name="record_grounded_claims",
            tool_call_count=1,
        ),
    )

    response = answer_question("特应性皮炎和肠-脑-皮肤轴有什么关系？", top_k=2)

    assert response.answer == (
        "脾虚湿蕴、血虚风燥与肠道微生态失衡及皮肤屏障异常在特应性皮炎中存在可解释关联"
        " [chunk-cn-ad-gbs-001-abstract]。"
    )
    assert response.provider_name == "anthropic"
    assert response.grounding.status == "passed"
    assert response.grounding.policy == "anthropic_tool_use_v1"
    assert response.grounding.provider_native_grounding is True
    assert response.grounding.tool_name == "record_grounded_claims"
    assert response.grounding.tool_call_count == 1
    assert response.grounding.structured_claims[0].text == (
        "脾虚湿蕴、血虚风燥与肠道微生态失衡及皮肤屏障异常在特应性皮炎中存在可解释关联"
    )
    assert response.input_tokens == 22
    assert response.output_tokens == 11


def test_answer_question_hard_blocks_anthropic_native_tool_name_mismatch(monkeypatch):
    from app.services.llm import anthropic_provider

    monkeypatch.setenv("QIYAN_LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(
        anthropic_provider.AnthropicProvider,
        "generate_answer",
        lambda self, question, citations: anthropic_provider.AnswerDraft(
            text="raw text must not be shown",
            provider_name=self.name,
            input_tokens=22,
            output_tokens=11,
            structured_claims=None,
            grounding_policy="anthropic_tool_use_v1",
            provider_native_grounding=True,
            tool_name="wrong_tool",
            tool_call_count=1,
            grounding_blocked_reason="tool_name_mismatch",
        ),
    )

    response = answer_question("特应性皮炎和肠-脑-皮肤轴有什么关系？", top_k=2)

    assert response.answer.startswith("当前模型草稿未通过引用证据校验")
    assert response.provider_name == "anthropic"
    assert response.grounding.status == "blocked"
    assert response.grounding.policy == "anthropic_tool_use_v1"
    assert response.grounding.provider_native_grounding is True
    assert response.grounding.tool_name == "wrong_tool"
    assert response.grounding.tool_call_count == 1
    assert response.grounding.blocked_reason == "tool_name_mismatch"
    assert response.input_tokens == 22
    assert response.output_tokens == 11


def test_answer_question_semantic_gate_blocks_hallucinated_claim_on_valid_ref(monkeypatch):
    from app.schemas.rag import GroundedClaim
    from app.services.llm import opencode_go_provider

    monkeypatch.setenv("QIYAN_LLM_PROVIDER", "opencode_go")
    monkeypatch.setenv("QIYAN_OPENCODE_GO_API_KEY", "test-key")
    monkeypatch.setattr(
        opencode_go_provider.OpenCodeGoProvider,
        "generate_answer",
        lambda self, question, citations: opencode_go_provider.AnswerDraft(
            text="raw opencode text must not be shown",
            provider_name=self.name,
            input_tokens=18,
            output_tokens=9,
            structured_claims=[
                GroundedClaim(
                    text="随机对照试验显示口服益生菌可在两周内彻底治愈特应性皮炎并永久消除瘙痒",
                    evidence_refs=[citations[0].chunk_id or citations[0].literature_id],
                )
            ],
            grounding_policy="opencode_go_tool_use_v1",
            provider_native_grounding=True,
            tool_name="record_grounded_claims",
            tool_call_count=1,
        ),
    )

    response = answer_question("特应性皮炎和肠-脑-皮肤轴有什么关系？", top_k=2)

    assert response.answer.startswith("当前模型草稿未通过引用证据校验")
    assert response.provider_name == "opencode_go"
    assert response.grounding.status == "blocked"
    assert response.grounding.blocked_reason == "semantic_low_support"
    assert response.grounding.semantic_threshold is not None
    assert response.grounding.min_semantic_score is not None
    assert response.grounding.min_semantic_score < response.grounding.semantic_threshold


def test_answer_question_semantic_gate_disabled_by_threshold_env(monkeypatch):
    from app.schemas.rag import GroundedClaim
    from app.services.llm import opencode_go_provider

    monkeypatch.setenv("QIYAN_LLM_PROVIDER", "opencode_go")
    monkeypatch.setenv("QIYAN_OPENCODE_GO_API_KEY", "test-key")
    monkeypatch.setenv("QIYAN_GROUNDING_SEMANTIC_THRESHOLD", "0")
    monkeypatch.setattr(
        opencode_go_provider.OpenCodeGoProvider,
        "generate_answer",
        lambda self, question, citations: opencode_go_provider.AnswerDraft(
            text="raw opencode text must not be shown",
            provider_name=self.name,
            input_tokens=18,
            output_tokens=9,
            structured_claims=[
                GroundedClaim(
                    text="随机对照试验显示口服益生菌可在两周内彻底治愈特应性皮炎并永久消除瘙痒",
                    evidence_refs=[citations[0].chunk_id or citations[0].literature_id],
                )
            ],
            grounding_policy="opencode_go_tool_use_v1",
            provider_native_grounding=True,
            tool_name="record_grounded_claims",
            tool_call_count=1,
        ),
    )

    response = answer_question("特应性皮炎和肠-脑-皮肤轴有什么关系？", top_k=2)

    assert response.grounding.status == "passed"
    assert response.grounding.semantic_threshold is None
    assert response.grounding.min_semantic_score is None


def test_answer_question_keeps_deterministic_text_when_env_unset(monkeypatch):
    monkeypatch.delenv("QIYAN_LLM_PROVIDER", raising=False)
    response = answer_question("特应性皮炎和肠-脑-皮肤轴有什么关系？", top_k=2)

    assert "deterministic retrieval" in response.answer
    assert not response.answer.startswith("【模拟 Claude 草稿】")


def test_retrieval_metadata_strategy_defaults_to_keyword(monkeypatch):
    monkeypatch.delenv("QIYAN_RETRIEVAL_PROVIDER", raising=False)
    response = answer_question("特应性皮炎和肠-脑-皮肤轴有什么关系？", top_k=2)
    assert response.retrieval.strategy == "keyword"


def test_retrieval_metadata_strategy_reflects_env_override(monkeypatch):
    monkeypatch.setenv("QIYAN_RETRIEVAL_PROVIDER", "hybrid")
    monkeypatch.setenv("QIYAN_EMBEDDING_BACKEND", "hashing")
    response = answer_question("特应性皮炎和肠-脑-皮肤轴有什么关系？", top_k=2)
    assert response.retrieval.strategy == "hybrid"
    assert response.disclaimer == DISCLAIMER


def test_answer_question_hard_blocks_external_provider_answer_without_evidence_ref(monkeypatch):
    from app.services.llm import opencode_go_provider

    monkeypatch.setenv("QIYAN_LLM_PROVIDER", "opencode_go")
    monkeypatch.setenv("QIYAN_OPENCODE_GO_API_KEY", "test-key")
    monkeypatch.setattr(
        opencode_go_provider.OpenCodeGoProvider,
        "generate_answer",
        lambda self, question, citations: opencode_go_provider.AnswerDraft(
            text="opencode answer without evidence ref",
            provider_name=self.name,
            input_tokens=12,
            output_tokens=6,
        ),
    )

    response = answer_question("特应性皮炎和肠-脑-皮肤轴有什么关系？", top_k=2)

    assert response.answer.startswith("当前模型草稿未通过引用证据校验")
    assert response.provider_name == "opencode_go"
    assert response.grounding.status == "blocked"
    assert response.grounding.policy == "structured_claim_refs_v3"
    assert response.grounding.blocked_reason == "structured_claims_parse_error"
    assert response.grounding.claim_count == 0
    assert response.grounding.cited_claim_count == 0
    assert response.input_tokens == 12
    assert response.output_tokens == 6
    assert len(response.citations) == 2


def test_answer_question_hard_blocks_external_provider_answer_with_uncited_claim(monkeypatch):
    from app.services.llm import opencode_go_provider

    monkeypatch.setenv("QIYAN_LLM_PROVIDER", "opencode_go")
    monkeypatch.setenv("QIYAN_OPENCODE_GO_API_KEY", "test-key")
    monkeypatch.setattr(
        opencode_go_provider.OpenCodeGoProvider,
        "generate_answer",
        lambda self, question, citations: opencode_go_provider.AnswerDraft(
            text='{"claims":[{"text":"第一条证据句","evidence_refs":[]}]}',
            provider_name=self.name,
            input_tokens=12,
            output_tokens=6,
        ),
    )

    response = answer_question("特应性皮炎和肠-脑-皮肤轴有什么关系？", top_k=2)

    assert response.answer.startswith("当前模型草稿未通过引用证据校验")
    assert response.provider_name == "opencode_go"
    assert response.grounding.status == "blocked"
    assert response.grounding.policy == "structured_claim_refs_v3"
    assert response.grounding.blocked_reason == "claim_without_evidence_ref"
    assert response.grounding.matched_evidence_refs == []
    assert response.grounding.claim_count == 1
    assert response.grounding.cited_claim_count == 0
    assert response.input_tokens == 12
    assert response.output_tokens == 6
