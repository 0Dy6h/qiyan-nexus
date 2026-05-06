from app.services.literature import detect_query_language, search_literature


def test_detect_query_language_returns_zh_for_chinese_query():
    assert detect_query_language("特应性皮炎") == "zh"


def test_detect_query_language_returns_en_for_english_query():
    assert detect_query_language("atopic dermatitis") == "en"


def test_search_literature_returns_sample_items_for_query():
    result = search_literature("特应性皮炎")

    assert result.query == "特应性皮炎"
    assert result.total == 2
    assert [item.id for item in result.items] == ["cn-ad-gbs-001", "en-ad-barrier-001"]


def test_search_literature_trims_query():
    result = search_literature("  atopic dermatitis  ")

    assert result.query == "atopic dermatitis"
