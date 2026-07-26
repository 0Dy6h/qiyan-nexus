"""PostgreSQL-backed network task repository for the opt-in storage spike."""

import json
import os
from collections.abc import Callable
from typing import Any

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool
from pydantic import TypeAdapter

from app.repositories.postgres_common import create_postgres_pool, ensure_postgres_schema
from app.schemas.network import (
    AnalysisType,
    DataMode,
    NetworkAnalysisResult,
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

_POSTGRES_DSN_ENV = "QIYAN_POSTGRES_DSN"
_DEFAULT_DSN = "postgresql://qiyan_dev:qiyan_dev_pass@localhost:5432/qiyan_nexus"


def _get_dsn() -> str:
    return os.getenv(_POSTGRES_DSN_ENV, _DEFAULT_DSN)


def _row_to_record(row: dict[str, Any]) -> NetworkTaskRecord:
    row.pop("created_at_order", None)
    if row.get("created_at") is not None and not isinstance(row["created_at"], str):
        row["created_at"] = row["created_at"].isoformat()
    if row.get("result") is not None:
        if isinstance(row["result"], str):
            row["result"] = json.loads(row["result"])
        row["result"] = NetworkAnalysisResult.model_validate(row["result"])
    if row.get("research_protocol") is not None:
        if isinstance(row["research_protocol"], str):
            row["research_protocol"] = json.loads(row["research_protocol"])
        row["research_protocol"] = NetworkResearchProtocol.model_validate(row["research_protocol"])
    if row.get("disease_target_import") is not None:
        if isinstance(row["disease_target_import"], str):
            row["disease_target_import"] = json.loads(row["disease_target_import"])
        row["disease_target_import"] = _DISEASE_TARGET_SNAPSHOT_ADAPTER.validate_python(
            row["disease_target_import"]
        )
    if row.get("compound_target_import") is not None:
        if isinstance(row["compound_target_import"], str):
            row["compound_target_import"] = json.loads(row["compound_target_import"])
        row["compound_target_import"] = _COMPOUND_TARGET_SNAPSHOT_ADAPTER.validate_python(
            row["compound_target_import"]
        )
    if row.get("warnings") is None:
        row["warnings"] = []
    elif isinstance(row["warnings"], str):
        row["warnings"] = json.loads(row["warnings"])
    if row.get("adjudications") is None:
        row.pop("adjudications", None)
    else:
        if isinstance(row["adjudications"], str):
            row["adjudications"] = json.loads(row["adjudications"])
        row["adjudications"] = _ADJUDICATION_LIST_ADAPTER.validate_python(row["adjudications"])
    return NetworkTaskRecord.model_validate(row)


class PostgresNetworkTaskRepository:
    """Network task repository backed by PostgreSQL JSONB state."""

    def __init__(self, dsn: str | None = None) -> None:
        self._dsn = dsn or _get_dsn()
        self._pool: ConnectionPool[Any] | None = None

    def _get_pool(self) -> ConnectionPool[Any]:
        if self._pool is None:
            self._pool = create_postgres_pool(self._dsn)
            ensure_postgres_schema(self._pool)
        return self._pool

    def close(self) -> None:
        if self._pool is not None:
            self._pool.close()
            self._pool = None

    def read_all(self) -> list[NetworkTaskRecord]:
        with self._get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("SELECT * FROM network_tasks ORDER BY created_at, task_id")
                rows = cur.fetchall()
                return [_row_to_record(dict(row)) for row in rows]

    def create(self, record: NetworkTaskRecord) -> bool:
        with self._get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    INSERT INTO network_tasks (
                        task_id, source_task_id, owner_id, query, analysis_type, status, progress,
                        poll_count, research_protocol, disease_target_import,
                        compound_target_import, data_mode, result, error, warnings, adjudications,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (task_id) DO NOTHING
                    RETURNING task_id
                    """,
                    (
                        record.task_id,
                        record.source_task_id,
                        record.owner_id,
                        record.query,
                        record.analysis_type,
                        record.status,
                        record.progress,
                        record.poll_count,
                        Jsonb(record.research_protocol.model_dump(mode="json"))
                        if record.research_protocol is not None
                        else None,
                        Jsonb(record.disease_target_import.model_dump(mode="json"))
                        if record.disease_target_import is not None
                        else None,
                        Jsonb(record.compound_target_import.model_dump(mode="json"))
                        if record.compound_target_import is not None
                        else None,
                        record.data_mode,
                        Jsonb(record.result.model_dump(mode="json"))
                        if record.result is not None
                        else None,
                        record.error,
                        Jsonb(record.warnings),
                        Jsonb(
                            [
                                adjudication.model_dump(mode="json")
                                for adjudication in record.adjudications
                            ]
                        ),
                        record.created_at,
                    ),
                )
                inserted = cur.fetchone() is not None
                conn.commit()
                return inserted

    def get(self, task_id: str) -> NetworkTaskRecord | None:
        with self._get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("SELECT * FROM network_tasks WHERE task_id = %s", (task_id,))
                row = cur.fetchone()
                return _row_to_record(dict(row)) if row else None

    def get_owned(self, task_id: str, owner_id: str) -> NetworkTaskRecord | None:
        with self._get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT * FROM network_tasks WHERE task_id = %s AND owner_id = %s",
                    (task_id, owner_id),
                )
                row = cur.fetchone()
                return _row_to_record(dict(row)) if row else None

    def list_records_for_owner(self, owner_id: str) -> list[NetworkTaskRecord]:
        with self._get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT * FROM network_tasks
                    WHERE owner_id = %s
                    ORDER BY created_at DESC, task_id DESC
                    """,
                    (owner_id,),
                )
                rows = cur.fetchall()
                return [_row_to_record(dict(row)) for row in rows]

    def advance(
        self,
        task_id: str,
        owner_id: str,
        transition: Callable[[NetworkTaskRecord], NetworkTaskRecord],
    ) -> NetworkTaskRecord | None:
        with self._get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT * FROM network_tasks WHERE task_id = %s AND owner_id = %s FOR UPDATE",
                    (task_id, owner_id),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                next_record = transition(_row_to_record(dict(row)))
                result_json = (
                    Jsonb(next_record.result.model_dump(mode="json"))
                    if next_record.result is not None
                    else None
                )
                cur.execute(
                    """
                    UPDATE network_tasks
                    SET query = %s,
                        analysis_type = %s,
                        status = %s,
                        progress = %s,
                        poll_count = %s,
                        data_mode = %s,
                        result = %s,
                        error = %s,
                        warnings = %s,
                        created_at = %s
                    WHERE task_id = %s AND owner_id = %s
                    RETURNING *
                    """,
                    (
                        next_record.query,
                        next_record.analysis_type,
                        next_record.status,
                        next_record.progress,
                        next_record.poll_count,
                        next_record.data_mode,
                        result_json,
                        next_record.error,
                        Jsonb(next_record.warnings),
                        next_record.created_at,
                        task_id,
                        owner_id,
                    ),
                )
                updated_row = cur.fetchone()
                conn.commit()
                return _row_to_record(dict(updated_row))

    def append_adjudication(
        self,
        task_id: str,
        owner_id: str,
        adjudication: NetworkTargetAdjudication,
    ) -> NetworkTaskRecord | None:
        with self._get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT * FROM network_tasks WHERE task_id = %s AND owner_id = %s FOR UPDATE",
                    (task_id, owner_id),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                record = _row_to_record(dict(row))
                adjudications = [*record.adjudications, adjudication]
                cur.execute(
                    """
                    UPDATE network_tasks
                    SET adjudications = %s
                    WHERE task_id = %s AND owner_id = %s
                    RETURNING *
                    """,
                    (
                        Jsonb([item.model_dump(mode="json") for item in adjudications]),
                        task_id,
                        owner_id,
                    ),
                )
                updated_row = cur.fetchone()
                conn.commit()
                return _row_to_record(dict(updated_row))

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
        result_json = Jsonb(result.model_dump(mode="json")) if result is not None else None
        research_protocol_json = (
            Jsonb(research_protocol.model_dump(mode="json"))
            if research_protocol is not None
            else None
        )
        disease_target_import_json = (
            Jsonb(disease_target_import.model_dump(mode="json"))
            if disease_target_import is not None
            else None
        )
        compound_target_import_json = (
            Jsonb(compound_target_import.model_dump(mode="json"))
            if compound_target_import is not None
            else None
        )
        warnings_json = Jsonb(warnings or [])
        with self._get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    INSERT INTO network_tasks (
                        task_id, source_task_id, owner_id, query, analysis_type, status, progress,
                        poll_count, research_protocol, disease_target_import,
                        compound_target_import, data_mode, result, error, warnings, adjudications,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (task_id) DO UPDATE SET
                        query = EXCLUDED.query,
                        analysis_type = EXCLUDED.analysis_type,
                        status = EXCLUDED.status,
                        progress = EXCLUDED.progress,
                        poll_count = EXCLUDED.poll_count,
                        data_mode = EXCLUDED.data_mode,
                        result = EXCLUDED.result,
                        error = EXCLUDED.error,
                        warnings = EXCLUDED.warnings,
                        created_at = EXCLUDED.created_at
                    RETURNING *
                    """,
                    (
                        task_id,
                        source_task_id,
                        owner_id,
                        query,
                        analysis_type,
                        status,
                        progress,
                        poll_count,
                        research_protocol_json,
                        disease_target_import_json,
                        compound_target_import_json,
                        data_mode,
                        result_json,
                        error,
                        warnings_json,
                        Jsonb([]),
                        created_at,
                    ),
                )
                row = cur.fetchone()
                conn.commit()
                return _row_to_record(dict(row))
