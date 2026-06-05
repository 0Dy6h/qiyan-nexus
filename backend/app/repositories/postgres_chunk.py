"""PostgreSQL-backed chunk repository.

Uses psycopg (psycopg3) for async PostgreSQL access with pgvector support.
Requires QIYAN_STATE_BACKEND="postgresql" and QIYAN_POSTGRES_DSN env var.
"""

import json
import os
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.schemas.chunk import LiteratureChunk

# Environment variable for PostgreSQL connection string
_POSTGRES_DSN_ENV = "QIYAN_POSTGRES_DSN"
_DEFAULT_DSN = "postgresql://qiyan_dev:qiyan_dev_pass@localhost:5432/qiyan_nexus"


def _get_dsn() -> str:
    """Get PostgreSQL connection string from environment or use default."""
    return os.getenv(_POSTGRES_DSN_ENV, _DEFAULT_DSN)


def _row_to_chunk(row: dict[str, Any]) -> LiteratureChunk:
    """Convert a database row dict to a LiteratureChunk."""
    # Remove embedding field if present (not part of LiteratureChunk schema)
    row.pop("embedding", None)
    row.pop("created_at", None)
    return LiteratureChunk(**row)


class PostgresChunkRepository:
    """PostgreSQL-backed chunk repository using psycopg (psycopg3)."""

    def __init__(self) -> None:
        """Initialize repository with connection pool."""
        self._dsn = _get_dsn()
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

    def list_chunks(self) -> list[LiteratureChunk]:
        """List all chunks."""
        with self._get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("SELECT * FROM chunks ORDER BY literature_id, chunk_id")
                rows = cur.fetchall()
                return [_row_to_chunk(dict(row)) for row in rows]

    def list_chunks_by_literature_id(self, literature_id: str) -> list[LiteratureChunk]:
        """List all chunks for a specific literature item."""
        with self._get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT * FROM chunks WHERE literature_id = %s ORDER BY chunk_id",
                    (literature_id,),
                )
                rows = cur.fetchall()
                return [_row_to_chunk(dict(row)) for row in rows]

    def get_chunk_by_id(self, chunk_id: str) -> LiteratureChunk | None:
        """Get a single chunk by ID."""
        with self._get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("SELECT * FROM chunks WHERE chunk_id = %s", (chunk_id,))
                row = cur.fetchone()
                return _row_to_chunk(dict(row)) if row else None

    def upsert_uploaded_pdf_chunk(
        self,
        chunk_id: str,
        literature_id: str,
        pdf_upload_id: str,
        text: str,
        source_quote: str,
        evidence_tags: list[str],
        related_entity_ids: list[str] | None = None,
    ) -> LiteratureChunk:
        """Upsert a chunk from an uploaded PDF."""
        if related_entity_ids is None:
            related_entity_ids = []

        with self._get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    INSERT INTO chunks (
                        chunk_id, literature_id, section, text, source_quote,
                        evidence_tags, related_entity_ids, source_type, pdf_upload_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s)
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        text = EXCLUDED.text,
                        source_quote = EXCLUDED.source_quote,
                        evidence_tags = EXCLUDED.evidence_tags,
                        related_entity_ids = EXCLUDED.related_entity_ids
                    RETURNING *
                    """,
                    (
                        chunk_id,
                        literature_id,
                        "full_text",  # section
                        text,
                        source_quote,
                        json.dumps(evidence_tags),
                        json.dumps(related_entity_ids),
                        "uploaded_pdf",
                        pdf_upload_id,
                    ),
                )
                row = cur.fetchone()
                conn.commit()
                return _row_to_chunk(dict(row))
