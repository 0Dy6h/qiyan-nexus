"""PostgreSQL-backed literature repository.

Uses psycopg (psycopg3) for async PostgreSQL access with connection pooling.
Requires QIYAN_STATE_BACKEND="postgresql" and QIYAN_POSTGRES_DSN env var.
"""

import json
import os
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.schemas.literature import LiteratureItem, PdfParseResult

# Environment variable for PostgreSQL connection string
_POSTGRES_DSN_ENV = "QIYAN_POSTGRES_DSN"
_DEFAULT_DSN = "postgresql://qiyan_dev:qiyan_dev_pass@localhost:5432/qiyan_nexus"

# PubMed-owned fields that bulk_upsert overwrites on existing rows
_PUBMED_FIELDS = frozenset(
    {
        "title",
        "abstract",
        "authors",
        "year",
        "keywords",
        "source",
        "snippet",
        "citation_url",
        "doi",
        "pubmed_id",
        "language",
        "source_type",
        "evidence_tags",
    }
)


def _get_dsn() -> str:
    """Get PostgreSQL connection string from environment or use default."""
    return os.getenv(_POSTGRES_DSN_ENV, _DEFAULT_DSN)


def _row_to_item(row: dict[str, Any]) -> LiteratureItem:
    """Convert a database row dict to a LiteratureItem."""
    # Convert timestamp strings to ISO format if needed
    for ts_field in ["pdf_parse_started_at", "pdf_parse_finished_at"]:
        if row.get(ts_field) is not None and not isinstance(row[ts_field], str):
            row[ts_field] = row[ts_field].isoformat()

    # Parse pdf_parse_result from JSONB
    if row.get("pdf_parse_result") is not None:
        row["pdf_parse_result"] = PdfParseResult(**row["pdf_parse_result"])

    return LiteratureItem(**row)


class PostgresLiteratureRepository:
    """PostgreSQL-backed literature repository using psycopg (psycopg3)."""

    def __init__(self) -> None:
        """Initialize repository with connection pool."""
        self._dsn = _get_dsn()
        # Connection pool will be created on first use (lazy init)
        self._pool: psycopg.ConnectionPool | None = None

    def _get_pool(self) -> psycopg.ConnectionPool:
        """Get or create connection pool."""
        if self._pool is None:
            self._pool = psycopg.ConnectionPool(
                self._dsn,
                min_size=2,
                max_size=10,
                open=True,
            )
        return self._pool

    def list_items(self) -> list[LiteratureItem]:
        """List all literature items."""
        with self._get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("SELECT * FROM literature ORDER BY year DESC, id")
                rows = cur.fetchall()
                return [_row_to_item(dict(row)) for row in rows]

    def get_item_by_id(self, item_id: str) -> LiteratureItem | None:
        """Get a single literature item by ID."""
        with self._get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("SELECT * FROM literature WHERE id = %s", (item_id,))
                row = cur.fetchone()
                return _row_to_item(dict(row)) if row else None

    def update_pdf_metadata(
        self,
        literature_id: str,
        pdf_upload_id: str,
        pdf_file_name: str,
        pdf_parse_status: str,
    ) -> LiteratureItem | None:
        """Update PDF metadata for a literature item."""
        with self._get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    UPDATE literature
                    SET pdf_upload_id = %s,
                        pdf_file_name = %s,
                        pdf_parse_status = %s
                    WHERE id = %s
                    RETURNING *
                    """,
                    (pdf_upload_id, pdf_file_name, pdf_parse_status, literature_id),
                )
                row = cur.fetchone()
                conn.commit()
                return _row_to_item(dict(row)) if row else None

    def update_pdf_parse_status(
        self,
        literature_id: str,
        pdf_parse_status: str,
        pdf_parse_message: str | None = None,
        pdf_parse_started_at: str | None = None,
        pdf_parse_finished_at: str | None = None,
        pdf_parse_result: PdfParseResult | None = None,
        last_parse_trigger: str | None = None,
    ) -> LiteratureItem | None:
        """Update PDF parse status and related fields."""
        with self._get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                # Prepare JSONB for pdf_parse_result
                result_json = (
                    json.dumps(pdf_parse_result.model_dump()) if pdf_parse_result else None
                )

                # Increment parse_attempt_count
                cur.execute(
                    """
                    UPDATE literature
                    SET pdf_parse_status = %s,
                        pdf_parse_message = %s,
                        pdf_parse_started_at = %s,
                        pdf_parse_finished_at = %s,
                        pdf_parse_result = %s::jsonb,
                        last_parse_trigger = %s,
                        parse_attempt_count = COALESCE(parse_attempt_count, 0) + 1
                    WHERE id = %s
                    RETURNING *
                    """,
                    (
                        pdf_parse_status,
                        pdf_parse_message,
                        pdf_parse_started_at,
                        pdf_parse_finished_at,
                        result_json,
                        last_parse_trigger,
                        literature_id,
                    ),
                )
                row = cur.fetchone()
                conn.commit()
                return _row_to_item(dict(row)) if row else None

    def bulk_upsert_pubmed_items(self, incoming_items: list[dict[str, Any]]) -> tuple[int, int]:
        """Bulk upsert PubMed literature items.

        Returns (created_count, updated_count).
        """
        if not incoming_items:
            return (0, 0)

        created = 0
        updated = 0

        with self._get_pool().connection() as conn:
            with conn.cursor() as cur:
                for item in incoming_items:
                    # Check if exists
                    cur.execute("SELECT id FROM literature WHERE id = %s", (item["id"],))
                    exists = cur.fetchone() is not None

                    if exists:
                        # Update only PubMed-owned fields
                        set_clause = ", ".join(f"{k} = %s" for k in _PUBMED_FIELDS)
                        values = [
                            json.dumps(item[k]) if k in {"authors", "keywords", "evidence_tags"} else item[k]
                            for k in _PUBMED_FIELDS
                        ]
                        values.append(item["id"])
                        cur.execute(
                            f"UPDATE literature SET {set_clause} WHERE id = %s",
                            values,
                        )
                        updated += 1
                    else:
                        # Insert new item
                        columns = list(item.keys())
                        placeholders = ", ".join(["%s"] * len(columns))
                        values = [
                            json.dumps(item[k]) if k in {"authors", "keywords", "evidence_tags", "related_entity_ids"} else item[k]
                            for k in columns
                        ]
                        cur.execute(
                            f"INSERT INTO literature ({', '.join(columns)}) VALUES ({placeholders})",
                            values,
                        )
                        created += 1

                conn.commit()

        return (created, updated)

