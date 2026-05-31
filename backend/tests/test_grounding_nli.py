"""Tests for the opt-in NLI entailment second-stage grounding gate.

The gate is default-OFF and only engages for external providers when an NLI
backend + threshold are supplied. These tests use a deterministic fake backend
so CI never imports transformers or downloads the ~560 MB mDeBERTa weights —
mirroring how the embedding tests avoid sentence-transformers.
"""

from app.schemas.rag import CitationCard
from app.services.grounding import BLOCKED_ANSWER_TEXT, evaluate_answer_grounding
from app.services.nli import NliBackend, select_nli_backend

_CHUNK_TEXT = (
    "文章从肠-脑-皮肤轴视角讨论特应性皮炎的中医证候演变，"
    "提出脾虚湿蕴、血虚风燥与肠道微生态失衡、皮肤屏障异常和神经免疫调节紊乱之间存在可解释关联。"
)


class _FakeNliBackend:
    """Maps each hypothesis to a fixed entailment score; no model involved."""

    name = "fake"

    def __init__(self, scores: dict[str, float], default: float = 0.0) -> None:
        self._scores = scores
        self._default = default

    def entailment(self, premise: str, hypothesis: str) -> float:
        return self._scores.get(hypothesis, self._default)


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


def test_nli_gate_passes_entailed_claim_and_surfaces_score():
    faithful = "特应性皮炎与肠道微生态失衡、皮肤屏障异常和神经免疫调节紊乱存在可解释关联"
    backend = _FakeNliBackend({faithful: 0.98})

    grounded_answer, metadata = evaluate_answer_grounding(
        provider_name="opencode_go",
        answer_text=_claims_json(faithful),
        citations=_citation_with_quote(),
        nli_backend=backend,
        nli_threshold=0.5,
    )

    assert metadata.status == "passed"
    assert grounded_answer != BLOCKED_ANSWER_TEXT
    assert metadata.nli_threshold == 0.5
    assert metadata.min_entailment_score == 0.98
    assert metadata.structured_claims[0].entailment_score == 0.98


def test_nli_gate_blocks_on_topic_fabrication_below_threshold():
    fabrication = "已通过随机对照试验证实纠正肠道微生态失衡可在四周内完全治愈特应性皮炎"
    backend = _FakeNliBackend({fabrication: 0.001})

    grounded_answer, metadata = evaluate_answer_grounding(
        provider_name="opencode_go",
        answer_text=_claims_json(fabrication),
        citations=_citation_with_quote(),
        nli_backend=backend,
        nli_threshold=0.5,
    )

    assert metadata.status == "blocked"
    assert metadata.blocked_reason == "nli_low_entailment"
    assert grounded_answer == BLOCKED_ANSWER_TEXT
    assert metadata.min_entailment_score is not None
    assert metadata.min_entailment_score < 0.5
    assert metadata.nli_threshold == 0.5


def test_nli_gate_is_noop_when_backend_or_threshold_missing():
    claim = "特应性皮炎与肠道微生态失衡存在可解释关联"
    backend = _FakeNliBackend({claim: 0.001})

    # threshold None -> gate disabled even with a backend present
    grounded_answer, metadata = evaluate_answer_grounding(
        provider_name="opencode_go",
        answer_text=_claims_json(claim),
        citations=_citation_with_quote(),
        nli_backend=backend,
        nli_threshold=None,
    )

    assert metadata.status == "passed"
    assert grounded_answer != BLOCKED_ANSWER_TEXT
    assert metadata.nli_threshold is None
    assert metadata.min_entailment_score is None
    assert metadata.structured_claims[0].entailment_score is None


def test_select_nli_backend_disabled_by_default():
    assert select_nli_backend(None) is None
    assert select_nli_backend("") is None
    assert select_nli_backend("off") is None
    assert select_nli_backend("none") is None


def test_select_nli_backend_unknown_name_falls_back_to_disabled():
    assert select_nli_backend("not-a-real-backend") is None


def test_transformers_nli_backend_is_selectable_without_loading_model():
    backend = select_nli_backend("transformers")
    assert backend is not None
    assert isinstance(backend, NliBackend)
    assert backend.name == "transformers"


def test_adversarial_nli_fixture_is_balanced_and_well_formed():
    """Lock the structure of the adversarial NLI fixture (no model load in CI).

    These pairs probe NLI failure modes the live-smoke fixture never tested
    (negation, number tampering, partial support, hedge removal, cross-chunk
    synthesis, overgeneralization, entity splicing). Scoring on the real model is
    done out-of-band by the eval doc; here we only guard the data shape so the
    documented separation result stays meaningful.
    """

    from pathlib import Path

    from app.schemas.eval import load_grounding_semantic_pairs

    path = Path(__file__).resolve().parents[1] / "data" / "evals" / "grounding_nli_adversarial.json"
    pairs = load_grounding_semantic_pairs(path)

    assert len(pairs) >= 18
    supported = [p for p in pairs if p.supported]
    non_supported = [p for p in pairs if not p.supported]
    assert supported, "adversarial fixture must contain faithful claims"
    assert non_supported, "adversarial fixture must contain non-supported claims"
    assert len({p.id for p in pairs}) == len(pairs), "pair ids must be unique"
    assert all(p.claim and p.chunk_text for p in pairs)
    # Every pair must carry a note explaining its intended failure mode / label.
    assert all(p.note for p in pairs), "each adversarial pair must document its rationale"
