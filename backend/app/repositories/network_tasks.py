import json
from collections.abc import Callable
from pathlib import Path
from threading import RLock
from typing import Any

from pydantic import TypeAdapter

from app.schemas.network import (
    AnalysisType,
    DataMode,
    NetworkAnalysisResult,
    NetworkAssemblyPlan,
    NetworkCompoundTargetSnapshot,
    NetworkDiseaseTargetSnapshot,
    NetworkResearchProtocol,
    NetworkTargetAdjudication,
    NetworkTaskRecord,
    TaskStatus,
)

_DISEASE_TARGET_SNAPSHOT_ADAPTER: TypeAdapter[NetworkDiseaseTargetSnapshot] = TypeAdapter(
    NetworkDiseaseTargetSnapshot
)
_COMPOUND_TARGET_SNAPSHOT_ADAPTER: TypeAdapter[NetworkCompoundTargetSnapshot] = TypeAdapter(
    NetworkCompoundTargetSnapshot
)
_ADJUDICATION_LIST_ADAPTER: TypeAdapter[list[NetworkTargetAdjudication]] = TypeAdapter(
    list[NetworkTargetAdjudication]
)


class NetworkTaskRepository:
    """JSON-backed task store for network analysis mock tasks.

    Mirrors the direct-Path-I/O style of InMemoryLiteratureRepository:
    every read parses the whole file; every mutation rewrites it.
    The file is a plain JSON list of NetworkTaskRecord dicts.
    """

    def __init__(self, data_path: Path):
        self.data_path = data_path
        self._assembly_plan_path = data_path.with_name(f"{data_path.stem}.assembly-plans.json")
        self._lock = RLock()

    def _read_assembly_plans(self) -> list[NetworkAssemblyPlan]:
        if not self._assembly_plan_path.exists():
            return []
        payload = json.loads(self._assembly_plan_path.read_text(encoding="utf-8"))
        return [NetworkAssemblyPlan.model_validate(item) for item in payload]

    def _write_assembly_plans(self, plans: list[NetworkAssemblyPlan]) -> None:
        self._assembly_plan_path.write_text(
            json.dumps(
                [plan.model_dump(mode="json") for plan in plans],
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def read_all(self) -> list[NetworkTaskRecord]:
        with self._lock:
            raw_items: list[dict[str, Any]] = json.loads(self.data_path.read_text(encoding="utf-8"))
            return [NetworkTaskRecord.model_validate(item) for item in raw_items]

    def create(self, record: NetworkTaskRecord) -> bool:
        with self._lock:
            raw_items: list[dict[str, Any]] = json.loads(self.data_path.read_text(encoding="utf-8"))
            if any(item.get("task_id") == record.task_id for item in raw_items):
                return False
            raw_items.append(record.model_dump(mode="json"))
            self.data_path.write_text(
                json.dumps(raw_items, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            return True

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

    def list_records_for_owner(self, owner_id: str) -> list[NetworkTaskRecord]:
        with self._lock:
            records = [record for record in self.read_all() if record.owner_id == owner_id]
            records.sort(key=lambda record: (record.created_at, record.task_id), reverse=True)
            return records

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
                research_protocol=next_record.research_protocol,
                disease_target_import=next_record.disease_target_import,
                compound_target_import=next_record.compound_target_import,
                source_task_id=next_record.source_task_id,
                status=next_record.status,
                progress=next_record.progress,
                poll_count=next_record.poll_count,
                result=next_record.result,
                created_at=next_record.created_at,
                data_mode=next_record.data_mode,
                error=next_record.error,
                warnings=next_record.warnings,
            )

    def append_adjudication(
        self,
        task_id: str,
        owner_id: str,
        adjudication: NetworkTargetAdjudication,
    ) -> NetworkTaskRecord | None:
        with self._lock:
            raw_items: list[dict[str, Any]] = json.loads(self.data_path.read_text(encoding="utf-8"))
            for index, existing in enumerate(raw_items):
                if existing.get("task_id") != task_id:
                    continue
                record = NetworkTaskRecord.model_validate(existing)
                if record.owner_id != owner_id:
                    return None
                next_record = record.model_copy(
                    update={"adjudications": [*record.adjudications, adjudication]}
                )
                raw_items[index] = next_record.model_dump(mode="json")
                self.data_path.write_text(
                    json.dumps(raw_items, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                return next_record
            return None

    def list_assembly_plans(self, task_id: str, owner_id: str) -> list[NetworkAssemblyPlan]:
        with self._lock:
            record = self.get_owned(task_id, owner_id)
            if record is None:
                return []
            return [plan for plan in self._read_assembly_plans() if plan.task_id == task_id]

    def get_assembly_plan(
        self, task_id: str, owner_id: str, plan_id: str
    ) -> NetworkAssemblyPlan | None:
        return next(
            (
                plan
                for plan in self.list_assembly_plans(task_id, owner_id)
                if plan.plan_id == plan_id
            ),
            None,
        )

    def seal_assembly_plan(
        self,
        task_id: str,
        owner_id: str,
        expected_adjudication_ids: tuple[str, ...],
        plan: NetworkAssemblyPlan,
    ) -> tuple[str, NetworkAssemblyPlan | None]:
        with self._lock:
            record = self.get_owned(task_id, owner_id)
            if record is None:
                return "not_found", None
            if (
                tuple(item.adjudication_id for item in record.adjudications)
                != expected_adjudication_ids
            ):
                return "conflict", None
            plans = self._read_assembly_plans()
            existing = next(
                (
                    item
                    for item in plans
                    if item.task_id == task_id
                    and item.canonical_plan_input_sha256 == plan.canonical_plan_input_sha256
                ),
                None,
            )
            if existing is not None:
                return "existing", existing
            task_plans = [item for item in plans if item.task_id == task_id]
            persisted = plan.model_copy(update={"plan_sequence": len(task_plans) + 1})
            plans.append(persisted)
            self._write_assembly_plans(plans)
            return "created", persisted

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
        research_protocol: NetworkResearchProtocol | None = None,
        disease_target_import: NetworkDiseaseTargetSnapshot | None = None,
        compound_target_import: NetworkCompoundTargetSnapshot | None = None,
        source_task_id: str | None = None,
        owner_id: str = "local-preview",
        data_mode: DataMode = "mock",
        error: str | None = None,
        warnings: list[str] | None = None,
    ) -> NetworkTaskRecord:
        with self._lock:
            raw_items: list[dict[str, Any]] = json.loads(self.data_path.read_text(encoding="utf-8"))
            existing_index: int | None = None
            persisted_owner_id: str | None = owner_id
            persisted_research_protocol = research_protocol
            persisted_disease_target_import = disease_target_import
            persisted_compound_target_import = compound_target_import
            persisted_source_task_id = source_task_id
            persisted_adjudications: list[NetworkTargetAdjudication] = []
            for index, existing in enumerate(raw_items):
                if existing.get("task_id") == task_id:
                    existing_index = index
                    persisted_owner_id = existing.get("owner_id")
                    existing_protocol = existing.get("research_protocol")
                    persisted_research_protocol = (
                        NetworkResearchProtocol.model_validate(existing_protocol)
                        if existing_protocol is not None
                        else None
                    )
                    existing_import = existing.get("disease_target_import")
                    persisted_disease_target_import = (
                        _DISEASE_TARGET_SNAPSHOT_ADAPTER.validate_python(existing_import)
                        if existing_import is not None
                        else None
                    )
                    existing_compound_import = existing.get("compound_target_import")
                    persisted_compound_target_import = (
                        _COMPOUND_TARGET_SNAPSHOT_ADAPTER.validate_python(existing_compound_import)
                        if existing_compound_import is not None
                        else None
                    )
                    persisted_source_task_id = existing.get("source_task_id")
                    existing_adjudications = existing.get("adjudications")
                    persisted_adjudications = (
                        _ADJUDICATION_LIST_ADAPTER.validate_python(existing_adjudications)
                        if existing_adjudications is not None
                        else []
                    )
                    break
            record = NetworkTaskRecord(
                task_id=task_id,
                source_task_id=persisted_source_task_id,
                owner_id=persisted_owner_id,
                query=query,
                analysis_type=analysis_type,
                research_protocol=persisted_research_protocol,
                disease_target_import=persisted_disease_target_import,
                compound_target_import=persisted_compound_target_import,
                status=status,
                progress=progress,
                poll_count=poll_count,
                data_mode=data_mode,
                result=result,
                error=error,
                warnings=warnings or [],
                adjudications=persisted_adjudications,
                created_at=created_at,
            )
            payload = record.model_dump(mode="json")
            if existing_index is None:
                raw_items.append(payload)
            else:
                raw_items[existing_index] = payload
            self.data_path.write_text(
                json.dumps(raw_items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            return record
