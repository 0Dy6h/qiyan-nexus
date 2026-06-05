"""PostgreSQL-backed chunk repository for the opt-in storage spike."""

import json
import os
from pathlib import Path
from typing import Any

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from app.repositories.postgres_common import create_postgres_pool, ensure_postgres_schema
from app.schemas.chunk import LiteratureChunk

_POSTGRES_DSN_ENV = "QIYAN_POSTGRES_DSN"
_DEFAULT_DSN = "postgresql://qiyan_dev:qiyan_dev_pass@localhost:5432/qiyan_nexus"
_JSONB_COLUMNS = frozenset({"evidence_tags", "related_entity_ids"})
_CHUNK_COLUMNS = [
    "chunk_id",
    "literature_id",
    "section",
    "text",
    "source_quote",
    "evidence_tags",
    "related_entity_ids",
    "source_type",
    "pdf_upload_id",
]


def _get_dsn() -> str:
    """Get PostgreSQL connection string from environment or use default."""
    return os.getenv(_POSTGRES_DSN_ENV, _DEFAULT_DSN)


def _as_jsonb(value: Any, fallback: Any) -> Jsonb:
    if value is None:
        value = fallback
    if isinstance(value, str):
        value = json.loads(value)
    return Jsonb(value)


def _prepare_value(column: str, value: Any) -> Any:
    if column in _JSONB_COLUMNS:
        return _as_jsonb(value, [])
    return value


def _row_to_chunk(row: dict[str, Any]) -> LiteratureChunk:
    """Convert a database row dict to a LiteratureChunk."""
    row.pop("embedding", None)
    row.pop("created_at", None)
    return LiteratureChunk(**row)


class PostgresChunkRepository:
    """PostgreSQL-backed chunk repository using psycopg (psycopg3)."""

    def __init__(self, dsn: str | None = None, seed_path: Path | None = None) -> None:
        """Initialize repository with connection pool."""
        self._dsn = dsn or _get_dsn()
        self._seed_path = seed_path
        self._pool: ConnectionPool[Any] | None = None
        self._bootstrapped = False

    def _get_pool(self) -> ConnectionPool[Any]:
        """Get or create connection pool."""
        if self._pool is None:
            self._pool = create_postgres_pool(self._dsn)
            ensure_postgres_schema(self._pool)
        if not self._bootstrapped:
            self._bootstrap_from_seed_if_empty()
            self._bootstrapped = True
        return self._pool

    def _bootstrap_from_seed_if_empty(self) -> None:
        """Load chunk seed JSON into PostgreSQL when the table is empty."""
        if self._pool is None:
            return
        from app.repositories.postgres_literature import bootstrap_literature_seed_if_empty

        bootstrap_literature_seed_if_empty(self._pool, None)
        with self._pool.connection() as conn:
            count = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()
            if count is not None and count[0] > 0:
                return
            if self._seed_path is None:
                from app.repositories.runtime_storage import resolve_chunk_storage_path

                self._seed_path = resolve_chunk_storage_path()
            raw_items: list[dict[str, Any]] = json.loads(
                self._seed_path.read_text(encoding="utf-8")
            )
            columns = ", ".join(_CHUNK_COLUMNS)
            placeholders = ", ".join(["%s"] * len(_CHUNK_COLUMNS))
            with conn.cursor() as cur:
                for item in raw_items:
                    item.setdefault("source_type", "sample")
                    values = [_prepare_value(column, item.get(column)) for column in _CHUNK_COLUMNS]
                    cur.execute(
                        f"INSERT INTO chunks ({columns}) VALUES ({placeholders})",
                        values,
                    )
            conn.commit()

    def close(self) -> None:
        if self._pool is not None:
            self._pool.close()
            self._pool = None

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
            related_entity_ids = ["disease:atopic-dermatitis"]

        with self._get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    INSERT INTO chunks (
                        chunk_id, literature_id, section, text, source_quote,
                        evidence_tags, related_entity_ids, source_type, pdf_upload_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        literature_id = EXCLUDED.literature_id,
                        section = EXCLUDED.section,
                        text = EXCLUDED.text,
                        source_quote = EXCLUDED.source_quote,
                        evidence_tags = EXCLUDED.evidence_tags,
                        related_entity_ids = EXCLUDED.related_entity_ids,
                        source_type = EXCLUDED.source_type,
                        pdf_upload_id = EXCLUDED.pdf_upload_id
                    RETURNING *
                    """,
                    (
                        chunk_id,
                        literature_id,
                        "uploaded_pdf",
                        text,
                        source_quote,
                        Jsonb(evidence_tags),
                        Jsonb(related_entity_ids),
                        "uploaded_pdf",
                        pdf_upload_id,
                    ),
                )
                row = cur.fetchone()
                conn.commit()
                return _row_to_chunk(dict(row))
