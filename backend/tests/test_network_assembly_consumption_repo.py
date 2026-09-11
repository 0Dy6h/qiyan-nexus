"""Repository-level tests for the writer consumption primitive.

The consume primitive must re-validate the mutable channels inside the same
critical section that writes the output and the consumption record: exactly-once
per ``(task_id, owner_id, plan_id)``, latest-plan only, adjudication-stream gap
guard, frozen-lineage hash recheck, and a per-task capacity limit. The JSON
backend additionally fail-closes on a foreign writer-process token (preview
boundary, D7-5b) and rolls back the paired output/consumption write.
"""

import json
import sqlite3
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

from app.core.canonical_json import canonical_json_sha256
from app.repositories.network_tasks import NetworkTaskRepository
from app.repositories.protocols import NetworkTaskRepositoryProtocol
from app.repositories.sqlite_network_tasks import SqliteNetworkTaskRepository
from app.schemas.network import (
    NetworkAnalysisResult,
    NetworkAssemblyConsumptionRecord,
    NetworkAssemblyOutput,
    NetworkAssemblyPlan,
    NetworkChain,
    NetworkTargetAdjudication,
    NetworkTargetIntersectionRow,
    NetworkTargetLineage,
    NetworkTargetLineageRow,
)
from app.services.rag import DISCLAIMER

OUTPUT_PAYLOAD = {"edges": [{"source": "IL6", "target": "STAT3"}]}


def _adjudication(
    lineage_row_id: str,
    adjudication_id: str,
    *,
    decision: str = "included",
) -> NetworkTargetAdjudication:
    return NetworkTargetAdjudication(
        adjudication_id=adjudication_id,
        lineage_row_id=lineage_row_id,
        decision=decision,  # type: ignore[arg-type]
        reason="人工复核",
        decided_at="2026-09-06T10:00:00+00:00",
        reviewer_id="reviewer-a",
    )


def _lineage() -> NetworkTargetLineage:
    row_common = {
        "query_date": "2026-07-11",
        "identifier_mapping": "test mapping",
        "evidence_origin": "known_activity",
    }
    return NetworkTargetLineage(
        disease_targets=[
            NetworkTargetLineageRow.model_validate(
                {
                    "lineage_row_id": "disease-row-1",
                    "raw_identifier": "ENSG1",
                    "canonical_symbol": "IL6",
                    "source_database": "Open Targets Platform",
                    **row_common,
                }
            )
        ],
        compound_targets=[
            NetworkTargetLineageRow.model_validate(
                {
                    "lineage_row_id": "compound-row-1",
                    "raw_identifier": "CHEMBL1",
                    "canonical_symbol": "IL6",
                    "source_database": "ChEMBL",
                    **row_common,
                }
            )
        ],
        intersection_targets=[
            NetworkTargetIntersectionRow.model_validate(
                {
                    "lineage_row_id": "intersection-row-1",
                    "canonical_symbol": "IL6",
                    "query_date": "2026-07-11",
                    "disease_lineage_row_ids": ["disease-row-1"],
                    "compound_lineage_row_ids": ["compound-row-1"],
                }
            )
        ],
    )


def _completed_result() -> NetworkAnalysisResult:
    return NetworkAnalysisResult(
        task_id="network-child-1",
        query="消风散",
        analysis_type="formula",
        target_lineage=_lineage(),
        chains=[],
        disclaimer=DISCLAIMER,
    )


def _adjudication_snapshot(
    record_lineage_ids: list[str], decisions: dict[str, str]
) -> list[dict[str, object]]:
    """Same shape as the service latest-wins snapshot builder."""
    return [
        {
            "adjudication_id": f"adjudication-{row_id}",
            "lineage_row_id": row_id,
            "decision": decisions[row_id],
            "reason": "人工复核",
            "decided_at": "2026-09-06T10:00:00+00:00",
        }
        for row_id in sorted(record_lineage_ids)
    ]


def _seed_task_with_plan(
    repo: NetworkTaskRepositoryProtocol,
    *,
    task_id: str = "network-child-1",
    owner_id: str = "reviewer-a",
) -> tuple[NetworkAssemblyPlan, tuple[str, ...]]:
    result = _completed_result()
    result = result.model_copy(update={"task_id": task_id})
    repo.upsert(
        task_id=task_id,
        owner_id=owner_id,
        query="消风散",
        analysis_type="formula",
        status="completed",
        progress=100,
        poll_count=2,
        result=result,
        created_at="2026-09-06T09:00:00+00:00",
    )
    lineage_ids = ["disease-row-1", "compound-row-1", "intersection-row-1"]
    decisions = {row_id: "included" for row_id in lineage_ids}
    for row_id in lineage_ids:
        assert (
            repo.append_adjudication(
                task_id, owner_id, _adjudication(row_id, f"adjudication-{row_id}")
            )
            is not None
        )
    record = repo.get_owned(task_id, owner_id)
    assert record is not None and record.result is not None
    lineage_hash = canonical_json_sha256(record.result.target_lineage.model_dump(mode="json"))
    adjudication_hash = canonical_json_sha256(_adjudication_snapshot(lineage_ids, decisions))
    plan = NetworkAssemblyPlan(
        plan_id=f"assembly-plan-{'c' * 64}",
        task_id=task_id,
        source_task_id="network-parent-1",
        parent_protocol_sha256="1" * 64,
        child_protocol_sha256="1" * 64,
        disease_source_artifact_sha256="2" * 64,
        compound_source_artifact_sha256="3" * 64,
        disease_import_payload_sha256="4" * 64,
        compound_import_payload_sha256="5" * 64,
        target_lineage_sha256=lineage_hash,
        adjudication_selection_sha256=adjudication_hash,
        canonical_plan_input_sha256="c" * 64,
        selected_intersections=[
            {
                "lineage_row_id": "intersection-row-1",
                "canonical_symbol": "IL6",
                "frozen_disease_lineage_row_ids": ["disease-row-1"],
                "frozen_compound_lineage_row_ids": ["compound-row-1"],
                "selected_disease_lineage_row_ids": ["disease-row-1"],
                "selected_compound_lineage_row_ids": ["compound-row-1"],
            }
        ],
        plan_sequence=1,
        created_at="2026-09-06T10:30:00+00:00",
    )
    expected_ids = tuple(item.adjudication_id for item in record.adjudications)
    state, persisted = repo.seal_assembly_plan(task_id, owner_id, expected_ids, plan)
    assert state == "created" and persisted is not None
    return persisted, expected_ids


def _output(
    plan: NetworkAssemblyPlan,
    writer_id: str,
    output_sha256: str,
    consumed_at: str = "2026-09-06T11:00:00+00:00",
    chains: list[NetworkChain] | None = None,
) -> NetworkAssemblyOutput:
    output_id = "assembly-output-" + canonical_json_sha256(
        {
            "task_id": plan.task_id,
            "plan_id": plan.plan_id,
            "plan_sequence": plan.plan_sequence,
            "canonical_plan_input_sha256": plan.canonical_plan_input_sha256,
            "output_sha256": output_sha256,
        }
    )
    return NetworkAssemblyOutput(
        output_id=output_id,
        task_id=plan.task_id,
        source_task_id=plan.source_task_id,
        plan_id=plan.plan_id,
        plan_sequence=plan.plan_sequence,
        canonical_plan_input_sha256=plan.canonical_plan_input_sha256,
        output_sha256=output_sha256,
        writer_id=writer_id,
        consumed_at=consumed_at,
        chains=chains if chains is not None else [],
        disclaimer=DISCLAIMER,
    )


def _consumption(
    plan: NetworkAssemblyPlan,
    output: NetworkAssemblyOutput,
    owner_id: str = "reviewer-a",
) -> NetworkAssemblyConsumptionRecord:
    return NetworkAssemblyConsumptionRecord(
        consumption_id="assembly-consumption-"
        + canonical_json_sha256(
            {
                "plan_id": plan.plan_id,
                "output_id": output.output_id,
                "nonce": "test-nonce",
            }
        ),
        task_id=plan.task_id,
        owner_id=owner_id,
        plan_id=plan.plan_id,
        plan_sequence=plan.plan_sequence,
        canonical_plan_input_sha256=plan.canonical_plan_input_sha256,
        output_id=output.output_id,
        output_sha256=output.output_sha256,
        writer_id=output.writer_id,
        consumed_at=output.consumed_at,
    )


def _payload_sha(payload: dict[str, object]) -> str:
    return canonical_json_sha256(payload)


# ── Parametrized fixture ──────────────────────────────────────────────


def _make_json_repo(path: Path) -> NetworkTaskRepository:
    path.write_text("[]\n", encoding="utf-8")
    return NetworkTaskRepository(path)


def _make_sqlite_repo(db_path: Path) -> SqliteNetworkTaskRepository:
    seed_path = db_path.parent / "network_tasks_state.json"
    seed_path.write_text("[]\n", encoding="utf-8")
    return SqliteNetworkTaskRepository(db_path, seed_path=seed_path)


_BACKEND_FACTORIES = {
    "json": lambda tmp: _make_json_repo(tmp / "network_tasks_state.json"),
    "sqlite": lambda tmp: _make_sqlite_repo(tmp / "backend_test.sqlite3"),
}


@pytest.fixture(params=["json", "sqlite"], ids=["json", "sqlite"])
def repo(tmp_path: Path, request: pytest.FixtureRequest) -> Iterator[NetworkTaskRepositoryProtocol]:
    factory = _BACKEND_FACTORIES[request.param]
    instance = factory(tmp_path)
    yield instance
    close = getattr(instance, "close", None)
    if callable(close):
        close()


# ── Tests ─────────────────────────────────────────────────────────────


class TestConsumeHappyPath:
    def test_consume_is_created_once_then_replays_idempotently(
        self, repo: NetworkTaskRepositoryProtocol
    ) -> None:
        plan, expected_ids = _seed_task_with_plan(repo)
        output = _output(plan, "writer-1", _payload_sha(OUTPUT_PAYLOAD))
        consumption = _consumption(plan, output)

        state, created_output, created_consumption = repo.consume_assembly_plan(
            plan.task_id,
            "reviewer-a",
            "writer-1",
            plan.plan_id,
            expected_ids,
            output,
            consumption,
            record_limit=1000,
        )
        assert state == "created"
        assert created_output is not None and created_consumption is not None
        assert created_output.output_id == output.output_id
        assert created_output.formal_network_ready is False
        assert created_output.disclaimer == DISCLAIMER

        persisted = repo.list_assembly_consumptions(plan.task_id, "reviewer-a")
        assert [item.consumption_id for item in persisted] == [created_consumption.consumption_id]

        # D5 idempotent replay: same writer + same output content → existing.
        replay_output = _output(plan, "writer-1", _payload_sha(OUTPUT_PAYLOAD))
        replay_consumption = _consumption(plan, replay_output)
        replay_state, replayed_output, replayed_consumption = repo.consume_assembly_plan(
            plan.task_id,
            "reviewer-a",
            "writer-1",
            plan.plan_id,
            expected_ids,
            replay_output,
            replay_consumption,
            record_limit=1000,
        )
        assert replay_state == "existing"
        assert replayed_output is not None and replayed_consumption is not None
        assert replayed_consumption.consumption_id == created_consumption.consumption_id
        assert replayed_consumption.consumed_at == created_consumption.consumed_at
        assert len(repo.list_assembly_consumptions(plan.task_id, "reviewer-a")) == 1

    def test_consume_roundtrips_assembled_chains(self, repo: NetworkTaskRepositoryProtocol) -> None:
        """The server-derived chains (2026-09-11 拍板) survive the output round trip.

        The D5 replay reads the persisted envelope back from disk, so the
        replayed ``chains`` equality proves both backends persist the new
        envelope fields verbatim instead of only the hash receipt.
        """
        plan, expected_ids = _seed_task_with_plan(repo)
        chains = [
            NetworkChain(
                herb="",
                formula=None,
                compound="CHEMBL1",
                target="IL6",
                pathway="Cytokine-cytokine receptor interaction",
                disease="Atopic dermatitis",
                score=0.64,
                related_entity_ids=["intersection-row-1", "disease-row-1", "compound-row-1"],
                target_evidence_type="predicted",
                evidence_level="predicted",
            )
        ]
        output = _output(plan, "writer-1", _payload_sha(OUTPUT_PAYLOAD), chains=chains)
        consumption = _consumption(plan, output)

        state, created_output, _ = repo.consume_assembly_plan(
            plan.task_id,
            "reviewer-a",
            "writer-1",
            plan.plan_id,
            expected_ids,
            output,
            consumption,
            record_limit=1000,
        )
        assert state == "created"
        assert created_output is not None
        assert created_output.chains == chains
        assert created_output.warnings == []

        replay_output = _output(plan, "writer-1", _payload_sha(OUTPUT_PAYLOAD), chains=chains)
        replay_state, replayed_output, _ = repo.consume_assembly_plan(
            plan.task_id,
            "reviewer-a",
            "writer-1",
            plan.plan_id,
            expected_ids,
            replay_output,
            _consumption(plan, replay_output),
            record_limit=1000,
        )
        assert replay_state == "existing"
        assert replayed_output is not None
        assert replayed_output.chains == chains

    def test_second_writer_or_new_output_is_already_consumed(
        self, repo: NetworkTaskRepositoryProtocol
    ) -> None:
        plan, expected_ids = _seed_task_with_plan(repo)
        first_output = _output(plan, "writer-1", _payload_sha(OUTPUT_PAYLOAD))
        state, _, _ = repo.consume_assembly_plan(
            plan.task_id,
            "reviewer-a",
            "writer-1",
            plan.plan_id,
            expected_ids,
            first_output,
            _consumption(plan, first_output),
            record_limit=1000,
        )
        assert state == "created"

        # Same writer, different output content → not a replay.
        other_payload_output = _output(plan, "writer-1", _payload_sha({"edges": []}))
        state, _, _ = repo.consume_assembly_plan(
            plan.task_id,
            "reviewer-a",
            "writer-1",
            plan.plan_id,
            expected_ids,
            other_payload_output,
            _consumption(plan, other_payload_output),
            record_limit=1000,
        )
        assert state == "already_consumed"

        # Different writer, same output content → still exactly-once.
        other_writer_output = _output(plan, "writer-2", _payload_sha(OUTPUT_PAYLOAD))
        state, _, _ = repo.consume_assembly_plan(
            plan.task_id,
            "reviewer-a",
            "writer-2",
            plan.plan_id,
            expected_ids,
            other_writer_output,
            _consumption(plan, other_writer_output),
            record_limit=1000,
        )
        assert state == "already_consumed"
        assert len(repo.list_assembly_consumptions(plan.task_id, "reviewer-a")) == 1

    def test_superseded_plan_is_not_consumable(self, repo: NetworkTaskRepositoryProtocol) -> None:
        plan_a, expected_ids = _seed_task_with_plan(repo)
        # Seal a second plan (different canonical input → new sequence).
        plan_b = plan_a.model_copy(
            update={
                "plan_id": f"assembly-plan-{'d' * 64}",
                "canonical_plan_input_sha256": "d" * 64,
            }
        )
        state, sealed_b = repo.seal_assembly_plan(
            plan_a.task_id, "reviewer-a", expected_ids, plan_b
        )
        assert state == "created" and sealed_b is not None and sealed_b.plan_sequence == 2

        output_a = _output(plan_a, "writer-1", _payload_sha(OUTPUT_PAYLOAD))
        state, _, _ = repo.consume_assembly_plan(
            plan_a.task_id,
            "reviewer-a",
            "writer-1",
            plan_a.plan_id,
            expected_ids,
            output_a,
            _consumption(plan_a, output_a),
            record_limit=1000,
        )
        assert state == "superseded"

        output_b = _output(sealed_b, "writer-1", _payload_sha(OUTPUT_PAYLOAD))
        state, _, _ = repo.consume_assembly_plan(
            sealed_b.task_id,
            "reviewer-a",
            "writer-1",
            sealed_b.plan_id,
            expected_ids,
            output_b,
            _consumption(sealed_b, output_b),
            record_limit=1000,
        )
        assert state == "created"

    def test_stale_adjudication_stream_conflicts(self, repo: NetworkTaskRepositoryProtocol) -> None:
        plan, expected_ids = _seed_task_with_plan(repo)
        # A new adjudication event lands after the service read the stream.
        assert (
            repo.append_adjudication(
                plan.task_id,
                "reviewer-a",
                _adjudication("disease-row-1", "adjudication-disease-row-1-2", decision="excluded"),
            )
            is not None
        )
        output = _output(plan, "writer-1", _payload_sha(OUTPUT_PAYLOAD))
        state, _, _ = repo.consume_assembly_plan(
            plan.task_id,
            "reviewer-a",
            "writer-1",
            plan.plan_id,
            expected_ids,
            output,
            _consumption(plan, output),
            record_limit=1000,
        )
        assert state == "conflict"
        assert repo.list_assembly_consumptions(plan.task_id, "reviewer-a") == []

        record = repo.get_owned(plan.task_id, "reviewer-a")
        assert record is not None
        fresh_ids = tuple(item.adjudication_id for item in record.adjudications)
        state, _, _ = repo.consume_assembly_plan(
            plan.task_id,
            "reviewer-a",
            "writer-1",
            plan.plan_id,
            fresh_ids,
            output,
            _consumption(plan, output),
            record_limit=1000,
        )
        # The snapshot the plan bound is now stale at the service layer; the
        # repository itself only guards the read-to-lock tuple gap, so with a
        # fresh tuple the primitive proceeds (the service would have already
        # returned adjudication_changed before calling it).
        assert state == "created"

    def test_tampered_lineage_fails_integrity(self, repo: NetworkTaskRepositoryProtocol) -> None:
        plan, expected_ids = _seed_task_with_plan(repo)
        record = repo.get_owned(plan.task_id, "reviewer-a")
        assert record is not None and record.result is not None
        tampered_lineage = record.result.target_lineage.model_copy(deep=True)
        tampered_row = tampered_lineage.disease_targets[0].model_copy(
            update={"canonical_symbol": "TNF"}
        )
        tampered_lineage = tampered_lineage.model_copy(update={"disease_targets": [tampered_row]})
        tampered_result = record.result.model_copy(update={"target_lineage": tampered_lineage})
        repo.upsert(
            task_id=record.task_id,
            owner_id=record.owner_id or "reviewer-a",
            query=record.query,
            analysis_type=record.analysis_type,
            status=record.status,
            progress=record.progress,
            poll_count=record.poll_count,
            result=tampered_result,
            created_at=record.created_at,
            research_protocol=record.research_protocol,
            disease_target_import=record.disease_target_import,
            compound_target_import=record.compound_target_import,
            source_task_id=record.source_task_id,
            data_mode=record.data_mode,
        )
        output = _output(plan, "writer-1", _payload_sha(OUTPUT_PAYLOAD))
        state, _, _ = repo.consume_assembly_plan(
            plan.task_id,
            "reviewer-a",
            "writer-1",
            plan.plan_id,
            expected_ids,
            output,
            _consumption(plan, output),
            record_limit=1000,
        )
        assert state == "integrity_failed"
        assert repo.list_assembly_consumptions(plan.task_id, "reviewer-a") == []

    def test_capacity_limit_blocks_new_consumptions(
        self, repo: NetworkTaskRepositoryProtocol
    ) -> None:
        plan_a, expected_ids = _seed_task_with_plan(repo)
        output_a = _output(plan_a, "writer-1", _payload_sha(OUTPUT_PAYLOAD))
        state, _, _ = repo.consume_assembly_plan(
            plan_a.task_id,
            "reviewer-a",
            "writer-1",
            plan_a.plan_id,
            expected_ids,
            output_a,
            _consumption(plan_a, output_a),
            record_limit=1,
        )
        assert state == "created"

        plan_b = plan_a.model_copy(
            update={
                "plan_id": f"assembly-plan-{'d' * 64}",
                "canonical_plan_input_sha256": "d" * 64,
            }
        )
        state, sealed_b = repo.seal_assembly_plan(
            plan_a.task_id, "reviewer-a", expected_ids, plan_b
        )
        assert state == "created" and sealed_b is not None

        output_b = _output(sealed_b, "writer-1", _payload_sha(OUTPUT_PAYLOAD))
        state, _, _ = repo.consume_assembly_plan(
            sealed_b.task_id,
            "reviewer-a",
            "writer-1",
            sealed_b.plan_id,
            expected_ids,
            output_b,
            _consumption(sealed_b, output_b),
            record_limit=1,
        )
        assert state == "capacity_exceeded"

        state, _, _ = repo.consume_assembly_plan(
            sealed_b.task_id,
            "reviewer-a",
            "writer-1",
            sealed_b.plan_id,
            expected_ids,
            output_b,
            _consumption(sealed_b, output_b),
            record_limit=2,
        )
        assert state == "created"

    def test_unknown_task_plan_or_owner_fails_closed(
        self, repo: NetworkTaskRepositoryProtocol
    ) -> None:
        plan, expected_ids = _seed_task_with_plan(repo)
        output = _output(plan, "writer-1", _payload_sha(OUTPUT_PAYLOAD))
        consumption = _consumption(plan, output)
        state, _, _ = repo.consume_assembly_plan(
            "network-unknown",
            "reviewer-a",
            "writer-1",
            plan.plan_id,
            expected_ids,
            output,
            consumption,
            record_limit=1000,
        )
        assert state == "not_found"
        state, _, _ = repo.consume_assembly_plan(
            plan.task_id,
            "reviewer-a",
            "writer-1",
            "assembly-plan-" + "e" * 64,
            expected_ids,
            output,
            consumption,
            record_limit=1000,
        )
        assert state == "not_found"
        state, _, _ = repo.consume_assembly_plan(
            plan.task_id,
            "reviewer-b",
            "writer-1",
            plan.plan_id,
            expected_ids,
            output,
            consumption,
            record_limit=1000,
        )
        assert state == "not_found"
        assert repo.list_assembly_consumptions(plan.task_id, "reviewer-b") == []


class TestConsumeConcurrency:
    def test_two_sqlite_instances_consume_same_plan_exactly_once(self, tmp_path: Path) -> None:
        db_path = tmp_path / "backend_test.sqlite3"
        first = _make_sqlite_repo(db_path)
        plan, _ = _seed_task_with_plan(first)
        record = first.get_owned(plan.task_id, "reviewer-a")
        assert record is not None
        expected_ids = tuple(item.adjudication_id for item in record.adjudications)
        second = _make_sqlite_repo(db_path)
        try:
            barrier = Barrier(2)

            def _consume(writer_id: str) -> str:
                output = _output(plan, writer_id, _payload_sha(OUTPUT_PAYLOAD))
                barrier.wait()
                state, _, _ = second.consume_assembly_plan(
                    plan.task_id,
                    "reviewer-a",
                    writer_id,
                    plan.plan_id,
                    expected_ids,
                    output,
                    _consumption(plan, output),
                    record_limit=1000,
                )
                return state

            with ThreadPoolExecutor(max_workers=2) as pool:
                states = list(pool.map(_consume, ["writer-1", "writer-2"]))
            assert sorted(states) == ["already_consumed", "created"]
            assert len(first.list_assembly_consumptions(plan.task_id, "reviewer-a")) == 1
        finally:
            second.close()
            first.close()

    def test_same_instance_threads_consume_same_plan_exactly_once(
        self, repo: NetworkTaskRepositoryProtocol
    ) -> None:
        plan, expected_ids = _seed_task_with_plan(repo)
        barrier = Barrier(2)

        def _consume(writer_id: str) -> str:
            output = _output(plan, writer_id, _payload_sha(OUTPUT_PAYLOAD))
            barrier.wait()
            state, _, _ = repo.consume_assembly_plan(
                plan.task_id,
                "reviewer-a",
                writer_id,
                plan.plan_id,
                expected_ids,
                output,
                _consumption(plan, output),
                record_limit=1000,
            )
            return state

        with ThreadPoolExecutor(max_workers=2) as pool:
            states = list(pool.map(_consume, ["writer-1", "writer-2"]))
        assert sorted(states) == ["already_consumed", "created"]
        assert len(repo.list_assembly_consumptions(plan.task_id, "reviewer-a")) == 1


class TestJsonPreviewBoundary:
    def test_foreign_process_token_fails_closed(self, tmp_path: Path) -> None:
        repo = _make_json_repo(tmp_path / "network_tasks_state.json")
        plan, expected_ids = _seed_task_with_plan(repo)
        consumptions_path = tmp_path / "network_tasks_state.assembly-consumptions.json"
        consumptions_path.write_text(
            json.dumps({"process_token": "another-process", "records": []}),
            encoding="utf-8",
        )
        output = _output(plan, "writer-1", _payload_sha(OUTPUT_PAYLOAD))
        state, _, _ = repo.consume_assembly_plan(
            plan.task_id,
            "reviewer-a",
            "writer-1",
            plan.plan_id,
            expected_ids,
            output,
            _consumption(plan, output),
            record_limit=1000,
        )
        assert state == "multi_process_blocked"
        assert json.loads(consumptions_path.read_text(encoding="utf-8"))["records"] == []

    def test_same_process_second_instance_consumes_sequentially(self, tmp_path: Path) -> None:
        state_path = tmp_path / "network_tasks_state.json"
        first = _make_json_repo(state_path)
        plan, _ = _seed_task_with_plan(first)
        # A second in-process instance shares the same process token; only the
        # seed must not be rewritten this time.
        second = NetworkTaskRepository(state_path)
        record = second.get_owned(plan.task_id, "reviewer-a")
        assert record is not None
        fresh_ids = tuple(item.adjudication_id for item in record.adjudications)
        output = _output(plan, "writer-1", _payload_sha(OUTPUT_PAYLOAD))
        state, _, consumption = second.consume_assembly_plan(
            plan.task_id,
            "reviewer-a",
            "writer-1",
            plan.plan_id,
            fresh_ids,
            output,
            _consumption(plan, output),
            record_limit=1000,
        )
        assert state == "created"
        assert len(first.list_assembly_consumptions(plan.task_id, "reviewer-a")) == 1

    def test_output_write_failure_rolls_back_consumption(self, tmp_path: Path) -> None:
        repo = _make_json_repo(tmp_path / "network_tasks_state.json")
        plan, expected_ids = _seed_task_with_plan(repo)
        consumptions_path = tmp_path / "network_tasks_state.assembly-consumptions.json"
        outputs_path = tmp_path / "network_tasks_state.assembly-outputs.json"

        original_write = repo._write_assembly_store

        def _failing_write(path: Path, records: list[object]) -> None:
            if path == consumptions_path:
                raise OSError("simulated disk failure")
            original_write(path, records)

        repo._write_assembly_store = _failing_write  # type: ignore[method-assign]
        output = _output(plan, "writer-1", _payload_sha(OUTPUT_PAYLOAD))
        with pytest.raises(OSError):
            repo.consume_assembly_plan(
                plan.task_id,
                "reviewer-a",
                "writer-1",
                plan.plan_id,
                expected_ids,
                output,
                _consumption(plan, output),
                record_limit=1000,
            )
        assert not outputs_path.exists()
        assert not consumptions_path.exists()
        del repo._write_assembly_store  # type: ignore[attr-defined]
        state, _, _ = repo.consume_assembly_plan(
            plan.task_id,
            "reviewer-a",
            "writer-1",
            plan.plan_id,
            expected_ids,
            output,
            _consumption(plan, output),
            record_limit=1000,
        )
        assert state == "created"


def test_sqlite_consumption_tables_share_the_single_database(tmp_path: Path) -> None:
    repo = _make_sqlite_repo(tmp_path / "backend_test.sqlite3")
    try:
        plan, expected_ids = _seed_task_with_plan(repo)
        output = _output(plan, "writer-1", _payload_sha(OUTPUT_PAYLOAD))
        state, _, consumption = repo.consume_assembly_plan(
            plan.task_id,
            "reviewer-a",
            "writer-1",
            plan.plan_id,
            expected_ids,
            output,
            _consumption(plan, output),
            record_limit=1000,
        )
        assert state == "created" and consumption is not None
        conn = sqlite3.connect(str(tmp_path / "backend_test.sqlite3"))
        try:
            outputs = conn.execute("SELECT COUNT(*) FROM network_assembly_output").fetchone()[0]
            records = conn.execute("SELECT COUNT(*) FROM network_assembly_consumption").fetchone()[
                0
            ]
            assert outputs == records == 1
        finally:
            conn.close()
    finally:
        repo.close()
