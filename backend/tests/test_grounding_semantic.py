from pathlib import Path

from app.core.config import Settings
from app.schemas.eval import GroundingSemanticPair, load_grounding_semantic_pairs
from app.schemas.rag import CitationCard
from app.services.eval import run_grounding_semantic_separation
from app.services.grounding import (
    BLOCKED_ANSWER_TEXT,
    evaluate_answer_grounding,
    score_claim_support,
)
from app.services.retrieval.embedding import HashingEmbeddingBackend

_DEFAULT_THRESHOLD = Settings().grounding_semantic_threshold

_PAIRS_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "evals" / "grounding_semantic_pairs.json"
)
_BGE_PAIRS_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "evals" / "grounding_semantic_pairs_bge.json"
)


def _load_pairs() -> list[GroundingSemanticPair]:
    return load_grounding_semantic_pairs(_PAIRS_PATH)


def _load_bge_pairs() -> list[GroundingSemanticPair]:
    return load_grounding_semantic_pairs(_BGE_PAIRS_PATH)


def test_load_grounding_semantic_pairs_has_both_labels():
    pairs = _load_pairs()

    assert len(pairs) >= 20
    supported = [pair for pair in pairs if pair.supported]
    hallucinated = [pair for pair in pairs if not pair.supported]
    assert supported, "fixture must contain faithful (supported=true) pairs"
    assert hallucinated, "fixture must contain hallucinated (supported=false) pairs"
    assert len(supported) == len(hallucinated), (
        "fixture should pair each faithful claim with a hallucinated counterpart"
    )
    assert all(pair.claim and pair.chunk_text for pair in pairs)
    assert len({pair.id for pair in pairs}) == len(pairs), "pair ids must be unique"


def test_bge_recalibration_fixture_is_balanced_and_paired():
    """Lock the structure of the real-LLM-style recalibration fixture.

    These pairs are faithful claims lifted verbatim from the 2026-05-31 live
    smoke, each twinned with an on-topic hard negative. The fixture is scored on
    the bge backend by ``scripts/sweep_threshold_recalibration.py``; it must keep
    its ``-faithful`` / ``-hallucinated`` pairing so the sweep stays valid.
    """

    pairs = _load_bge_pairs()
    by_id = {pair.id: pair for pair in pairs}

    supported = [pair for pair in pairs if pair.supported]
    hallucinated = [pair for pair in pairs if not pair.supported]
    assert supported, "bge fixture must contain faithful claims"
    assert hallucinated, "bge fixture must contain hard-negative claims"
    assert len(supported) == len(hallucinated), "each faithful claim needs a hard-negative twin"
    assert len({pair.id for pair in pairs}) == len(pairs), "pair ids must be unique"
    for faithful_pair in supported:
        twin_id = faithful_pair.id.replace("-faithful", "-hallucinated")
        assert twin_id in by_id, f"{faithful_pair.id} is missing its hard-negative twin {twin_id}"
        # The hard negative reuses the faithful claim's cited chunk so the gate
        # is tested against on-topic fabrication, not a topic mismatch.
        assert by_id[twin_id].chunk_text == faithful_pair.chunk_text


def test_score_claim_support_returns_normalised_cosine():
    backend = HashingEmbeddingBackend()

    identical = score_claim_support("肠道菌群与皮肤屏障相关", "肠道菌群与皮肤屏障相关", backend)
    assert 0.0 <= identical <= 1.0
    assert identical > 0.99, "identical text should score near 1.0"


def test_score_claim_support_separates_faithful_from_hallucinated():
    backend = HashingEmbeddingBackend()
    pairs = _load_pairs()
    by_id = {pair.id: pair for pair in pairs}

    faithful = [pair for pair in pairs if pair.supported]
    for faithful_pair in faithful:
        hallucinated_id = faithful_pair.id.replace("-faithful", "-hallucinated")
        hallucinated_pair = by_id[hallucinated_id]
        faithful_score = score_claim_support(faithful_pair.claim, faithful_pair.chunk_text, backend)
        hallucinated_score = score_claim_support(
            hallucinated_pair.claim, hallucinated_pair.chunk_text, backend
        )
        assert faithful_score > hallucinated_score, (
            f"{faithful_pair.id} ({faithful_score:.3f}) must outscore"
            f" {hallucinated_id} ({hallucinated_score:.3f}) on the hashing backend"
        )


_CHUNK_TEXT = (
    "文章从肠-脑-皮肤轴视角讨论特应性皮炎的中医证候演变，"
    "提出脾虚湿蕴、血虚风燥与肠道微生态失衡、皮肤屏障异常和神经免疫调节紊乱之间存在可解释关联。"
)


def _citation_with_quote() -> list[CitationCard]:
    return [
        CitationCard(
            literature_id="cn-ad-gbs-001",
            chunk_id="chunk-cn-ad-gbs-001-abstract",
            title="肠-脑-皮肤轴与特应性皮炎中医证候研究",
            source="CNKI curated AD sample",
            snippet="围绕特应性皮炎、肠-脑-皮肤轴与中医证候关联进行综述。",
            quote=_CHUNK_TEXT,
            reason="gut_skin_axis, tcm_syndrome",
            confidence=0.86,
        )
    ]


def _claims_json(claim_text: str) -> str:
    return (
        '{"claims":[{"text":"'
        + claim_text
        + '","evidence_refs":["chunk-cn-ad-gbs-001-abstract"]}]}'
    )


def test_semantic_gate_passes_faithful_claim_and_surfaces_score():
    backend = HashingEmbeddingBackend()
    faithful_claim = (
        "特应性皮炎的中医证候演变与肠道微生态失衡、皮肤屏障异常及神经免疫调节紊乱存在可解释关联"
    )

    grounded_answer, metadata = evaluate_answer_grounding(
        provider_name="opencode_go",
        answer_text=_claims_json(faithful_claim),
        citations=_citation_with_quote(),
        semantic_backend=backend,
        semantic_threshold=0.2,
    )

    assert metadata.status == "passed"
    assert grounded_answer != BLOCKED_ANSWER_TEXT
    assert metadata.semantic_threshold == 0.2
    assert metadata.min_semantic_score is not None
    assert metadata.min_semantic_score >= 0.2
    assert metadata.structured_claims[0].semantic_score == metadata.min_semantic_score


def test_semantic_gate_blocks_low_support_claim():
    backend = HashingEmbeddingBackend()
    hallucinated_claim = "随机对照试验显示口服益生菌可在两周内彻底治愈特应性皮炎并永久消除瘙痒"

    grounded_answer, metadata = evaluate_answer_grounding(
        provider_name="opencode_go",
        answer_text=_claims_json(hallucinated_claim),
        citations=_citation_with_quote(),
        semantic_backend=backend,
        semantic_threshold=0.5,
    )

    assert metadata.status == "blocked"
    assert metadata.blocked_reason == "semantic_low_support"
    assert grounded_answer == BLOCKED_ANSWER_TEXT
    assert metadata.min_semantic_score is not None
    assert metadata.min_semantic_score < 0.5
    assert metadata.semantic_threshold == 0.5


def test_semantic_gate_is_noop_when_threshold_is_none():
    backend = HashingEmbeddingBackend()
    hallucinated_claim = "随机对照试验显示口服益生菌可在两周内彻底治愈特应性皮炎并永久消除瘙痒"

    grounded_answer, metadata = evaluate_answer_grounding(
        provider_name="opencode_go",
        answer_text=_claims_json(hallucinated_claim),
        citations=_citation_with_quote(),
        semantic_backend=backend,
        semantic_threshold=None,
    )

    assert metadata.status == "passed"
    assert grounded_answer != BLOCKED_ANSWER_TEXT
    assert metadata.semantic_threshold is None
    assert metadata.min_semantic_score is None
    assert metadata.structured_claims[0].semantic_score is None


def test_separation_eval_default_threshold_has_no_false_rejects_on_hashing():
    report = run_grounding_semantic_separation(_DEFAULT_THRESHOLD, backend_name="hashing")

    assert report["backend_name"] == "hashing"
    assert report["false_rejected_faithful"] == 0, (
        "the default threshold must not block any genuinely faithful claim on the"
        f" hashing proxy (min faithful score = {report['min_faithful_score']})"
    )
    assert report["min_faithful_score"] > _DEFAULT_THRESHOLD


def test_separation_eval_default_threshold_rejects_most_hallucinations_on_hashing():
    report = run_grounding_semantic_separation(_DEFAULT_THRESHOLD, backend_name="hashing")

    # The hashing backend is a lexical proxy: one high-overlap fabrication (reusing
    # most of the source chunk's characters) can slip through, so we require a
    # strong majority rejected rather than all of them. The bge backend separates
    # far more cleanly; see docs/current-state.md.
    assert report["rejected_hallucinated"] >= 7
    assert report["false_accepted_hallucinated"] <= 3


def test_separation_eval_paired_separation_is_perfect_on_hashing():
    report = run_grounding_semantic_separation(_DEFAULT_THRESHOLD, backend_name="hashing")

    assert report["paired_separation"] == report["paired_total"], (
        "every faithful claim must outscore its own hallucinated twin"
    )
