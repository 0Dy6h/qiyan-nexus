"""ADR-0016 / borrow ②: transparent, computed retrieval match score.

The per-citation ``confidence`` is a per-source-type constant (a prior), not a
computed relevance. This slice adds ``match_score`` — a transparent value
derived from the real retrieval score of each selected candidate — and keeps
``confidence`` only as an honestly-labelled source-type prior. ``match_score``
is a relevance signal, NOT a probability or efficacy estimate.
"""

from app.services.rag import answer_question


def test_citations_carry_a_computed_match_score_in_unit_range():
    response = answer_question("特应性皮炎和肠-脑-皮肤轴有什么关系？")

    assert response.citations, "expected at least one citation for an on-topic query"
    for citation in response.citations:
        assert citation.match_score is not None
        assert 0.0 <= citation.match_score <= 1.0


def test_match_score_is_not_the_constant_confidence_prior():
    """match_score must reflect real retrieval ranking, not the source-type prior."""
    response = answer_question("特应性皮炎和肠-脑-皮肤轴有什么关系？")

    top = response.citations[0]
    # The top-ranked citation's real match should saturate at 1.0 (best in set),
    # which the two constant confidence priors (0.86 / 0.74) never equal.
    assert top.match_score == 1.0
    assert top.confidence in (0.86, 0.74)


def test_match_score_is_monotonic_with_ranking():
    response = answer_question("特应性皮炎和肠-脑-皮肤轴有什么关系？")

    scores = [c.match_score for c in response.citations if c.match_score is not None]
    assert scores == sorted(scores, reverse=True)


def test_off_topic_query_has_no_citations_and_no_match_scores():
    response = answer_question("高血压一线降压药是什么？")
    assert response.citations == []
