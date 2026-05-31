"""SPIKE (throwaway): does NLI entailment separate faithful claims from on-topic
hard negatives where BGE cosine failed?

Hypothesis: cosine similarity cannot tell a faithful paraphrase from an on-topic
fabrication (both are topically similar to the cited chunk). An NLI model scores
*entailment* (premise=chunk entails hypothesis=claim?), which should give faithful
claims high entailment / low contradiction and hard negatives low entailment /
higher contradiction.

Scores the same 14-pair fixture used in
docs/evaluations/2026-06-01-threshold-recalibration.md so the result is directly
comparable to the cosine sweep. NOT wired into the app; this only validates the
go/no-go before implementing a real gate stage.

Run (PowerShell, from backend; proxy only needed for the first download)::

    $env:HTTPS_PROXY = "http://172.26.0.1:7897"
    & .uv-test-venv/Scripts/python.exe scripts/spike_nli_grounding.py
"""

from __future__ import annotations

import sys
from pathlib import Path

backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from app.schemas.eval import load_grounding_semantic_pairs  # noqa: E402
from app.services.eval import SEMANTIC_PAIRS_BGE_PATH  # noqa: E402

_MODEL = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(_MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(_MODEL)
    model.eval()
    # label order for this model: 0=entailment, 1=neutral, 2=contradiction
    id2label = model.config.id2label

    pairs = load_grounding_semantic_pairs(SEMANTIC_PAIRS_BGE_PATH)

    def nli(premise: str, hypothesis: str) -> dict[str, float]:
        inputs = tok(premise, hypothesis, truncation=True, return_tensors="pt", max_length=256)
        with torch.no_grad():
            logits = model(**inputs).logits[0]
        probs = torch.softmax(logits, dim=-1).tolist()
        return {id2label[i].lower(): round(p, 4) for i, p in enumerate(probs)}

    rows = []
    for p in pairs:
        scores = nli(p.chunk_text, p.claim)
        ent = scores.get("entailment", 0.0)
        con = scores.get("contradiction", 0.0)
        rows.append((p.id, p.supported, ent, con, ent - con))

    faithful = [r for r in rows if r[1]]
    hard_neg = [r for r in rows if not r[1]]

    print("=" * 84)
    print(f"NLI spike on {SEMANTIC_PAIRS_BGE_PATH.name} ({len(pairs)} pairs) — model {_MODEL}")
    print("premise = cited chunk, hypothesis = claim; labels: entail / neutral / contradict")
    print("=" * 84)

    def dump(title: str, data: list[tuple[str, bool, float, float, float]]) -> None:
        print(f"\n{title} (sorted by entailment):")
        print(f"  {'entail':>7} {'contra':>7} {'e-c':>7}  id")
        for pid, _, ent, con, diff in sorted(data, key=lambda r: r[2]):
            print(f"  {ent:>7.4f} {con:>7.4f} {diff:>+7.4f}  {pid}")

    dump("FAITHFUL (want HIGH entail / LOW contra)", faithful)
    dump("HARD NEGATIVE (want LOW entail / HIGH contra)", hard_neg)

    min_f_ent = min(r[2] for r in faithful)
    max_h_ent = max(r[2] for r in hard_neg)
    print("\n" + "-" * 84)
    print(f"min faithful entailment = {min_f_ent:.4f}")
    print(f"max hard-neg  entailment = {max_h_ent:.4f}")
    print(f"ENTAILMENT GAP (min_faithful - max_hardneg) = {min_f_ent - max_h_ent:+.4f}")

    print("\nEntailment-threshold sweep (faithful must PASS = entail>=t; hardneg must BLOCK):")
    print(
        f"  {'thr':>5} | {'faith_pass':>10} | {'hardneg_block':>13} | {'false_rej':>9} | {'false_acc':>9}"
    )
    for t in [0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90]:
        fp = sum(1 for r in faithful if r[2] >= t)
        hb = sum(1 for r in hard_neg if r[2] < t)
        fr = len(faithful) - fp
        fa = len(hard_neg) - hb
        print(
            f"  {t:>5.2f} | {fp:>4}/{len(faithful):<5} | {hb:>5}/{len(hard_neg):<7} | {fr:>9} | {fa:>9}"
        )


if __name__ == "__main__":
    main()
