#!/usr/bin/env python3
"""Seed PostgreSQL database with sample literature and chunk data.

Usage:
    python scripts/postgres_seed.py          # Insert seed data (skip if already present)
    python scripts/postgres_seed.py --reset  # Clear all data and re-insert seed data

Requires:
    - Docker compose up -d postgres (see infra/README.md)
    - QIYAN_POSTGRES_URL set in .env or environment
"""

import argparse
import json
import os
import sys
from pathlib import Path

import psycopg


def load_seed_data(data_dir: Path) -> tuple[list[dict], list[dict]]:
    """Load literature and chunk seed data from JSON files."""
    lit_path = data_dir / "literature" / "sample_ad_literature.json"
    chunk_path = data_dir / "literature" / "sample_ad_chunks.json"

    with open(lit_path, encoding="utf-8") as f:
        literature = json.load(f)

    with open(chunk_path, encoding="utf-8") as f:
        chunks = json.load(f)

    return literature, chunks


def reset_tables(conn: psycopg.Connection) -> None:
    """Clear all runtime state tables."""
    print("⚠️  Clearing all tables...")
    with conn.cursor() as cur:
        cur.execute("DELETE FROM literature_chunk")
        cur.execute("DELETE FROM literature")
        cur.execute("DELETE FROM network_task")
    conn.commit()
    print("✅ Tables cleared")


def seed_literature(conn: psycopg.Connection, items: list[dict]) -> int:
    """Insert literature items. Returns count inserted."""
    inserted = 0
    with conn.cursor() as cur:
        for item in items:
            lit_id = item["id"]
            # Check if exists
            cur.execute("SELECT 1 FROM literature WHERE id = %s", (lit_id,))
            if cur.fetchone():
                continue  # Skip existing

            cur.execute(
                """
                INSERT INTO literature (
                    id, title, language, source_type, source, year,
                    snippet, authors, keywords, evidence_tags, abstract,
                    citation_url, pubmed_id, doi, pdf_upload_id, pdf_file_name,
                    pdf_parse_status, related_entity_ids
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    lit_id,
                    item["title"],
                    item["language"],
                    item["source_type"],
                    item["source"],
                    item["year"],
                    item["snippet"],
                    json.dumps(item.get("authors", [])),
                    json.dumps(item.get("keywords", [])),
                    json.dumps(item.get("evidence_tags", [])),
                    item.get("abstract"),
                    item.get("citation_url"),
                    item.get("pubmed_id"),
                    item.get("doi"),
                    item.get("pdf_upload_id"),
                    item.get("pdf_file_name"),
                    item.get("pdf_parse_status"),
                    json.dumps(item.get("related_entity_ids", [])),
                ),
            )
            inserted += 1

    conn.commit()
    return inserted


def seed_chunks(conn: psycopg.Connection, chunks: list[dict]) -> int:
    """Insert literature chunks. Returns count inserted."""
    inserted = 0
    with conn.cursor() as cur:
        for chunk in chunks:
            chunk_id = chunk["chunk_id"]
            # Check if exists
            cur.execute("SELECT 1 FROM literature_chunk WHERE chunk_id = %s", (chunk_id,))
            if cur.fetchone():
                continue  # Skip existing

            cur.execute(
                """
                INSERT INTO literature_chunk (
                    chunk_id, literature_id, chunk_index, text,
                    page_number, section_title, evidence_tags, metadata,
                    embedding, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    chunk_id,
                    chunk["literature_id"],
                    chunk["chunk_index"],
                    chunk["text"],
                    chunk.get("page_number"),
                    chunk.get("section_title"),
                    json.dumps(chunk.get("evidence_tags", [])),
                    json.dumps(chunk.get("metadata", {})),
                    None,  # embedding will be filled by pgvector smoke script
                    chunk.get("created_at", "2025-01-01T00:00:00Z"),
                ),
            )
            inserted += 1

    conn.commit()
    return inserted


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed PostgreSQL with sample data")
    parser.add_argument("--reset", action="store_true", help="Clear all data before seeding")
    args = parser.parse_args()

    # Check environment
    postgres_url = os.environ.get("QIYAN_POSTGRES_URL")
    if not postgres_url:
        print("❌ Error: QIYAN_POSTGRES_URL not set", file=sys.stderr)
        print("   Set it in .env or environment, then retry", file=sys.stderr)
        return 1

    # Locate seed data
    repo_root = Path(__file__).resolve().parents[1]
    data_dir = repo_root / "data"
    if not data_dir.exists():
        print(f"❌ Error: data directory not found at {data_dir}", file=sys.stderr)
        return 1

    print(f"📦 Loading seed data from {data_dir}")
    literature, chunks = load_seed_data(data_dir)
    print(f"   Found {len(literature)} literature items, {len(chunks)} chunks")

    print(f"🔌 Connecting to PostgreSQL...")
    try:
        conn = psycopg.connect(postgres_url)
    except Exception as e:
        print(f"❌ Connection failed: {e}", file=sys.stderr)
        print("   Ensure Docker is running and postgres service is healthy", file=sys.stderr)
        return 1

    try:
        if args.reset:
            reset_tables(conn)

        print("📥 Seeding literature...")
        lit_inserted = seed_literature(conn, literature)
        print(f"   ✅ Inserted {lit_inserted} literature items (skipped {len(literature) - lit_inserted} existing)")

        print("📥 Seeding chunks...")
        chunk_inserted = seed_chunks(conn, chunks)
        print(f"   ✅ Inserted {chunk_inserted} chunks (skipped {len(chunks) - chunk_inserted} existing)")

        # Verify counts
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM literature")
            lit_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM literature_chunk")
            chunk_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM network_task")
            task_count = cur.fetchone()[0]

        print(f"\n✅ Seed complete!")
        print(f"   Literature: {lit_count} rows")
        print(f"   Chunks:     {chunk_count} rows")
        print(f"   Tasks:      {task_count} rows")

    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
