from app.schemas.rag import GroundingMetadata, ProviderSli, RagAnswerResponse, RetrievalMetadata
from scripts.capture_real_answer_claims import _build_capture_meta, _build_question_capture_entry


def test_build_question_capture_entry_summarizes_claim_refs_and_sli():
    response = RagAnswerResponse(
        question="特应性皮炎和肠-脑-皮肤轴有什么关系？",
        answer="当前模型草稿未通过引用证据校验，系统已拦截展示。",
        disclaimer="非诊断结论、需结合临床。",
        retrieval=RetrievalMetadata(
            applied_source="all",
            applied_top_k=2,
            available_citation_count=4,
            strategy="keyword",
        ),
        citations=[],
        answered_at="2026-06-02T00:00:00+00:00",
        provider_name="opencode_go",
        grounding=GroundingMetadata(
            status="blocked",
            checked=True,
            blocked_reason="nli_low_entailment",
            min_semantic_score=0.42,
            nli_threshold=0.5,
            min_entailment_score=0.12,
        ),
        input_tokens=1234,
        output_tokens=321,
        sli=ProviderSli(provider_latency_ms=9876, estimated_cost_usd=0.0042),
    )
    claim_entries = [
        {"text": "没有证据引用的声明", "evidence_refs": []},
        {"text": "单证据声明", "evidence_refs": ["chunk-1"]},
        {"text": "多证据声明", "evidence_refs": ["chunk-1", "chunk-2"]},
    ]

    entry = _build_question_capture_entry(
        question_id="rag-eval-001",
        question=response.question,
        source_preference="all",
        response=response,
        claim_entries=claim_entries,
    )

    assert entry["provider_name"] == "opencode_go"
    assert entry["grounding_status"] == "blocked"
    assert entry["blocked_reason"] == "nli_low_entailment"
    assert entry["retrieval_strategy"] == "keyword"
    assert entry["claim_count"] == 3
    assert entry["claims_with_zero_refs"] == 1
    assert entry["claims_with_one_ref"] == 1
    assert entry["claims_with_multi_refs"] == 1
    assert entry["min_semantic_score"] == 0.42
    assert entry["nli_threshold"] == 0.5
    assert entry["min_entailment_score"] == 0.12
    assert entry["input_tokens"] == 1234
    assert entry["output_tokens"] == 321
    assert entry["provider_latency_ms"] == 9876
    assert entry["estimated_cost_usd"] == 0.0042
    assert entry["claims"] == claim_entries


def test_build_capture_meta_summarizes_statuses_and_claim_ref_shapes(monkeypatch):
    monkeypatch.setenv("QIYAN_LLM_PROVIDER", "opencode_go")
    monkeypatch.setenv("QIYAN_EMBEDDING_BACKEND", "bge")
    monkeypatch.setenv("QIYAN_GROUNDING_SEMANTIC_THRESHOLD", "0.3")
    monkeypatch.setenv("QIYAN_OPENCODE_GO_MAX_TOKENS", "4000")

    meta = _build_capture_meta(
        "live_opencode_go",
        [
            {
                "grounding_status": "blocked",
                "blocked_reason": "nli_low_entailment",
                "claim_count": 3,
                "claims_with_zero_refs": 0,
                "claims_with_one_ref": 3,
                "claims_with_multi_refs": 0,
                "provider_name": "opencode_go",
            },
            {
                "grounding_status": "passed",
                "blocked_reason": None,
                "claim_count": 1,
                "claims_with_zero_refs": 0,
                "claims_with_one_ref": 1,
                "claims_with_multi_refs": 0,
                "provider_name": "opencode_go",
            },
            {
                "grounding_status": "blocked",
                "blocked_reason": "semantic_low_support",
                "claim_count": 2,
                "claims_with_zero_refs": 1,
                "claims_with_one_ref": 0,
                "claims_with_multi_refs": 1,
                "provider_name": "deterministic",
            },
        ],
    )

    assert meta["source"] == "live_opencode_go"
    assert meta["questions_captured"] == 3
    assert meta["total_claims"] == 6
    assert meta["grounding_status_counts"] == {"blocked": 2, "passed": 1}
    assert meta["blocked_reason_counts"] == {
        "nli_low_entailment": 1,
        "semantic_low_support": 1,
    }
    assert meta["provider_counts"] == {"opencode_go": 2, "deterministic": 1}
    assert meta["claims_with_zero_refs"] == 1
    assert meta["claims_with_one_ref"] == 4
    assert meta["claims_with_multi_refs"] == 1
    assert meta["llm_provider"] == "opencode_go"
    assert meta["embedding_backend"] == "bge"
