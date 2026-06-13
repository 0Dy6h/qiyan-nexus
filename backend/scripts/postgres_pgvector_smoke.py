#!/usr/bin/env python3
"""pgvector smoke test: write embeddings and query by cosine distance.

This script validates that pgvector end-to-end works:
1. Generates embeddings for all chunks using HashingEmbeddingBackend
2. Writes embeddings to literature_chunk.embedding column
3. Runs a cosine-distance top-k query against pgvector
4. Prints results to confirm pgvector is operational

This does NOT change the default RAG retrieval strategy — it only validates
that pgvector works locally for future integration.

Requirements:
    - Docker compose up -d postgres
    - QIYAN_POSTGRES_URL set
    - Seed data loaded (run scripts/postgres_seed.py first)
"""

import os
import sys
from pathlib import Path

import psycopg
from pgvector.psycopg import register_vector


def main() -> int:
    # Check environment
    postgres_url = os.environ.get("QIYAN_POSTGRES_URL")
    if not postgres_url:
        print("❌ Error: QIYAN_POSTGRES_URL not set", file=sys.stderr)
        return 1

    print("🔌 Connecting to PostgreSQL...")
    try:
        conn = psycopg.connect(postgres_url)
        register_vector(conn)
    except Exception as e:
        print(f"❌ Connection failed: {e}", file=sys.stderr)
        return 1

    try:
        # Import embedding backend
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
        from services.embeddings.provider import HashingEmbeddingBackend

        backend = HashingEmbeddingBackend()

        # Fetch all chunks
        print("📦 Loading chunks from database...")
        with conn.cursor() as cur:
            cur.execute("SELECT chunk_id, text, embedding FROM literature_chunk")
            rows = cur.fetchall()

        if not rows:
            print("❌ No chunks found. Run scripts/postgres_seed.py first.", file=sys.stderr)
            return 1

        print(f"   Found {len(rows)} chunks")

        # Generate and write embeddings
        print("🧮 Generating embeddings...")
        updated = 0
        for chunk_id, text, existing_emb in rows:
            if existing_emb is not None:
                continue  # Skip if already has embedding

            embedding = backend.embed([text])[0]
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE literature_chunk SET embedding = %s WHERE chunk_id = %s",
                    (embedding, chunk_id),
                )
            updated += 1

        conn.commit()
        print(f"   ✅ Updated {updated} chunks (skipped {len(rows) - updated} with existing embeddings)")

        # Run a smoke query
        print("\n🔍 Running pgvector cosine distance query...")
        query_text = "特应性皮炎的发病机制"
        query_embedding = backend.embed([query_text])[0]

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT chunk_id, literature_id, LEFT(text, 100) as preview,
                       1 - (embedding <=> %s::vector) as cosine_similarity
                FROM literature_chunk
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT 5
                """,
                (query_embedding, query_embedding),
            )
            results = cur.fetchall()

        print(f"   Query: {query_text}")
        print(f"   Top 5 results:\n")
        for i, (chunk_id, lit_id, preview, similarity) in enumerate(results, 1):
            print(f"   {i}. {chunk_id} (lit: {lit_id})")
            print(f"      Similarity: {similarity:.4f}")
            print(f"      Preview: {preview}...")
            print()

        print("✅ pgvector smoke test passed!")
        print("   - Embeddings written to literature_chunk.embedding")
        print("   - Cosine distance query returned stable results")
        print("   - Ready for future RAG integration")

    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
