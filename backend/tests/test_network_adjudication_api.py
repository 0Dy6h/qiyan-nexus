"""Owner-scoped per-row manual adjudication API tests.

``POST /api/network/result/{task_id}/adjudications`` appends reviewer decisions
for frozen target lineage rows of a completed task.  Adjudications are
append-only audit data: they must never mutate the immutable lineage rows,
provenance hashes, or readiness, and must never expose reviewer identity.
"""

import hashlib
import importlib
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
from app.schemas.network import NetworkAnalysisResult, NetworkTaskRecord

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

ADJUDICATION_RESPONSE_FIELDS = {
    "adjudication_id",
    "lineage_row_id",
    "decision",
    "reason",
    "decided_at",
}

ADJUDICATION_ID_PATTERN = re.compile(r"^adjudication-[0-9a-f]{64}$")


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


def _create_verified_disease_task(
    client: TestClient,
    headers: dict[str, str] | None = None,
) -> str:
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
        headers=headers,
    )
    assert response.status_code == 202
    return response.json()["task_id"]


def _create_compound_child_task(
    client: TestClient,
    source_task_id: str,
    headers: dict[str, str] | None = None,
) -> str:
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
        headers=headers,
    )
    assert response.status_code == 202
    return response.json()["task_id"]


def _create_completed_compound_child_task(
    client: TestClient,
    headers: dict[str, str] | None = None,
) -> tuple[str, dict[str, object]]:
    """Create a completed double-sided snapshot task and return (task_id, result GET payload)."""
    source_task_id = _create_verified_disease_task(client, headers)
    child_task_id = _create_compound_child_task(client, source_task_id, headers)
    running = client.get(f"/api/network/result/{child_task_id}", headers=headers)
    assert running.json()["status"] == "running"
    completed = client.get(f"/api/network/result/{child_task_id}", headers=headers)
    assert completed.status_code == 200
    payload = completed.json()
    assert payload["status"] == "completed"
    return child_task_id, payload


def _lineage_row_ids(payload: dict[str, object]) -> dict[str, list[str]]:
    lineage = payload["result"]["target_lineage"]  # type: ignore[index]
    return {
        set_name: [row["lineage_row_id"] for row in lineage[set_name]]
        for set_name in ("disease_targets", "compound_targets", "intersection_targets")
    }


def _total_lineage_rows(payload: dict[str, object]) -> int:
    return sum(len(ids) for ids in _lineage_row_ids(payload).values())


def _post_adjudication(
    client: TestClient,
    task_id: str,
    body: dict[str, object],
    headers: dict[str, str] | None = None,
) -> "TestClient":
    return client.post(
        f"/api/network/result/{task_id}/adjudications",
        json=body,
        headers=headers,
    )


# ── Happy path ──────────────────────────────────────────────────────


def test_submit_adjudication_returns_201_projection_without_reviewer_identity() -> None:
    client = TestClient(app)
    task_id, payload = _create_completed_compound_child_task(client)
    row_id = _lineage_row_ids(payload)["disease_targets"][0]

    response = _post_adjudication(
        client,
        task_id,
        {"lineage_row_id": row_id, "decision": "included", "reason": "指南推荐靶点"},
    )

    assert response.status_code == 201
    projection = response.json()
    assert set(projection.keys()) == ADJUDICATION_RESPONSE_FIELDS
    assert "reviewer_id" not in projection
    assert "owner_id" not in projection
    assert projection["lineage_row_id"] == row_id
    assert projection["decision"] == "included"
    assert projection["reason"] == "指南推荐靶点"
    assert ADJUDICATION_ID_PATTERN.fullmatch(projection["adjudication_id"])
    assert isinstance(projection["decided_at"], str) and projection["decided_at"]


def test_submit_adjudication_accepts_intersection_and_compound_rows() -> None:
    client = TestClient(app)
    task_id, payload = _create_completed_compound_child_task(client)
    row_ids = _lineage_row_ids(payload)

    for set_name, decision in (
        ("compound_targets", "excluded"),
        ("intersection_targets", "needs_review"),
    ):
        response = _post_adjudication(
            client,
            task_id,
            {"lineage_row_id": row_ids[set_name][0], "decision": decision},
        )
        assert response.status_code == 201
        assert response.json()["decision"] == decision


def test_submit_adjudication_defaults_reason_to_null_and_trims_whitespace() -> None:
    client = TestClient(app)
    task_id, payload = _create_completed_compound_child_task(client)
    first_row, second_row = _lineage_row_ids(payload)["disease_targets"]

    without_reason = _post_adjudication(
        client, task_id, {"lineage_row_id": first_row, "decision": "included"}
    )
    padded_reason = _post_adjudication(
        client,
        task_id,
        {"lineage_row_id": second_row, "decision": "excluded", "reason": "  证据不足  "},
    )

    assert without_reason.status_code == 201
    assert without_reason.json()["reason"] is None
    assert padded_reason.status_code == 201
    assert padded_reason.json()["reason"] == "证据不足"


def test_submit_adjudication_persists_append_only_history_and_latest_wins() -> None:
    client = TestClient(app)
    task_id, payload = _create_completed_compound_child_task(client)
    row_id = _lineage_row_ids(payload)["disease_targets"][0]

    first = _post_adjudication(
        client, task_id, {"lineage_row_id": row_id, "decision": "included", "reason": "先纳入"}
    )
    second = _post_adjudication(
        client, task_id, {"lineage_row_id": row_id, "decision": "excluded", "reason": "复核后排除"}
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["adjudication_id"] != second.json()["adjudication_id"]

    persisted = get_network_task_repository().get_owned(task_id, "local-preview")
    assert persisted is not None
    assert len(persisted.adjudications) == 2
    assert persisted.adjudications[0].decision == "included"
    assert persisted.adjudications[1].decision == "excluded"
    assert persisted.adjudications[0].reviewer_id == "local-preview"

    projection = client.get(f"/api/network/result/{task_id}").json()["adjudication"]
    current_by_row = {entry["lineage_row_id"]: entry for entry in projection["current"]}
    assert current_by_row[row_id]["decision"] == "excluded"
    assert current_by_row[row_id]["reason"] == "复核后排除"
    assert projection["counts"] == {
        "included": 0,
        "excluded": 1,
        "needs_review": 0,
        "pending": _total_lineage_rows(payload) - 1,
    }


def test_repeated_identical_adjudications_keep_distinct_audit_ids() -> None:
    """An identical resubmit (e.g. a retried POST) must not collide audit ids.

    ``adjudication_id`` is the only handle for referencing one audit event, and the
    pre-write ``sequence`` can repeat across concurrent submissions, so identical
    payloads must still yield distinct ids and distinct appended events.
    """
    client = TestClient(app)
    task_id, payload = _create_completed_compound_child_task(client)
    row_id = _lineage_row_ids(payload)["disease_targets"][0]
    body = {"lineage_row_id": row_id, "decision": "included"}

    responses = [_post_adjudication(client, task_id, body) for _ in range(5)]

    assert [response.status_code for response in responses] == [201] * 5
    ids = [response.json()["adjudication_id"] for response in responses]
    assert len(set(ids)) == 5
    assert all(ADJUDICATION_ID_PATTERN.match(value) for value in ids)

    persisted = get_network_task_repository().get_owned(task_id, "local-preview")
    assert persisted is not None
    assert len(persisted.adjudications) == 5
    assert len({item.adjudication_id for item in persisted.adjudications}) == 5

    # the projection still collapses the row to a single latest decision
    projection = client.get(f"/api/network/result/{task_id}").json()["adjudication"]
    assert len([entry for entry in projection["current"] if entry["lineage_row_id"] == row_id]) == 1
    assert projection["counts"]["included"] == 1


# ── Fail-closed ownership ───────────────────────────────────────────


def test_submit_adjudication_hides_legacy_ownerless_task() -> None:
    client = TestClient(app)
    repo = get_network_task_repository()
    assert (
        repo.create(
            NetworkTaskRecord(
                task_id="network-ownerless-adj",
                owner_id=None,
                query="消风散",
                analysis_type="formula",
                status="completed",
                progress=100,
                poll_count=2,
                result=NetworkAnalysisResult(
                    task_id="network-ownerless-adj",
                    query="消风散",
                    analysis_type="formula",
                    chains=[],
                    disclaimer="非诊断结论、需结合临床。",
                ),
                created_at="2026-07-15T00:00:00+00:00",
            )
        )
        is True
    )

    response = _post_adjudication(
        client,
        "network-ownerless-adj",
        {"lineage_row_id": "disease-" + "a" * 64, "decision": "included"},
    )

    assert response.status_code == 404
    assert repo.get_owned("network-ownerless-adj", "local-preview") is None
    persisted = repo.get("network-ownerless-adj")
    assert persisted is not None
    assert persisted.adjudications == []


def test_submit_adjudication_is_owner_scoped_between_reviewers_in_protected_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_access_tokens = os.environ.get("QIYAN_ACCESS_TOKENS")
    monkeypatch.setenv("QIYAN_ACCESS_TOKENS", "alpha")
    main_module = importlib.import_module("app.main")
    importlib.reload(main_module)
    reviewer_a_headers = {
        "X-Access-Token": "alpha",
        "X-Qiyan-Reviewer": "reviewer-a",
    }
    reviewer_b_headers = {
        "X-Access-Token": "alpha",
        "X-Qiyan-Reviewer": "reviewer-b",
    }

    try:
        client = TestClient(main_module.app)
        task_id, payload = _create_completed_compound_child_task(client, reviewer_a_headers)
        row_id = _lineage_row_ids(payload)["disease_targets"][0]
        body = {"lineage_row_id": row_id, "decision": "included"}

        foreign = _post_adjudication(client, task_id, body, reviewer_b_headers)
        owned = _post_adjudication(client, task_id, body, reviewer_a_headers)

        assert foreign.status_code == 404
        assert owned.status_code == 201

        persisted = get_network_task_repository().get_owned(task_id, "reviewer-a")
        assert persisted is not None
        assert len(persisted.adjudications) == 1
        assert persisted.adjudications[0].reviewer_id == "reviewer-a"

        unauthenticated = client.post(
            f"/api/network/result/{task_id}/adjudications",
            json=body,
        )
        assert unauthenticated.status_code == 401
    finally:
        if original_access_tokens is None:
            monkeypatch.delenv("QIYAN_ACCESS_TOKENS", raising=False)
        else:
            monkeypatch.setenv("QIYAN_ACCESS_TOKENS", original_access_tokens)
        importlib.reload(main_module)


# ── State-machine and payload guards ────────────────────────────────


def test_submit_adjudication_rejects_non_completed_task_without_advancing_it() -> None:
    client = TestClient(app)
    source_task_id = _create_verified_disease_task(client)
    queued_child_id = _create_compound_child_task(client, source_task_id)

    response = _post_adjudication(
        client,
        queued_child_id,
        {"lineage_row_id": "compound-" + "a" * 64, "decision": "included"},
    )

    assert response.status_code == 409
    persisted = get_network_task_repository().get_owned(queued_child_id, "local-preview")
    assert persisted is not None
    assert persisted.status == "queued"
    assert persisted.poll_count == 0
    assert persisted.adjudications == []


def test_submit_adjudication_rejects_failed_task() -> None:
    client = TestClient(app)
    repo = get_network_task_repository()
    assert (
        repo.create(
            NetworkTaskRecord(
                task_id="network-failed-adj",
                owner_id="local-preview",
                query="消风散",
                analysis_type="formula",
                status="failed",
                progress=100,
                poll_count=2,
                result=None,
                error="live provider returned no chains",
                created_at="2026-07-15T00:00:00+00:00",
            )
        )
        is True
    )

    response = _post_adjudication(
        client,
        "network-failed-adj",
        {"lineage_row_id": "disease-" + "a" * 64, "decision": "included"},
    )

    assert response.status_code == 409


def test_submit_adjudication_rejects_unknown_lineage_row() -> None:
    client = TestClient(app)
    task_id, _ = _create_completed_compound_child_task(client)

    response = _post_adjudication(
        client,
        task_id,
        {"lineage_row_id": "disease-" + "f" * 64, "decision": "included"},
    )

    assert response.status_code == 422
    persisted = get_network_task_repository().get_owned(task_id, "local-preview")
    assert persisted is not None
    assert persisted.adjudications == []


def test_submit_adjudication_rejects_mock_task_without_lineage_rows() -> None:
    client = TestClient(app)
    repo = get_network_task_repository()
    assert (
        repo.create(
            NetworkTaskRecord(
                task_id="network-mock-no-lineage",
                owner_id="local-preview",
                query="黄芪",
                analysis_type="herb",
                status="completed",
                progress=100,
                poll_count=2,
                result=NetworkAnalysisResult(
                    task_id="network-mock-no-lineage",
                    query="黄芪",
                    analysis_type="herb",
                    chains=[],
                    disclaimer="非诊断结论、需结合临床。",
                ),
                created_at="2026-07-15T00:00:00+00:00",
            )
        )
        is True
    )

    response = _post_adjudication(
        client,
        "network-mock-no-lineage",
        {"lineage_row_id": "compound-" + "a" * 64, "decision": "included"},
    )

    assert response.status_code == 422
    persisted = repo.get_owned("network-mock-no-lineage", "local-preview")
    assert persisted is not None
    assert persisted.adjudications == []


def test_submit_adjudication_rejects_extra_body_fields() -> None:
    client = TestClient(app)
    task_id, payload = _create_completed_compound_child_task(client)
    row_id = _lineage_row_ids(payload)["disease_targets"][0]

    response = _post_adjudication(
        client,
        task_id,
        {
            "lineage_row_id": row_id,
            "decision": "included",
            "reviewer_id": "client-controlled",
        },
    )

    assert response.status_code == 422
    persisted = get_network_task_repository().get_owned(task_id, "local-preview")
    assert persisted is not None
    assert persisted.adjudications == []


@pytest.mark.parametrize(
    "body",
    [
        {"decision": "included"},
        {"lineage_row_id": "disease-" + "a" * 64},
        {"lineage_row_id": "disease-" + "a" * 64, "decision": "maybe"},
        {"lineage_row_id": "", "decision": "included"},
        {"lineage_row_id": "disease-" + "a" * 64, "decision": "included", "reason": "x" * 501},
    ],
)
def test_submit_adjudication_rejects_invalid_body(body: dict[str, object]) -> None:
    client = TestClient(app)
    task_id, _ = _create_completed_compound_child_task(client)

    response = _post_adjudication(client, task_id, body)

    assert response.status_code == 422
    persisted = get_network_task_repository().get_owned(task_id, "local-preview")
    assert persisted is not None
    assert persisted.adjudications == []


# ── Read-only projections ───────────────────────────────────────────


def test_result_projection_includes_zeroed_adjudication_block_before_any_decision() -> None:
    client = TestClient(app)
    task_id, payload = _create_completed_compound_child_task(client)
    expected_pending = _total_lineage_rows(payload)
    assert expected_pending > 0

    projection = client.get(f"/api/network/result/{task_id}").json()["adjudication"]

    assert projection["counts"] == {
        "included": 0,
        "excluded": 0,
        "needs_review": 0,
        "pending": expected_pending,
    }
    assert projection["current"] == []


def test_result_projection_counts_each_decision_bucket() -> None:
    client = TestClient(app)
    task_id, payload = _create_completed_compound_child_task(client)
    row_ids = _lineage_row_ids(payload)
    decisions = (
        ("disease_targets", "included"),
        ("compound_targets", "excluded"),
        ("intersection_targets", "needs_review"),
    )
    for set_name, decision in decisions:
        response = _post_adjudication(
            client,
            task_id,
            {"lineage_row_id": row_ids[set_name][0], "decision": decision},
        )
        assert response.status_code == 201

    projection = client.get(f"/api/network/result/{task_id}").json()["adjudication"]

    assert projection["counts"] == {
        "included": 1,
        "excluded": 1,
        "needs_review": 1,
        "pending": _total_lineage_rows(payload) - 3,
    }
    current_by_row = {entry["lineage_row_id"]: entry for entry in projection["current"]}
    assert set(current_by_row) == {row_ids[set_name][0] for set_name, _ in decisions}
    for entry in projection["current"]:
        assert set(entry.keys()) == {"lineage_row_id", "decision", "reason", "decided_at"}
        assert "reviewer_id" not in entry


def test_adjudication_does_not_mutate_frozen_lineage_or_readiness() -> None:
    client = TestClient(app)
    task_id, payload = _create_completed_compound_child_task(client)
    row_id = _lineage_row_ids(payload)["disease_targets"][0]
    lineage_before = json.dumps(payload["result"]["target_lineage"], sort_keys=True)
    readiness_before = json.dumps(payload["result"]["readiness"], sort_keys=True)
    assert payload["result"]["readiness"]["formal_network_ready"] is False

    response = _post_adjudication(
        client,
        task_id,
        {"lineage_row_id": row_id, "decision": "included", "reason": "人工纳入"},
    )
    assert response.status_code == 201

    after = client.get(f"/api/network/result/{task_id}").json()
    assert json.dumps(after["result"]["target_lineage"], sort_keys=True) == lineage_before
    assert json.dumps(after["result"]["readiness"], sort_keys=True) == readiness_before
    assert after["result"]["readiness"]["formal_network_ready"] is False

    persisted = get_network_task_repository().get_owned(task_id, "local-preview")
    assert persisted is not None
    assert persisted.result is not None
    persisted_lineage = json.dumps(
        persisted.result.target_lineage.model_dump(mode="json"), sort_keys=True
    )
    assert persisted_lineage == lineage_before
    assert persisted.result.readiness.formal_network_ready is False
    assert all(
        row.adjudication_status == "pending"
        for row in persisted.result.target_lineage.disease_targets
    )


def test_result_get_stays_read_only_after_adjudication() -> None:
    client = TestClient(app)
    task_id, payload = _create_completed_compound_child_task(client)
    row_id = _lineage_row_ids(payload)["disease_targets"][0]
    created = _post_adjudication(
        client, task_id, {"lineage_row_id": row_id, "decision": "included"}
    )
    assert created.status_code == 201

    first = client.get(f"/api/network/result/{task_id}")
    second = client.get(f"/api/network/result/{task_id}")

    assert first.status_code == 200
    assert second.status_code == 200
    persisted = get_network_task_repository().get_owned(task_id, "local-preview")
    assert persisted is not None
    assert len(persisted.adjudications) == 1
    assert persisted.status == "completed"
    assert first.json()["adjudication"] == second.json()["adjudication"]


# ── Report projection ───────────────────────────────────────────────


def test_report_includes_read_only_adjudication_section() -> None:
    client = TestClient(app)
    task_id, payload = _create_completed_compound_child_task(client)
    row_id = _lineage_row_ids(payload)["disease_targets"][0]
    created = _post_adjudication(
        client,
        task_id,
        {"lineage_row_id": row_id, "decision": "included", "reason": "指南推荐靶点"},
    )
    assert created.status_code == 201

    response = client.get(f"/api/network/result/{task_id}/report")

    assert response.status_code == 200
    markdown = response.text
    assert "## 人工判定" in markdown
    assert "Included" in markdown
    assert "Pending" in markdown
    assert row_id in markdown
    assert "included" in markdown
    assert "指南推荐靶点" in markdown
    # The report read must not advance or rewrite the persisted record.
    persisted = get_network_task_repository().get_owned(task_id, "local-preview")
    assert persisted is not None
    assert persisted.status == "completed"
    assert persisted.poll_count == 2
    assert len(persisted.adjudications) == 1


def test_report_shows_zeroed_adjudication_section_before_any_decision() -> None:
    client = TestClient(app)
    task_id, payload = _create_completed_compound_child_task(client)
    expected_pending = _total_lineage_rows(payload)

    response = client.get(f"/api/network/result/{task_id}/report")

    assert response.status_code == 200
    markdown = response.text
    assert "## 人工判定" in markdown
    assert "（尚无人工判定记录。）" in markdown
    assert f"| 0 | 0 | 0 | {expected_pending} |" in markdown
    persisted = get_network_task_repository().get_owned(task_id, "local-preview")
    assert persisted is not None
    assert persisted.adjudications == []
