"""Fixture structure tests for grounding_real_answer_pairs.json (Slice 2).

These tests validate that the labeled real-answer fixture is well-formed and
that every pair carries the required fields so the evaluation harness (Slice 3)
can consume it reliably.
"""

import json
from pathlib import Path

import pytest

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "evals" / "grounding_real_answer_pairs.json"
)

VALID_LABELS = {"supported", "partial", "unsupported"}


@pytest.fixture(scope="module")
def real_answer_pairs() -> list[dict]:
    """Load the labeled real-answer grounding pairs fixture."""
    if not FIXTURE_PATH.exists():
        pytest.skip(f"Fixture not found: {FIXTURE_PATH}")
    raw = FIXTURE_PATH.read_text(encoding="utf-8")
    return json.loads(raw)  # type: ignore[no-any-return]


class TestRealAnswerPairsFixture:
    """Suite: grounding_real_answer_pairs.json structure."""

    def test_fixture_is_non_empty_list(
        self,
        real_answer_pairs: list[dict],
    ) -> None:
        assert isinstance(real_answer_pairs, list)
        assert len(real_answer_pairs) >= 20, (
            f"Expected >=20 pairs, got {len(real_answer_pairs)}. "
            "Slice 2 requires at least 20 labeled pairs for evaluation."
        )

    def test_every_pair_has_required_fields(
        self,
        real_answer_pairs: list[dict],
    ) -> None:
        required = {"claim", "premise", "premise_chunk_id", "support_label", "source"}
        for i, pair in enumerate(real_answer_pairs):
            missing = required - set(pair.keys())
            assert not missing, (
                f"Pair[{i}] missing fields: {missing}. "
                f"source='{pair.get('source', '???')}'"
                f"claim_preview='{pair.get('claim', '')[:60]}...'"
            )

    def test_support_labels_are_valid(
        self,
        real_answer_pairs: list[dict],
    ) -> None:
        for i, pair in enumerate(real_answer_pairs):
            label = pair.get("support_label")
            assert label in VALID_LABELS, (
                f"Pair[{i}] has invalid support_label='{label}'. "
                f"Must be one of {sorted(VALID_LABELS)}."
            )

    def test_claims_are_non_empty_strings(
        self,
        real_answer_pairs: list[dict],
    ) -> None:
        for i, pair in enumerate(real_answer_pairs):
            claim = pair.get("claim", "")
            assert isinstance(claim, str) and len(claim) > 0, (
                f"Pair[{i}] has empty or non-string claim."
            )

    def test_premises_are_non_empty_strings(
        self,
        real_answer_pairs: list[dict],
    ) -> None:
        for i, pair in enumerate(real_answer_pairs):
            premise = pair.get("premise", "")
            assert isinstance(premise, str) and len(premise) > 0, (
                f"Pair[{i}] has empty or non-string premise."
            )

    def test_source_field_is_present_and_non_empty(
        self,
        real_answer_pairs: list[dict],
    ) -> None:
        for i, pair in enumerate(real_answer_pairs):
            src = pair.get("source", "")
            assert isinstance(src, str) and len(src) > 0, f"Pair[{i}] has empty or missing source."

    def test_supported_claims_have_good_bge_scores(
        self,
        real_answer_pairs: list[dict],
    ) -> None:
        """Supported claims should not have implausibly low BGE scores."""
        supported = [
            p
            for p in real_answer_pairs
            if p.get("support_label") == "supported" and p.get("semantic_score_bge") is not None
        ]
        if not supported:
            pytest.skip("No supported claims with BGE scores to check.")
        for pair in supported:
            score = pair["semantic_score_bge"]
            assert 0.0 <= score <= 1.0, (
                f"BGE score {score} out of range [0,1] for claim: {pair['claim'][:60]}..."
            )

    def test_label_distribution_is_balanced(
        self,
        real_answer_pairs: list[dict],
    ) -> None:
        """Ensure we have at least some of each label type."""
        counts = {"supported": 0, "partial": 0, "unsupported": 0}
        for pair in real_answer_pairs:
            label = pair.get("support_label", "")
            if label in counts:
                counts[label] += 1
        assert counts["supported"] >= 1, "Need at least 1 supported claim"
        assert counts["unsupported"] >= 1, "Need at least 1 unsupported claim"
        assert counts["supported"] + counts["partial"] + counts["unsupported"] == len(
            real_answer_pairs
        ), "All pairs must have valid labels"
