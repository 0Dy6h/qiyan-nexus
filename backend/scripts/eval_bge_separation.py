"""BGE semantic grounding separation evaluation script.

Runs the grounding semantic separation eval on the BGE backend and compares
it against the hashing baseline. Outputs detailed metrics and score distributions
to inform threshold recalibration decisions.

Usage:
    cd backend
    .venv/bin/python scripts/eval_bge_separation.py

    # With proxy (if Hugging Face download fails):
    HF_ENDPOINT=https://hf-mirror.com .venv/bin/python scripts/eval_bge_separation.py
"""

import os
import sys
from pathlib import Path

# Set Hugging Face mirror if not already set (helps with China network)
if "HF_ENDPOINT" not in os.environ:
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

# Add backend root to path so we can import app modules
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from app.services.eval import run_grounding_semantic_separation
from app.schemas.eval import load_grounding_semantic_pairs

_SEMANTIC_PAIRS_PATH = backend_root / "data" / "evals" / "grounding_semantic_pairs.json"


def main() -> None:
    print("=" * 80)
    print("BGE Semantic Grounding Separation Evaluation")
    print("=" * 80)
    print()

    # Load the labeled pairs to show dataset info
    pairs = load_grounding_semantic_pairs(_SEMANTIC_PAIRS_PATH)
    faithful_count = sum(1 for p in pairs if p.supported)
    hallucinated_count = sum(1 for p in pairs if not p.supported)

    print(f"Dataset: {len(pairs)} labeled pairs")
    print(f"  - Faithful claims: {faithful_count}")
    print(f"  - Hallucinated claims: {hallucinated_count}")
    print()

    # Default threshold from config
    default_threshold = 0.40

    print("Running evaluation on HASHING backend (baseline)...")
    print("-" * 80)
    hashing_result = run_grounding_semantic_separation(
        threshold=default_threshold,
        backend_name="hashing"
    )
    print_result(hashing_result)
    print()

    print("Running evaluation on BGE backend (BAAI/bge-small-zh-v1.5)...")
    print("Note: First run will download ~95 MB model weights from Hugging Face")
    print("-" * 80)
    try:
        bge_result = run_grounding_semantic_separation(
            threshold=default_threshold,
            backend_name="bge"
        )
        print_result(bge_result)
        print()

        print("=" * 80)
        print("COMPARISON SUMMARY")
        print("=" * 80)
        print_comparison(hashing_result, bge_result)
        print()

        print("=" * 80)
        print("THRESHOLD RECOMMENDATION")
        print("=" * 80)
        print_threshold_recommendation(bge_result)

    except Exception as e:
        print(f"ERROR: Failed to run BGE evaluation: {e}")
        print()
        print("Possible causes:")
        print("  1. Network issue downloading model from Hugging Face")
        print("  2. Missing sentence-transformers dependency")
        print("  3. Insufficient disk space for model cache")
        print()
        print("Troubleshooting:")
        print("  - Check internet connection and proxy settings")
        print("  - Verify sentence-transformers is installed: pip list | grep sentence")
        print("  - Check disk space in ~/.cache/huggingface/")
        sys.exit(1)


def print_result(result: dict) -> None:
    """Print formatted evaluation result."""
    print(f"Backend: {result['backend_name']}")
    print(f"Threshold: {result['threshold']}")
    print()

    print("Confusion Matrix:")
    print(f"  Faithful claims (should PASS):")
    print(f"    [OK] Accepted: {result['accepted_faithful']}/{result['faithful_total']}")
    print(f"    [FAIL] False Rejected: {result['false_rejected_faithful']}/{result['faithful_total']}")
    print()
    print(f"  Hallucinated claims (should BLOCK):")
    print(f"    [OK] Rejected: {result['rejected_hallucinated']}/{result['hallucinated_total']}")
    print(f"    [FAIL] False Accepted: {result['false_accepted_hallucinated']}/{result['hallucinated_total']}")
    print()

    print("Score Distribution:")
    print(f"  Min faithful score: {result['min_faithful_score']:.3f}")
    print(f"  Max hallucinated score: {result['max_hallucinated_score']:.3f}")
    print(f"  Gap: {result['min_faithful_score'] - result['max_hallucinated_score']:.3f}")
    print()

    print("Paired Separation:")
    print(f"  {result['paired_separation']}/{result['paired_total']} pairs correctly separated")
    print(f"  ({result['paired_separation'] / result['paired_total'] * 100:.1f}%)")


def print_comparison(hashing: dict, bge: dict) -> None:
    """Print side-by-side comparison of hashing vs BGE."""
    print(f"{'Metric':<40} {'Hashing':<15} {'BGE':<15} {'Change'}")
    print("-" * 80)

    # False rejects (should be 0)
    print(f"{'False Rejected Faithful':<40} "
          f"{hashing['false_rejected_faithful']:<15} "
          f"{bge['false_rejected_faithful']:<15} "
          f"{format_delta(hashing['false_rejected_faithful'], bge['false_rejected_faithful'])}")

    # False accepts (should be minimized)
    print(f"{'False Accepted Hallucinated':<40} "
          f"{hashing['false_accepted_hallucinated']:<15} "
          f"{bge['false_accepted_hallucinated']:<15} "
          f"{format_delta(hashing['false_accepted_hallucinated'], bge['false_accepted_hallucinated'])}")

    # Paired separation (should be 100%)
    hashing_sep_pct = hashing['paired_separation'] / hashing['paired_total'] * 100
    bge_sep_pct = bge['paired_separation'] / bge['paired_total'] * 100
    print(f"{'Paired Separation %':<40} "
          f"{hashing_sep_pct:.1f}%{'':<10} "
          f"{bge_sep_pct:.1f}%{'':<10} "
          f"{format_delta_pct(hashing_sep_pct, bge_sep_pct)}")

    # Score gap
    hashing_gap = hashing['min_faithful_score'] - hashing['max_hallucinated_score']
    bge_gap = bge['min_faithful_score'] - bge['max_hallucinated_score']
    print(f"{'Score Gap (min_faithful - max_halluc)':<40} "
          f"{hashing_gap:.3f}{'':<10} "
          f"{bge_gap:.3f}{'':<10} "
          f"{format_delta_float(hashing_gap, bge_gap)}")


def print_threshold_recommendation(bge: dict) -> None:
    """Recommend threshold based on BGE score distribution."""
    min_faithful = bge['min_faithful_score']
    max_hallucinated = bge['max_hallucinated_score']
    current_threshold = bge['threshold']
    false_rejects = bge['false_rejected_faithful']
    false_accepts = bge['false_accepted_hallucinated']

    print(f"Current threshold: {current_threshold}")
    print(f"Min faithful score: {min_faithful:.3f}")
    print(f"Max hallucinated score: {max_hallucinated:.3f}")
    print()

    if false_rejects == 0 and false_accepts == 0:
        print("[PERFECT] PERFECT SEPARATION at current threshold!")
        print(f"  Recommendation: Keep threshold at {current_threshold}")
        print(f"  All faithful claims pass, all hallucinations blocked.")
    elif false_rejects == 0 and false_accepts > 0:
        if min_faithful > max_hallucinated:
            # Clean separation, can tighten threshold
            recommended = round((min_faithful + max_hallucinated) / 2, 2)
            print(f"[GOOD] Zero false rejects, but {false_accepts} false accepts remain.")
            print(f"  Score distributions do NOT overlap (gap: {min_faithful - max_hallucinated:.3f})")
            print(f"  Recommendation: Tighten threshold to {recommended:.2f}")
            print(f"  This will block all hallucinations while preserving all faithful claims.")
        else:
            # Overlap exists, need to balance
            print(f"[WARNING] Zero false rejects, but {false_accepts} false accepts remain.")
            print(f"  Score distributions OVERLAP (min_faithful {min_faithful:.3f} <= max_halluc {max_hallucinated:.3f})")
            print(f"  Recommendation: Keep threshold at {current_threshold} (conservative)")
            print(f"  OR accept some false rejects to reduce false accepts (requires domain judgment)")
    elif false_rejects > 0:
        print(f"[ERROR] BLOCKING FAITHFUL CLAIMS: {false_rejects} false rejects!")
        print(f"  Recommendation: LOWER threshold to {min_faithful:.2f} or below")
        print(f"  Current threshold is too strict for BGE backend.")
    else:
        print(f"[OK] Threshold {current_threshold} appears appropriate for BGE.")


def format_delta(old: int, new: int) -> str:
    """Format integer delta with color indicator."""
    delta = new - old
    if delta == 0:
        return "→"
    elif delta < 0:
        return f"↓ {abs(delta)} (better)"
    else:
        return f"↑ {delta} (worse)"


def format_delta_pct(old: float, new: float) -> str:
    """Format percentage delta."""
    delta = new - old
    if abs(delta) < 0.1:
        return "→"
    elif delta > 0:
        return f"↑ {delta:.1f}pp (better)"
    else:
        return f"↓ {abs(delta):.1f}pp (worse)"


def format_delta_float(old: float, new: float) -> str:
    """Format float delta."""
    delta = new - old
    if abs(delta) < 0.01:
        return "→"
    elif delta > 0:
        return f"↑ {delta:.3f} (better)"
    else:
        return f"↓ {abs(delta):.3f} (worse)"


if __name__ == "__main__":
    main()
