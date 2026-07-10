"""Parametrized tests that exercise both JSON and SQLite chunk backends.

Run with:
    pytest tests/test_chunk_repository_backends.py          # json only (default)
    QIYAN_STATE_BACKEND=sqlite pytest tests/test_chunk_repository_backends.py  # sqlite only

Or run both at once:
    pytest tests/test_chunk_repository_backends.py -k "json or sqlite"
"""

import json
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from typing import Any

import pytest

from app.repositories.chunk import InMemoryChunkRepository
from app.repositories.protocols import ChunkRepository
from app.repositories.runtime_storage import (
    clear_chunk_repository_cache,
    get_chunk_repository,
)
from app.repositories.sqlite_chunk import SqliteChunkRepository

# ── Minimal seed data ──────────────────────────────────────────────────

SEED_CHUNKS: list[dict[str, Any]] = [
    {
        "chunk_id": "chunk-cn-ad-gbs-001-abstract",
        "literature_id": "cn-ad-gbs-001",
        "section": "abstract",
        "text": "文章从肠-脑-皮肤轴视角讨论特应性皮炎的中医证候演变。",
        "source_quote": "提出脾虚湿蕴、血虚风燥与肠道微生态失衡之间存在可解释关联。",
        "evidence_tags": ["gut_skin_axis", "tcm_syndrome"],
        "related_entity_ids": ["disease:atopic-dermatitis", "pathway:gut-skin-axis"],
    },
    {
        "chunk_id": "chunk-cn-ad-formula-002-summary",
        "literature_id": "cn-ad-formula-002",
        "section": "summary",
        "text": "综述特应性皮炎常用中药复方的基础与临床研究。",
        "source_quote": "归纳其在 Th2 炎症抑制、屏障修复和瘙痒控制中的潜在作用。",
        "evidence_tags": ["formula", "immune_pathway"],
        "related_entity_ids": ["disease:atopic-dermatitis", "formula:xiaofengsan"],
    },
]


def _write_json_seed(path: Path) -> None:
    """Write SEED_CHUNKS to a JSON file for InMemoryChunkRepository."""
    path.write_text(json.dumps(SEED_CHUNKS, ensure_ascii=False), encoding="utf-8")


def _make_json_repo(path: Path) -> InMemoryChunkRepository:
    _write_json_seed(path)
    return InMemoryChunkRepository(path)


def _make_sqlite_repo(db_path: Path) -> SqliteChunkRepository:
    """Create a SqliteChunkRepository, bootstrapping from SEED_CHUNKS."""
    seed_path = db_path.parent / "chunk_state.json"
    _write_json_seed(seed_path)
    return SqliteChunkRepository(db_path, seed_path=seed_path)


# ── Parametrized fixture ──────────────────────────────────────────────

_BACKEND_FACTORIES = {
    "json": lambda tmp: _make_json_repo(tmp / "chunk_state.json"),
    "sqlite": lambda tmp: _make_sqlite_repo(tmp / "backend_test.sqlite3"),
}


@pytest.fixture(params=["json", "sqlite"], ids=["json", "sqlite"])
def repo(tmp_path: Path, request: pytest.FixtureRequest) -> Iterator[ChunkRepository]:
    """Yield a ChunkRepository for both backends; close SQLite on teardown."""
    factory = _BACKEND_FACTORIES[request.param]
    instance = factory(tmp_path)
    yield instance
    close = getattr(instance, "close", None)
    if callable(close):
        close()


# ── Tests ─────────────────────────────────────────────────────────────


class TestListChunks:
    def test_returns_all_seed_items(self, repo: ChunkRepository) -> None:
        chunks = repo.list_chunks()
        assert len(chunks) == 2

    def test_ids_match_seed(self, repo: ChunkRepository) -> None:
        ids = {c.chunk_id for c in repo.list_chunks()}
        assert ids == {"chunk-cn-ad-gbs-001-abstract", "chunk-cn-ad-formula-002-summary"}


class TestListChunksByLiteratureId:
    def test_filters_by_literature_id(self, repo: ChunkRepository) -> None:
        chunks = repo.list_chunks_by_literature_id("cn-ad-gbs-001")
        assert len(chunks) == 1
        assert chunks[0].chunk_id == "chunk-cn-ad-gbs-001-abstract"

    def test_returns_empty_for_unknown_id(self, repo: ChunkRepository) -> None:
        chunks = repo.list_chunks_by_literature_id("nonexistent")
        assert chunks == []


class TestGetChunkById:
    def test_found(self, repo: ChunkRepository) -> None:
        chunk = repo.get_chunk_by_id("chunk-cn-ad-gbs-001-abstract")
        assert chunk is not None
        assert chunk.literature_id == "cn-ad-gbs-001"
        assert chunk.section == "abstract"

    def test_not_found(self, repo: ChunkRepository) -> None:
        assert repo.get_chunk_by_id("nonexistent") is None


class TestUpsertUploadedPdfChunk:
    def test_insert_new_chunk(self, repo: ChunkRepository) -> None:
        result = repo.upsert_uploaded_pdf_chunk(
            chunk_id="chunk-pdf-upload-001",
            literature_id="cn-ad-gbs-001",
            pdf_upload_id="pdf-upload-001",
            text="Uploaded PDF parsed content.",
            source_quote="parsed content",
            evidence_tags=["uploaded_pdf", "atopic_dermatitis"],
            related_entity_ids=["disease:atopic-dermatitis"],
        )
        assert result.chunk_id == "chunk-pdf-upload-001"
        assert result.literature_id == "cn-ad-gbs-001"
        assert result.section == "uploaded_pdf"
        assert result.source_type == "uploaded_pdf"
        assert result.pdf_upload_id == "pdf-upload-001"
        assert result.evidence_tags == ["uploaded_pdf", "atopic_dermatitis"]

        # Verify persistence
        again = repo.get_chunk_by_id("chunk-pdf-upload-001")
        assert again is not None
        assert again.text == "Uploaded PDF parsed content."

    def test_update_existing_chunk(self, repo: ChunkRepository) -> None:
        # First insert
        repo.upsert_uploaded_pdf_chunk(
            chunk_id="chunk-cn-ad-gbs-001-abstract",
            literature_id="cn-ad-gbs-001",
            pdf_upload_id="pdf-update-001",
            text="Updated text content.",
            source_quote="updated quote",
            evidence_tags=["updated_tag"],
        )
        # Now update the same chunk_id
        result = repo.upsert_uploaded_pdf_chunk(
            chunk_id="chunk-cn-ad-gbs-001-abstract",
            literature_id="cn-ad-gbs-001",
            pdf_upload_id="pdf-update-002",
            text="Re-updated text content.",
            source_quote="re-updated quote",
            evidence_tags=["re_updated_tag"],
        )
        assert result.text == "Re-updated text content."
        assert result.pdf_upload_id == "pdf-update-002"
        assert result.evidence_tags == ["re_updated_tag"]

    def test_default_related_entity_ids(self, repo: ChunkRepository) -> None:
        result = repo.upsert_uploaded_pdf_chunk(
            chunk_id="chunk-pdf-default-ids",
            literature_id="cn-ad-gbs-001",
            pdf_upload_id="pdf-default-ids",
            text="Text",
            source_quote="quote",
            evidence_tags=["tag"],
            related_entity_ids=None,
        )
        assert result.related_entity_ids == ["disease:atopic-dermatitis"]

    def test_sqlite_shared_connection_accepts_concurrent_upserts_without_data_loss(
        self, tmp_path: Path
    ) -> None:
        sqlite_repo = _make_sqlite_repo(tmp_path / "concurrent.sqlite3")
        worker_count = 8
        records_per_worker = 20
        start = Barrier(worker_count)

        def write_records(worker_id: int) -> None:
            start.wait()
            for record_id in range(records_per_worker):
                suffix = f"{worker_id:02d}-{record_id:02d}"
                sqlite_repo.upsert_uploaded_pdf_chunk(
                    chunk_id=f"chunk-concurrent-{suffix}",
                    literature_id="cn-ad-gbs-001",
                    pdf_upload_id=f"pdf-concurrent-{suffix}",
                    text="Concurrent parsed content.",
                    source_quote="Concurrent quote.",
                    evidence_tags=["uploaded_pdf"],
                )

        try:
            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                futures = [
                    executor.submit(write_records, worker_id) for worker_id in range(worker_count)
                ]
                for future in futures:
                    future.result()

            concurrent_chunks = [
                chunk
                for chunk in sqlite_repo.list_chunks()
                if chunk.chunk_id.startswith("chunk-concurrent-")
            ]
            assert len(concurrent_chunks) == worker_count * records_per_worker
        finally:
            sqlite_repo.close()


# ── Factory / Protocol tests ──────────────────────────────────────────


class TestGetChunkRepository:
    def test_json_backend_returns_in_memory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        json_path = tmp_path / "chunk_state.json"
        _write_json_seed(json_path)
        monkeypatch.setenv("CHUNK_RUNTIME_STATE_PATH", str(json_path))
        monkeypatch.setenv("QIYAN_STATE_BACKEND", "json")
        clear_chunk_repository_cache()

        repo = get_chunk_repository()
        assert isinstance(repo, InMemoryChunkRepository)

    def test_sqlite_backend_returns_sqlite(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        json_path = tmp_path / "chunk_state.json"
        _write_json_seed(json_path)
        db_path = tmp_path / "test.sqlite3"
        monkeypatch.setenv("CHUNK_RUNTIME_STATE_PATH", str(json_path))
        monkeypatch.setenv("QIYAN_STATE_BACKEND", "sqlite")
        monkeypatch.setenv("QIYAN_SQLITE_DB_PATH", str(db_path))
        clear_chunk_repository_cache()

        repo = get_chunk_repository()
        assert isinstance(repo, SqliteChunkRepository)

    def test_cache_is_reused(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        json_path = tmp_path / "chunk_state.json"
        _write_json_seed(json_path)
        monkeypatch.setenv("CHUNK_RUNTIME_STATE_PATH", str(json_path))
        monkeypatch.setenv("QIYAN_STATE_BACKEND", "json")
        clear_chunk_repository_cache()

        repo1 = get_chunk_repository()
        repo2 = get_chunk_repository()
        assert repo1 is repo2

    def test_cache_invalidated_on_backend_change(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        json_path = tmp_path / "chunk_state.json"
        _write_json_seed(json_path)
        db_path = tmp_path / "test.sqlite3"
        monkeypatch.setenv("CHUNK_RUNTIME_STATE_PATH", str(json_path))
        monkeypatch.setenv("QIYAN_SQLITE_DB_PATH", str(db_path))

        monkeypatch.setenv("QIYAN_STATE_BACKEND", "json")
        clear_chunk_repository_cache()
        repo_json = get_chunk_repository()
        assert isinstance(repo_json, InMemoryChunkRepository)

        monkeypatch.setenv("QIYAN_STATE_BACKEND", "sqlite")
        clear_chunk_repository_cache()
        repo_sqlite = get_chunk_repository()
        assert isinstance(repo_sqlite, SqliteChunkRepository)

    def test_clear_cache_resets(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        json_path = tmp_path / "chunk_state.json"
        _write_json_seed(json_path)
        monkeypatch.setenv("CHUNK_RUNTIME_STATE_PATH", str(json_path))
        monkeypatch.setenv("QIYAN_STATE_BACKEND", "json")
        clear_chunk_repository_cache()

        repo1 = get_chunk_repository()
        clear_chunk_repository_cache()
        repo2 = get_chunk_repository()
        assert repo1 is not repo2
