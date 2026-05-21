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


def test_repository_bulk_upsert_pubmed_items_inserts_new_items_and_preserves_existing(
    tmp_path: Path,
):
    data_path = tmp_path / "sample_ad_literature.json"
    write_sample_data(data_path, SAMPLE_ITEMS)
    repository = InMemoryLiteratureRepository(data_path)

    incoming = [
        {
            "id": "pmid-39000003",
            "title": "Targeted therapy for atopic dermatitis: JAK inhibitors review",
            "language": "en",
            "source_type": "pubmed",
            "source": "PubMed live sync",
            "year": 2025,
            "snippet": "Targeted therapy for atopic dermatitis: JAK inhibitors review",
            "abstract": "A systematic review of JAK inhibitors in atopic dermatitis.",
            "authors": ["Liu Wei"],
            "keywords": ["JAK", "atopic dermatitis"],
            "pubmed_id": "39000003",
            "doi": "10.1000/ad.2025.003",
            "citation_url": "https://pubmed.ncbi.nlm.nih.gov/39000003/",
        },
        {
            "id": "pmid-40100001",
            "title": "Atopic dermatitis, skin barrier dysfunction (refreshed 2025)",
            "language": "en",
            "source_type": "pubmed",
            "source": "PubMed live sync",
            "year": 2025,
            "snippet": "Atopic dermatitis, skin barrier dysfunction (refreshed 2025)",
            "abstract": "Refreshed abstract with new mechanistic data.",
            "authors": ["Emily Carter"],
            "keywords": ["atopic dermatitis", "barrier"],
            "pubmed_id": "40100001",
            "doi": "10.1000/ad.2024.001",
            "citation_url": "https://pubmed.ncbi.nlm.nih.gov/40100001/",
        },
    ]

    created, updated = repository.bulk_upsert_pubmed_items(incoming)

    assert created == 1
    assert updated == 1
    items_by_id = {item.id: item for item in repository.list_items()}
    new_item = items_by_id["pmid-39000003"]
    assert new_item.title.startswith("Targeted therapy")
    assert new_item.source == "PubMed live sync"
    assert new_item.year == 2025
    refreshed = items_by_id["pmid-40100001"]
    assert refreshed.title.endswith("(refreshed 2025)")
    assert refreshed.year == 2025
    assert "肠-脑-皮肤轴与特应性皮炎中医证候研究" == items_by_id["cn-ad-gbs-001"].title


def test_repository_bulk_upsert_pubmed_items_preserves_pdf_metadata_on_update(tmp_path: Path):
    data_path = tmp_path / "sample_ad_literature.json"
    existing = [
        {
            "id": "pmid-40100001",
            "title": "Old title",
            "language": "en",
            "source_type": "pubmed",
            "source": "PubMed curated AD sample",
            "year": 2024,
            "snippet": "Old snippet",
            "pdf_upload_id": "pdf-pmid-40100001-evidence-pdf",
            "pdf_file_name": "evidence.pdf",
            "pdf_parse_status": "parsed",
            "pdf_parse_message": "Mock parser completed successfully",
            "parse_attempt_count": 2,
        },
    ]
    write_sample_data(data_path, existing)
    repository = InMemoryLiteratureRepository(data_path)

    repository.bulk_upsert_pubmed_items(
        [
            {
                "id": "pmid-40100001",
                "title": "Refreshed title",
                "language": "en",
                "source_type": "pubmed",
                "source": "PubMed live sync",
                "year": 2025,
                "snippet": "Refreshed snippet",
                "abstract": "Refreshed abstract",
                "pubmed_id": "40100001",
            },
        ]
    )

    item = repository.get_item_by_id("pmid-40100001")
    assert item is not None
    assert item.title == "Refreshed title"
    assert item.pdf_upload_id == "pdf-pmid-40100001-evidence-pdf"
    assert item.pdf_file_name == "evidence.pdf"
    assert item.pdf_parse_status == "parsed"
    assert item.pdf_parse_message == "Mock parser completed successfully"
    assert item.parse_attempt_count == 2
