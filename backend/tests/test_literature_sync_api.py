import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.repositories.literature import InMemoryLiteratureRepository
from app.services.pubmed import PubmedRecord

SEED_ITEMS = [
    {
        "id": "pmid-40100001",
        "title": "Atopic dermatitis, skin barrier dysfunction, and immune pathways",
        "language": "en",
        "source_type": "pubmed",
        "source": "PubMed curated AD sample",
        "year": 2024,
        "snippet": "Reviewing barrier disruption, Th2 skewing.",
        "abstract": "Old abstract.",
        "authors": ["Emily Carter"],
        "keywords": ["atopic dermatitis"],
        "pubmed_id": "40100001",
        "pdf_upload_id": "pdf-pmid-40100001-keep-pdf",
        "pdf_file_name": "keep.pdf",
        "pdf_parse_status": "parsed",
        "parse_attempt_count": 1,
    },
]


class _FakePubmedFetcher:
    def __init__(self, records: list[PubmedRecord]) -> None:
        self._records = records
        self.esearch_calls: list[tuple[str, int]] = []

    def esearch(self, query: str, *, max_results: int) -> list[str]:
        self.esearch_calls.append((query, max_results))
        return [record.pmid for record in self._records]

    def efetch(self, pmids: list[str]) -> list[PubmedRecord]:
        return [record for record in self._records if record.pmid in pmids]


@pytest.fixture
def runtime_state_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    path = tmp_path / "literature_state.json"
    path.write_text(json.dumps(SEED_ITEMS, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("LITERATURE_RUNTIME_STATE_PATH", str(path))
    import importlib

    from app.api import literature as literature_api
    from app.repositories import runtime_storage
    from app.services import literature as literature_service
    from app.services import rag as rag_service

    importlib.reload(runtime_storage)
    importlib.reload(literature_service)
    importlib.reload(rag_service)
    importlib.reload(literature_api)
    from app.main import app

    app.dependency_overrides.clear()
    try:
        yield path
    finally:
        monkeypatch.delenv("LITERATURE_RUNTIME_STATE_PATH", raising=False)
        importlib.reload(runtime_storage)
        importlib.reload(literature_service)
        importlib.reload(rag_service)
        importlib.reload(literature_api)


@pytest.fixture
def fake_records() -> list[PubmedRecord]:
    return [
        PubmedRecord(
            pmid="40100001",
            title="Atopic dermatitis skin barrier (refreshed)",
            abstract="Refreshed abstract from PubMed live sync.",
            authors=["Carter Emily"],
            keywords=["atopic dermatitis", "barrier"],
            year=2025,
            journal="J Am Acad Dermatol",
            doi="10.1000/ad.2024.001",
        ),
        PubmedRecord(
            pmid="39000003",
            title="JAK inhibitors for atopic dermatitis",
            abstract="Live abstract on JAK pathway.",
            authors=["Liu Wei"],
            keywords=["JAK"],
            year=2025,
            journal="J Allergy Clin Immunol",
            doi="10.1000/ad.2025.003",
        ),
    ]


def _install_fake_client(
    monkeypatch: pytest.MonkeyPatch, records: list[PubmedRecord]
) -> _FakePubmedFetcher:
    fake = _FakePubmedFetcher(records)
    from app.services import literature as literature_service

    monkeypatch.setattr(literature_service, "_default_pubmed_fetcher", lambda: fake)
    return fake


def test_literature_sync_inserts_new_pubmed_items_and_refreshes_existing(
    monkeypatch: pytest.MonkeyPatch,
    runtime_state_path: Path,
    fake_records: list[PubmedRecord],
):
    _install_fake_client(monkeypatch, fake_records)
    from app.main import app

    response = TestClient(app).post(
        "/api/literature/sync",
        json={"source": "pubmed", "q": "atopic dermatitis", "max_results": 5},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["source"] == "pubmed"
    assert payload["query"] == "atopic dermatitis"
    assert payload["fetched"] == 2
    assert payload["created"] == 1
    assert payload["updated"] == 1
    item_ids = [item["id"] for item in payload["items"]]
    assert "pmid-40100001" in item_ids
    assert "pmid-39000003" in item_ids

    raw = json.loads(runtime_state_path.read_text(encoding="utf-8"))
    items_by_id = {item["id"]: item for item in raw}
    refreshed = items_by_id["pmid-40100001"]
    assert refreshed["title"].endswith("(refreshed)")
    assert refreshed["year"] == 2025
    assert refreshed["source"] == "PubMed live sync"
    assert refreshed["pdf_upload_id"] == "pdf-pmid-40100001-keep-pdf"
    assert refreshed["pdf_parse_status"] == "parsed"
    new_item = items_by_id["pmid-39000003"]
    assert new_item["title"] == "JAK inhibitors for atopic dermatitis"
    assert new_item["source"] == "PubMed live sync"
    assert new_item["pubmed_id"] == "39000003"


def test_literature_sync_rejects_non_pubmed_source(
    monkeypatch: pytest.MonkeyPatch, runtime_state_path: Path
):
    _install_fake_client(monkeypatch, [])
    from app.main import app

    response = TestClient(app).post(
        "/api/literature/sync",
        json={"source": "cn_literature", "q": "atopic", "max_results": 5},
    )

    assert response.status_code == 422


def test_literature_sync_rejects_empty_query(
    monkeypatch: pytest.MonkeyPatch, runtime_state_path: Path
):
    _install_fake_client(monkeypatch, [])
    from app.main import app

    response = TestClient(app).post(
        "/api/literature/sync",
        json={"source": "pubmed", "q": "", "max_results": 5},
    )

    assert response.status_code == 422


def test_literature_sync_caps_max_results_at_50(
    monkeypatch: pytest.MonkeyPatch, runtime_state_path: Path
):
    _install_fake_client(monkeypatch, [])
    from app.main import app

    response = TestClient(app).post(
        "/api/literature/sync",
        json={"source": "pubmed", "q": "atopic", "max_results": 999},
    )

    assert response.status_code == 422


def test_literature_sync_returns_zero_counts_when_no_pmids(
    monkeypatch: pytest.MonkeyPatch, runtime_state_path: Path
):
    _install_fake_client(monkeypatch, [])
    from app.main import app

    response = TestClient(app).post(
        "/api/literature/sync",
        json={"source": "pubmed", "q": "atopic", "max_results": 5},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["fetched"] == 0
    assert payload["created"] == 0
    assert payload["updated"] == 0
    assert payload["items"] == []
    assert (
        InMemoryLiteratureRepository(runtime_state_path).get_item_by_id("pmid-40100001") is not None
    )
