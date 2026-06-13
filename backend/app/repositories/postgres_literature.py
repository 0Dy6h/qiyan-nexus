"""PostgreSQL-backed literature repository using psycopg3."""

from __future__ import annotations

import json
from typing import Any

import psycopg

from app.schemas.literature import LiteratureItem, PdfParseResult


class PostgresLiteratureRepository:
    """PostgreSQL implementation of LiteratureRepository protocol.

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

    def list_items(self) -> list[LiteratureItem]:
        """Return all literature items."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM literature ORDER BY year DESC")
                rows = cur.fetchall()
                return [self._row_to_item(row, cur.description) for row in rows]

    def get_item_by_id(self, item_id: str) -> LiteratureItem | None:
        """Fetch a single literature item by ID."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM literature WHERE id = %s", (item_id,))
                row = cur.fetchone()
                if not row:
                    return None
                return self._row_to_item(row, cur.description)

    def update_pdf_metadata(
        self,
        literature_id: str,
        pdf_upload_id: str,
        pdf_file_name: str,
        pdf_parse_status: str,
    ) -> LiteratureItem | None:
        """Update PDF metadata for a literature item."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE literature
                    SET pdf_upload_id = %s, pdf_file_name = %s, pdf_parse_status = %s,
                        pdf_parse_message = NULL, pdf_parse_started_at = NULL,
                        pdf_parse_finished_at = NULL, pdf_parse_result = NULL,
                        last_parse_trigger = NULL, parse_attempt_count = 0
                    WHERE id = %s
                    RETURNING *
                    """,
                    (pdf_upload_id, pdf_file_name, pdf_parse_status, literature_id),
                )
                row = cur.fetchone()
                conn.commit()
                if not row:
                    return None
                return self._row_to_item(row, cur.description)

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
        with self._connect() as conn:
            with conn.cursor() as cur:
                # Fetch current parse_attempt_count
                cur.execute(
                    "SELECT pdf_upload_id, pdf_file_name, parse_attempt_count FROM literature WHERE id = %s",
                    (literature_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None

                pdf_upload_id, pdf_file_name, parse_attempt_count = row
                if not pdf_upload_id or not pdf_file_name:
                    return None  # No PDF uploaded yet

                parse_attempt_count = (parse_attempt_count or 0) + 1

                cur.execute(
                    """
                    UPDATE literature
                    SET pdf_parse_status = %s, pdf_parse_message = %s,
                        pdf_parse_started_at = %s, pdf_parse_finished_at = %s,
                        pdf_parse_result = %s, last_parse_trigger = %s,
                        parse_attempt_count = %s
                    WHERE id = %s
                    RETURNING *
                    """,
                    (
                        pdf_parse_status,
                        pdf_parse_message,
                        pdf_parse_started_at,
                        pdf_parse_finished_at,
                        json.dumps(pdf_parse_result.model_dump()) if pdf_parse_result else None,
                        last_parse_trigger,
                        parse_attempt_count,
                        literature_id,
                    ),
                )
                updated_row = cur.fetchone()
                conn.commit()
                if not updated_row:
                    return None
                return self._row_to_item(updated_row, cur.description)

    def bulk_upsert_pubmed_items(self, incoming_items: list[dict[str, Any]]) -> tuple[int, int]:
        """Bulk upsert PubMed items. Returns (inserted, updated) counts."""
        if not incoming_items:
            return (0, 0)

        inserted = 0
        updated = 0

        with self._connect() as conn:
            with conn.cursor() as cur:
                for item_dict in incoming_items:
                    lit_id = item_dict["id"]
                    cur.execute("SELECT id FROM literature WHERE id = %s", (lit_id,))
                    exists = cur.fetchone() is not None

                    if exists:
                        # Update only PubMed-owned fields
                        cur.execute(
                            """
                            UPDATE literature
                            SET title = %s, abstract = %s, authors = %s, year = %s,
                                keywords = %s, evidence_tags = %s, source = %s,
                                snippet = %s, citation_url = %s, doi = %s,
                                pubmed_id = %s, language = %s, source_type = %s
                            WHERE id = %s
                            """,
                            (
                                item_dict["title"],
                                item_dict.get("abstract"),
                                json.dumps(item_dict.get("authors", [])),
                                item_dict["year"],
                                json.dumps(item_dict.get("keywords", [])),
                                json.dumps(item_dict.get("evidence_tags", [])),
                                item_dict["source"],
                                item_dict["snippet"],
                                item_dict.get("citation_url"),
                                item_dict.get("doi"),
                                item_dict.get("pubmed_id"),
                                item_dict["language"],
                                item_dict["source_type"],
                                lit_id,
                            ),
                        )
                        updated += 1
                    else:
                        # Insert new item with all fields
                        cur.execute(
                            """
                            INSERT INTO literature (
                                id, title, language, source_type, source, year,
                                snippet, authors, keywords, evidence_tags, abstract,
                                citation_url, pubmed_id, doi, related_entity_ids
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                lit_id,
                                item_dict["title"],
                                item_dict["language"],
                                item_dict["source_type"],
                                item_dict["source"],
                                item_dict["year"],
                                item_dict["snippet"],
                                json.dumps(item_dict.get("authors", [])),
                                json.dumps(item_dict.get("keywords", [])),
                                json.dumps(item_dict.get("evidence_tags", [])),
                                item_dict.get("abstract"),
                                item_dict.get("citation_url"),
                                item_dict.get("pubmed_id"),
                                item_dict.get("doi"),
                                json.dumps(item_dict.get("related_entity_ids", [])),
                            ),
                        )
                        inserted += 1

                conn.commit()

        return (inserted, updated)

    def _row_to_item(self, row: tuple[Any, ...], description: Any) -> LiteratureItem:
        """Convert a database row to a LiteratureItem."""
        col_names = [desc[0] for desc in description]
        data = dict(zip(col_names, row, strict=False))

        # Parse JSON fields
        for json_field in ["authors", "keywords", "evidence_tags", "related_entity_ids"]:
            data[json_field] = data.get(json_field) or []

        # Parse pdf_parse_result if present
        if data.get("pdf_parse_result"):
            data["pdf_parse_result"] = PdfParseResult.model_validate(data["pdf_parse_result"])

        return LiteratureItem.model_validate(data)
