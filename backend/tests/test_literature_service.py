from app.services.literature import (
    build_pdf_upload_id,
    detect_query_language,
    get_literature_item,
    search_literature,
)


def test_detect_query_language_returns_zh_for_chinese_query():
    assert detect_query_language("特应性皮炎") == "zh"


def test_detect_query_language_returns_en_for_english_query():
    assert detect_query_language("atopic dermatitis") == "en"


def test_search_literature_prioritizes_chinese_items_for_chinese_query():
    result = search_literature("特应性皮炎")

    assert result.query == "特应性皮炎"
    assert result.total == 20
    assert result.page == 1
    assert result.page_size == 10
    assert result.total_pages == 2
    assert result.sort == "relevance"
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


def test_search_literature_filters_by_keyword_relevance():
    result = search_literature("瘙痒")

    assert 0 < result.total < 20
    assert result.items[0].id == "cn-ad-pruritus-005"


def test_search_literature_returns_empty_result_for_unknown_keyword():
    result = search_literature("完全不存在关键词 xyz")

    assert result.total == 0
    assert result.total_pages == 0
    assert result.items == []


def test_search_literature_paginates_filtered_results():
    first_page = search_literature("特应性皮炎", page=1, page_size=5)
    second_page = search_literature("特应性皮炎", page=2, page_size=5)

    assert first_page.total == 20
    assert first_page.total_pages == 4
    assert len(first_page.items) == 5
    assert second_page.page == 2
    assert second_page.page_size == 5
    assert len(second_page.items) == 5
    assert {item.id for item in first_page.items}.isdisjoint(
        {item.id for item in second_page.items}
    )


def test_search_literature_sorts_by_year_ascending():
    result = search_literature("特应性皮炎", page_size=20, sort="year_asc")

    years = [item.year for item in result.items]
    assert result.sort == "year_asc"
    assert years == sorted(years)


def test_get_literature_item_returns_item_by_id():
    item = get_literature_item("cn-ad-gbs-001")

    assert item is not None
    assert item.id == "cn-ad-gbs-001"
    assert item.source_type == "cn_literature"
    assert item.authors == ["王琳", "张倩", "刘晨"]
    assert item.evidence_tags == ["gut_skin_axis", "tcm_syndrome", "skin_barrier"]


def test_get_literature_item_returns_none_for_unknown_id():
    assert get_literature_item("unknown") is None


def test_build_pdf_upload_id_preserves_ascii_slug():
    assert (
        build_pdf_upload_id("cn-ad-gbs-001", "ad-evidence.pdf")
        == "pdf-cn-ad-gbs-001-ad-evidence-pdf"
    )


def test_build_pdf_upload_id_disambiguates_pure_chinese_filename():
    upload_id = build_pdf_upload_id(
        "cn-ad-gbs-001", "除湿糊剂治疗特应性皮炎的实验与临床观察_王琼.pdf"
    )

    assert upload_id != "pdf-cn-ad-gbs-001-pdf"
    assert upload_id.startswith("pdf-cn-ad-gbs-001-pdf-")
    suffix = upload_id.removeprefix("pdf-cn-ad-gbs-001-pdf-")
    assert len(suffix) == 8
    assert all(c in "0123456789abcdef" for c in suffix)


def test_build_pdf_upload_id_two_distinct_chinese_filenames_do_not_collide():
    a = build_pdf_upload_id("cn-ad-gbs-001", "除湿糊剂治疗特应性皮炎_王琼.pdf")
    b = build_pdf_upload_id("cn-ad-gbs-001", "中医内外合治特应性皮炎疗效观察_刘汉长.pdf")

    assert a != b


def test_build_pdf_upload_id_same_chinese_filename_is_idempotent():
    a = build_pdf_upload_id("cn-ad-gbs-001", "中医内外合治特应性皮炎疗效观察_刘汉长.pdf")
    b = build_pdf_upload_id("cn-ad-gbs-001", "中医内外合治特应性皮炎疗效观察_刘汉长.pdf")

    assert a == b


def test_build_pdf_upload_id_disambiguates_empty_slug():
    upload_id = build_pdf_upload_id("cn-ad-gbs-001", "中医内外合治特应性皮炎疗效观察_刘汉长")

    assert upload_id.startswith("pdf-cn-ad-gbs-001-pdf-")
