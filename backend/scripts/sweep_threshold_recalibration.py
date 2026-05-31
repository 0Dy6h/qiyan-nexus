"""Threshold-recalibration sweep on the harder real-LLM-style grounding fixture.

Scores ``data/evals/grounding_semantic_pairs_bge.json`` (faithful claims lifted
from the 2026-05-31 opencode_go live smoke, each paired with an on-topic hard
negative) across a range of semantic thresholds on the bge backend. Prints a
per-threshold confusion matrix and the faithful/hard-negative score
distributions so the cosine-vs-entailment overlap is measurable.

This backs ``docs/evaluations/2026-06-01-threshold-recalibration.md`` and the
ADR-0012 finding that a pure cosine threshold cannot separate faithful
paraphrases from on-topic fabrications.

Usage (PowerShell, from the backend directory)::

    $env:HF_HUB_OFFLINE = "1"   # use the locally cached bge weights
    & .uv-test-venv/Scripts/python.exe scripts/sweep_threshold_recalibration.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

if "HF_ENDPOINT" not in os.environ:
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from app.schemas.eval import load_grounding_semantic_pairs  # noqa: E402
from app.services.eval import (  # noqa: E402
    SEMANTIC_PAIRS_BGE_PATH,
    run_grounding_semantic_separation,
)
from app.services.grounding import score_claim_support  # noqa: E402
from app.services.retrieval.embedding import select_embedding_backend  # noqa: E402

_THRESHOLDS = [0.55, 0.58, 0.60, 0.62, 0.64, 0.66, 0.68, 0.70, 0.72, 0.74, 0.76, 0.78]


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

    backend_name = "bge"
    backend = select_embedding_backend(backend_name)
    pairs = load_grounding_semantic_pairs(SEMANTIC_PAIRS_BGE_PATH)
    scored = [(p, score_claim_support(p.claim, p.chunk_text, backend)) for p in pairs]
    faithful = sorted(((p, s) for p, s in scored if p.supported), key=lambda x: x[1])
    hard_neg = sorted(((p, s) for p, s in scored if not p.supported), key=lambda x: x[1])

    print("=" * 78)
    print(f"Threshold recalibration sweep on {backend.name} backend")
    print(f"Fixture: {SEMANTIC_PAIRS_BGE_PATH.name} ({len(pairs)} pairs)")
    print("=" * 78)

    print("\nFAITHFUL claims (must PASS), low -> high:")
    for p, s in faithful:
        print(f"  {s:.3f}  {p.id}")
    min_faithful = min(s for _, s in faithful)
    print(f"  min faithful = {min_faithful:.3f}")

    print("\nHARD NEGATIVE claims (must BLOCK), low -> high:")
    for p, s in hard_neg:
        print(f"  {s:.3f}  {p.id}")
    max_hard_neg = max(s for _, s in hard_neg)
    print(f"  max hard-negative = {max_hard_neg:.3f}")

    gap = min_faithful - max_hard_neg
    print(f"\nGAP (min_faithful - max_hard_negative) = {gap:+.3f}")
    if gap <= 0:
        print(
            "  OVERLAP: no single cosine threshold separates faithful paraphrases"
            " from on-topic hard negatives. See ADR-0012."
        )

    print("\nThreshold sweep (confusion matrix):")
    print(
        f"  {'thr':>5} | {'faith_pass':>10} | {'hardneg_block':>13} | {'false_rej':>9} | {'false_acc':>9}"
    )
    for t in _THRESHOLDS:
        report = run_grounding_semantic_separation(
            threshold=t, backend_name=backend_name, pairs_path=SEMANTIC_PAIRS_BGE_PATH
        )
        ft = report["faithful_total"]
        ht = report["hallucinated_total"]
        print(
            f"  {t:>5.2f} | {report['accepted_faithful']:>4}/{ft:<5} |"
            f" {report['rejected_hallucinated']:>5}/{ht:<7} |"
            f" {report['false_rejected_faithful']:>9} | {report['false_accepted_hallucinated']:>9}"
        )


if __name__ == "__main__":
    main()
