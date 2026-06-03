import json
import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.repositories.literature import InMemoryLiteratureRepository
from app.repositories.protocols import LiteratureRepository
from app.services.pubmed import PubmedRecord

json_backend_only = pytest.mark.skipif(
    os.environ.get("QIYAN_STATE_BACKEND") == "sqlite",
    reason="Sync API tests require JSON backend (direct JSON file I/O)",
)

sqlite_backend_only = pytest.mark.skipif(
    os.environ.get("QIYAN_STATE_BACKEND") != "sqlite",
    reason="SQLite sync integration test only runs with QIYAN_STATE_BACKEND=sqlite",
)

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

    runtime_storage.clear_literature_repository_cache()
    runtime_storage.clear_chunk_repository_cache()
    _close_repository_if_needed(literature_service._REPOSITORY)
    _close_repository_if_needed(rag_service._REPOSITORY)
    _close_repository_if_needed(rag_service._CHUNK_REPOSITORY)

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


def _close_repository_if_needed(repo: object) -> None:
    close = getattr(repo, "close", None)
    if callable(close):
        close()


@pytest.fixture
def sqlite_runtime_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[LiteratureRepository]:
    """Run the sync API through the SQLite repository factory.

    This fixture mirrors ``runtime_state_path`` but points the repository factory
    at a temporary SQLite database. The seed JSON is still used for bootstrap;
    assertions read back through the repository instead of direct JSON file I/O.
    """
    literature_path = tmp_path / "literature_state.json"
    literature_path.write_text(json.dumps(SEED_ITEMS, ensure_ascii=False), encoding="utf-8")
    sqlite_path = tmp_path / "qiyan_sync_test.sqlite3"
    monkeypatch.setenv("LITERATURE_RUNTIME_STATE_PATH", str(literature_path))
    monkeypatch.setenv("QIYAN_STATE_BACKEND", "sqlite")
    monkeypatch.setenv("QIYAN_SQLITE_DB_PATH", str(sqlite_path))

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
        yield runtime_storage.get_literature_repository()
    finally:
        _close_repository_if_needed(literature_service._REPOSITORY)
        _close_repository_if_needed(rag_service._REPOSITORY)
        _close_repository_if_needed(rag_service._CHUNK_REPOSITORY)
        runtime_storage.clear_literature_repository_cache()
        runtime_storage.clear_chunk_repository_cache()
        monkeypatch.delenv("LITERATURE_RUNTIME_STATE_PATH", raising=False)
        monkeypatch.delenv("QIYAN_STATE_BACKEND", raising=False)
        monkeypatch.delenv("QIYAN_SQLITE_DB_PATH", raising=False)
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


@json_backend_only
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


@sqlite_backend_only
def test_literature_sync_sqlite_backend_inserts_and_refreshes_existing(
    monkeypatch: pytest.MonkeyPatch,
    sqlite_runtime_repository: LiteratureRepository,
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

    refreshed = sqlite_runtime_repository.get_item_by_id("pmid-40100001")
    assert refreshed is not None
    assert refreshed.title.endswith("(refreshed)")
    assert refreshed.year == 2025
    assert refreshed.source == "PubMed live sync"
    assert refreshed.pdf_upload_id == "pdf-pmid-40100001-keep-pdf"
    assert refreshed.pdf_parse_status == "parsed"

    new_item = sqlite_runtime_repository.get_item_by_id("pmid-39000003")
    assert new_item is not None
    assert new_item.title == "JAK inhibitors for atopic dermatitis"
    assert new_item.source == "PubMed live sync"
    assert new_item.pubmed_id == "39000003"


@json_backend_only
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


@json_backend_only
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


@json_backend_only
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


@json_backend_only
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
