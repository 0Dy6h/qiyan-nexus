"""SQLite-backed network task repository.

Uses only the Python standard library ``sqlite3`` module — zero new
dependencies.  The database file is shared with other repositories
(literature, chunk) via ``resolve_sqlite_db_path()``; each repository
creates its own table with ``CREATE TABLE IF NOT EXISTS``.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.schemas.network import (
    AnalysisType,
    NetworkAnalysisResult,
    NetworkTaskRecord,
    TaskStatus,
)

_CREATE_TABLE_SQL = """\
CREATE TABLE IF NOT EXISTS network_task (
    task_id        TEXT PRIMARY KEY,
    query          TEXT NOT NULL,
    analysis_type  TEXT NOT NULL,
    status         TEXT NOT NULL,
    progress       INTEGER NOT NULL,
    poll_count     INTEGER NOT NULL,
    result         TEXT,
    created_at     TEXT NOT NULL
)
"""


def _row_to_record(row: sqlite3.Row) -> NetworkTaskRecord:
    """Convert a database row to a ``NetworkTaskRecord``."""
    data: dict[str, Any] = dict(row)
    # result is stored as JSON TEXT; None stays None
    if data.get("result") is not None:
        data["result"] = NetworkAnalysisResult.model_validate(json.loads(data["result"]))
    return NetworkTaskRecord.model_validate(data)


class SqliteNetworkTaskRepository:
    """Network task repository backed by a local SQLite database."""

    def __init__(self, db_path: Path, seed_path: Path | None = None) -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._closed = False
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(_CREATE_TABLE_SQL)
        self._conn.commit()

        # Bootstrap from seed JSON if the table is empty.
        # Network tasks are mutation-only — seed is typically an empty list.
        count = self._conn.execute("SELECT COUNT(*) FROM network_task").fetchone()[0]
        if count == 0:
            self._bootstrap_from_seed(seed_path)

    # ------------------------------------------------------------------
    # Bootstrap
    # ------------------------------------------------------------------

    def _bootstrap_from_seed(self, seed_path: Path | None = None) -> None:
        """Load seed data from the standard network tasks JSON file.

        If *seed_path* is provided, use it directly; otherwise fall back to
        ``resolve_network_tasks_storage_path()``.
        """
        if seed_path is None:
            from app.repositories.runtime_storage import resolve_network_tasks_storage_path

            seed_path = resolve_network_tasks_storage_path()

        raw_items: list[dict[str, Any]] = json.loads(seed_path.read_text(encoding="utf-8"))
        for item in raw_items:
            self._insert_item(item)
        self._conn.commit()

    def _insert_item(self, item: dict[str, Any]) -> None:
        """Insert a single item dict into the database."""
        result_val = item.get("result")
        if result_val is not None:
            if isinstance(result_val, NetworkAnalysisResult):
                result_val = result_val.model_dump()
            item["result"] = json.dumps(result_val, ensure_ascii=False)

        columns = [
            "task_id",
            "query",
            "analysis_type",
            "status",
            "progress",
            "poll_count",
            "result",
            "created_at",
        ]
        values = [item.get(c) for c in columns]
        placeholders = ", ".join("?" for _ in columns)
        col_names = ", ".join(columns)
        self._conn.execute(
            f"INSERT INTO network_task ({col_names}) VALUES ({placeholders})",
            values,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying SQLite connection. Safe to call repeatedly."""
        if not self._closed:
            self._conn.close()
            self._closed = True

    def __del__(self) -> None:
        self.close()

    def read_all(self) -> list[NetworkTaskRecord]:
        rows = self._conn.execute("SELECT * FROM network_task").fetchall()
        return [_row_to_record(row) for row in rows]

    def get(self, task_id: str) -> NetworkTaskRecord | None:
        row = self._conn.execute(
            "SELECT * FROM network_task WHERE task_id = ?",
            (task_id,),
        ).fetchone()
        return _row_to_record(row) if row else None

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
        result_json: str | None = None
        if result is not None:
            result_json = json.dumps(result.model_dump(), ensure_ascii=False)

        existing = self._conn.execute(
            "SELECT task_id FROM network_task WHERE task_id = ?",
            (task_id,),
        ).fetchone()

        if existing is not None:
            self._conn.execute(
                """UPDATE network_task
                   SET query = ?,
                       analysis_type = ?,
                       status = ?,
                       progress = ?,
                       poll_count = ?,
                       result = ?,
                       created_at = ?
                   WHERE task_id = ?""",
                (
                    query,
                    analysis_type,
                    status,
                    progress,
                    poll_count,
                    result_json,
                    created_at,
                    task_id,
                ),
            )
        else:
            self._conn.execute(
                """INSERT INTO network_task
                   (task_id, query, analysis_type, status, progress, poll_count, result, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    task_id,
                    query,
                    analysis_type,
                    status,
                    progress,
                    poll_count,
                    result_json,
                    created_at,
                ),
            )
        self._conn.commit()

        row = self._conn.execute(
            "SELECT * FROM network_task WHERE task_id = ?",
            (task_id,),
        ).fetchone()
        return _row_to_record(row)
