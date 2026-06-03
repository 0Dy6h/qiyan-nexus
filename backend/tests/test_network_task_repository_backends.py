"""Parametrized tests that exercise both JSON and SQLite network task backends.

Run with:
    pytest tests/test_network_task_repository_backends.py          # json only (default)
    QIYAN_STATE_BACKEND=sqlite pytest tests/test_network_task_repository_backends.py  # sqlite only

Or run both at once:
    pytest tests/test_network_task_repository_backends.py -k "json or sqlite"
"""

from collections.abc import Iterator
from pathlib import Path

import pytest

from app.repositories.network_tasks import NetworkTaskRepository
from app.repositories.protocols import NetworkTaskRepositoryProtocol
from app.repositories.runtime_storage import (
    clear_network_task_repository_cache,
    get_network_task_repository,
)
from app.repositories.sqlite_network_tasks import SqliteNetworkTaskRepository
from app.schemas.network import NetworkAnalysisResult, NetworkChain


def _write_empty_seed(path: Path) -> None:
    """Write an empty list to a JSON file for NetworkTaskRepository."""
    path.write_text("[]\n", encoding="utf-8")


def _make_json_repo(path: Path) -> NetworkTaskRepository:
    _write_empty_seed(path)
    return NetworkTaskRepository(path)


def _make_sqlite_repo(db_path: Path) -> SqliteNetworkTaskRepository:
    """Create a SqliteNetworkTaskRepository, bootstrapping from empty seed."""
    seed_path = db_path.parent / "network_tasks_state.json"
    _write_empty_seed(seed_path)
    return SqliteNetworkTaskRepository(db_path, seed_path=seed_path)


# ── Parametrized fixture ──────────────────────────────────────────────

_BACKEND_FACTORIES = {
    "json": lambda tmp: _make_json_repo(tmp / "network_tasks_state.json"),
    "sqlite": lambda tmp: _make_sqlite_repo(tmp / "backend_test.sqlite3"),
}


@pytest.fixture(params=["json", "sqlite"], ids=["json", "sqlite"])
def repo(tmp_path: Path, request: pytest.FixtureRequest) -> Iterator[NetworkTaskRepositoryProtocol]:
    """Yield a NetworkTaskRepositoryProtocol for both backends; close SQLite on teardown."""
    factory = _BACKEND_FACTORIES[request.param]
    instance = factory(tmp_path)
    yield instance
    close = getattr(instance, "close", None)
    if callable(close):
        close()


# ── Tests ─────────────────────────────────────────────────────────────


class TestReadAll:
    def test_empty_initially(self, repo: NetworkTaskRepositoryProtocol) -> None:
        records = repo.read_all()
        assert records == []


class TestGet:
    def test_found(self, repo: NetworkTaskRepositoryProtocol) -> None:
        repo.upsert(
            task_id="network-test001",
            query="黄芪",
            analysis_type="herb",
            status="queued",
            progress=0,
            poll_count=0,
            result=None,
            created_at="2025-01-01T00:00:00",
        )
        record = repo.get("network-test001")
        assert record is not None
        assert record.task_id == "network-test001"
        assert record.query == "黄芪"
        assert record.analysis_type == "herb"

    def test_not_found(self, repo: NetworkTaskRepositoryProtocol) -> None:
        assert repo.get("nonexistent") is None


class TestUpsert:
    def test_create_new_task(self, repo: NetworkTaskRepositoryProtocol) -> None:
        record = repo.upsert(
            task_id="network-create001",
            query="黄连解毒汤",
            analysis_type="formula",
            status="queued",
            progress=0,
            poll_count=0,
            result=None,
            created_at="2025-06-01T12:00:00",
        )
        assert record.task_id == "network-create001"
        assert record.query == "黄连解毒汤"
        assert record.analysis_type == "formula"
        assert record.status == "queued"
        assert record.progress == 0
        assert record.poll_count == 0
        assert record.result is None

        # Verify persistence
        again = repo.get("network-create001")
        assert again is not None
        assert again.query == "黄连解毒汤"

    def test_update_existing_task(self, repo: NetworkTaskRepositoryProtocol) -> None:
        # Create
        repo.upsert(
            task_id="network-update001",
            query="黄芪",
            analysis_type="herb",
            status="queued",
            progress=0,
            poll_count=0,
            result=None,
            created_at="2025-01-01T00:00:00",
        )
        # Update to running
        record = repo.upsert(
            task_id="network-update001",
            query="黄芪",
            analysis_type="herb",
            status="running",
            progress=60,
            poll_count=1,
            result=None,
            created_at="2025-01-01T00:00:00",
        )
        assert record.status == "running"
        assert record.progress == 60
        assert record.poll_count == 1

        # Update to completed with result
        chains = [
            NetworkChain(
                herb="黄芪",
                compound="astragaloside IV",
                target="NF-κB",
                pathway="Inflammatory pathway",
                disease="atopic dermatitis",
                score=0.85,
                related_entity_ids=["herb:huangqi", "compound:astragaloside-iv"],
            )
        ]
        result_payload = NetworkAnalysisResult(
            task_id="network-update001",
            query="黄芪",
            analysis_type="herb",
            chains=chains,
            disclaimer="非诊断结论、需结合临床。",
        )
        completed = repo.upsert(
            task_id="network-update001",
            query="黄芪",
            analysis_type="herb",
            status="completed",
            progress=100,
            poll_count=2,
            result=result_payload,
            created_at="2025-01-01T00:00:00",
        )
        assert completed.status == "completed"
        assert completed.progress == 100
        assert completed.poll_count == 2
        assert completed.result is not None
        assert completed.result.chains[0].herb == "黄芪"

    def test_read_all_returns_all_tasks(self, repo: NetworkTaskRepositoryProtocol) -> None:
        repo.upsert(
            task_id="network-list001",
            query="黄芪",
            analysis_type="herb",
            status="queued",
            progress=0,
            poll_count=0,
            result=None,
            created_at="2025-01-01T00:00:00",
        )
        repo.upsert(
            task_id="network-list002",
            query="黄连解毒汤",
            analysis_type="formula",
            status="queued",
            progress=0,
            poll_count=0,
            result=None,
            created_at="2025-01-01T00:01:00",
        )
        records = repo.read_all()
        assert len(records) == 2
        ids = {r.task_id for r in records}
        assert ids == {"network-list001", "network-list002"}


# ── Factory / Protocol tests ──────────────────────────────────────────


class TestGetNetworkTaskRepository:
    def test_json_backend_returns_in_memory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        json_path = tmp_path / "network_tasks_state.json"
        _write_empty_seed(json_path)
        monkeypatch.setenv("NETWORK_TASKS_RUNTIME_STATE_PATH", str(json_path))
        monkeypatch.setenv("QIYAN_STATE_BACKEND", "json")
        clear_network_task_repository_cache()

        repo = get_network_task_repository()
        assert isinstance(repo, NetworkTaskRepository)

    def test_sqlite_backend_returns_sqlite(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        json_path = tmp_path / "network_tasks_state.json"
        _write_empty_seed(json_path)
        db_path = tmp_path / "test.sqlite3"
        monkeypatch.setenv("NETWORK_TASKS_RUNTIME_STATE_PATH", str(json_path))
        monkeypatch.setenv("QIYAN_STATE_BACKEND", "sqlite")
        monkeypatch.setenv("QIYAN_SQLITE_DB_PATH", str(db_path))
        clear_network_task_repository_cache()

        repo = get_network_task_repository()
        assert isinstance(repo, SqliteNetworkTaskRepository)

    def test_cache_is_reused(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        json_path = tmp_path / "network_tasks_state.json"
        _write_empty_seed(json_path)
        monkeypatch.setenv("NETWORK_TASKS_RUNTIME_STATE_PATH", str(json_path))
        monkeypatch.setenv("QIYAN_STATE_BACKEND", "json")
        clear_network_task_repository_cache()

        repo1 = get_network_task_repository()
        repo2 = get_network_task_repository()
        assert repo1 is repo2

    def test_cache_invalidated_on_backend_change(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        json_path = tmp_path / "network_tasks_state.json"
        _write_empty_seed(json_path)
        db_path = tmp_path / "test.sqlite3"
        monkeypatch.setenv("NETWORK_TASKS_RUNTIME_STATE_PATH", str(json_path))
        monkeypatch.setenv("QIYAN_SQLITE_DB_PATH", str(db_path))

        monkeypatch.setenv("QIYAN_STATE_BACKEND", "json")
        clear_network_task_repository_cache()
        repo_json = get_network_task_repository()
        assert isinstance(repo_json, NetworkTaskRepository)

        monkeypatch.setenv("QIYAN_STATE_BACKEND", "sqlite")
        clear_network_task_repository_cache()
        repo_sqlite = get_network_task_repository()
        assert isinstance(repo_sqlite, SqliteNetworkTaskRepository)

    def test_clear_cache_resets(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        json_path = tmp_path / "network_tasks_state.json"
        _write_empty_seed(json_path)
        monkeypatch.setenv("NETWORK_TASKS_RUNTIME_STATE_PATH", str(json_path))
        monkeypatch.setenv("QIYAN_STATE_BACKEND", "json")
        clear_network_task_repository_cache()

        repo1 = get_network_task_repository()
        clear_network_task_repository_cache()
        repo2 = get_network_task_repository()
        assert repo1 is not repo2
