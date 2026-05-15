import json
from pathlib import Path

from app.schemas.literature import LiteratureItem, PdfParseResult


class InMemoryLiteratureRepository:
    def __init__(self, data_path: Path):
        self.data_path = data_path

    def list_items(self) -> list[LiteratureItem]:
        raw_items = json.loads(self.data_path.read_text(encoding="utf-8"))
        return [LiteratureItem(**item) for item in raw_items]

    def get_item_by_id(self, item_id: str) -> LiteratureItem | None:
        for item in self.list_items():
            if item.id == item_id:
                return item
        return None

    def update_pdf_metadata(
        self,
        literature_id: str,
        pdf_upload_id: str,
        pdf_file_name: str,
        pdf_parse_status: str,
    ) -> LiteratureItem | None:
        raw_items = json.loads(self.data_path.read_text(encoding="utf-8"))
        for item in raw_items:
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
                self.data_path.write_text(json.dumps(raw_items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
        raw_items = json.loads(self.data_path.read_text(encoding="utf-8"))
        for item in raw_items:
            if item["id"] == literature_id:
                if not item.get("pdf_upload_id") or not item.get("pdf_file_name"):
                    return None
                item["pdf_parse_status"] = pdf_parse_status
                item["pdf_parse_message"] = pdf_parse_message
                item["pdf_parse_started_at"] = pdf_parse_started_at
                item["pdf_parse_finished_at"] = pdf_parse_finished_at
                item["pdf_parse_result"] = pdf_parse_result.dict() if pdf_parse_result is not None else None
                item["last_parse_trigger"] = last_parse_trigger
                item["parse_attempt_count"] = int(item.get("parse_attempt_count") or 0) + 1
                self.data_path.write_text(json.dumps(raw_items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                return LiteratureItem(**item)
        return None
