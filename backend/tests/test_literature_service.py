from app.services.literature import detect_query_language, get_literature_item, search_literature


def test_detect_query_language_returns_zh_for_chinese_query():
    assert detect_query_language("特应性皮炎") == "zh"


def test_detect_query_language_returns_en_for_english_query():
    assert detect_query_language("atopic dermatitis") == "en"


def test_search_literature_prioritizes_chinese_items_for_chinese_query():
    result = search_literature("特应性皮炎")

    assert result.query == "特应性皮炎"
    assert result.total == 20
    assert [item.id for item in result.items[:3]] == [
        "cn-ad-gbs-001",
        "cn-ad-formula-002",
        "cn-ad-microbiome-003",
    ]


def test_search_literature_prioritizes_pubmed_items_for_english_query():
    result = search_literature("atopic dermatitis")

    assert result.query == "atopic dermatitis"
    assert result.total == 20
    assert [item.id for item in result.items[:3]] == [
        "pmid-40100001",
        "pmid-40100002",
        "pmid-40100003",
    ]


def test_search_literature_filters_cn_literature_source():
    result = search_literature("atopic dermatitis", source="cn_literature")

    assert result.total == 10
    assert [item.source_type for item in result.items] == ["cn_literature"] * 10


def test_search_literature_filters_pubmed_source():
    result = search_literature("特应性皮炎", source="pubmed")

    assert result.total == 10
    assert [item.source_type for item in result.items] == ["pubmed"] * 10


def test_search_literature_trims_query():
    result = search_literature("  atopic dermatitis  ")

    assert result.query == "atopic dermatitis"


def test_get_literature_item_returns_item_by_id():
    item = get_literature_item("cn-ad-gbs-001")

    assert item is not None
    assert item.id == "cn-ad-gbs-001"
    assert item.source_type == "cn_literature"
    assert item.authors == ["王琳", "张倩", "刘晨"]
    assert item.evidence_tags == ["gut_skin_axis", "tcm_syndrome", "skin_barrier"]


def test_get_literature_item_returns_none_for_unknown_id():
    assert get_literature_item("unknown") is None
