import hashlib
import json
import re
from pathlib import Path
from typing import Any

_CACHE_SCHEMA_VERSION = "v1"
_SAFE_CACHE_KEY_RE = re.compile(r"^[a-zA-Z0-9_.-]+$")


def build_network_cache_key(
    *,
    provider: str,
    query: str,
    params: dict[str, Any],
) -> str:
    canonical = json.dumps(
        {
            "provider": provider,
            "query": query,
            "params": params,
            "schema_version": _CACHE_SCHEMA_VERSION,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
    safe_provider = re.sub(r"[^a-zA-Z0-9_.-]+", "-", provider.strip().lower()) or "provider"
    return f"{safe_provider}-{_CACHE_SCHEMA_VERSION}-{digest}"


class NetworkCacheRepository:
    """Small JSON cache rooted under runtime state for opt-in live network data."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def _path_for_key(self, cache_key: str) -> Path | None:
        if not _SAFE_CACHE_KEY_RE.match(cache_key):
            return None
        root = self.root.resolve()
        path = (root / f"{cache_key}.json").resolve()
        if root != path.parent:
            return None
        return path

    def read_json(self, cache_key: str) -> Any | None:
        path = self._path_for_key(cache_key)
        if path is None or not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def write_json(self, cache_key: str, payload: Any) -> None:
        path = self._path_for_key(cache_key)
        if path is None:
            raise ValueError("Invalid network cache key")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
