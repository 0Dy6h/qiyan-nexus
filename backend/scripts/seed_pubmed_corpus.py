r"""Operator tool: populate a real PubMed corpus into runtime state.

The seed literature set is intentionally a small *synthetic* sample (it must not
ship real, copyrighted abstracts as fixtures). When you want a realistic,
broader corpus for an internal trial or reviewer walkthrough, run this script:
it calls the existing ``sync_pubmed`` service for several curated AD + TCM
queries and accumulates the real ``pubmed_live`` records into runtime state
(``backend/data/runtime/``, gitignored) — never into the seed fixtures.

Usage (from ``backend/`` with the project venv):

    & .\.uv-test-venv\Scripts\python.exe scripts\seed_pubmed_corpus.py
    & .\.uv-test-venv\Scripts\python.exe scripts\seed_pubmed_corpus.py --per-query 15

This makes live calls to NCBI E-utilities; set ``NCBI_API_KEY`` to raise the
rate limit from 3 to 10 req/s. To reset, clear the runtime literature state.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

# Curated atopic-dermatitis + TCM queries spanning the corpus's themes.
DEFAULT_QUERIES = [
    "atopic dermatitis traditional chinese medicine",
    "atopic dermatitis chinese herbal medicine randomized",
    "atopic dermatitis acupuncture",
    "eczema gut skin axis microbiome",
    "atopic dermatitis skin barrier filaggrin",
    "atopic dermatitis network pharmacology",
    "atopic dermatitis pruritus IL-31",
    "atopic dermatitis JAK inhibitor",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed a real PubMed corpus into runtime state.")
    parser.add_argument(
        "--per-query",
        type=int,
        default=10,
        help="Max records to fetch per query (1-50, NCBI hard cap 50).",
    )
    args = parser.parse_args()

    # Imported lazily so --help works without importing the app stack.
    from app.repositories.runtime_storage import get_literature_repository
    from app.services.literature import sync_pubmed

    per_query = max(1, min(args.per_query, 50))
    total_created = 0
    total_updated = 0
    for query in DEFAULT_QUERIES:
        try:
            result = sync_pubmed(query, per_query)
        except Exception as exc:  # noqa: BLE001 - operator script, report and continue
            print(f"  ! '{query}' failed: {exc}")
            continue
        total_created += result.created
        total_updated += result.updated
        print(
            f"  '{query}': fetched={result.fetched} created={result.created} updated={result.updated}"
        )

    items = get_literature_repository().list_items()
    live = sum(1 for item in items if item.record_origin == "pubmed_live")
    seed = sum(1 for item in items if item.record_origin == "seed_sample")
    print(
        f"\nDone. created={total_created} updated={total_updated}. "
        f"Runtime corpus now: {len(items)} items ({live} pubmed_live, {seed} seed_sample)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
