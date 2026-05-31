"""Simplified BGE evaluation - hashing baseline only.

Since BGE model download requires network access, this script runs the hashing
baseline evaluation and provides analysis based on existing test results.
"""

import sys
from pathlib import Path

backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from app.services.eval import run_grounding_semantic_separation
from app.schemas.eval import load_grounding_semantic_pairs

_SEMANTIC_PAIRS_PATH = backend_root / "data" / "evals" / "grounding_semantic_pairs.json"


def main() -> None:
    print("=" * 80)
    print("Semantic Grounding Separation Evaluation - Hashing Baseline")
    print("=" * 80)
    print()

    # Load the labeled pairs
    pairs = load_grounding_semantic_pairs(_SEMANTIC_PAIRS_PATH)
    faithful_count = sum(1 for p in pairs if p.supported)
    hallucinated_count = sum(1 for p in pairs if not p.supported)

    print(f"Dataset: {len(pairs)} labeled pairs")
    print(f"  - Faithful claims: {faithful_count}")
    print(f"  - Hallucinated claims: {hallucinated_count}")
    print()

    # Default threshold from config
    default_threshold = 0.40

    print("Running evaluation on HASHING backend (lexical overlap proxy)...")
    print("-" * 80)
    result = run_grounding_semantic_separation(
        threshold=default_threshold,
        backend_name="hashing"
    )

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
    print()

    print("=" * 80)
    print("ANALYSIS")
    print("=" * 80)

    false_rejects = result['false_rejected_faithful']
    false_accepts = result['false_accepted_hallucinated']

    print(f"\n[HASHING BACKEND PERFORMANCE]")
    print(f"  - Zero false rejects: {false_rejects == 0} (conservative, safe)")
    print(f"  - False accepts: {false_accepts}/{result['hallucinated_total']} (lexical overlap limitation)")
    print(f"  - Paired separation: {result['paired_separation']}/{result['paired_total']} (100% = perfect)")

    if result['min_faithful_score'] > result['max_hallucinated_score']:
        print(f"  - Score distributions: CLEAN SEPARATION (gap: {result['min_faithful_score'] - result['max_hallucinated_score']:.3f})")
    else:
        print(f"  - Score distributions: OVERLAP (min_faithful {result['min_faithful_score']:.3f} <= max_halluc {result['max_hallucinated_score']:.3f})")

    print(f"\n[BGE BACKEND EXPECTATIONS]")
    print(f"  Based on test suite comments and handoff documentation:")
    print(f"  - BGE uses true semantic embeddings (512-dim, BAAI/bge-small-zh-v1.5)")
    print(f"  - Expected: CLEANER separation than hashing (fewer false accepts)")
    print(f"  - Expected: Zero false rejects maintained (threshold 0.40 is conservative)")
    print(f"  - Expected: Higher score gap between faithful and hallucinated claims")

    print(f"\n[THRESHOLD RECOMMENDATION]")
    if false_rejects == 0 and false_accepts <= 3:
        print(f"  Current threshold 0.40 on hashing: ACCEPTABLE for conservative gate")
        print(f"  - Tolerates {false_accepts} high-lexical-overlap fabrications")
        print(f"  - Never blocks faithful claims (zero false rejects)")
        print(f"  For BGE backend:")
        print(f"    - Likely can TIGHTEN threshold (e.g., 0.50-0.60)")
        print(f"    - Should achieve near-zero false accepts with true semantics")
        print(f"    - Recommend running BGE eval when network available")
    else:
        print(f"  [WARNING] Unexpected hashing performance")
        print(f"  - False rejects: {false_rejects} (should be 0)")
        print(f"  - False accepts: {false_accepts} (should be <=3)")

    print()
    print("=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print()
    print("1. Run BGE evaluation when network/proxy is available:")
    print("   HTTPS_PROXY=http://172.26.0.1:7897 .venv/Scripts/python.exe scripts/eval_bge_separation.py")
    print()
    print("2. Compare BGE vs hashing false accept rates")
    print()
    print("3. If BGE achieves <3 false accepts, consider:")
    print("   - Tightening threshold to min_faithful_score")
    print("   - Updating QIYAN_GROUNDING_SEMANTIC_THRESHOLD in .env.example")
    print()
    print("4. Document findings in docs/handoffs/2026-05-31-bge-semantic-recalibration.md")


if __name__ == "__main__":
    main()
