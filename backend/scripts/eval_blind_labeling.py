r"""Blind relevance-labeling harness for a NON-circular retrieval eval.

Why this exists
---------------
The committed eval set (``backend/data/evals/rag_ad_eval_questions.json``) authors
``expected_literature_ids`` alongside the retriever, on the 20 synthetic seed
records. Its reported recall = 1.0 is therefore a circular, seed-only artifact:
the same author wrote the corpus, the queries, and the "right" answers, then tuned
a deterministic ranker until it reproduced them. That measures memorisation, not
retrieval quality.

This harness breaks the circularity:

  1. It runs the real retriever over a **real corpus** (point the runtime env at a
     ``pubmed_live`` corpus — see ``scripts/seed_pubmed_corpus.py``).
  2. It emits the retriever's ACTUAL top-k for each query, with an empty
     ``relevant`` slot per candidate.
  3. A domain expert judges each candidate relevant / not — **blind to score and
     rank**, and NOT the person who tuned the retriever.
  4. It scores precision@k and MRR from those human labels.

Ground truth comes from the human, not from the retriever's author. No labels are
fabricated here — the ``relevant`` fields ship empty on purpose.

Recall is intentionally NOT reported: true recall needs pooled annotation over the
whole corpus (every relevant doc, not just the top-k). Precision@k and MRR only
need the top-k judged, so they are honestly computable from one worksheet.

Usage (from ``backend/`` with the project venv)::

    # point the runtime at a real corpus first, e.g.:
    #   $env:LITERATURE_RUNTIME_STATE_PATH = "..\.tmp\real-only\literature_state.json"
    #   $env:CHUNK_RUNTIME_STATE_PATH     = "..\.tmp\real-only\chunk_state.json"

    python scripts/eval_blind_labeling.py build \
        --queries scripts/eval_queries.sample.json \
        --out ../.tmp/eval-worksheet/worksheet.json --top-k 5

    # ... a domain expert opens the worksheet and sets each "relevant": true/false ...

    python scripts/eval_blind_labeling.py score \
        --worksheet ../.tmp/eval-worksheet/worksheet.json

The worksheet contains real abstract snippets, so it is written under a gitignored
path (``.tmp/`` / ``backend/data/runtime/``); do not commit it as a fixture.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

_SNIPPET_CHARS = 200


def build_worksheet(queries: list[str], top_k: int) -> dict[str, Any]:
    """Run the real retriever over the current corpus and emit a labeling worksheet.

    Each query gets the retriever's top-k distinct documents with an empty
    ``relevant`` field for a human to fill. Imports are lazy so ``--help`` works
    without importing the app stack.
    """

    from app.repositories.runtime_storage import get_chunk_repository, get_literature_repository
    from app.services.literature import detect_query_language
    from app.services.retrieval.provider import select_retrieval_provider

    literature_repo = get_literature_repository()
    chunk_repo = get_chunk_repository()
    items = literature_repo.list_items()
    chunks_by_item = {item.id: chunk_repo.list_chunks_by_literature_id(item.id) for item in items}
    provider = select_retrieval_provider()

    live = sum(1 for item in items if item.record_origin == "pubmed_live")
    entries: list[dict[str, Any]] = []
    for query in queries:
        preferred = "cn_literature" if detect_query_language(query) == "zh" else "pubmed"
        ranked = provider.rank(query, items, chunks_by_item, preferred)
        candidates: list[dict[str, Any]] = []
        seen: set[str] = set()
        for candidate in ranked:
            if candidate.item.id in seen:
                continue
            seen.add(candidate.item.id)
            candidates.append(
                {
                    "rank": len(candidates) + 1,
                    "literature_id": candidate.item.id,
                    "record_origin": candidate.item.record_origin,
                    "score": candidate.score,
                    "title": candidate.item.title,
                    "snippet": candidate.item.snippet[:_SNIPPET_CHARS],
                    "relevant": None,
                }
            )
            if len(candidates) >= top_k:
                break
        entries.append({"query": query, "candidates": candidates})

    return {
        "corpus_size": len(items),
        "pubmed_live_records": live,
        "top_k": top_k,
        "instructions": (
            "For each candidate set 'relevant' to true or false, judged blind to "
            "score/rank. Do not edit the query or candidate text. This scores "
            "precision@k and MRR; recall needs pooled annotation over the full corpus."
        ),
        "queries": entries,
    }


def score_worksheet(worksheet: dict[str, Any]) -> dict[str, Any]:
    """Compute precision@k and MRR from a filled worksheet.

    A query whose candidates are not all labelled is skipped and counted under
    ``unlabeled_queries`` (partial labels would bias the metrics).
    """

    per_query: list[dict[str, Any]] = []
    precisions: list[float] = []
    reciprocal_ranks: list[float] = []
    unlabeled = 0

    for entry in worksheet.get("queries", []):
        candidates = entry.get("candidates", [])
        if not candidates or any(c.get("relevant") is None for c in candidates):
            unlabeled += 1
            continue
        relevant_positions = [i for i, c in enumerate(candidates) if c.get("relevant") is True]
        precision = len(relevant_positions) / len(candidates)
        first_rank = relevant_positions[0] + 1 if relevant_positions else None
        reciprocal = 1.0 / first_rank if first_rank is not None else 0.0
        precisions.append(precision)
        reciprocal_ranks.append(reciprocal)
        per_query.append(
            {
                "query": entry.get("query"),
                "precision_at_k": round(precision, 3),
                "first_relevant_rank": first_rank,
                "reciprocal_rank": round(reciprocal, 3),
            }
        )

    labeled = len(precisions)
    return {
        "labeled_queries": labeled,
        "unlabeled_queries": unlabeled,
        "mean_precision_at_k": round(sum(precisions) / labeled, 3) if labeled else None,
        "mrr": round(sum(reciprocal_ranks) / labeled, 3) if labeled else None,
        "note": "recall not computed (needs pooled annotation over the full corpus).",
        "per_query": per_query,
    }


def _cmd_build(args: argparse.Namespace) -> int:
    queries_payload = json.loads(Path(args.queries).read_text(encoding="utf-8"))
    queries = (
        queries_payload.get("queries") if isinstance(queries_payload, dict) else queries_payload
    )
    if not isinstance(queries, list) or not all(isinstance(q, str) for q in queries):
        print("queries file must be a list of strings or {'queries': [...]}.")
        return 2
    worksheet = build_worksheet(queries, max(1, args.top_k))
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(worksheet, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Wrote worksheet: {out_path} "
        f"({len(queries)} queries, top_k={args.top_k}, "
        f"{worksheet['pubmed_live_records']}/{worksheet['corpus_size']} real records)."
    )
    print("Next: a domain expert fills each candidate's 'relevant' true/false, then run 'score'.")
    return 0


def _cmd_score(args: argparse.Namespace) -> int:
    worksheet = json.loads(Path(args.worksheet).read_text(encoding="utf-8"))
    result = score_worksheet(worksheet)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["unlabeled_queries"]:
        print(f"\n{result['unlabeled_queries']} query(ies) still unlabeled — not scored.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="mode", required=True)

    build_parser = sub.add_parser(
        "build", help="Generate a labeling worksheet from the real corpus."
    )
    build_parser.add_argument("--queries", required=True, help="JSON list of query strings.")
    build_parser.add_argument("--out", required=True, help="Output worksheet path (gitignored).")
    build_parser.add_argument(
        "--top-k", type=int, default=5, help="Candidates per query (default 5)."
    )
    build_parser.set_defaults(func=_cmd_build)

    score_parser = sub.add_parser("score", help="Score a filled worksheet (precision@k, MRR).")
    score_parser.add_argument("--worksheet", required=True, help="Filled worksheet path.")
    score_parser.set_defaults(func=_cmd_score)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
