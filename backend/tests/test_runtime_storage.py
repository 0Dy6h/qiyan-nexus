import json
from pathlib import Path

from app.repositories.runtime_storage import (
    resolve_chunk_storage_path,
    resolve_literature_storage_path,
    resolve_network_tasks_storage_path,
)


def _sample_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "literature" / "sample_ad_literature.json"


def _chunk_sample_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "literature" / "sample_ad_chunks.json"


def _read_json(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: list[dict]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_bootstrap_when_runtime_file_does_not_exist(tmp_path: Path, monkeypatch):
    target = tmp_path / "literature_state.json"
    monkeypatch.setenv("LITERATURE_RUNTIME_STATE_PATH", str(target))

    assert not target.exists()
    result = resolve_literature_storage_path()

    assert result == target
    assert target.exists()
    assert _read_json(target) == _read_json(_sample_path())


def test_idempotent_when_runtime_file_already_exists(tmp_path: Path, monkeypatch):
    target = tmp_path / "literature_state.json"
    monkeypatch.setenv("LITERATURE_RUNTIME_STATE_PATH", str(target))

    resolve_literature_storage_path()

    mutated = [{"id": "custom"}]
    _write_json(target, mutated)

    result = resolve_literature_storage_path()

    assert result == target
    assert _read_json(target) == mutated


def test_env_override_points_to_custom_path_and_bootstraps(tmp_path: Path, monkeypatch):
    custom = tmp_path / "custom" / "state.json"
    monkeypatch.setenv("LITERATURE_RUNTIME_STATE_PATH", str(custom))

    assert not custom.parent.exists()
    result = resolve_literature_storage_path()

    assert result == custom
    assert custom.exists()
    assert _read_json(custom) == _read_json(_sample_path())


def test_env_override_bootstraps_only_once(tmp_path: Path, monkeypatch):
    custom = tmp_path / "only_once.json"
    monkeypatch.setenv("LITERATURE_RUNTIME_STATE_PATH", str(custom))

    resolve_literature_storage_path()
    mtime1 = custom.stat().st_mtime

    resolve_literature_storage_path()
    mtime2 = custom.stat().st_mtime

    assert mtime2 == mtime1


def test_chunk_bootstrap_when_runtime_file_does_not_exist(tmp_path: Path, monkeypatch):
    target = tmp_path / "chunk_state.json"
    monkeypatch.setenv("CHUNK_RUNTIME_STATE_PATH", str(target))

    assert not target.exists()
    result = resolve_chunk_storage_path()

    assert result == target
    assert target.exists()
    assert _read_json(target) == _read_json(_chunk_sample_path())


def test_chunk_idempotent_when_runtime_file_already_exists(tmp_path: Path, monkeypatch):
    target = tmp_path / "chunk_state.json"
    monkeypatch.setenv("CHUNK_RUNTIME_STATE_PATH", str(target))

    resolve_chunk_storage_path()

    mutated = [{"chunk_id": "custom-runtime-only"}]
    _write_json(target, mutated)

    result = resolve_chunk_storage_path()

    assert result == target
    assert _read_json(target) == mutated


def test_chunk_env_override_bootstraps_only_once(tmp_path: Path, monkeypatch):
    custom = tmp_path / "chunk_only_once.json"
    monkeypatch.setenv("CHUNK_RUNTIME_STATE_PATH", str(custom))

    resolve_chunk_storage_path()
    mtime1 = custom.stat().st_mtime

    resolve_chunk_storage_path()
    mtime2 = custom.stat().st_mtime

    assert mtime2 == mtime1


def test_network_tasks_storage_bootstraps_to_empty_list(tmp_path: Path, monkeypatch):
    target = tmp_path / "network_tasks_state.json"
    monkeypatch.setenv("NETWORK_TASKS_RUNTIME_STATE_PATH", str(target))

    assert not target.exists()
    result = resolve_network_tasks_storage_path()

    assert result == target
    assert target.exists()
    assert _read_json(target) == []


def test_network_tasks_storage_preserves_existing_runtime_file(tmp_path: Path, monkeypatch):
    target = tmp_path / "network_tasks_state.json"
    monkeypatch.setenv("NETWORK_TASKS_RUNTIME_STATE_PATH", str(target))

    resolve_network_tasks_storage_path()
    seeded = [{"task_id": "network-keep-me"}]
    _write_json(target, seeded)

    result = resolve_network_tasks_storage_path()

    assert result == target
    assert _read_json(target) == seeded


def test_network_tasks_storage_env_override_bootstraps_only_once(tmp_path: Path, monkeypatch):
    custom = tmp_path / "network_only_once.json"
    monkeypatch.setenv("NETWORK_TASKS_RUNTIME_STATE_PATH", str(custom))

    resolve_network_tasks_storage_path()
    mtime1 = custom.stat().st_mtime

    resolve_network_tasks_storage_path()
    mtime2 = custom.stat().st_mtime

    assert mtime2 == mtime1
