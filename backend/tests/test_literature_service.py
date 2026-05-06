from app.services.literature import search_literature


def test_search_literature_returns_sample_items_for_query():
    result = search_literature("特应性皮炎")

    assert result.query == "特应性皮炎"
    assert result.total == 2
    assert [item.id for item in result.items] == ["cn-ad-gbs-001", "en-ad-barrier-001"]


def test_search_literature_trims_query():
    result = search_literature("  atopic dermatitis  ")

    assert result.query == "atopic dermatitis"
