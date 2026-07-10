"""Parametrized tests that exercise both JSON and SQLite network task backends.

Run with:
    pytest tests/test_network_task_repository_backends.py          # json only (default)
    QIYAN_STATE_BACKEND=sqlite pytest tests/test_network_task_repository_backends.py  # sqlite only

Or run both at once:
    pytest tests/test_network_task_repository_backends.py -k "json or sqlite"
"""

import json
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier, Lock

import pytest

from app.repositories import network_tasks as network_tasks_module
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

    def test_upsert_does_not_transfer_existing_task_owner(
        self, repo: NetworkTaskRepositoryProtocol
    ) -> None:
        repo.upsert(
            task_id="network-owner-immutable",
            owner_id="reviewer-a",
            query="黄芪",
            analysis_type="herb",
            status="queued",
            progress=0,
            poll_count=0,
            result=None,
            created_at="2025-01-01T00:00:00",
        )

        updated = repo.upsert(
            task_id="network-owner-immutable",
            owner_id="reviewer-b",
            query="黄芪",
            analysis_type="herb",
            status="running",
            progress=60,
            poll_count=1,
            result=None,
            created_at="2025-01-01T00:00:00",
        )

        assert updated.owner_id == "reviewer-a"

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
                sqlite_repo.upsert(
                    task_id=f"network-{worker_id:02d}-{record_id:02d}",
                    query="黄芪",
                    analysis_type="herb",
                    status="queued",
                    progress=0,
                    poll_count=0,
                    result=None,
                    created_at="2025-01-01T00:00:00",
                )

        try:
            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                futures = [
                    executor.submit(write_records, worker_id) for worker_id in range(worker_count)
                ]
                for future in futures:
                    future.result()

            records = sqlite_repo.read_all()
            assert len(records) == worker_count * records_per_worker
        finally:
            sqlite_repo.close()


class TestAdvance:
    def test_matches_task_id_and_owner_id_atomically(
        self, repo: NetworkTaskRepositoryProtocol
    ) -> None:
        repo.upsert(
            task_id="network-owned001",
            owner_id="reviewer-a",
            query="黄芪",
            analysis_type="herb",
            status="queued",
            progress=0,
            poll_count=0,
            result=None,
            created_at="2025-01-01T00:00:00",
        )

        foreign_result = repo.advance(
            "network-owned001",
            "reviewer-b",
            lambda record: record.model_copy(
                update={"status": "running", "progress": 60, "poll_count": 1}
            ),
        )
        owner_result = repo.advance(
            "network-owned001",
            "reviewer-a",
            lambda record: record.model_copy(
                update={"status": "running", "progress": 60, "poll_count": 1}
            ),
        )

        assert foreign_result is None
        assert owner_result is not None
        assert owner_result.owner_id == "reviewer-a"
        assert owner_result.status == "running"

    def test_two_sqlite_instances_do_not_lose_concurrent_advances(self, tmp_path: Path) -> None:
        db_path = tmp_path / "shared-advance.sqlite3"
        seed_path = tmp_path / "network_tasks_state.json"
        _write_empty_seed(seed_path)
        first_repo = SqliteNetworkTaskRepository(db_path, seed_path=seed_path)
        second_repo = SqliteNetworkTaskRepository(db_path, seed_path=seed_path)
        first_repo.upsert(
            task_id="network-shared-advance",
            owner_id="reviewer-a",
            query="黄芪",
            analysis_type="herb",
            status="queued",
            progress=0,
            poll_count=0,
            result=None,
            created_at="2025-01-01T00:00:00",
        )
        workers_ready = Barrier(2)
        observed_poll_counts: list[int] = []
        observation_lock = Lock()

        def transition(record):
            with observation_lock:
                observed_poll_counts.append(record.poll_count)
            if record.poll_count == 0:
                time.sleep(0.05)
            return record.model_copy(update={"poll_count": record.poll_count + 1})

        def advance(repository: SqliteNetworkTaskRepository):
            workers_ready.wait()
            return repository.advance(
                "network-shared-advance",
                "reviewer-a",
                transition,
            )

        try:
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [
                    executor.submit(advance, repository) for repository in (first_repo, second_repo)
                ]
                results = [future.result() for future in futures]

            assert sorted(observed_poll_counts) == [0, 1]
            assert sorted(result.poll_count for result in results if result is not None) == [1, 2]
            persisted = first_repo.get("network-shared-advance")
            assert persisted is not None
            assert persisted.poll_count == 2
        finally:
            first_repo.close()
            second_repo.close()

    @pytest.mark.parametrize("backend", ["json", "sqlite"])
    def test_legacy_record_without_owner_id_is_not_claimed_by_local_preview(
        self, tmp_path: Path, backend: str
    ) -> None:
        seed_path = tmp_path / "legacy_network_tasks.json"
        seed_path.write_text(
            json.dumps(
                [
                    {
                        "task_id": "network-legacy001",
                        "query": "黄芪",
                        "analysis_type": "herb",
                        "status": "queued",
                        "progress": 0,
                        "poll_count": 0,
                        "result": None,
                        "created_at": "2025-01-01T00:00:00",
                    }
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        if backend == "json":
            legacy_repo: NetworkTaskRepositoryProtocol = NetworkTaskRepository(seed_path)
        else:
            legacy_repo = SqliteNetworkTaskRepository(
                tmp_path / "legacy.sqlite3", seed_path=seed_path
            )

        try:
            record = legacy_repo.get("network-legacy001")
            advanced = legacy_repo.advance(
                "network-legacy001",
                "local-preview",
                lambda current: current.model_copy(update={"status": "running"}),
            )

            assert record is not None
            assert record.owner_id is None
            assert advanced is None
        finally:
            close = getattr(legacy_repo, "close", None)
            if callable(close):
                close()


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

    def test_concurrent_cold_start_returns_one_cached_repository(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        json_path = tmp_path / "network_tasks_state.json"
        _write_empty_seed(json_path)
        monkeypatch.setenv("NETWORK_TASKS_RUNTIME_STATE_PATH", str(json_path))
        monkeypatch.setenv("QIYAN_STATE_BACKEND", "json")
        clear_network_task_repository_cache()
        callers_ready = Barrier(2)
        constructor_count = 0
        count_lock = Lock()
        original_repository = NetworkTaskRepository

        def slow_repository(path: Path) -> NetworkTaskRepository:
            nonlocal constructor_count
            with count_lock:
                constructor_count += 1
            time.sleep(0.05)
            return original_repository(path)

        monkeypatch.setattr(network_tasks_module, "NetworkTaskRepository", slow_repository)

        def load_repository(_: int) -> NetworkTaskRepositoryProtocol:
            callers_ready.wait()
            return get_network_task_repository()

        with ThreadPoolExecutor(max_workers=2) as executor:
            repositories = list(executor.map(load_repository, range(2)))

        assert constructor_count == 1
        assert repositories[0] is repositories[1]

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
