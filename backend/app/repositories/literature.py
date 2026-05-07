import json
from pathlib import Path

from app.schemas.literature import LiteratureItem


class InMemoryLiteratureRepository:
    def __init__(self, data_path: Path):
        self.data_path = data_path

    def list_items(self) -> list[LiteratureItem]:
        raw_items = json.loads(self.data_path.read_text(encoding="utf-8"))
        return [LiteratureItem(**item) for item in raw_items]
