"""Measure NLI gate latency for the §4b SLI baseline.

Times the cold model load and warm per-claim entailment forward passes on the
configured NLI backend, so the per-answer cost of enabling the gate is a measured
number, not a guess. CPU torch in this environment; numbers will differ on GPU.

Run (PowerShell, from backend)::

    $env:HF_HUB_OFFLINE = "1"
    & .uv-test-venv/Scripts/python.exe scripts/bench_nli_latency.py
"""

from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from app.schemas.eval import load_grounding_semantic_pairs  # noqa: E402
from app.services.eval import SEMANTIC_PAIRS_BGE_PATH  # noqa: E402
from app.services.nli import select_nli_backend  # noqa: E402

_WARMUP = 2
_TYPICAL_CLAIMS_PER_ANSWER = 3  # live smoke produced 2-3 structured claims per answer


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * pct
    lo = int(k)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

    backend = select_nli_backend("transformers")
    assert backend is not None

    pairs = load_grounding_semantic_pairs(SEMANTIC_PAIRS_BGE_PATH)

    print("=" * 72)
    print(f"NLI latency benchmark — backend {backend.name}")
    print(f"pairs: {len(pairs)}; warmup: {_WARMUP}")
    print("=" * 72)

    # Cold load: first entailment call triggers lazy model load.
    first = pairs[0]
    t0 = time.perf_counter()
    backend.entailment(first.chunk_text, first.claim)
    cold_ms = (time.perf_counter() - t0) * 1000
    print(f"\nCold first-call (includes model load): {cold_ms:.0f} ms")

    # Warmup to stabilise CPU/threadpool.
    for p in pairs[:_WARMUP]:
        backend.entailment(p.chunk_text, p.claim)

    per_claim_ms: list[float] = []
    for p in pairs:
        t = time.perf_counter()
        backend.entailment(p.chunk_text, p.claim)
        per_claim_ms.append((time.perf_counter() - t) * 1000)

    mean = statistics.mean(per_claim_ms)
    p50 = _percentile(per_claim_ms, 0.50)
    p95 = _percentile(per_claim_ms, 0.95)
    mx = max(per_claim_ms)

    print("\nWarm per-claim entailment forward pass:")
    print(f"  mean = {mean:.1f} ms")
    print(f"  p50  = {p50:.1f} ms")
    print(f"  p95  = {p95:.1f} ms")
    print(f"  max  = {mx:.1f} ms")

    print(f"\nPer-answer added latency (x{_TYPICAL_CLAIMS_PER_ANSWER} claims, sequential):")
    print(f"  p50  ≈ {p50 * _TYPICAL_CLAIMS_PER_ANSWER:.0f} ms")
    print(f"  p95  ≈ {p95 * _TYPICAL_CLAIMS_PER_ANSWER:.0f} ms")
    print("\nNote: cold load is paid once per process; subsequent answers pay only warm cost.")


if __name__ == "__main__":
    main()
