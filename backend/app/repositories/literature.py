import json
from pathlib import Path
from typing import Any

from app.schemas.literature import LiteratureItem, PdfParseResult


class InMemoryLiteratureRepository:
    def __init__(self, data_path: Path):
        self.data_path = data_path
        self._items: list[dict[str, Any]] = self._load()

    def _load(self) -> list[dict[str, Any]]:
        """Load items from JSON file into memory."""
        items: list[dict[str, Any]] = json.loads(self.data_path.read_text(encoding="utf-8"))
        return items

    def _save(self) -> None:
        """Persist in-memory items to JSON file."""
        self.data_path.write_text(
            json.dumps(self._items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def list_items(self) -> list[LiteratureItem]:
        return [LiteratureItem(**item) for item in self._items]

    def get_item_by_id(self, item_id: str) -> LiteratureItem | None:
        for item in self._items:
            if item["id"] == item_id:
                return LiteratureItem(**item)
        return None

    def update_pdf_metadata(
        self,
        literature_id: str,
        pdf_upload_id: str,
        pdf_file_name: str,
        pdf_parse_status: str,
    ) -> LiteratureItem | None:
        for item in self._items:
            if item["id"] == literature_id:
                item["pdf_upload_id"] = pdf_upload_id
                item["pdf_file_name"] = pdf_file_name
                item["pdf_parse_status"] = pdf_parse_status
                item["pdf_parse_message"] = None
                item["pdf_parse_started_at"] = None
                item["pdf_parse_finished_at"] = None
                item["pdf_parse_result"] = None
                item["last_parse_trigger"] = None
                item["parse_attempt_count"] = 0
                self._save()
                return LiteratureItem(**item)
        return None

    def update_pdf_parse_status(
        self,
        literature_id: str,
        pdf_parse_status: str,
        pdf_parse_message: str | None = None,
        pdf_parse_started_at: str | None = None,
        pdf_parse_finished_at: str | None = None,
        pdf_parse_result: PdfParseResult | None = None,
        last_parse_trigger: str | None = None,
    ) -> LiteratureItem | None:
        for item in self._items:
            if item["id"] == literature_id:
                if not item.get("pdf_upload_id") or not item.get("pdf_file_name"):
                    return None
                item["pdf_parse_status"] = pdf_parse_status
                item["pdf_parse_message"] = pdf_parse_message
                item["pdf_parse_started_at"] = pdf_parse_started_at
                item["pdf_parse_finished_at"] = pdf_parse_finished_at
                item["pdf_parse_result"] = (
                    pdf_parse_result.model_dump() if pdf_parse_result is not None else None
                )
                item["last_parse_trigger"] = last_parse_trigger
                item["parse_attempt_count"] = int(item.get("parse_attempt_count") or 0) + 1
                self._save()
                return LiteratureItem(**item)
        return None

    def bulk_upsert_pubmed_items(self, incoming_items: list[dict[str, Any]]) -> tuple[int, int]:
        """Insert new PubMed items and refresh existing ones in-place.

        PubMed-owned fields (title/abstract/authors/year/keywords/source/snippet/
        citation_url/doi/pubmed_id/language/source_type) are overwritten.
        PDF upload + parse fields are preserved on existing rows so user uploads
        are not clobbered by a sync.
        """
        index_by_id: dict[str, int] = {item["id"]: idx for idx, item in enumerate(self._items)}
        pubmed_fields = {
            "title",
            "abstract",
            "authors",
            "year",
            "keywords",
            "evidence_tags",
            "source",
            "snippet",
            "citation_url",
            "doi",
            "pubmed_id",
            "language",
            "source_type",
        }
        created = 0
        updated = 0
        for incoming in incoming_items:
            item_id = incoming["id"]
            if item_id in index_by_id:
                existing = self._items[index_by_id[item_id]]
                for field_name, value in incoming.items():
                    if field_name in pubmed_fields:
                        existing[field_name] = value
                updated += 1
            else:
                self._items.append(incoming)
                index_by_id[item_id] = len(self._items) - 1
                created += 1
        self._save()
        return created, updated

    def close(self) -> None:
        """No-op for protocol alignment with SQLite repository."""
        pass
