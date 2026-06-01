"""eval_nli_real_distribution.py — Slice 3: NLI gate evaluation on real-answer validation set.

Scores the ``grounding_real_answer_pairs.json`` fixture with the NLI entailment
backend and reports the confusion matrix at the recommended production threshold
(0.5). Requires ``QIYAN_NLI_BACKEND=transformers`` (lazy-loads ~560 MB model).

Usage (offline, after model cached):
  cd backend
  QIYAN_NLI_BACKEND=transformers QIYAN_NLI_THRESHOLD=0.5 \
    ./.uv-test-venv/Scripts/python.exe scripts/eval_nli_real_distribution.py

The script prints a human-readable summary and writes the full JSON report to
``backend/data/runtime/eval_nli_real_distribution_<timestamp>.json``.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

# ── path / encoding setup ────────────────────────────────────────────────────

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

# ── imports (after path setup) ───────────────────────────────────────────────

from app.services.eval import REAL_ANSWER_PAIRS_PATH, run_nli_real_distribution_eval  # noqa: E402

RUNTIME_DIR = BACKEND_ROOT / "data" / "runtime"


def main() -> None:
    print("=" * 70)
    print("  NLI Real-Distribution Evaluation — Slice 3")
    print("=" * 70)
    print()

    nli_backend = os.getenv("QIYAN_NLI_BACKEND", "")
    if nli_backend != "transformers":
        print("❌ QIYAN_NLI_BACKEND=transformers is required.")
        print("   This script needs the NLI model loaded to score entailment.")
        print("   No API key needed — the model runs locally (~560 MB, cached).")
        sys.exit(1)

    threshold_str = os.getenv("QIYAN_NLI_THRESHOLD", "0.5")
    try:
        threshold = float(threshold_str)
    except ValueError:
        threshold = 0.5

    print(f"  Fixture: {REAL_ANSWER_PAIRS_PATH.name}")
    print(f"  Threshold: {threshold}")
    print(f"  Model: {os.getenv('QIYAN_NLI_MODEL', 'mDeBERTa-v3-base-mnli-xnli')}")
    print()
    print("Loading NLI model (first call lazy-loads ~560 MB)...")
    print()

    try:
        result = run_nli_real_distribution_eval(threshold=threshold)
    except ValueError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        sys.exit(1)

    # ── print summary ────────────────────────────────────────────────────

    strict = result["strict"]
    stats = result["per_label_stats"]
    counts = result["label_counts"]

    print("─" * 70)
    print("  RESULTS")
    print("─" * 70)
    print(f"  Total pairs: {result['total_pairs']}")
    print(f"    supported:  {counts['supported']}")
    print(f"    partial:    {counts['partial']}")
    print(f"    unsupported: {counts['unsupported']}")
    print()

    print("  Strict confusion matrix (supported vs unsupported):")
    print(f"    Accepted supported  (TP):  {strict['accepted_supported']:>3d}")
    print(f"    Rejected unsupported (TN):  {strict['rejected_unsupported']:>3d}")
    print(f"    False accepts        (FP):  {strict['false_accepts']:>3d}")
    print(f"    False rejects        (FN):  {strict['false_rejects']:>3d}")
    print(f"    Accuracy:                  {strict['accuracy']:.1%}")
    print()

    print("  Entailment score distributions:")
    for label in ["supported", "partial", "unsupported"]:
        s = stats[label]
        if s["min"] is not None:
            print(
                f"    {label:>11s}:  min={s['min']:.4f}  max={s['max']:.4f}  mean={s['mean']:.4f}"
            )
        else:
            print(f"    {label:>11s}:  (no pairs)")
    print()

    # Check for clean separation
    sup_min = stats["supported"]["min"]
    unsup_max = stats["unsupported"]["max"]
    if sup_min is not None and unsup_max is not None:
        gap = sup_min - unsup_max
        if gap > 0:
            print(
                f"  ✅ Clean separation: supported min ({sup_min:.4f}) > "
                f"unsupported max ({unsup_max:.4f}), gap = +{gap:.4f}"
            )
            print(f"     Any threshold in ({unsup_max:.4f}, {sup_min:.4f}) is perfect.")
        else:
            print(
                f"  ⚠️  Overlap: supported min ({sup_min:.4f}) <= "
                f"unsupported max ({unsup_max:.4f}), gap = {gap:.4f}"
            )
    print()

    partial = result["partial"]
    if counts["partial"] > 0:
        print(f"  Partial claims ({counts['partial']} pairs, excluded from strict):")
        print(f"    Accepted: {partial['accepted']}, Rejected: {partial['rejected']}")
        print()

    print("  Per-pair details:")
    false_accept_pairs = [
        p for p in result["per_pair"] if p["support_label"] == "unsupported" and p["accepted"]
    ]
    false_reject_pairs = [
        p for p in result["per_pair"] if p["support_label"] == "supported" and not p["accepted"]
    ]
    if false_accept_pairs:
        print(f"    ❌ FALSE ACCEPTS ({len(false_accept_pairs)}):")
        for p in false_accept_pairs:
            print(f"       [{p['entailment_score']:.4f}] {p['claim_preview']}...")
    else:
        print("    ✅ No false accepts.")
    if false_reject_pairs:
        print(f"    ⚠️  FALSE REJECTS ({len(false_reject_pairs)}):")
        for p in false_reject_pairs:
            print(f"       [{p['entailment_score']:.4f}] {p['claim_preview']}...")
    else:
        print("    ✅ No false rejects.")

    # ── write report ─────────────────────────────────────────────────────

    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M")
    out_path = RUNTIME_DIR / f"eval_nli_real_distribution_{ts}.json"
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n  Full report: {out_path}")
    print()

    # ── verdict ──────────────────────────────────────────────────────────

    if strict["false_accepts"] == 0 and strict["false_rejects"] == 0:
        print(
            "  🎯 PERFECT SEPARATION — NLI gate at threshold "
            f"{threshold} achieves 0 false accepts and 0 false rejects "
            "on the real-answer distribution."
        )
    elif strict["false_accepts"] == 0:
        print(
            f"  ✅ No false accepts at threshold {threshold}. "
            f"{strict['false_rejects']} false reject(s) — "
            "safe, conservative gate."
        )
    else:
        print(
            f"  ⚠️  {strict['false_accepts']} false accept(s) at threshold "
            f"{threshold}. Gate needs tuning or additional stages."
        )


if __name__ == "__main__":
    main()
