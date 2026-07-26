"""Owner-scoped read-only network task list API tests.

``GET /api/network/tasks`` is a pure observation surface like the report GET:
it must never advance queued/running tasks, must never expose ``owner_id``,
and must fail closed for legacy ownerless records.
"""

import importlib
import os

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.runtime_storage import get_network_task_repository
from app.schemas.network import (
    NetworkAnalysisResult,
    NetworkCompoundTargetVerifiedSnapshot,
    NetworkResearchReadiness,
    NetworkTaskRecord,
)

RESEARCH_PROTOCOL = {
    "disease": "atopic_dermatitis",
    "phenotype": "特应性皮炎伴 2 型炎症与皮肤屏障异常",
    "species": "Homo sapiens",
    "evidence_policy": "direct_human_first",
    "query_date": "2026-07-11",
}

SUMMARY_FIELDS = {
    "task_id",
    "source_task_id",
    "query",
    "analysis_type",
    "status",
    "data_mode",
    "formal_network_ready",
    "created_at",
}


def _create_task(
    client: TestClient,
    query: str = "消风散",
    headers: dict[str, str] | None = None,
) -> str:
    response = client.post(
        "/api/network/analyze",
        json={
            "query": query,
            "analysis_type": "formula",
            "research_protocol": RESEARCH_PROTOCOL,
        },
        headers=headers,
    )
    assert response.status_code == 202
    task_id = response.json()["task_id"]
    assert isinstance(task_id, str)
    return task_id


def _verified_compound_snapshot_payload() -> dict[str, object]:
    return {
        "source_profile": "chembl_known_activity_v1",
        "compound_id": "CHEMBL1201587",
        "compound_label": "Quercetin",
        "species": "Homo sapiens",
        "source_database": "ChEMBL",
        "database_version": "34",
        "source_query_id": "CHEMBL1201587",
        "source_query_label": "Quercetin",
        "source_query_parameters": {"assay_organism": "Homo sapiens", "pchembl_value_min": 6.0},
        "query_date": "2026-07-12",
        "retrieved_at": "2026-07-12T08:30:00Z",
        "score_name": "pchembl_value",
        "applied_threshold": 6.0,
        "threshold_operator": "gte",
        "identifier_mapping": "ChEMBL target component gene symbol",
        "identifier_mapping_version": "34",
        "usage_license_note": "ChEMBL data; see database terms.",
        "records": [
            {
                "raw_identifier": "CHEMBL1792",
                "canonical_symbol": "IL6",
                "source_record_id": "CHEMBL_ACTIVITY_1001",
                "source_score": 6.4,
            }
        ],
        "provenance_verification_status": "server_verified_raw_artifact",
        "import_payload_sha256": "a" * 64,
        "source_artifact_sha256": "b" * 64,
        "source_artifact_filename": "chembl-known-activities.json",
        "source_artifact_media_type": "application/json",
    }


def test_list_tasks_returns_summaries_without_owner_id() -> None:
    client = TestClient(app)
    first_task_id = _create_task(client, query="消风散")
    second_task_id = _create_task(client, query="黄连解毒汤")

    response = client.get("/api/network/tasks")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {"tasks"}
    tasks = payload["tasks"]
    assert len(tasks) == 2
    for summary in tasks:
        assert set(summary.keys()) == SUMMARY_FIELDS
        assert "owner_id" not in summary
    newest = tasks[0]
    assert newest["task_id"] == second_task_id
    assert newest["query"] == "黄连解毒汤"
    assert newest["analysis_type"] == "formula"
    assert newest["status"] == "queued"
    assert newest["data_mode"] == "mock"
    assert newest["source_task_id"] is None
    assert newest["formal_network_ready"] is False
    assert isinstance(newest["created_at"], str) and newest["created_at"]
    assert tasks[1]["task_id"] == first_task_id


def test_list_tasks_orders_newest_first() -> None:
    client = TestClient(app)
    first_task_id = _create_task(client, query="消风散")
    second_task_id = _create_task(client, query="消风散")

    tasks = client.get("/api/network/tasks").json()["tasks"]

    assert [task["task_id"] for task in tasks] == [second_task_id, first_task_id]


def test_list_tasks_projects_formal_network_ready_from_readiness() -> None:
    client = TestClient(app)
    repo = get_network_task_repository()
    result = NetworkAnalysisResult(
        task_id="network-ready0001",
        query="消风散",
        analysis_type="formula",
        readiness=NetworkResearchReadiness(
            protocol_complete=True,
            formal_network_ready=True,
            blocking_reasons=[],
        ),
        chains=[],
        disclaimer="非诊断结论、需结合临床。",
    )
    assert (
        repo.create(
            NetworkTaskRecord(
                task_id="network-ready0001",
                owner_id="local-preview",
                query="消风散",
                analysis_type="formula",
                status="completed",
                progress=100,
                poll_count=2,
                result=result,
                created_at="2026-07-15T00:00:00+00:00",
            )
        )
        is True
    )

    response = client.get("/api/network/tasks")

    assert response.status_code == 200
    summaries = {task["task_id"]: task for task in response.json()["tasks"]}
    assert summaries["network-ready0001"]["formal_network_ready"] is True
    assert summaries["network-ready0001"]["status"] == "completed"


def test_list_tasks_excludes_legacy_ownerless_records() -> None:
    client = TestClient(app)
    repo = get_network_task_repository()
    assert (
        repo.create(
            NetworkTaskRecord(
                task_id="network-legacyownerless",
                owner_id=None,
                query="黄芪",
                analysis_type="herb",
                status="queued",
                progress=0,
                poll_count=0,
                result=None,
                created_at="2026-07-10T00:00:00+00:00",
            )
        )
        is True
    )
    owned_task_id = _create_task(client)

    response = client.get("/api/network/tasks")

    assert response.status_code == 200
    assert [task["task_id"] for task in response.json()["tasks"]] == [owned_task_id]


def test_list_tasks_does_not_advance_queued_tasks() -> None:
    client = TestClient(app)
    task_id = _create_task(client)
    repo = get_network_task_repository()

    first = client.get("/api/network/tasks")
    second = client.get("/api/network/tasks")

    assert first.status_code == 200
    assert second.status_code == 200
    persisted = repo.get(task_id)
    assert persisted is not None
    assert persisted.status == "queued"
    assert persisted.poll_count == 0
    listed = {task["task_id"]: task for task in second.json()["tasks"]}[task_id]
    assert listed["status"] == "queued"


def test_list_tasks_projects_legacy_unlinked_compound_child_as_failed() -> None:
    client = TestClient(app)
    repo = get_network_task_repository()
    snapshot = NetworkCompoundTargetVerifiedSnapshot.model_validate(
        _verified_compound_snapshot_payload()
    )
    assert (
        repo.create(
            NetworkTaskRecord(
                task_id="network-unlinkedchild",
                owner_id="local-preview",
                query="消风散",
                analysis_type="formula",
                compound_target_import=snapshot,
                status="queued",
                progress=0,
                poll_count=0,
                result=None,
                created_at="2026-07-12T00:00:00+00:00",
            )
        )
        is True
    )

    response = client.get("/api/network/tasks")

    assert response.status_code == 200
    summaries = {task["task_id"]: task for task in response.json()["tasks"]}
    assert summaries["network-unlinkedchild"]["status"] == "failed"
    # The list read must not repair or advance the persisted record either.
    persisted = repo.get("network-unlinkedchild")
    assert persisted is not None
    assert persisted.status == "queued"
    assert persisted.poll_count == 0


def test_list_tasks_is_owner_scoped_between_reviewers_in_protected_mode(
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
        task_a = _create_task(client, query="消风散", headers=reviewer_a_headers)
        task_b = _create_task(client, query="黄连解毒汤", headers=reviewer_b_headers)

        response_a = client.get("/api/network/tasks", headers=reviewer_a_headers)
        response_b = client.get("/api/network/tasks", headers=reviewer_b_headers)

        assert response_a.status_code == 200
        assert [task["task_id"] for task in response_a.json()["tasks"]] == [task_a]
        assert response_b.status_code == 200
        assert [task["task_id"] for task in response_b.json()["tasks"]] == [task_b]

        unauthenticated = client.get("/api/network/tasks")
        assert unauthenticated.status_code == 401
    finally:
        if original_access_tokens is None:
            monkeypatch.delenv("QIYAN_ACCESS_TOKENS", raising=False)
        else:
            monkeypatch.setenv("QIYAN_ACCESS_TOKENS", original_access_tokens)
        importlib.reload(main_module)
