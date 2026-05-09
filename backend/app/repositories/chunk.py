import json
from pathlib import Path

from app.schemas.chunk import LiteratureChunk


class InMemoryChunkRepository:
    def __init__(self, data_path: Path):
        self.data_path = data_path

    def list_chunks(self) -> list[LiteratureChunk]:
        raw_items = json.loads(self.data_path.read_text(encoding="utf-8"))
        return [LiteratureChunk(**item) for item in raw_items]

    def list_chunks_by_literature_id(self, literature_id: str) -> list[LiteratureChunk]:
        return [chunk for chunk in self.list_chunks() if chunk.literature_id == literature_id]

    def get_chunk_by_id(self, chunk_id: str) -> LiteratureChunk | None:
        for chunk in self.list_chunks():
            if chunk.chunk_id == chunk_id:
                return chunk
        return None
