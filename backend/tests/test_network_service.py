from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

from app.repositories.sqlite_network_tasks import SqliteNetworkTaskRepository
from app.services import network as network_service
from app.services.network import _build_chains_from_seed


def test_formula_query_expands_to_constituent_herbs():
    chains = _build_chains_from_seed("消风散", "formula")

    assert len(chains) >= 1
    assert all(chain.formula == "消风散" for chain in chains)
    # 消风散 = 荆芥 + 防风 + 牛蒡子 in seed; chains must come from this set.
    constituent_herbs = {"荆芥", "防风", "牛蒡子"}
    assert {chain.herb for chain in chains} <= constituent_herbs
    # Chains are scored 0-1 and sorted desc; top should match the curated seed.
    scores = [chain.score for chain in chains]
    assert scores == sorted(scores, reverse=True)
    assert chains[0].disease == "Atopic dermatitis"


def test_herb_query_restricts_chains_to_that_herb_only():
    chains = _build_chains_from_seed("黄芪", "herb")

    assert len(chains) >= 1
    assert all(chain.herb == "黄芪" for chain in chains)
    assert all(chain.formula is None for chain in chains)


def test_unknown_query_returns_no_chains_instead_of_inventing_relationships():
    chains = _build_chains_from_seed("不存在的方剂", "formula")

    assert chains == []


def test_chain_count_capped_to_max_five():
    chains = _build_chains_from_seed("消风散", "formula")
    assert len(chains) <= 5


def test_network_chains_include_entity_ids_for_frontend_chips():
    chains = _build_chains_from_seed("消风散", "formula")

    assert len(chains) >= 1
    first = chains[0]
    assert "herb-" in first.related_entity_ids[0]
    assert first.related_entity_ids[1].startswith("compound-")
    assert first.related_entity_ids[2].startswith("target-")
    assert first.related_entity_ids[3].startswith("pathway-")


def test_concurrent_sqlite_polls_advance_without_losing_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_path = tmp_path / "network_tasks_state.json"
    seed_path.write_text("[]\n", encoding="utf-8")
    repo = SqliteNetworkTaskRepository(tmp_path / "network.sqlite3", seed_path=seed_path)
    task_id = "network-concurrent-poll"
    repo.upsert(
        task_id=task_id,
        query="黄芪",
        analysis_type="herb",
        status="queued",
        progress=0,
        poll_count=0,
        result=None,
        created_at="2025-01-01T00:00:00",
    )

    reads_complete = Barrier(2)

    class SynchronizedReadRepository:
        # Regression trap: the correct service path calls atomic ``advance`` and
        # never reaches this barrier. If it regresses to separate get/upsert
        # calls, both workers deterministically read poll_count=0 before either
        # can write, reproducing the original lost-update race.
        def get(self, current_task_id: str):
            record = repo.get(current_task_id)
            reads_complete.wait()
            return record

        def get_owned(self, current_task_id: str, owner_id: str):
            record = repo.get_owned(current_task_id, owner_id)
            reads_complete.wait()
            return record

        def advance(self, current_task_id: str, owner_id: str, transition):
            return repo.advance(current_task_id, owner_id, transition)

        def upsert(self, **kwargs):
            return repo.upsert(**kwargs)

    synchronized_repo = SynchronizedReadRepository()
    monkeypatch.setattr(network_service, "_get_repository", lambda: synchronized_repo)

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(
                executor.map(
                    lambda _: network_service.get_network_analysis_result(task_id), range(2)
                )
            )

        assert {response.status for _, response in responses if response is not None} == {
            "running",
            "completed",
        }
        persisted = repo.get(task_id)
        assert persisted is not None
        assert persisted.poll_count == 2
        assert persisted.status == "completed"
        assert persisted.progress == 100
        assert persisted.result is not None
        assert persisted.result.task_id == task_id
    finally:
        repo.close()


def test_failed_network_task_is_terminal_and_read_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_path = tmp_path / "network_tasks_state.json"
    seed_path.write_text("[]\n", encoding="utf-8")
    repo = SqliteNetworkTaskRepository(tmp_path / "network.sqlite3", seed_path=seed_path)
    task_id = "network-failed-terminal"
    repo.upsert(
        task_id=task_id,
        owner_id="reviewer-a",
        query="黄芪",
        analysis_type="herb",
        status="failed",
        progress=100,
        poll_count=2,
        result=None,
        error="provider unavailable",
        created_at="2025-01-01T00:00:00",
    )
    monkeypatch.setattr(network_service, "_get_repository", lambda: repo)

    try:
        before = repo.get(task_id)
        first_state, first_response = network_service.get_network_analysis_result(
            task_id, "reviewer-a"
        )
        second_state, second_response = network_service.get_network_analysis_result(
            task_id, "reviewer-a"
        )
        after = repo.get(task_id)

        assert before is not None
        assert first_state == second_state == "ok"
        assert first_response is not None and first_response.status == "failed"
        assert second_response is not None and second_response.status == "failed"
        assert after == before
    finally:
        repo.close()
