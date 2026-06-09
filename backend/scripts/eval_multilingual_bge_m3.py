"""Spike sub-slice ③: compare multilingual BGE-M3 against the keyword baseline.

Runs ``run_cross_lingual_retrieval_eval()`` under four configurations:

  1. keyword                       (no embedding, current default cross-lingual baseline)
  2. vector + hashing              (sanity check: deterministic embedding floor)
  3. vector + multilingual_bge_m3  (the spike's headline configuration)
  4. hybrid + multilingual_bge_m3  (RRF fusion with the keyword bridge)

Embeds BGE-M3 weights are downloaded lazily on first encode (~1.4GB to
``~/.cache/huggingface/``). The script is *not* part of the per-commit gauntlet
and *does not* mutate any default env or pyproject; it just twiddles process
env before constructing each provider so the retrieval module picks up the
correct embedding backend.

Usage:
    python scripts/eval_multilingual_bge_m3.py                  # all four
    python scripts/eval_multilingual_bge_m3.py vector_bge       # single config
    python scripts/eval_multilingual_bge_m3.py --corpus runtime # opt into local state
    python scripts/eval_multilingual_bge_m3.py --json out.json  # also dump JSON
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# Allow `python scripts/eval_multilingual_bge_m3.py` from backend/ without -m.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _run_config(
    *,
    label: str,
    retrieval_strategy: str,
    embedding_backend: str,
    corpus: str,
) -> dict[str, Any]:
    """Set env, import the eval harness fresh, run it, capture metrics."""
    os.environ["QIYAN_RETRIEVAL_PROVIDER"] = retrieval_strategy
    os.environ["QIYAN_EMBEDDING_BACKEND"] = embedding_backend

    # Re-import so module-level singletons (vector index cache, embedding
    # backend selection) pick up the fresh env. Cheap; no fixture state shared
    # across configs.
    for mod in [
        m
        for m in list(sys.modules)
        if m.startswith("app.services.retrieval") or m == "app.services.retrieval_eval"
    ]:
        sys.modules.pop(mod, None)

    from app.services.retrieval_eval import run_cross_lingual_retrieval_eval

    start = time.perf_counter()
    report = run_cross_lingual_retrieval_eval(strategy=retrieval_strategy, corpus=corpus)
    elapsed_s = time.perf_counter() - start

    summary = report.summary
    return {
        "label": label,
        "corpus": summary.corpus,
        "retrieval_strategy": summary.retrieval_strategy,
        "embedding_backend": embedding_backend,
        "total_questions": summary.total_questions,
        "top_k": summary.top_k,
        "avg_monolingual_recall": summary.avg_monolingual_recall,
        "avg_cross_lingual_recall": summary.avg_cross_lingual_recall,
        "avg_language_diversity": summary.avg_language_diversity,
        "avg_precision_at_k": summary.avg_precision_at_k,
        "avg_mrr": summary.avg_mrr,
        "elapsed_s": round(elapsed_s, 2),
        "items": [
            {
                "id": item.id,
                "question_language": item.question_language,
                "cross_lingual_recall": item.cross_lingual_recall,
                "monolingual_recall": item.monolingual_recall,
                "mrr": item.mean_reciprocal_rank,
                "retrieved_ids": item.retrieved_ids,
            }
            for item in report.items
        ],
    }


_CONFIGS: dict[str, dict[str, str]] = {
    "keyword": {"retrieval": "keyword", "embedding": "hashing"},
    "vector_hashing": {"retrieval": "vector", "embedding": "hashing"},
    "vector_bge_m3": {"retrieval": "vector", "embedding": "multilingual_bge_m3"},
    "hybrid_bge_m3": {"retrieval": "hybrid", "embedding": "multilingual_bge_m3"},
}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "configs",
        nargs="*",
        choices=list(_CONFIGS) + ["all"],
        default=["all"],
        help="which configs to run; default all four",
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=None,
        help="optional path to dump full per-item JSON",
    )
    parser.add_argument(
        "--corpus",
        choices=["seed", "runtime"],
        default="seed",
        help="evaluation corpus: immutable seed benchmark or runtime local state; default seed",
    )
    args = parser.parse_args(argv[1:])

    requested = list(_CONFIGS) if "all" in args.configs or not args.configs else args.configs

    results: list[dict[str, Any]] = []
    for label in requested:
        cfg = _CONFIGS[label]
        print(
            f"\n=== {label} (corpus={args.corpus}, retrieval={cfg['retrieval']}, "
            f"embedding={cfg['embedding']}) ===",
            flush=True,
        )
        try:
            result = _run_config(
                label=label,
                retrieval_strategy=cfg["retrieval"],
                embedding_backend=cfg["embedding"],
                corpus=args.corpus,
            )
        except Exception as exc:  # noqa: BLE001 — surface all failures, downloads can flake
            print(f"  FAILED: {type(exc).__name__}: {exc}", flush=True)
            results.append({"label": label, "error": f"{type(exc).__name__}: {exc}"})
            continue

        results.append(result)
        print(
            f"  corpus={result['corpus']} N={result['total_questions']} top_k={result['top_k']} "
            f"mono={result['avg_monolingual_recall']:.4f} "
            f"cross={result['avg_cross_lingual_recall']:.4f} "
            f"div={result['avg_language_diversity']:.4f} "
            f"mrr={result['avg_mrr']:.4f} "
            f"elapsed={result['elapsed_s']:.2f}s",
            flush=True,
        )

    print("\n## Summary table\n")
    print("| label | corpus | strategy | embedding | N | mono | cross | div | MRR | elapsed |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for r in results:
        if "error" in r:
            print(f"| {r['label']} | — | — | — | — | — | — | — | — | ERROR: {r['error']} |")
            continue
        print(
            f"| {r['label']} | {r['corpus']} | {r['retrieval_strategy']} | {r['embedding_backend']} "
            f"| {r['total_questions']} "
            f"| {r['avg_monolingual_recall']:.4f} "
            f"| {r['avg_cross_lingual_recall']:.4f} "
            f"| {r['avg_language_diversity']:.4f} "
            f"| {r['avg_mrr']:.4f} "
            f"| {r['elapsed_s']:.2f}s |"
        )

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nJSON dumped to {args.json}")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
