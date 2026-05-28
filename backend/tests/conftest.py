from pathlib import Path

import pytest


def _copy_seed(source_name: str, target: Path) -> None:
    source = Path(__file__).resolve().parents[1] / "data" / "literature" / source_name
    target.write_bytes(source.read_bytes())


@pytest.fixture(autouse=True)
def isolate_runtime_state(
    request: pytest.FixtureRequest,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep tests deterministic even after local demo uploads mutate runtime JSON."""

    if request.node.path.name in {"test_config.py", "test_runtime_storage.py"}:
        yield
        return

    literature_path = tmp_path / "literature_state.json"
    chunk_path = tmp_path / "chunk_state.json"
    network_path = tmp_path / "network_tasks_state.json"
    vector_path = tmp_path / "vector_index_state.npy"
    upload_dir = tmp_path / "uploads"

    _copy_seed("sample_ad_literature.json", literature_path)
    _copy_seed("sample_ad_chunks.json", chunk_path)
    network_path.write_text("[]\n", encoding="utf-8")

    monkeypatch.setenv("LITERATURE_RUNTIME_STATE_PATH", str(literature_path))
    monkeypatch.setenv("CHUNK_RUNTIME_STATE_PATH", str(chunk_path))
    monkeypatch.setenv("NETWORK_TASKS_RUNTIME_STATE_PATH", str(network_path))
    monkeypatch.setenv("VECTOR_INDEX_RUNTIME_CACHE_PATH", str(vector_path))
    monkeypatch.setenv("UPLOAD_STORAGE_DIR", str(upload_dir))

    from app.core.config import get_settings
    from app.repositories.chunk import InMemoryChunkRepository
    from app.repositories.literature import InMemoryLiteratureRepository
    from app.services import fake_parser, literature, rag
    from app.services.retrieval.vector_index import reset_chunk_vector_index_cache

    get_settings.cache_clear()
    reset_chunk_vector_index_cache()

    monkeypatch.setattr(literature, "_REPOSITORY", InMemoryLiteratureRepository(literature_path))
    monkeypatch.setattr(rag, "_REPOSITORY", InMemoryLiteratureRepository(literature_path))
    monkeypatch.setattr(rag, "_CHUNK_REPOSITORY", InMemoryChunkRepository(chunk_path))
    monkeypatch.setattr(fake_parser, "_CHUNK_REPOSITORY", InMemoryChunkRepository(chunk_path))

    yield

    get_settings.cache_clear()
    reset_chunk_vector_index_cache()
