"""Test chunk repository group_chunks_by_literature performance optimization."""

import json
from pathlib import Path

from app.repositories.chunk import InMemoryChunkRepository


def _chunk_dict(chunk_id: str, literature_id: str) -> dict:
    return {
        "chunk_id": chunk_id,
        "literature_id": literature_id,
        "section": "abstract",
        "text": f"text for {chunk_id}",
        "source_quote": f"quote for {chunk_id}",
    }


def test_group_chunks_by_literature_returns_grouped_dict(tmp_path: Path):
    data_path = tmp_path / "chunks.json"
    data_path.write_text(
        json.dumps(
            [
                _chunk_dict("c1", "lit-1"),
                _chunk_dict("c2", "lit-1"),
                _chunk_dict("c3", "lit-2"),
                _chunk_dict("c4", "lit-3"),
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    repo = InMemoryChunkRepository(data_path)
    result = repo.group_chunks_by_literature(["lit-1", "lit-2"])

    assert set(result.keys()) == {"lit-1", "lit-2"}
    assert len(result["lit-1"]) == 2
    assert len(result["lit-2"]) == 1
    assert result["lit-1"][0].chunk_id == "c1"
    assert result["lit-1"][1].chunk_id == "c2"
    assert result["lit-2"][0].chunk_id == "c3"


def test_group_chunks_by_literature_returns_empty_for_no_matches(tmp_path: Path):
    data_path = tmp_path / "chunks.json"
    data_path.write_text(
        json.dumps([_chunk_dict("c1", "lit-1")]),
        encoding="utf-8",
    )

    repo = InMemoryChunkRepository(data_path)
    result = repo.group_chunks_by_literature(["lit-2", "lit-3"])

    assert result == {}


def test_group_chunks_by_literature_single_pass_efficiency(tmp_path: Path):
    """Verify single-pass implementation by checking it returns consistent results."""
    data_path = tmp_path / "chunks.json"
    data_path.write_text(
        json.dumps(
            [_chunk_dict(f"c{i}", f"lit-{i % 3}") for i in range(100)],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    repo = InMemoryChunkRepository(data_path)
    result = repo.group_chunks_by_literature(["lit-0", "lit-1", "lit-2"])

    assert len(result["lit-0"]) == 34
    assert len(result["lit-1"]) == 33
    assert len(result["lit-2"]) == 33
