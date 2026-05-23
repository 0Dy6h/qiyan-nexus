"""Ablation: run the 50-question AD eval across retrieval strategies.

Prints a small markdown table comparing the configured strategies (default:
``keyword`` + ``hybrid``) on pass_rate / citation_hit / chunk_hit. Uses the
FastAPI TestClient so the script doesn't need a running server.

Usage:
    python scripts/compare_retrieval_strategies.py                # keyword, hybrid
    python scripts/compare_retrieval_strategies.py keyword vector hybrid
    QIYAN_EMBEDDING_BACKEND=bge python scripts/compare_retrieval_strategies.py
"""

from __future__ import annotations

import sys

from fastapi.testclient import TestClient

from app.main import app


def _run(strategy: str) -> dict[str, object]:
    client = TestClient(app)
    response = client.get("/api/evals/rag-ad/report", params={"strategy": strategy})
    response.raise_for_status()
    summary = response.json()["summary"]
    return {
        "strategy": summary["retrieval_strategy"],
        "pass_rate": summary["pass_rate"],
        "citation_hit": summary["citation_hit_count"],
        "chunk_hit": summary["chunk_hit_count"],
    }


def main(argv: list[str]) -> int:
    strategies = argv[1:] or ["keyword", "hybrid"]
    rows = [_run(strategy) for strategy in strategies]

    header = "| strategy | pass_rate | citation_hit | chunk_hit |"
    divider = "|---|---|---|---|"
    lines = [header, divider]
    for row in rows:
        lines.append(
            f"| {row['strategy']} | {row['pass_rate']:.3f} "
            f"| {row['citation_hit']}/50 | {row['chunk_hit']}/50 |"
        )
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
