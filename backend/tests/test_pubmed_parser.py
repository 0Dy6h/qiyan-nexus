from pathlib import Path

from app.services.pubmed import parse_efetch_xml, parse_esearch_xml

FIXTURES = Path(__file__).parent / "fixtures" / "pubmed"


def test_parse_esearch_xml_returns_pmids_in_order():
    xml_text = (FIXTURES / "esearch_two_ids.xml").read_text(encoding="utf-8")
    pmids = parse_esearch_xml(xml_text)
    assert pmids == ["39000001", "39000002"]


def test_parse_efetch_xml_extracts_core_fields_from_first_article():
    xml_text = (FIXTURES / "efetch_two_articles.xml").read_text(encoding="utf-8")
    records = parse_efetch_xml(xml_text)
    assert len(records) == 2
    first = records[0]
    assert first.pmid == "39000001"
    assert first.title.startswith("Skin barrier dysfunction in atopic dermatitis")
    assert "Atopic dermatitis is a chronic inflammatory skin disease." in first.abstract
    assert "filaggrin loss-of-function" in first.abstract
    assert "IL-4/IL-13 axis" in first.abstract
    assert first.authors == ["Smith Jane A", "Wang Li", "Atopic Dermatitis Consortium"]
    assert first.year == 2025
    assert first.journal == "Journal of the American Academy of Dermatology"
    assert first.keywords == ["atopic dermatitis", "filaggrin", "Th2 cytokines"]
    assert first.doi == "10.1016/j.jaad.2025.01.001"


def test_parse_efetch_xml_falls_back_to_journal_pubdate_when_no_article_date():
    xml_text = (FIXTURES / "efetch_two_articles.xml").read_text(encoding="utf-8")
    records = parse_efetch_xml(xml_text)
    second = records[1]
    assert second.pmid == "39000002"
    assert second.year == 2024
    assert second.journal == "British Journal of Dermatology"
    assert second.authors == ["Garcia Maria"]
    assert second.keywords == []
    assert second.doi is None
    assert second.abstract == "Pediatric AD cases show altered gut microbiota composition."


def test_parse_esearch_xml_returns_empty_list_when_no_hits():
    xml_text = """<?xml version="1.0"?><eSearchResult><Count>0</Count><IdList/></eSearchResult>"""
    assert parse_esearch_xml(xml_text) == []


def test_parse_efetch_xml_returns_empty_list_when_no_articles():
    xml_text = """<?xml version="1.0"?><PubmedArticleSet></PubmedArticleSet>"""
    assert parse_efetch_xml(xml_text) == []
