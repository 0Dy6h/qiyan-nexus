"""Test that InMemoryLiteratureRepository caches items in memory."""

import json
from pathlib import Path
from unittest.mock import mock_open, patch

from app.repositories.literature import InMemoryLiteratureRepository

SAMPLE_ITEMS = [
    {
        "id": "test-001",
        "title": "Test Literature",
        "language": "zh",
        "source_type": "cn_literature",
        "source": "Test Source",
        "year": 2025,
        "snippet": "Test snippet",
    }
]


def test_repository_loads_json_once_on_construction(tmp_path: Path):
    """list_items() should not trigger disk I/O after construction."""
    data_path = tmp_path / "literature.json"
    data_path.write_text(json.dumps(SAMPLE_ITEMS, ensure_ascii=False), encoding="utf-8")

    repo = InMemoryLiteratureRepository(data_path)

    # Mock builtin open to track file access
    with patch("builtins.open", mock_open()) as mock_file:
        items1 = repo.list_items()
        items2 = repo.list_items()
        items3 = repo.list_items()

        assert len(items1) == 1
        assert len(items2) == 1
        assert len(items3) == 1
        # No file open calls after construction
        mock_file.assert_not_called()


def test_repository_get_item_by_id_uses_memory_cache(tmp_path: Path):
    """get_item_by_id should not trigger disk I/O."""
    data_path = tmp_path / "literature.json"
    data_path.write_text(json.dumps(SAMPLE_ITEMS, ensure_ascii=False), encoding="utf-8")

    repo = InMemoryLiteratureRepository(data_path)

    with patch("builtins.open", mock_open()) as mock_file:
        item = repo.get_item_by_id("test-001")
        assert item is not None
        assert item.id == "test-001"
        mock_file.assert_not_called()
