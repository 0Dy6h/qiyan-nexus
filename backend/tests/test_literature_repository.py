import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.repositories.literature import InMemoryLiteratureRepository


SAMPLE_ITEMS = [
    {
        "id": "cn-ad-gbs-001",
        "title": "肠-脑-皮肤轴与特应性皮炎中医证候研究",
        "language": "zh",
        "source_type": "cn_literature",
        "source": "CNKI curated AD sample",
        "year": 2025,
        "snippet": "围绕特应性皮炎、肠-脑-皮肤轴与中医证候关联进行综述，强调脾虚湿蕴、血虚风燥等证候与皮肤屏障、神经免疫调节之间的联系。",
        "authors": ["王琳", "张倩", "刘晨"],
        "keywords": ["特应性皮炎", "肠-脑-皮肤轴", "中医证候", "皮肤屏障"],
        "evidence_tags": ["gut_skin_axis", "tcm_syndrome", "skin_barrier"],
        "abstract": "文章从肠-脑-皮肤轴视角讨论特应性皮炎的中医证候演变，提出脾虚湿蕴、血虚风燥与肠道微生态失衡、皮肤屏障异常和神经免疫调节紊乱之间存在可解释关联。",
        "citation_url": "https://example.org/cnki/cn-ad-gbs-001",
    },
    {
        "id": "pmid-40100001",
        "title": "Atopic dermatitis, skin barrier dysfunction, and immune pathways",
        "language": "en",
        "source_type": "pubmed",
        "source": "PubMed curated AD sample",
        "year": 2024,
        "snippet": "Reviewing barrier disruption, Th2 skewing, and epithelial cytokines as central drivers of atopic dermatitis.",
        "authors": ["Emily Carter", "Jason Lee"],
        "keywords": ["atopic dermatitis", "skin barrier", "Th2", "immune pathway"],
        "evidence_tags": ["skin_barrier", "immune_pathway", "review"],
        "abstract": "This review summarizes how barrier disruption, alarmins, and type 2 inflammation interact in atopic dermatitis and discusses implications for targeted therapy.",
        "pubmed_id": "40100001",
        "doi": "10.1000/ad.2024.001",
        "citation_url": "https://pubmed.ncbi.nlm.nih.gov/40100001/",
    },
]


def write_sample_data(path: Path, items: list[dict]) -> None:
    path.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")


def test_repository_loads_all_sample_items_from_json(tmp_path: Path):
    data_path = tmp_path / "sample_ad_literature.json"
    write_sample_data(data_path, SAMPLE_ITEMS)

    items = InMemoryLiteratureRepository(data_path).list_items()

    assert [item.id for item in items] == ["cn-ad-gbs-001", "pmid-40100001"]


def test_repository_exposes_required_and_extended_fields(tmp_path: Path):
    data_path = tmp_path / "sample_ad_literature.json"
    write_sample_data(data_path, SAMPLE_ITEMS)

    item = InMemoryLiteratureRepository(data_path).list_items()[0]

    assert item.title == "肠-脑-皮肤轴与特应性皮炎中医证候研究"
    assert item.language == "zh"
    assert item.source_type == "cn_literature"
    assert item.source == "CNKI curated AD sample"
    assert item.year == 2025
    assert item.snippet.startswith("围绕特应性皮炎")
    assert item.authors == ["王琳", "张倩", "刘晨"]
    assert item.keywords == ["特应性皮炎", "肠-脑-皮肤轴", "中医证候", "皮肤屏障"]
    assert item.evidence_tags == ["gut_skin_axis", "tcm_syndrome", "skin_barrier"]
    assert item.abstract is not None
    assert item.citation_url == "https://example.org/cnki/cn-ad-gbs-001"
    assert item.pubmed_id is None
    assert item.doi is None
    assert item.pdf_upload_id is None
    assert item.pdf_file_name is None
    assert item.pdf_parse_status is None


def test_repository_exposes_pubmed_identifiers_when_present(tmp_path: Path):
    data_path = tmp_path / "sample_ad_literature.json"
    write_sample_data(data_path, SAMPLE_ITEMS)

    item = InMemoryLiteratureRepository(data_path).get_item_by_id("pmid-40100001")

    assert item is not None
    assert item.pubmed_id == "40100001"
    assert item.doi == "10.1000/ad.2024.001"
    assert item.citation_url == "https://pubmed.ncbi.nlm.nih.gov/40100001/"


def test_repository_get_item_by_id_returns_none_for_unknown_id(tmp_path: Path):
    data_path = tmp_path / "sample_ad_literature.json"
    write_sample_data(data_path, SAMPLE_ITEMS)

    item = InMemoryLiteratureRepository(data_path).get_item_by_id("unknown")

    assert item is None


def test_repository_raises_validation_error_for_missing_required_fields(tmp_path: Path):
    data_path = tmp_path / "sample_ad_literature.json"
    write_sample_data(data_path, [{"id": "missing-fields"}])

    with pytest.raises(ValidationError):
        InMemoryLiteratureRepository(data_path).list_items()
