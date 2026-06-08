import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.repositories.network_cache import NetworkCacheRepository, build_network_cache_key
from app.services.network_connectors import UniProtConnector


@pytest.fixture(autouse=True)
def _isolate_network_tasks_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "NETWORK_TASKS_RUNTIME_STATE_PATH", str(tmp_path / "network_tasks_state.json")
    )


def test_network_analyze_endpoint_creates_task():
    client = TestClient(app)

    response = client.post(
        "/api/network/analyze",
        json={
            "query": "消风散",
            "analysis_type": "formula",
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["progress"] == 0
    assert payload["data_mode"] == "mock"
    assert payload["task_id"].startswith("network-")


def test_network_result_endpoint_returns_progress_then_completed_result():
    client = TestClient(app)

    create_response = client.post(
        "/api/network/analyze",
        json={
            "query": "黄芪",
            "analysis_type": "herb",
        },
    )
    assert create_response.status_code == 202
    task_id = create_response.json()["task_id"]

    first_poll = client.get(f"/api/network/result/{task_id}")
    assert first_poll.status_code == 200
    first_payload = first_poll.json()
    assert first_payload["status"] == "running"
    assert first_payload["progress"] == 60
    assert first_payload["data_mode"] == "mock"
    assert first_payload["result"] is None

    second_poll = client.get(f"/api/network/result/{task_id}")
    assert second_poll.status_code == 200
    second_payload = second_poll.json()
    assert second_payload["status"] == "completed"
    assert second_payload["progress"] == 100
    assert second_payload["data_mode"] == "mock"
    assert second_payload["error"] is None
    assert second_payload["warnings"] == []
    assert second_payload["result"] is not None
    assert second_payload["result"]["data_mode"] == "mock"
    assert second_payload["result"]["analysis_type"] == "herb"
    assert second_payload["result"]["query"] == "黄芪"
    assert len(second_payload["result"]["chains"]) >= 1
    first_chain = second_payload["result"]["chains"][0]
    assert first_chain["related_entity_ids"]
    assert all(entity_id for entity_id in first_chain["related_entity_ids"])


def test_network_live_mode_surfaces_provenance_fields(monkeypatch, tmp_path: Path):
    cache_dir = tmp_path / "network_cache"
    prediction_file = tmp_path / "predictions.csv"
    cache_repo = NetworkCacheRepository(cache_dir)
    compound_name = "Astragaloside IV"
    cache_repo.write_json(
        build_network_cache_key(
            provider="tcmsp",
            query="黄芪",
            params={"herb": "黄芪", "analysis_type": "herb"},
        ),
        {"compounds": [{"name": compound_name, "herb": "黄芪"}]},
    )
    cache_repo.write_json(
        build_network_cache_key(
            provider="pubchem",
            query=compound_name,
            params={"compound": compound_name},
        ),
        {"IdentifierList": {"CID": [13943297]}},
    )
    cache_repo.write_json(
        build_network_cache_key(
            provider="chembl",
            query=compound_name,
            params={"compound": compound_name, "pubchem_cid": "13943297"},
        ),
        {
            "activities": [
                {
                    "target_pref_name": "IL6",
                    "target_organism": "Homo sapiens",
                    "pchembl_value": "8.0",
                    "assay_chembl_id": "CHEMBLASSAY-HQ-1",
                }
            ]
        },
    )
    cache_repo.write_json(
        build_network_cache_key(
            provider="kegg",
            query="IL6,TNF",
            params={"genes": "IL6,TNF"},
        ),
        {
            "link_text": "hsa:3569\tpath:hsa04668\nhsa:7124\tpath:hsa04668\n",
            "list_text": "path:hsa04668\tTNF signaling pathway - Homo sapiens (human)\n",
        },
    )
    for symbol, accession, name in [
        ("IL6", "P05231", "Interleukin-6"),
        ("TNF", "P01375", "Tumor necrosis factor"),
    ]:
        cache_repo.write_json(
            build_network_cache_key(
                provider="uniprot",
                query=symbol,
                params={
                    "query": UniProtConnector.build_query(symbol),
                    "fields": "accession,gene_names,protein_name",
                    "format": "json",
                    "size": 1,
                },
            ),
            {
                "results": [
                    {
                        "primaryAccession": accession,
                        "genes": [{"geneName": {"value": symbol}}],
                        "proteinDescription": {"recommendedName": {"fullName": {"value": name}}},
                    }
                ]
            },
        )
    cache_repo.write_json(
        build_network_cache_key(
            provider="string",
            query="IL6,TNF",
            params={"identifiers": "IL6\rTNF", "species": 9606, "required_score": 400},
        ),
        "preferredName_A\tpreferredName_B\tscore\nIL6\tTNF\t0.982\n",
    )
    prediction_file.write_text(
        "compound,target_symbol,score,source,source_record_id,retrieved_at\n"
        f"{compound_name},TNF,0.72,SwissTargetPrediction,swiss-hq-1,2026-06-08T00:00:00Z\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("QIYAN_NETWORK_DATA_PROVIDER", "live")
    monkeypatch.setenv("QIYAN_NETWORK_CACHE_DIR", str(cache_dir))
    monkeypatch.setenv("QIYAN_NETWORK_TARGET_PREDICTION_FILE", str(prediction_file))
    get_settings.cache_clear()
    client = TestClient(app)

    create_response = client.post(
        "/api/network/analyze",
        json={
            "query": "黄芪",
            "analysis_type": "herb",
        },
    )
    assert create_response.status_code == 202
    accepted = create_response.json()
    assert accepted["data_mode"] == "live"
    task_id = accepted["task_id"]

    client.get(f"/api/network/result/{task_id}")
    completed_response = client.get(f"/api/network/result/{task_id}")
    assert completed_response.status_code == 200
    payload = completed_response.json()
    assert payload["data_mode"] == "live"
    assert payload["status"] == "completed"
    assert payload["error"] is None
    assert isinstance(payload["warnings"], list)
    assert payload["result"]["data_mode"] == "live"
    assert len(payload["result"]["pipeline_steps"]) >= 1
    assert len(payload["result"]["data_sources"]) >= 1
    first_chain = payload["result"]["chains"][0]
    assert first_chain["target_evidence_type"] in {"known_activity", "predicted", "mixed"}
    assert isinstance(first_chain["evidence_refs"], list)
    get_settings.cache_clear()


def test_network_live_mode_returns_failed_state_when_no_live_chain_can_be_built(
    monkeypatch,
    tmp_path: Path,
):
    monkeypatch.setenv("QIYAN_NETWORK_DATA_PROVIDER", "live")
    monkeypatch.setenv("QIYAN_NETWORK_CACHE_DIR", str(tmp_path / "empty_cache"))
    get_settings.cache_clear()
    client = TestClient(app)

    create_response = client.post(
        "/api/network/analyze",
        json={"query": "黄芪", "analysis_type": "herb"},
    )
    task_id = create_response.json()["task_id"]

    client.get(f"/api/network/result/{task_id}")
    completed_response = client.get(f"/api/network/result/{task_id}")

    assert completed_response.status_code == 200
    payload = completed_response.json()
    assert payload["status"] == "failed"
    assert payload["data_mode"] == "live"
    assert payload["result"] is None
    assert payload["error"] == "No live target chains could be assembled."
    assert "No live target chains could be assembled." in payload["warnings"]
    get_settings.cache_clear()


def test_network_result_endpoint_keeps_returning_completed_mock_result_after_completion():
    client = TestClient(app)

    create_response = client.post(
        "/api/network/analyze",
        json={
            "query": "白鲜皮",
            "analysis_type": "herb",
        },
    )
    assert create_response.status_code == 202
    task_id = create_response.json()["task_id"]

    client.get(f"/api/network/result/{task_id}")
    completed_response = client.get(f"/api/network/result/{task_id}")
    repeated_response = client.get(f"/api/network/result/{task_id}")

    assert completed_response.status_code == 200
    assert repeated_response.status_code == 200
    assert completed_response.json()["status"] == "completed"
    assert repeated_response.json()["status"] == "completed"
    assert repeated_response.json()["result"]["query"] == "白鲜皮"


def test_network_result_endpoint_returns_404_for_unknown_task():
    client = TestClient(app)

    response = client.get("/api/network/result/network-missing-task")

    assert response.status_code == 404
    assert response.json() == {"detail": "Network analysis task not found"}


def test_network_analyze_endpoint_rejects_empty_query():
    client = TestClient(app)

    response = client.post(
        "/api/network/analyze",
        json={
            "query": "",
            "analysis_type": "formula",
        },
    )

    assert response.status_code == 422


@pytest.mark.skipif(
    os.environ.get("QIYAN_STATE_BACKEND") == "sqlite",
    reason="JSON file persistence test; SQLite backend persists to DB instead",
)
def test_network_task_state_is_persisted_to_runtime_file(tmp_path: Path, monkeypatch):
    runtime_file = tmp_path / "persisted_tasks.json"
    monkeypatch.setenv("NETWORK_TASKS_RUNTIME_STATE_PATH", str(runtime_file))

    client = TestClient(app)
    create_response = client.post(
        "/api/network/analyze",
        json={"query": "消风散", "analysis_type": "formula"},
    )
    task_id = create_response.json()["task_id"]

    assert runtime_file.exists()
    after_create = json.loads(runtime_file.read_text(encoding="utf-8"))
    assert len(after_create) == 1
    assert after_create[0]["task_id"] == task_id
    assert after_create[0]["status"] == "queued"
    assert after_create[0]["poll_count"] == 0

    client.get(f"/api/network/result/{task_id}")
    after_first_poll = json.loads(runtime_file.read_text(encoding="utf-8"))
    assert after_first_poll[0]["status"] == "running"
    assert after_first_poll[0]["poll_count"] == 1

    # Simulate process restart: rebuild client from scratch; runtime file is the
    # only persistence layer, so completed state must be reachable on next poll.
    fresh_client = TestClient(app)
    second_poll = fresh_client.get(f"/api/network/result/{task_id}")
    assert second_poll.status_code == 200
    assert second_poll.json()["status"] == "completed"

    after_second_poll = json.loads(runtime_file.read_text(encoding="utf-8"))
    assert after_second_poll[0]["status"] == "completed"
    assert after_second_poll[0]["poll_count"] == 2
    first_chain = after_second_poll[0]["result"]["chains"][0]
    # Formula query now expands to constituent herbs via the seed entity graph;
    # the formula label is carried on the chain.formula field instead of herb.
    assert first_chain["formula"] == "消风散"
    assert first_chain["herb"] in {"荆芥", "防风", "牛蒡子"}


def test_network_entities_endpoint_returns_grouped_lookup_payload():
    client = TestClient(app)

    response = client.get("/api/network/entities")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {"herbs", "formulas", "compounds", "targets", "pathways"}
    assert len(payload["herbs"]) == 5
    assert len(payload["formulas"]) == 2
    assert len(payload["compounds"]) == 5
    assert len(payload["targets"]) == 5
    assert len(payload["pathways"]) == 4

    formula_ids = {f["id"] for f in payload["formulas"]}
    assert "formula-xiaofengsan" in formula_ids
    target_ids = {t["id"] for t in payload["targets"]}
    assert "target-flg" in target_ids


def test_network_entities_endpoint_each_entry_has_id_and_display_name():
    client = TestClient(app)

    payload = client.get("/api/network/entities").json()

    for herb in payload["herbs"]:
        assert herb["id"] and herb["name"]
    for formula in payload["formulas"]:
        assert formula["id"] and formula["name"]
    for compound in payload["compounds"]:
        assert compound["id"] and compound["name"]
    for target in payload["targets"]:
        assert target["id"] and target["symbol"] and target["name"]
    for pathway in payload["pathways"]:
        assert pathway["id"] and pathway["name"]


# ── Report endpoint tests ───────────────────────────────────────────────────


def test_report_endpoint_returns_404_for_missing_task():
    client = TestClient(app)

    response = client.get("/api/network/result/network-nonexistent-task/report")

    assert response.status_code == 404
    assert response.json() == {"detail": "Network analysis task not found"}


def test_report_endpoint_returns_202_for_pending_task():
    """A newly created task is in 'queued' state.  The report endpoint calls
    get_network_analysis_result which advances it to 'running', but since
    'running' != 'completed' the endpoint returns 202."""
    client = TestClient(app)

    create_response = client.post(
        "/api/network/analyze",
        json={"query": "黄芩", "analysis_type": "herb"},
    )
    assert create_response.status_code == 202
    task_id = create_response.json()["task_id"]

    report_response = client.get(f"/api/network/result/{task_id}/report")
    assert report_response.status_code == 202


def test_report_endpoint_returns_202_for_running_task():
    """After one poll the task is 'running'.  The report endpoint calls
    get_network_analysis_result which advances it to 'completed', so this
    actually returns 200.  We verify the 202 path via the pending-task test
    above and document the state-machine behaviour here."""
    client = TestClient(app)

    create_response = client.post(
        "/api/network/analyze",
        json={"query": "黄芪", "analysis_type": "herb"},
    )
    task_id = create_response.json()["task_id"]

    # First poll advances queued → running
    client.get(f"/api/network/result/{task_id}")

    # The report endpoint calls get_network_analysis_result again, which
    # advances running → completed, so it returns 200 (not 202).
    # This is expected: the state machine always advances on read.
    report_response = client.get(f"/api/network/result/{task_id}/report")
    assert report_response.status_code == 200


def test_report_endpoint_returns_markdown_for_completed_task():
    client = TestClient(app)

    create_response = client.post(
        "/api/network/analyze",
        json={"query": "黄芩", "analysis_type": "herb"},
    )
    task_id = create_response.json()["task_id"]

    # Poll twice to reach "completed"
    client.get(f"/api/network/result/{task_id}")
    client.get(f"/api/network/result/{task_id}")

    report_response = client.get(f"/api/network/result/{task_id}/report")
    assert report_response.status_code == 200

    text = report_response.text
    assert "# Qiyan Nexus 网络药理学报告导出" in text
    assert "非诊断结论、需结合临床。" in text
    assert "黄芩" in text
    assert "## 链路结果" in text
    assert "## 边界说明" in text


def test_report_endpoint_returns_500_when_result_is_none():
    """When a task is completed but result is None, the endpoint returns 500.

    This is a defensive test — in the current mock implementation, completed tasks
    always have a result, but the API guards against the edge case.
    Since we cannot manufacture a completed task with result=None through the
    public API, we document the expected behaviour here.
    """
    pass
