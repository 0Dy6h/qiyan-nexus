from app.services.rag import answer_question


DISCLAIMER = "非诊断结论、需结合临床。"


def test_answer_question_returns_ranked_citation_cards_for_gut_skin_axis_question():
    response = answer_question("特应性皮炎和肠-脑-皮肤轴有什么关系？")

    assert response.question == "特应性皮炎和肠-脑-皮肤轴有什么关系？"
    assert "deterministic retrieval" in response.answer
    assert response.disclaimer == DISCLAIMER
    assert len(response.citations) == 2
    assert response.citations[0].literature_id == "cn-ad-gbs-001"
    assert response.citations[0].chunk_id == "chunk-cn-ad-gbs-001-abstract"
    assert response.citations[0].quote == "提出脾虚湿蕴、血虚风燥与肠道微生态失衡、皮肤屏障异常和神经免疫调节紊乱之间存在可解释关联。"
    assert response.citations[0].reason == "gut_skin_axis, tcm_syndrome"
    assert response.citations[1].literature_id == "cn-ad-microbiome-003"


def test_answer_question_trims_question():
    response = answer_question("  atopic dermatitis barrier  ")

    assert response.question == "atopic dermatitis barrier"


def test_answer_question_prioritizes_pubmed_citation_for_english_barrier_question():
    response = answer_question("atopic dermatitis barrier")

    assert response.citations[0].literature_id == "pmid-40100001"
    assert response.citations[1].literature_id == "pmid-40100006"


def test_answer_question_limits_citations_by_top_k():
    response = answer_question("特应性皮炎", top_k=1)

    assert len(response.citations) == 1
    assert response.citations[0].literature_id == "cn-ad-gbs-001"


def test_answer_question_filters_citations_by_source():
    response = answer_question("特应性皮炎 肠道菌群", source="pubmed")

    assert len(response.citations) == 2
    assert [citation.literature_id for citation in response.citations] == [
        "pmid-40100002",
        "pmid-40100007",
    ]


def test_answer_question_returns_retrieval_metadata_for_positive_matches():
    response = answer_question("特应性皮炎 肠道菌群", source="pubmed", top_k=1)

    assert response.retrieval.applied_source == "pubmed"
    assert response.retrieval.applied_top_k == 1
    assert response.retrieval.available_citation_count == 2


def test_answer_question_falls_back_when_no_positive_match_exists():
    response = answer_question("completely unrelated token", source="pubmed", top_k=1)

    assert len(response.citations) == 1
    assert response.retrieval.available_citation_count == 10
    assert "没有检索到足够匹配的证据片段" in response.answer or "deterministic retrieval" in response.answer
