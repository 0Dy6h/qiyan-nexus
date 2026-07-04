"""Scorer-math tests for the non-circular blind-labeling eval harness.

Only the metric computation is behaviour worth locking; ``build_worksheet`` is a
thin wrapper over the retriever exercised elsewhere.
"""

from scripts.eval_blind_labeling import score_worksheet


def test_score_worksheet_computes_precision_at_k_and_mrr():
    worksheet = {
        "top_k": 3,
        "queries": [
            {
                "query": "q1",
                "candidates": [
                    {"relevant": False},
                    {"relevant": True},
                    {"relevant": True},
                ],
            },
            {
                "query": "q2",
                "candidates": [
                    {"relevant": True},
                    {"relevant": False},
                    {"relevant": False},
                ],
            },
        ],
    }

    result = score_worksheet(worksheet)

    assert result["labeled_queries"] == 2
    assert result["unlabeled_queries"] == 0
    # q1: 2/3 relevant, first relevant at rank 2 -> rr = 0.5
    assert result["per_query"][0]["precision_at_k"] == round(2 / 3, 3)
    assert result["per_query"][0]["first_relevant_rank"] == 2
    assert result["per_query"][0]["reciprocal_rank"] == 0.5
    # q2: 1/3 relevant, first relevant at rank 1 -> rr = 1.0
    assert result["per_query"][1]["precision_at_k"] == round(1 / 3, 3)
    assert result["per_query"][1]["reciprocal_rank"] == 1.0
    assert result["mrr"] == round((0.5 + 1.0) / 2, 3)
    assert result["mean_precision_at_k"] == round((2 / 3 + 1 / 3) / 2, 3)


def test_score_worksheet_skips_partially_labeled_query():
    worksheet = {
        "top_k": 2,
        "queries": [
            {"query": "q", "candidates": [{"relevant": None}, {"relevant": True}]},
        ],
    }

    result = score_worksheet(worksheet)

    assert result["labeled_queries"] == 0
    assert result["unlabeled_queries"] == 1
    assert result["mrr"] is None
    assert result["mean_precision_at_k"] is None


def test_score_worksheet_handles_query_with_no_relevant_hits():
    worksheet = {
        "top_k": 2,
        "queries": [
            {"query": "q", "candidates": [{"relevant": False}, {"relevant": False}]},
        ],
    }

    result = score_worksheet(worksheet)

    assert result["labeled_queries"] == 1
    assert result["per_query"][0]["precision_at_k"] == 0.0
    assert result["per_query"][0]["first_relevant_rank"] is None
    assert result["per_query"][0]["reciprocal_rank"] == 0.0
    assert result["mrr"] == 0.0
