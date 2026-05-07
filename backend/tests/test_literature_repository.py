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
        "source": "中文本地样本文献库",
        "year": 2025,
        "snippet": "围绕特应性皮炎、肠-脑-皮肤轴与中医证候关联进行综述。",
    },
    {
        "id": "en-ad-barrier-001",
        "title": "Atopic dermatitis, skin barrier dysfunction, and immune pathways",
        "language": "en",
        "source_type": "pubmed",
        "source": "PubMed sample",
        "year": 2024,
        "snippet": "A sample English literature record for AD barrier and immune pathway retrieval.",
    },
]


def write_sample_data(path: Path, items: list[dict]) -> None:
    path.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")


def test_repository_loads_all_sample_items_from_json(tmp_path: Path):
    data_path = tmp_path / "sample_ad_literature.json"
    write_sample_data(data_path, SAMPLE_ITEMS)

    items = InMemoryLiteratureRepository(data_path).list_items()

    assert [item.id for item in items] == ["cn-ad-gbs-001", "en-ad-barrier-001"]


def test_repository_exposes_required_fields(tmp_path: Path):
    data_path = tmp_path / "sample_ad_literature.json"
    write_sample_data(data_path, SAMPLE_ITEMS)

    item = InMemoryLiteratureRepository(data_path).list_items()[0]

    assert item.title == "肠-脑-皮肤轴与特应性皮炎中医证候研究"
    assert item.language == "zh"
    assert item.source_type == "cn_literature"
    assert item.source == "中文本地样本文献库"
    assert item.year == 2025
    assert item.snippet == "围绕特应性皮炎、肠-脑-皮肤轴与中医证候关联进行综述。"


def test_repository_get_item_by_id_returns_matching_item(tmp_path: Path):
    data_path = tmp_path / "sample_ad_literature.json"
    write_sample_data(data_path, SAMPLE_ITEMS)

    item = InMemoryLiteratureRepository(data_path).get_item_by_id("en-ad-barrier-001")

    assert item is not None
    assert item.id == "en-ad-barrier-001"
    assert item.title == "Atopic dermatitis, skin barrier dysfunction, and immune pathways"


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
