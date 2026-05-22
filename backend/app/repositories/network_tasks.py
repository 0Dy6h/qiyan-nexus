import json
from pathlib import Path
from typing import Any

from app.schemas.network import (
    AnalysisType,
    NetworkAnalysisResult,
    NetworkTaskRecord,
    TaskStatus,
)


class NetworkTaskRepository:
    """JSON-backed task store for network analysis mock tasks.

    Mirrors the direct-Path-I/O style of InMemoryLiteratureRepository:
    every read parses the whole file; every mutation rewrites it.
    The file is a plain JSON list of NetworkTaskRecord dicts.
    """

    def __init__(self, data_path: Path):
        self.data_path = data_path

    def read_all(self) -> list[NetworkTaskRecord]:
        raw_items: list[dict[str, Any]] = json.loads(self.data_path.read_text(encoding="utf-8"))
        return [NetworkTaskRecord.model_validate(item) for item in raw_items]

    def get(self, task_id: str) -> NetworkTaskRecord | None:
        for record in self.read_all():
            if record.task_id == task_id:
                return record
        return None

    def upsert(
        self,
        task_id: str,
        query: str,
        analysis_type: AnalysisType,
        status: TaskStatus,
        progress: int,
        poll_count: int,
        result: NetworkAnalysisResult | None,
        created_at: str,
    ) -> NetworkTaskRecord:
        raw_items: list[dict[str, Any]] = json.loads(self.data_path.read_text(encoding="utf-8"))
        record = NetworkTaskRecord(
            task_id=task_id,
            query=query,
            analysis_type=analysis_type,
            status=status,
            progress=progress,
            poll_count=poll_count,
            result=result,
            created_at=created_at,
        )
        payload = record.model_dump()
        for index, existing in enumerate(raw_items):
            if existing.get("task_id") == task_id:
                raw_items[index] = payload
                break
        else:
            raw_items.append(payload)
        self.data_path.write_text(
            json.dumps(raw_items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return record
