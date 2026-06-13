"""PostgreSQL-backed network task repository using psycopg3."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import psycopg

from app.schemas.network import AnalysisType, NetworkAnalysisResult, NetworkTaskRecord, TaskStatus


class PostgresNetworkTaskRepository:
    """PostgreSQL implementation of NetworkTaskRepositoryProtocol.

    Uses synchronous psycopg3 with short-lived connections per method call.
    Connection pooling is deferred to future optimization.
    """

    def __init__(self, database_url: str):
        self.database_url = database_url

    def _connect(self) -> psycopg.Connection[tuple[Any, ...]]:
        """Open a new connection to the database."""
        return psycopg.connect(self.database_url)

    def close(self) -> None:
        """No-op for protocol compatibility. Connections are short-lived."""
        pass

    def read_all(self) -> list[NetworkTaskRecord]:
        """Return all network tasks."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM network_task ORDER BY created_at DESC")
                rows = cur.fetchall()
                return [self._row_to_task(row, cur.description) for row in rows]

    def get(self, task_id: str) -> NetworkTaskRecord | None:
        """Fetch a single task by ID."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM network_task WHERE task_id = %s", (task_id,))
                row = cur.fetchone()
                if not row:
                    return None
                return self._row_to_task(row, cur.description)

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
        """Insert or update a network task."""
        now = datetime.now(UTC).isoformat()

        # Build indication_keywords from query (simple split)
        indication_keywords = [kw.strip() for kw in query.split() if kw.strip()]

        with self._connect() as conn:
            with conn.cursor() as cur:
                # Check if task exists
                cur.execute("SELECT task_id FROM network_task WHERE task_id = %s", (task_id,))
                exists = cur.fetchone() is not None

                result_json = json.dumps(result.model_dump()) if result else None

                if exists:
                    # Update
                    cur.execute(
                        """
                        UPDATE network_task
                        SET indication_keywords = %s, status = %s,
                            error_message = %s, result = %s, updated_at = %s
                        WHERE task_id = %s
                        RETURNING *
                        """,
                        (
                            json.dumps(indication_keywords),
                            status,
                            None,  # error_message - not in current upsert signature
                            result_json,
                            now,
                            task_id,
                        ),
                    )
                else:
                    # Insert
                    cur.execute(
                        """
                        INSERT INTO network_task (
                            task_id, indication_keywords, tcm_indication,
                            status, error_message, result, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING *
                        """,
                        (
                            task_id,
                            json.dumps(indication_keywords),
                            None,  # tcm_indication - not in current upsert signature
                            status,
                            None,
                            result_json,
                            created_at,
                            now,
                        ),
                    )

                row = cur.fetchone()
                if not row:
                    raise RuntimeError("INSERT/UPDATE RETURNING failed")
                conn.commit()
                return self._row_to_task(row, cur.description)

    def _row_to_task(self, row: tuple[Any, ...], description: Any) -> NetworkTaskRecord:
        """Convert a database row to a NetworkTaskRecord."""
        col_names = [desc[0] for desc in description]
        data = dict(zip(col_names, row, strict=False))

        # Parse JSON fields
        data["indication_keywords"] = data.get("indication_keywords") or []

        # Parse result if present
        if data.get("result"):
            data["result"] = NetworkAnalysisResult.model_validate(data["result"])

        return NetworkTaskRecord.model_validate(data)
