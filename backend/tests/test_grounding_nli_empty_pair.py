"""Test NLI grounding when all evidence_refs point to missing references.

When structured_claims reference evidence IDs that are not in the citation list
(e.g., a hallucinated chunk ID or a literature_id with no quote), the batch NLI
loop produces zero (premise, hypothesis) pairs. The empty-pair branch must block
with min_entailment_score=0.0 rather than pass through.
"""

from app.schemas.rag import CitationCard
from app.services.grounding import BLOCKED_ANSWER_TEXT, evaluate_answer_grounding


class _FakeNliBackend:
    """Deterministic NLI stub for testing empty-pair logic."""

    name = "fake"

    def entailment(self, premise: str, hypothesis: str) -> float:
        return 1.0

    def entailment_batch(self, premises: list[str], hypotheses: list[str]) -> list[float]:
        return [1.0] * len(hypotheses)


def _claims_json(claim_text: str, ref: str) -> str:
    return f'{{"claims":[{{"text":"{claim_text}","evidence_refs":["{ref}"]}}]}}'


def test_nli_gate_blocks_when_all_evidence_refs_are_missing():
    """When all evidence_refs are missing, min_entailment_score must be 0.0 and block."""
    citation_without_quote = CitationCard(
        literature_id="cn-ad-gbs-001",
        chunk_id=None,
        title="肠-脑-皮肤轴与特应性皮炎中医证候研究",
        source="CNKI curated AD sample",
        snippet="围绕特应性皮炎、肠-脑-皮肤轴与中医证候关联进行综述。",
        quote=None,  # No quote → reference_text will be the snippet
        reason="gut_skin_axis",
        confidence=0.86,
    )
    # Claim references a chunk_id that does not exist in the citation list.
    claim = "特应性皮炎与肠道微生态失衡存在可解释关联"
    missing_ref = "chunk-that-does-not-exist"
    backend = _FakeNliBackend()

    grounded_answer, metadata = evaluate_answer_grounding(
        provider_name="opencode_go",
        answer_text=_claims_json(claim, missing_ref),
        citations=[citation_without_quote],
        nli_backend=backend,
        nli_threshold=0.5,
    )

    assert metadata.status == "blocked"
    assert metadata.blocked_reason == "unsupported_evidence_ref"
    assert grounded_answer == BLOCKED_ANSWER_TEXT


def test_nli_gate_blocks_when_citation_has_no_text():
    """When citation exists but has no quote/snippet, pair_claim_idx is empty → block."""
    empty_citation = CitationCard(
        literature_id="cn-ad-gbs-001",
        chunk_id="chunk-cn-ad-gbs-001-abstract",
        title="肠-脑-皮肤轴与特应性皮炎中医证候研究",
        source="CNKI curated AD sample",
        snippet="",  # Empty snippet
        quote=None,
        reason="gut_skin_axis",
        confidence=0.86,
    )
    claim = "特应性皮炎与肠道微生态失衡存在可解释关联"
    backend = _FakeNliBackend()

    grounded_answer, metadata = evaluate_answer_grounding(
        provider_name="opencode_go",
        answer_text=_claims_json(claim, "chunk-cn-ad-gbs-001-abstract"),
        citations=[empty_citation],
        nli_backend=backend,
        nli_threshold=0.5,
    )

    assert metadata.status == "blocked"
    assert metadata.blocked_reason == "nli_low_entailment"
    assert grounded_answer == BLOCKED_ANSWER_TEXT
    assert metadata.min_entailment_score == 0.0
    assert metadata.structured_claims[0].entailment_score == 0.0
