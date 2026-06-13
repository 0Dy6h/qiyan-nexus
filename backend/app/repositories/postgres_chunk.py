"""PostgreSQL-backed chunk repository using psycopg3."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

import psycopg

from app.schemas.chunk import LiteratureChunk


class PostgresChunkRepository:
    """PostgreSQL implementation of ChunkRepository protocol.

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

    def list_chunks(self) -> list[LiteratureChunk]:
        """Return all chunks."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM literature_chunk ORDER BY chunk_id")
                rows = cur.fetchall()
                return [self._row_to_chunk(row, cur.description) for row in rows]

    def list_chunks_by_literature_id(self, literature_id: str) -> list[LiteratureChunk]:
        """Return all chunks for a given literature item."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM literature_chunk
                    WHERE literature_id = %s
                    ORDER BY chunk_index
                    """,
                    (literature_id,),
                )
                rows = cur.fetchall()
                return [self._row_to_chunk(row, cur.description) for row in rows]

    def group_chunks_by_literature(
        self, literature_ids: list[str]
    ) -> dict[str, list[LiteratureChunk]]:
        """Group chunks by literature_id for a batch of IDs."""
        if not literature_ids:
            return {}

        grouped: dict[str, list[LiteratureChunk]] = defaultdict(list)

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM literature_chunk
                    WHERE literature_id = ANY(%s)
                    ORDER BY literature_id, chunk_index
                    """,
                    (literature_ids,),
                )
                rows = cur.fetchall()
                for row in rows:
                    chunk = self._row_to_chunk(row, cur.description)
                    grouped[chunk.literature_id].append(chunk)

        return dict(grouped)

    def get_chunk_by_id(self, chunk_id: str) -> LiteratureChunk | None:
        """Fetch a single chunk by ID."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM literature_chunk WHERE chunk_id = %s", (chunk_id,))
                row = cur.fetchone()
                if not row:
                    return None
                return self._row_to_chunk(row, cur.description)

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
        """Insert or update a chunk from an uploaded PDF."""
        now = datetime.now(UTC).isoformat()

        metadata = {
            "pdf_upload_id": pdf_upload_id,
            "source_quote": source_quote,
            "related_entity_ids": related_entity_ids or [],
        }

        with self._connect() as conn:
            with conn.cursor() as cur:
                # Check if chunk exists
                cur.execute(
                    "SELECT chunk_index FROM literature_chunk WHERE chunk_id = %s", (chunk_id,)
                )
                existing = cur.fetchone()

                if existing:
                    # Update
                    cur.execute(
                        """
                        UPDATE literature_chunk
                        SET text = %s, evidence_tags = %s, metadata = %s
                        WHERE chunk_id = %s
                        RETURNING *
                        """,
                        (text, json.dumps(evidence_tags), json.dumps(metadata), chunk_id),
                    )
                else:
                    # Insert - determine next chunk_index
                    cur.execute(
                        """
                        SELECT COALESCE(MAX(chunk_index), -1) + 1
                        FROM literature_chunk
                        WHERE literature_id = %s
                        """,
                        (literature_id,),
                    )
                    index_row = cur.fetchone()
                    if not index_row:
                        raise RuntimeError("Failed to compute next chunk_index")
                    next_index = index_row[0]

                    cur.execute(
                        """
                        INSERT INTO literature_chunk (
                            chunk_id, literature_id, chunk_index, text,
                            page_number, section_title, evidence_tags, metadata,
                            embedding, created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING *
                        """,
                        (
                            chunk_id,
                            literature_id,
                            next_index,
                            text,
                            None,
                            None,
                            json.dumps(evidence_tags),
                            json.dumps(metadata),
                            None,
                            now,
                        ),
                    )

                row = cur.fetchone()
                if not row:
                    raise RuntimeError("INSERT RETURNING failed")
                conn.commit()
                return self._row_to_chunk(row, cur.description)

    def _row_to_chunk(self, row: tuple[Any, ...], description: Any) -> LiteratureChunk:
        """Convert a database row to a LiteratureChunk."""
        col_names = [desc[0] for desc in description]
        data = dict(zip(col_names, row, strict=False))

        # Parse JSON fields
        data["evidence_tags"] = data.get("evidence_tags") or []
        data["metadata"] = data.get("metadata") or {}

        # Drop embedding field (not part of LiteratureChunk schema)
        data.pop("embedding", None)

        return LiteratureChunk.model_validate(data)
