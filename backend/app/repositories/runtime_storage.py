import os
from pathlib import Path

_SAMPLE_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "literature" / "sample_ad_literature.json"
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
