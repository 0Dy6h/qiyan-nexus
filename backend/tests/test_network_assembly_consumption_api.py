"""API-level tests for the writer consumption primitive.

``POST /api/network/result/{task_id}/assembly-plans/{plan_id}/consume`` is the
write-time enforcement point of the writer consumption contract (D1-D9
approved): exactly-once per plan, latest-plan only, adjudication-stream and
frozen-lineage bindings re-verified atomically, honest failure codes, and a
response envelope that never implies scientific readiness.
"""

import hashlib
import json
import os
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.runtime_storage import (
    clear_network_task_repository_cache,
    get_network_task_repository,
)
from app.services.rag import DISCLAIMER

OPEN_TARGETS_FIXTURE = (
    Path(__file__).parent / "data" / "open_targets_graphql_associations_25_06.json"
)
CHEMBL_FIXTURE = Path(__file__).parent / "data" / "chembl_known_activities_34.json"

DISEASE_METADATA = {
    "source_profile": "open_targets_association_v1",
    "disease": "atopic_dermatitis",
    "phenotype": "特应性皮炎伴 2 型炎症与皮肤屏障异常",
    "species": "Homo sapiens",
    "source_database": "Open Targets Platform",
    "database_version": "25.06",
    "source_query_id": "EFO_0000274",
    "source_query_label": "atopic eczema",
    "source_query_parameters": {"datatype": "overall"},
    "query_date": "2026-07-11",
    "retrieved_at": "2026-07-11T08:30:00Z",
    "score_name": "association_score",
    "applied_threshold": 0.6,
    "threshold_operator": "gte",
    "identifier_mapping": "Ensembl target approvedSymbol",
    "identifier_mapping_version": "25.06",
    "usage_license_note": "Open Targets Platform data; see platform terms.",
}

COMPOUND_METADATA = {
    "source_profile": "chembl_known_activity_v1",
    "compound_id": "CHEMBL1201587",
    "compound_label": "Quercetin",
    "species": "Homo sapiens",
    "source_database": "ChEMBL",
    "database_version": "34",
    "source_query_id": "CHEMBL1201587",
    "source_query_label": "Quercetin",
    "source_query_parameters": {
        "assay_organism": "Homo sapiens",
        "standard_type": "IC50",
        "pchembl_value_min": 6.0,
    },
    "query_date": "2026-07-11",
    "retrieved_at": "2026-07-11T08:30:00Z",
    "score_name": "pchembl_value",
    "applied_threshold": 6.0,
    "threshold_operator": "gte",
    "identifier_mapping": "ChEMBL target component gene symbol",
    "identifier_mapping_version": "34",
    "usage_license_note": "ChEMBL data; see database terms.",
}

WRITER_ID = "assembly-writer-01"
OUTPUT_PAYLOAD = {
    "policy_id": "network_assembly_writer_v1",
    "edges": [{"canonical_symbol": "IL6", "weight": 1.0}],
}


@pytest.fixture(autouse=True)
def _isolate_network_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clear_network_task_repository_cache()
    monkeypatch.setenv(
        "NETWORK_TASKS_RUNTIME_STATE_PATH", str(tmp_path / "network_tasks_state.json")
    )
    monkeypatch.setenv("NETWORK_RAW_ARTIFACT_DIR", str(tmp_path / "network_raw_artifacts"))
    disease_manifest = tmp_path / "trusted-open-targets-manifest.json"
    disease_manifest.write_text(
        json.dumps(
            {
                "artifacts": {
                    hashlib.sha256(OPEN_TARGETS_FIXTURE.read_bytes()).hexdigest(): DISEASE_METADATA
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    compound_manifest = tmp_path / "trusted-chembl-manifest.json"
    compound_manifest.write_text(
        json.dumps(
            {
                "artifacts": {
                    hashlib.sha256(CHEMBL_FIXTURE.read_bytes()).hexdigest(): COMPOUND_METADATA
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("NETWORK_OPEN_TARGETS_MANIFEST_PATH", str(disease_manifest))
    monkeypatch.setenv("NETWORK_CHEMBL_MANIFEST_PATH", str(compound_manifest))
    yield
    clear_network_task_repository_cache()


def _create_verified_disease_task(client: TestClient) -> str:
    response = client.post(
        "/api/network/disease-import/verify",
        data={
            "query": "消风散",
            "analysis_type": "formula",
            "evidence_policy": "direct_human_first",
            "metadata": json.dumps(DISEASE_METADATA, ensure_ascii=False),
        },
        files={
            "file": (
                OPEN_TARGETS_FIXTURE.name,
                OPEN_TARGETS_FIXTURE.read_bytes(),
                "application/json",
            )
        },
    )
    assert response.status_code == 202
    return response.json()["task_id"]


def _create_completed_compound_child_task(client: TestClient) -> tuple[str, dict[str, object]]:
    source_task_id = _create_verified_disease_task(client)
    assert client.get(f"/api/network/result/{source_task_id}").status_code == 200
    completed_parent = client.get(f"/api/network/result/{source_task_id}")
    assert completed_parent.status_code == 200
    assert completed_parent.json()["status"] == "completed"
    response = client.post(
        "/api/network/compound-import/verify",
        data={
            "source_task_id": source_task_id,
            "metadata": json.dumps(COMPOUND_METADATA, ensure_ascii=False),
        },
        files={
            "file": (
                CHEMBL_FIXTURE.name,
                CHEMBL_FIXTURE.read_bytes(),
                "application/json",
            )
        },
    )
    assert response.status_code == 202
    child_task_id = response.json()["task_id"]
    running = client.get(f"/api/network/result/{child_task_id}")
    assert running.json()["status"] == "running"
    completed = client.get(f"/api/network/result/{child_task_id}")
    assert completed.status_code == 200 and completed.json()["status"] == "completed"
    return child_task_id, completed.json()


def _lineage_row_ids(payload: dict[str, object]) -> dict[str, list[str]]:
    lineage = payload["result"]["target_lineage"]  # type: ignore[index]
    return {
        set_name: [row["lineage_row_id"] for row in lineage[set_name]]
        for set_name in ("disease_targets", "compound_targets", "intersection_targets")
    }


def _adjudicate_all_rows(
    client: TestClient,
    task_id: str,
    payload: dict[str, object],
    *,
    decision: str = "included",
) -> None:
    for row_ids in _lineage_row_ids(payload).values():
        for row_id in row_ids:
            response = client.post(
                f"/api/network/result/{task_id}/adjudications",
                json={"lineage_row_id": row_id, "decision": decision},
            )
            assert response.status_code == 201


def _seal(client: TestClient, task_id: str) -> dict[str, object]:
    response = client.post(f"/api/network/result/{task_id}/assembly-plans")
    assert response.status_code == 201, response.json()
    return response.json()


def _consume(
    client: TestClient,
    task_id: str,
    plan_id: str,
    *,
    writer_id: str = WRITER_ID,
    output_payload: dict[str, object] | None = None,
    canonical_plan_input_sha256: str | None = None,
    extra_fields: dict[str, object] | None = None,
) -> "TestClient":
    body: dict[str, object] = {
        "writer_id": writer_id,
        "output_payload": OUTPUT_PAYLOAD if output_payload is None else output_payload,
    }
    if canonical_plan_input_sha256 is not None:
        body["canonical_plan_input_sha256"] = canonical_plan_input_sha256
    if extra_fields:
        body.update(extra_fields)
    return client.post(f"/api/network/result/{task_id}/assembly-plans/{plan_id}/consume", json=body)


def _reseal_new_plan(
    client: TestClient,
    task_id: str,
    payload: dict[str, object],
) -> dict[str, object]:
    """Flip a row through needs_review back to included so the stream changes."""
    row_id = _lineage_row_ids(payload)["disease_targets"][0]
    assert (
        client.post(
            f"/api/network/result/{task_id}/adjudications",
            json={"lineage_row_id": row_id, "decision": "needs_review"},
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/network/result/{task_id}/adjudications",
            json={"lineage_row_id": row_id, "decision": "included", "reason": "补充证据后纳入"},
        ).status_code
        == 201
    )
    return _seal(client, task_id)


# ── Happy path ──────────────────────────────────────────────────────


def test_consume_creates_output_and_consumption_atomically() -> None:
    client = TestClient(app)
    task_id, payload = _create_completed_compound_child_task(client)
    _adjudicate_all_rows(client, task_id, payload)
    plan = _seal(client, task_id)

    response = _consume(client, task_id, plan["plan_id"])

    assert response.status_code == 201
    body = response.json()
    assert set(body.keys()) == {
        "state",
        "backend_fidelity",
        "output",
        "consumption",
        "preview_boundaries",
    }
    assert body["state"] == "created"
    assert body["backend_fidelity"] == "preview"
    assert body["preview_boundaries"]
    output = body["output"]
    assert re.fullmatch(r"assembly-output-[0-9a-f]{64}", output["output_id"])
    assert output["plan_id"] == plan["plan_id"]
    assert output["plan_sequence"] == plan["plan_sequence"]
    assert output["canonical_plan_input_sha256"] == plan["canonical_plan_input_sha256"]
    assert output["writer_id"] == WRITER_ID
    assert output["assembly_input_ready"] is True
    assert output["formal_network_ready"] is False
    assert output["disclaimer"] == DISCLAIMER
    consumption = body["consumption"]
    assert re.fullmatch(r"assembly-consumption-[0-9a-f]{64}", consumption["consumption_id"])
    assert consumption["output_id"] == output["output_id"]
    assert set(consumption.keys()) == {
        "consumption_id",
        "plan_id",
        "plan_sequence",
        "canonical_plan_input_sha256",
        "output_id",
        "output_sha256",
        "writer_id",
        "consumed_at",
    }
    assert "owner_id" not in json.dumps(body)
    assert "reviewer_id" not in json.dumps(body)

    # D6 read-only projections flip without advancing state.
    result_payload = client.get(f"/api/network/result/{task_id}").json()
    assert result_payload["assembly_gate"]["latest_plan"]["is_consumed"] is True
    assert result_payload["result"]["readiness"]["formal_network_ready"] is False  # type: ignore[index]
    audit = client.get(f"/api/network/result/{task_id}/assembly-plans/{plan['plan_id']}")
    assert audit.status_code == 200
    audit_view = audit.json()
    assert audit_view["is_consumed"] is True
    assert audit_view["is_latest_plan"] is True
    assert audit_view["is_superseded_by"] is None
    assert audit_view["consumption"]["consumption_id"] == consumption["consumption_id"]
    persisted = get_network_task_repository().get_owned(task_id, "local-preview")
    assert persisted is not None
    assert persisted.status == "completed"

    report = client.get(f"/api/network/result/{task_id}/report")
    assert report.status_code == 200
    assert "消费状态：已被 writer 消费" in report.text


def test_replay_returns_existing_with_original_record() -> None:
    client = TestClient(app)
    task_id, payload = _create_completed_compound_child_task(client)
    _adjudicate_all_rows(client, task_id, payload)
    plan = _seal(client, task_id)
    created = _consume(client, task_id, plan["plan_id"])
    assert created.status_code == 201

    replayed = _consume(client, task_id, plan["plan_id"])

    assert replayed.status_code == 200
    assert replayed.json()["state"] == "existing"
    assert replayed.json()["consumption"] == created.json()["consumption"]
    assert replayed.json()["output"] == created.json()["output"]


def test_different_output_or_writer_is_already_consumed() -> None:
    client = TestClient(app)
    task_id, payload = _create_completed_compound_child_task(client)
    _adjudicate_all_rows(client, task_id, payload)
    plan = _seal(client, task_id)
    assert _consume(client, task_id, plan["plan_id"]).status_code == 201

    different_payload = _consume(client, task_id, plan["plan_id"], output_payload={"edges": []})
    assert different_payload.status_code == 409
    assert different_payload.json()["detail"]["code"] == "plan_already_consumed"

    different_writer = _consume(client, task_id, plan["plan_id"], writer_id="writer-2")
    assert different_writer.status_code == 409
    assert different_writer.json()["detail"]["code"] == "plan_already_consumed"


# ── Revision channels ───────────────────────────────────────────────


def test_adjudication_append_without_reseal_is_adjudication_changed() -> None:
    client = TestClient(app)
    task_id, payload = _create_completed_compound_child_task(client)
    _adjudicate_all_rows(client, task_id, payload)
    plan = _seal(client, task_id)
    row_id = _lineage_row_ids(payload)["disease_targets"][0]
    assert (
        client.post(
            f"/api/network/result/{task_id}/adjudications",
            json={"lineage_row_id": row_id, "decision": "included", "reason": "复核补充"},
        ).status_code
        == 201
    )

    response = _consume(client, task_id, plan["plan_id"])

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "adjudication_changed"


def test_resealed_plan_supersedes_the_old_plan() -> None:
    client = TestClient(app)
    task_id, payload = _create_completed_compound_child_task(client)
    _adjudicate_all_rows(client, task_id, payload)
    first_plan = _seal(client, task_id)
    second_plan = _reseal_new_plan(client, task_id, payload)
    assert second_plan["plan_sequence"] == 2

    stale = _consume(client, task_id, first_plan["plan_id"])
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "plan_superseded"

    current = _consume(client, task_id, second_plan["plan_id"])
    assert current.status_code == 201
    superseded_view = client.get(
        f"/api/network/result/{task_id}/assembly-plans/{first_plan['plan_id']}"
    ).json()
    assert superseded_view["is_latest_plan"] is False
    assert superseded_view["is_superseded_by"] == second_plan["plan_id"]
    assert superseded_view["is_consumed"] is False


# ── Fail-closed integrity paths ─────────────────────────────────────


def test_tampered_lineage_is_a_high_severity_integrity_error(
    tmp_path: Path,
) -> None:
    client = TestClient(app)
    task_id, payload = _create_completed_compound_child_task(client)
    _adjudicate_all_rows(client, task_id, payload)
    plan = _seal(client, task_id)

    state_path = Path(os.environ["NETWORK_TASKS_RUNTIME_STATE_PATH"])
    raw = json.loads(state_path.read_text(encoding="utf-8"))
    for item in raw:
        if item.get("task_id") == task_id:
            item["result"]["target_lineage"]["disease_targets"][0]["canonical_symbol"] = "TNF2"
    state_path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")

    response = _consume(client, task_id, plan["plan_id"])

    assert response.status_code == 500
    body = response.json()
    assert body["detail"]["code"] == "assembly_integrity_failed"
    assert "target_lineage_binding" in body["detail"]["checks"]
    assert get_network_task_repository().list_assembly_consumptions(task_id, "local-preview") == []


def test_broken_parent_link_fails_closed(tmp_path: Path) -> None:
    client = TestClient(app)
    task_id, payload = _create_completed_compound_child_task(client)
    _adjudicate_all_rows(client, task_id, payload)
    plan = _seal(client, task_id)

    state_path = Path(os.environ["NETWORK_TASKS_RUNTIME_STATE_PATH"])
    raw = json.loads(state_path.read_text(encoding="utf-8"))
    for item in raw:
        if item.get("task_id") == task_id:
            item["source_task_id"] = "network-deadbeefdeadbeef"
    state_path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")

    response = _consume(client, task_id, plan["plan_id"])

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "broken_parent_link"


def test_unknown_plan_or_task_is_404() -> None:
    client = TestClient(app)
    task_id, payload = _create_completed_compound_child_task(client)
    _adjudicate_all_rows(client, task_id, payload)
    plan = _seal(client, task_id)

    unknown_plan = _consume(client, task_id, "assembly-plan-" + "e" * 64)
    assert unknown_plan.status_code == 404
    unknown_task = _consume(client, "network-nope000000000000000", plan["plan_id"])
    assert unknown_task.status_code == 404


def test_malformed_requests_are_422() -> None:
    client = TestClient(app)
    task_id, payload = _create_completed_compound_child_task(client)
    _adjudicate_all_rows(client, task_id, payload)
    plan = _seal(client, task_id)

    missing_writer = client.post(
        f"/api/network/result/{task_id}/assembly-plans/{plan['plan_id']}/consume",
        json={"output_payload": {}},
    )
    assert missing_writer.status_code == 422

    forged_field = client.post(
        f"/api/network/result/{task_id}/assembly-plans/{plan['plan_id']}/consume",
        json={
            "writer_id": WRITER_ID,
            "output_payload": {},
            "adjudication_selection_sha256": "a" * 64,
        },
    )
    assert forged_field.status_code == 422

    hash_mismatch = _consume(
        client,
        task_id,
        plan["plan_id"],
        canonical_plan_input_sha256="b" * 64,
    )
    assert hash_mismatch.status_code == 422
    assert hash_mismatch.json()["detail"]["code"] == "invalid_consume_request"

    oversized = _consume(
        client,
        task_id,
        plan["plan_id"],
        output_payload={"blob": "x" * (256 * 1024 + 10)},
    )
    assert oversized.status_code == 422


def test_capacity_limit_returns_429(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QIYAN_CONSUMPTION_RECORD_LIMIT", "1")
    client = TestClient(app)
    task_id, payload = _create_completed_compound_child_task(client)
    _adjudicate_all_rows(client, task_id, payload)
    first_plan = _seal(client, task_id)
    assert _consume(client, task_id, first_plan["plan_id"]).status_code == 201

    second_plan = _reseal_new_plan(client, task_id, payload)
    response = _consume(client, task_id, second_plan["plan_id"], writer_id="writer-2")

    assert response.status_code == 429
    assert response.json()["detail"]["code"] == "consumption_limit_reached"


def test_sqlite_backend_reports_production_fidelity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("QIYAN_STATE_BACKEND", "sqlite")
    monkeypatch.setenv("QIYAN_SQLITE_DB_PATH", str(tmp_path / "consumption.sqlite3"))
    clear_network_task_repository_cache()
    try:
        client = TestClient(app)
        task_id, payload = _create_completed_compound_child_task(client)
        _adjudicate_all_rows(client, task_id, payload)
        plan = _seal(client, task_id)

        response = _consume(client, task_id, plan["plan_id"])

        assert response.status_code == 201
        body = response.json()
        assert body["state"] == "created"
        assert body["backend_fidelity"] == "production"
        assert body["preview_boundaries"] == []
        replayed = _consume(client, task_id, plan["plan_id"])
        assert replayed.status_code == 200
        assert replayed.json()["state"] == "existing"
        assert replayed.json()["consumption"] == body["consumption"]
    finally:
        clear_network_task_repository_cache()
