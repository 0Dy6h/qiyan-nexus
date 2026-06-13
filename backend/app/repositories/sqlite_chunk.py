"""SQLite-backed chunk repository.

Uses only the Python standard library ``sqlite3`` module — zero new
dependencies.  The database file is shared with other repositories
(literature, network_task) via ``resolve_sqlite_db_path()``; each
repository creates its own table with ``CREATE TABLE IF NOT EXISTS``.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.schemas.chunk import LiteratureChunk

_JSON_COLUMNS = frozenset({"evidence_tags", "related_entity_ids"})

# Allowed column names for SQL query construction (security: prevent injection)
_ALLOWED_COLUMNS = frozenset(
    {
        "chunk_id",
        "literature_id",
        "section",
        "text",
        "source_quote",
        "evidence_tags",
        "related_entity_ids",
        "source_type",
        "pdf_upload_id",
    }
)

_CREATE_TABLE_SQL = """\
CREATE TABLE IF NOT EXISTS chunk (
    chunk_id          TEXT PRIMARY KEY,
    literature_id     TEXT NOT NULL,
    section           TEXT NOT NULL,
    text              TEXT NOT NULL,
    source_quote      TEXT NOT NULL,
    evidence_tags     TEXT NOT NULL DEFAULT '[]',
    related_entity_ids TEXT NOT NULL DEFAULT '[]',
    source_type       TEXT NOT NULL DEFAULT 'sample',
    pdf_upload_id     TEXT
)
"""


def _row_to_chunk(row: sqlite3.Row) -> LiteratureChunk:
    """Convert a database row to a ``LiteratureChunk``."""
    data: dict[str, Any] = dict(row)
    for col in _JSON_COLUMNS:
        val = data[col]
        if isinstance(val, str):
            data[col] = json.loads(val)
    return LiteratureChunk(**data)


def _validate_column_names(columns: list[str]) -> None:
    """Validate that all column names are in the allowed whitelist.

    Raises ValueError if any column name is not in _ALLOWED_COLUMNS.
    This prevents potential SQL injection if column names ever come from external input.
    """
    for col in columns:
        if col not in _ALLOWED_COLUMNS:
            raise ValueError(
                f"Invalid column name: {col!r}. "
                f"Column names must be from the fixed whitelist defined in _ALLOWED_COLUMNS."
            )


class SqliteChunkRepository:
    """Chunk repository backed by a local SQLite database."""

    def __init__(self, db_path: Path, seed_path: Path | None = None) -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._closed = False
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(_CREATE_TABLE_SQL)
        self._conn.commit()

        # Bootstrap from seed JSON if the table is empty.
        count = self._conn.execute("SELECT COUNT(*) FROM chunk").fetchone()[0]
        if count == 0:
            self._bootstrap_from_seed(seed_path)

    # ------------------------------------------------------------------
    # Bootstrap
    # ------------------------------------------------------------------

    def _bootstrap_from_seed(self, seed_path: Path | None = None) -> None:
        """Load seed data from the standard chunk JSON file."""
        if seed_path is None:
            from app.repositories.runtime_storage import resolve_chunk_storage_path

            seed_path = resolve_chunk_storage_path()

        raw_items: list[dict[str, Any]] = json.loads(seed_path.read_text(encoding="utf-8"))
        for item in raw_items:
            self._insert_item(item)
        self._conn.commit()

    def _insert_item(self, item: dict[str, Any]) -> None:
        """Insert a single item dict into the database."""
        for col in _JSON_COLUMNS:
            val = item.get(col, [])
            item[col] = json.dumps(val, ensure_ascii=False) if not isinstance(val, str) else val

        # source_type defaults to "sample" if not provided (seed data may omit it)
        if "source_type" not in item or item.get("source_type") is None:
            item["source_type"] = "sample"

        columns = [
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
        _validate_column_names(columns)  # Security: validate before SQL construction
        values = [item.get(c) for c in columns]
        placeholders = ", ".join("?" for _ in columns)
        col_names = ", ".join(columns)
        self._conn.execute(
            f"INSERT INTO chunk ({col_names}) VALUES ({placeholders})",
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

    def list_chunks(self) -> list[LiteratureChunk]:
        rows = self._conn.execute("SELECT * FROM chunk").fetchall()
        return [_row_to_chunk(row) for row in rows]

    def list_chunks_by_literature_id(self, literature_id: str) -> list[LiteratureChunk]:
        rows = self._conn.execute(
            "SELECT * FROM chunk WHERE literature_id = ?",
            (literature_id,),
        ).fetchall()
        return [_row_to_chunk(row) for row in rows]

    def group_chunks_by_literature(
        self, literature_ids: list[str]
    ) -> dict[str, list[LiteratureChunk]]:
        """Group chunks by literature_id in a single query."""
        from collections import defaultdict

        if not literature_ids:
            return {}
        placeholders = ",".join("?" for _ in literature_ids)
        rows = self._conn.execute(
            f"SELECT * FROM chunk WHERE literature_id IN ({placeholders})",
            literature_ids,
        ).fetchall()
        result: dict[str, list[LiteratureChunk]] = defaultdict(list)
        for row in rows:
            chunk = _row_to_chunk(row)
            result[chunk.literature_id].append(chunk)
        return dict(result)

    def get_chunk_by_id(self, chunk_id: str) -> LiteratureChunk | None:
        row = self._conn.execute(
            "SELECT * FROM chunk WHERE chunk_id = ?",
            (chunk_id,),
        ).fetchone()
        return _row_to_chunk(row) if row else None

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
        evidence_json = json.dumps(evidence_tags, ensure_ascii=False)
        related_json = json.dumps(
            related_entity_ids or ["disease:atopic-dermatitis"], ensure_ascii=False
        )

        existing = self._conn.execute(
            "SELECT chunk_id FROM chunk WHERE chunk_id = ?",
            (chunk_id,),
        ).fetchone()

        if existing is not None:
            self._conn.execute(
                """UPDATE chunk
                   SET literature_id = ?,
                       section = 'uploaded_pdf',
                       text = ?,
                       source_quote = ?,
                       evidence_tags = ?,
                       related_entity_ids = ?,
                       source_type = 'uploaded_pdf',
                       pdf_upload_id = ?
                   WHERE chunk_id = ?""",
                (
                    literature_id,
                    text,
                    source_quote,
                    evidence_json,
                    related_json,
                    pdf_upload_id,
                    chunk_id,
                ),
            )
        else:
            self._conn.execute(
                """INSERT INTO chunk
                   (chunk_id, literature_id, section, text, source_quote,
                    evidence_tags, related_entity_ids, source_type, pdf_upload_id)
                   VALUES (?, ?, 'uploaded_pdf', ?, ?, ?, ?, 'uploaded_pdf', ?)""",
                (
                    chunk_id,
                    literature_id,
                    text,
                    source_quote,
                    evidence_json,
                    related_json,
                    pdf_upload_id,
                ),
            )
        self._conn.commit()

        row = self._conn.execute(
            "SELECT * FROM chunk WHERE chunk_id = ?",
            (chunk_id,),
        ).fetchone()
        return _row_to_chunk(row)
