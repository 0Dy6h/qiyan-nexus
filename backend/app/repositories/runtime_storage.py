import os
from pathlib import Path

_SAMPLE_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "literature" / "sample_ad_literature.json"
)
_CHUNK_SAMPLE_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "literature" / "sample_ad_chunks.json"
)


def resolve_literature_storage_path() -> Path:
    """
    Return absolute path to runtime literature state file:
    backend/data/runtime/literature_state.json

    On first call:
    - If LITERATURE_RUNTIME_STATE_PATH env var is set, use it as target path
    - If target file already exists, return its path directly
    - If target does not exist, bootstrap from sample (binary copy), then return

    Creates backend/data/runtime/ directory if needed.
    """
    env_path = os.environ.get("LITERATURE_RUNTIME_STATE_PATH")
    if env_path:
        target = Path(env_path)
    else:
        target = Path(__file__).resolve().parents[2] / "data" / "runtime" / "literature_state.json"

    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(_SAMPLE_PATH.read_bytes())

    return target


def resolve_chunk_storage_path() -> Path:
    """
    Return absolute path to runtime chunk state file:
    backend/data/runtime/chunk_state.json

    Mirrors resolve_literature_storage_path so uploaded PDF chunks land in
    gitignored runtime state, not in the tracked seed file. Bootstrap is
    binary-identical to sample_ad_chunks.json on first call.

    Env override: CHUNK_RUNTIME_STATE_PATH.
    """
    env_path = os.environ.get("CHUNK_RUNTIME_STATE_PATH")
    if env_path:
        target = Path(env_path)
    else:
        target = Path(__file__).resolve().parents[2] / "data" / "runtime" / "chunk_state.json"

    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(_CHUNK_SAMPLE_PATH.read_bytes())

    return target


def resolve_network_tasks_storage_path() -> Path:
    """
    Return absolute path to runtime network task state file:
    backend/data/runtime/network_tasks_state.json

    Network tasks are mutation-only state with no tracked seed, so first-call
    bootstrap writes an empty list "[]\n" instead of copying a sample file.

    Env override: NETWORK_TASKS_RUNTIME_STATE_PATH.
    """
    env_path = os.environ.get("NETWORK_TASKS_RUNTIME_STATE_PATH")
    if env_path:
        target = Path(env_path)
    else:
        target = (
            Path(__file__).resolve().parents[2] / "data" / "runtime" / "network_tasks_state.json"
        )

    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("[]\n", encoding="utf-8")

    return target


def resolve_vector_index_cache_path() -> Path:
    """
    Return absolute path to the chunk vector index cache file:
    backend/data/runtime/vector_index_state.npy

    Unlike literature/chunk runtime files, the vector index is a *derived*
    artifact — first build writes it; missing cache is normal. The companion
    metadata file lives next to it as ``vector_index_state.meta.json``.

    Env override: VECTOR_INDEX_RUNTIME_CACHE_PATH.
    """
    env_path = os.environ.get("VECTOR_INDEX_RUNTIME_CACHE_PATH")
    if env_path:
        target = Path(env_path)
    else:
        target = Path(__file__).resolve().parents[2] / "data" / "runtime" / "vector_index_state.npy"
    target.parent.mkdir(parents=True, exist_ok=True)
    return target
