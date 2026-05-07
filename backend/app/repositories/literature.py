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
