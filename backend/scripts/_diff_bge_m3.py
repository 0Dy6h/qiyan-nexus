"""One-shot diff helper for sub-slice ③ writeup. Not part of the suite."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
keyword = json.loads(
    (ROOT / "docs/evaluations/keyword_baseline_eval_data.json").read_text(encoding="utf-8")
)[0]
bge_data = json.loads(
    (ROOT / "docs/evaluations/bge_m3_eval_data.json").read_text(encoding="utf-8")
)
vec_bge = bge_data[0]
hyb_bge = bge_data[1]

print("Per-item cross_lingual_recall comparison:")
print(f"{'id':<14} {'keyword':>8} {'vec_bge':>8} {'hyb_bge':>8}")
for k, v, h in zip(keyword["items"], vec_bge["items"], hyb_bge["items"], strict=True):
    assert k["id"] == v["id"] == h["id"]
    print(
        f"{k['id']:<14} {k['cross_lingual_recall']:>8.3f} "
        f"{v['cross_lingual_recall']:>8.3f} {h['cross_lingual_recall']:>8.3f}"
    )

print("\nDiffs hybrid_bge_m3 vs keyword:")
for k, h in zip(keyword["items"], hyb_bge["items"], strict=True):
    if k["cross_lingual_recall"] != h["cross_lingual_recall"]:
        print(f"  {k['id']}: keyword={k['cross_lingual_recall']:.3f}, hybrid={h['cross_lingual_recall']:.3f}")
        print(f"    keyword:    {k['retrieved_ids']}")
        print(f"    hybrid_bge: {h['retrieved_ids']}")
