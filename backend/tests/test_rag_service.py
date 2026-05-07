from app.services.rag import answer_question


DISCLAIMER = "非诊断结论、需结合临床。"


def test_answer_question_returns_mock_answer_with_citation_cards():
    response = answer_question("特应性皮炎和肠-脑-皮肤轴有什么关系？")

    assert response.question == "特应性皮炎和肠-脑-皮肤轴有什么关系？"
    assert "肠-脑-皮肤轴" in response.answer
    assert response.disclaimer == DISCLAIMER
    assert len(response.citations) == 2
    assert response.citations[0].literature_id == "cn-ad-gbs-001"
    assert response.citations[0].source == "中文本地样本文献库"
    assert response.citations[0].snippet == "围绕特应性皮炎、肠-脑-皮肤轴与中医证候关联进行综述。"
    assert response.citations[0].confidence == 0.86


def test_answer_question_trims_question():
    response = answer_question("  atopic dermatitis barrier  ")

    assert response.question == "atopic dermatitis barrier"


def test_answer_question_prioritizes_pubmed_citation_for_english_question():
    response = answer_question("atopic dermatitis barrier")

    assert response.citations[0].literature_id == "en-ad-barrier-001"


def test_answer_question_limits_citations_by_top_k():
    response = answer_question("特应性皮炎", top_k=1)

    assert len(response.citations) == 1
    assert response.citations[0].literature_id == "cn-ad-gbs-001"


def test_answer_question_filters_citations_by_source():
    response = answer_question("特应性皮炎", source="pubmed")

    assert len(response.citations) == 1
    assert response.citations[0].literature_id == "en-ad-barrier-001"


def test_answer_question_returns_retrieval_metadata():
    response = answer_question("特应性皮炎", source="pubmed", top_k=1)

    assert response.retrieval.applied_source == "pubmed"
    assert response.retrieval.applied_top_k == 1
    assert response.retrieval.available_citation_count == 1
