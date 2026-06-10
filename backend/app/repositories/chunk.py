import json
from pathlib import Path
from typing import Any

from app.schemas.chunk import LiteratureChunk


class InMemoryChunkRepository:
    def __init__(self, data_path: Path):
        self.data_path = data_path
        self._items: list[dict[str, Any]] = self._load()

    def _load(self) -> list[dict[str, Any]]:
        """Load chunks from JSON file into memory."""
        items: list[dict[str, Any]] = json.loads(self.data_path.read_text(encoding="utf-8"))
        return items

    def _save(self) -> None:
        """Persist in-memory chunks to JSON file."""
        self.data_path.write_text(
            json.dumps(self._items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def list_chunks(self) -> list[LiteratureChunk]:
        return [LiteratureChunk(**item) for item in self._items]

    def list_chunks_by_literature_id(self, literature_id: str) -> list[LiteratureChunk]:
        return [
            LiteratureChunk(**item)
            for item in self._items
            if item["literature_id"] == literature_id
        ]

    def group_chunks_by_literature(
        self, literature_ids: list[str]
    ) -> dict[str, list[LiteratureChunk]]:
        """Group chunks by literature_id in a single pass. O(M) instead of O(N×M)."""
        from collections import defaultdict

        result: dict[str, list[LiteratureChunk]] = defaultdict(list)
        id_set = set(literature_ids)
        for item in self._items:
            lit_id = item.get("literature_id")
            if lit_id in id_set:
                result[lit_id].append(LiteratureChunk(**item))
        return dict(result)

    def get_chunk_by_id(self, chunk_id: str) -> LiteratureChunk | None:
        for item in self._items:
            if item["chunk_id"] == chunk_id:
                return LiteratureChunk(**item)
        return None

    def upsert_uploaded_pdf_chunk(
        self,
        chunk_id: str,
        literature_id: str,
        pdf_upload_id: str,
        text: str,
        source_quote: str,
        evidence_tags: list[str],
        related_entity_ids: list[str] | None = None,
    ) -> LiteratureChunk:
        next_item: dict[str, Any] = {
            "chunk_id": chunk_id,
            "literature_id": literature_id,
            "section": "uploaded_pdf",
            "text": text,
            "source_quote": source_quote,
            "evidence_tags": evidence_tags,
            "related_entity_ids": related_entity_ids or ["disease:atopic-dermatitis"],
            "source_type": "uploaded_pdf",
            "pdf_upload_id": pdf_upload_id,
        }

        for index, item in enumerate(self._items):
            if item.get("chunk_id") == chunk_id:
                self._items[index] = next_item
                self._save()
                return LiteratureChunk(**next_item)

        self._items.append(next_item)
        self._save()
        return LiteratureChunk(**next_item)

    def close(self) -> None:
        """No-op for protocol alignment with SQLite repository."""
        pass
