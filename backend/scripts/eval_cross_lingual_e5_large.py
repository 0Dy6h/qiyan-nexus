"""Cross-lingual retrieval evaluation with multilingual-e5-large backend.

Runs the 17-question bilingual subset of rag_ad_eval_questions across retrieval
strategies (keyword, vector, hybrid) with QIYAN_EMBEDDING_BACKEND=multilingual-e5-large.

Compares against the locked keyword baseline (avg_cross_lingual_recall=0.9688).

Usage:
    python scripts/eval_cross_lingual_e5_large.py
    QIYAN_EMBEDDING_BACKEND=multilingual-e5-large python scripts/eval_cross_lingual_e5_large.py
"""

from __future__ import annotations

import os
import sys
from typing import Literal

from app.services.retrieval_eval import run_cross_lingual_retrieval_eval

RetrievalStrategy = Literal["keyword", "vector", "hybrid"]


def main() -> int:
    backend = os.getenv("QIYAN_EMBEDDING_BACKEND", "hashing")
    print(f"# Cross-Lingual Retrieval Evaluation — multilingual-e5-large")
    print(f"\n**Embedding Backend**: `{backend}`\n")

    strategies: list[RetrievalStrategy] = ["keyword", "vector", "hybrid"]
    results = []

    for strategy in strategies:
        print(f"Running {strategy}...", file=sys.stderr)
        report = run_cross_lingual_retrieval_eval(
            strategy=strategy,
            top_k=10,
        )
        results.append({
            "strategy": strategy,
            "n": len(report.items),
            "mono": report.summary.avg_monolingual_recall,
            "cross": report.summary.avg_cross_lingual_recall,
            "diversity": report.summary.avg_language_diversity,
            "p_at_k": report.summary.avg_precision_at_k,
            "mrr": report.summary.avg_mrr,
        })

    # Markdown table
    print("\n## Summary\n")
    print("| Strategy | n | Mono Recall | Cross Recall | Diversity | P@10 | MRR |")
    print("|----------|---|-------------|--------------|-----------|------|-----|")
    for r in results:
        print(
            f"| {r['strategy']} | {r['n']} "
            f"| {r['mono']:.4f} | {r['cross']:.4f} "
            f"| {r['diversity']:.4f} | {r['p_at_k']:.4f} | {r['mrr']:.4f} |"
        )

    # Baseline comparison (keyword locked at 0.9688)
    baseline_cross = 0.9688
    print(f"\n## vs Keyword Baseline (locked: {baseline_cross:.4f})\n")
    for r in results:
        if r["strategy"] == "keyword":
            delta = 0.0000
        else:
            delta = r["cross"] - baseline_cross
        print(f"- **{r['strategy']}**: {r['cross']:.4f} (Δ {delta:+.4f})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
