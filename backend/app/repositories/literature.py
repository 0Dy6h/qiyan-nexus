import json
from pathlib import Path

from app.schemas.literature import LiteratureItem


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
                self.data_path.write_text(json.dumps(raw_items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                return LiteratureItem(**item)
        return None

    def update_pdf_parse_status(self, literature_id: str, pdf_parse_status: str) -> LiteratureItem | None:
        raw_items = json.loads(self.data_path.read_text(encoding="utf-8"))
        for item in raw_items:
            if item["id"] == literature_id:
                if not item.get("pdf_upload_id") or not item.get("pdf_file_name"):
                    return None
                item["pdf_parse_status"] = pdf_parse_status
                self.data_path.write_text(json.dumps(raw_items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                return LiteratureItem(**item)
        return None
