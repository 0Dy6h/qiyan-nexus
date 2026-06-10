"""Shared JSON serialization helpers for in-memory repositories."""

import json
from pathlib import Path
from typing import Any


def read_json_list(path: Path) -> list[dict[str, Any]]:
    """Read a JSON array file from disk."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_list(path: Path, items: list[dict[str, Any]]) -> None:
    """Write a JSON array to disk with consistent formatting."""
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
