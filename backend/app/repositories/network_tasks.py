import json
from collections.abc import Callable
from pathlib import Path
from threading import RLock
from typing import Any

from app.schemas.network import (
    AnalysisType,
    DataMode,
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
        self._lock = RLock()

    def read_all(self) -> list[NetworkTaskRecord]:
        with self._lock:
            raw_items: list[dict[str, Any]] = json.loads(self.data_path.read_text(encoding="utf-8"))
            return [NetworkTaskRecord.model_validate(item) for item in raw_items]

    def get(self, task_id: str) -> NetworkTaskRecord | None:
        with self._lock:
            for record in self.read_all():
                if record.task_id == task_id:
                    return record
            return None

    def get_owned(self, task_id: str, owner_id: str) -> NetworkTaskRecord | None:
        with self._lock:
            record = self.get(task_id)
            if record is None or record.owner_id != owner_id:
                return None
            return record

    def advance(
        self,
        task_id: str,
        owner_id: str,
        transition: Callable[[NetworkTaskRecord], NetworkTaskRecord],
    ) -> NetworkTaskRecord | None:
        with self._lock:
            record = self.get(task_id)
            if record is None or record.owner_id != owner_id:
                return None
            next_record = transition(record)
            return self.upsert(
                task_id=next_record.task_id,
                owner_id=owner_id,
                query=next_record.query,
                analysis_type=next_record.analysis_type,
                status=next_record.status,
                progress=next_record.progress,
                poll_count=next_record.poll_count,
                result=next_record.result,
                created_at=next_record.created_at,
                data_mode=next_record.data_mode,
                error=next_record.error,
                warnings=next_record.warnings,
            )

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
        owner_id: str = "local-preview",
        data_mode: DataMode = "mock",
        error: str | None = None,
        warnings: list[str] | None = None,
    ) -> NetworkTaskRecord:
        with self._lock:
            raw_items: list[dict[str, Any]] = json.loads(self.data_path.read_text(encoding="utf-8"))
            existing_index: int | None = None
            persisted_owner_id: str | None = owner_id
            for index, existing in enumerate(raw_items):
                if existing.get("task_id") == task_id:
                    existing_index = index
                    persisted_owner_id = existing.get("owner_id")
                    break
            record = NetworkTaskRecord(
                task_id=task_id,
                owner_id=persisted_owner_id,
                query=query,
                analysis_type=analysis_type,
                status=status,
                progress=progress,
                poll_count=poll_count,
                data_mode=data_mode,
                result=result,
                error=error,
                warnings=warnings or [],
                created_at=created_at,
            )
            payload = record.model_dump()
            if existing_index is None:
                raw_items.append(payload)
            else:
                raw_items[existing_index] = payload
            self.data_path.write_text(
                json.dumps(raw_items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            return record
