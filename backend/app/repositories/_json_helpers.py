"""Shared JSON serialization helpers for in-memory repositories."""

import json
from pathlib import Path
from typing import Any


def read_json_list(path: Path) -> list[dict[str, Any]]:
    """Read a JSON array file from disk."""
    data: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise TypeError(f"Expected JSON array, got {type(data).__name__}")
    if not all(isinstance(item, dict) for item in data):
        raise TypeError("Expected all array elements to be objects")
    return data


def write_json_list(path: Path, items: list[dict[str, Any]]) -> None:
    """Write a JSON array to disk with consistent formatting."""
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
