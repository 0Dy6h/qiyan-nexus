r"""capture_real_answer_claims.py — Slice 1: capture real LLM answer claims + cited chunk texts.

Captures structured claims from real `opencode_go` RAG answers alongside the full
text of each cited chunk, producing a JSON dump suitable for human labeling in Slice 2.

Two modes:
  LIVE   — with QIYAN_OPENCODE_GO_API_KEY set: runs a subset of eval questions through
           the real provider, captures claims + cited chunk texts.
  OFFLINE — no key: uses pre-recorded claim texts from the 2026-05-31 live smoke
           (docs/evaluations/2026-05-31-opencode-go-bge-smoke.md) and pairs them with
           deterministic-retrieved chunks for manual review.

Output: backend/data/runtime/captured_real_claims_<timestamp>.json (gitignored).

Usage (LIVE):
  cd backend
  QIYAN_OPENCODE_GO_API_KEY=<key> QIYAN_LLM_PROVIDER=opencode_go \
  QIYAN_EMBEDDING_BACKEND=bge QIYAN_GROUNDING_SEMANTIC_THRESHOLD=0.78 \
  QIYAN_OPENCODE_GO_MAX_TOKENS=4000 \
  ./.uv-test-venv/Scripts/python.exe scripts/capture_real_answer_claims.py

Usage (OFFLINE — no key required):
  cd backend
  ./.uv-test-venv/Scripts/python.exe scripts/capture_real_answer_claims.py
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

from app.repositories.chunk import InMemoryChunkRepository  # noqa: E402
from app.repositories.runtime_storage import resolve_chunk_storage_path  # noqa: E402
from app.services.rag import answer_question  # noqa: E402

# ── constants ────────────────────────────────────────────────────────────────

EVAL_QUESTIONS_PATH = BACKEND_ROOT / "data" / "evals" / "rag_ad_eval_questions.json"
RUNTIME_DIR = BACKEND_ROOT / "data" / "runtime"

# Number of eval questions to sample in LIVE mode (keep small for cost).
LIVE_QUESTION_LIMIT = 10

# ── offline fallback: claims from 2026-05-31 live smoke ──────────────────────

# These 7 claims are lifted verbatim from the 2026-05-31 live smoke evaluation
# (docs/evaluations/2026-05-31-opencode-go-bge-smoke.md). They were produced by
# opencode_go (deepseek-v4-flash) at max_tokens=4000 with BGE threshold 0.78.
# Scores are the BGE cosine similarity of claim text vs. its cited chunk text.
SMOKE_QUESTIONS: list[dict] = [
    {
        "question": "特应性皮炎和肠-脑-皮肤轴之间有什么关系？",
        "source_preference": "all",
        "claims": [
            {
                "text": (
                    "特应性皮炎与肠-脑-皮肤轴密切相关，"
                    "该轴失调表现为肠道微生态失衡、皮肤屏障异常和神经免疫调节紊乱。"
                ),
                "semantic_score": 0.716,
            },
            {
                "text": (
                    "肠道菌群失衡，尤其是双歧杆菌、乳酸杆菌减少，"
                    "与特应性皮炎发病相关，菌群干预可能有助于恢复免疫稳态。"
                ),
                "semantic_score": 0.782,
            },
            {
                "text": (
                    "脾虚湿蕴、血虚风燥等中医证候与肠-脑-皮肤轴环节失调存在可解释关联，"
                    "为特应性皮炎治疗提供靶点。"
                ),
                "semantic_score": 0.881,
            },
        ],
    },
    {
        "question": "黄芩在治疗特应性皮炎中的作用机制是什么？",
        "source_preference": "all",
        "claims": [
            {
                "text": (
                    "中医药干预特应性皮炎瘙痒的机制涉及调节IL-31、神经肽等介质，"
                    "以及瘙痒-搔抓循环的恶性环路。"
                ),
                "semantic_score": 0.700,
            },
            {
                "text": (
                    "网络药理学分析提示特应性皮炎常用方剂的作用机制"
                    "常涉及PI3K-Akt、NF-kB、JAK-STAT等关键信号通路。"
                ),
                "semantic_score": 0.727,
            },
        ],
    },
    {
        "question": "中医药治疗特应性皮炎的临床证据有哪些？",
        "source_preference": "all",
        "claims": [
            {
                "text": (
                    "中西医结合诊疗共识将皮肤屏障维护、规律外用润肤剂、"
                    "辨证施治与长期管理列为特应性皮炎的核心管理要点。"
                ),
                "semantic_score": 0.920,
            },
            {
                "text": (
                    "特应性皮炎中医证候研究强调脾虚湿蕴、血虚风燥等证候"
                    "与皮肤屏障及神经免疫调节之间的联系。"
                ),
                "semantic_score": 0.591,
            },
        ],
    },
]


# ── helpers ──────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _load_chunk_repo() -> InMemoryChunkRepository:
    chunk_path = resolve_chunk_storage_path()
    if not chunk_path.exists():
        print(f"❌ Chunk data not found at {chunk_path}", file=sys.stderr)
        sys.exit(1)
    return InMemoryChunkRepository(chunk_path)


def _build_capture_meta(source: str, question_count: int, claim_count: int) -> dict:
    return {
        "source": source,
        "captured_at": _now_iso(),
        "llm_provider": os.getenv("QIYAN_LLM_PROVIDER", "deterministic"),
        "embedding_backend": os.getenv("QIYAN_EMBEDDING_BACKEND", "hashing"),
        "semantic_threshold": os.getenv("QIYAN_GROUNDING_SEMANTIC_THRESHOLD", "not_set"),
        "max_tokens": os.getenv("QIYAN_OPENCODE_GO_MAX_TOKENS", "not_set"),
        "questions_captured": question_count,
        "total_claims": claim_count,
    }


def _enrich_claim(claim: dict, chunk_repo: InMemoryChunkRepository) -> dict:
    """Attach full cited-chunk text to a claim dict (mutates in place, returns it)."""
    cited_chunks: list[dict] = []
    for ref in claim.get("evidence_refs", []):
        chunk = chunk_repo.get_chunk_by_id(ref)
        cited_chunks.append({
            "chunk_id": ref,
            "text": chunk.text if chunk else "CHUNK_NOT_FOUND",
            "literature_id": chunk.literature_id if chunk else None,
            "section": chunk.section if chunk else None,
        })
    claim["cited_chunks"] = cited_chunks
    return claim


# ── LIVE mode ────────────────────────────────────────────────────────────────

def run_live_capture(chunk_repo: InMemoryChunkRepository) -> Path:
    """Run RAG with opencode_go on a subset of eval questions, capture claims."""
    api_key = os.getenv("QIYAN_OPENCODE_GO_API_KEY", "")
    if not api_key:
        print("❌ LIVE mode requires QIYAN_OPENCODE_GO_API_KEY", file=sys.stderr)
        sys.exit(1)

    questions_raw = json.loads(EVAL_QUESTIONS_PATH.read_text(encoding="utf-8"))
    sample = questions_raw[:LIVE_QUESTION_LIMIT]

    results: list[dict] = []
    total_claims = 0

    for i, q in enumerate(sample, 1):
        print(f"[{i}/{len(sample)}] {q['question'][:60]}...", flush=True)
        try:
            resp = answer_question(
                q["question"],
                source=q.get("source_preference", "all"),
            )
        except Exception as exc:
            print(f"  ⚠️  Error: {exc}", flush=True)
            continue

        claims = resp.grounding.structured_claims
        claim_entries = []
        for claim in claims:
            entry = {
                "text": claim.text,
                "evidence_refs": claim.evidence_refs,
                "semantic_score": claim.semantic_score,
                "entailment_score": claim.entailment_score,
            }
            _enrich_claim(entry, chunk_repo)
            claim_entries.append(entry)
            total_claims += 1

        results.append({
            "question_id": q.get("id", f"live-{i}"),
            "question": q["question"],
            "source_preference": q.get("source_preference", "all"),
            "provider_name": resp.provider_name,
            "grounding_status": resp.grounding.status,
            "blocked_reason": resp.grounding.blocked_reason,
            "answer": resp.answer,
            "citations": [
                {"literature_id": c.literature_id, "chunk_id": c.chunk_id, "title": c.title}
                for c in resp.citations
            ],
            "claims": claim_entries,
        })
        print(f"  ✓ {len(claim_entries)} claims, status={resp.grounding.status}", flush=True)

    meta = _build_capture_meta("live_opencode_go", len(results), total_claims)
    return _write_output(meta, results, "live")


# ── OFFLINE mode ─────────────────────────────────────────────────────────────

def run_offline_capture(chunk_repo: InMemoryChunkRepository) -> Path:
    """Use deterministic RAG on smoke questions + pre-recorded claim texts."""
    print("🔹 OFFLINE mode: using pre-recorded 2026-05-31 smoke claims", flush=True)
    print("   Run deterministic RAG to get citation chunks for pairing.", flush=True)

    results: list[dict] = []
    total_claims = 0

    for entry in SMOKE_QUESTIONS:
        question = entry["question"]
        print(f"  Q: {question[:60]}...", flush=True)

        # Get deterministic citations for this question
        try:
            resp = answer_question(question, source=entry.get("source_preference", "all"))
        except Exception as exc:
            print(f"  ⚠️  Error: {exc}", flush=True)
            continue

        # Build a lookup of chunk_id → chunk text from deterministic retrieval
        chunk_lookup: dict[str, dict] = {}
        for citation in resp.citations:
            if citation.chunk_id:
                chunk = chunk_repo.get_chunk_by_id(citation.chunk_id)
                if chunk:
                    chunk_lookup[citation.chunk_id] = {
                        "chunk_id": citation.chunk_id,
                        "text": chunk.text,
                        "literature_id": chunk.literature_id,
                        "section": chunk.section,
                    }

        claim_entries = []
        for claim_data in entry["claims"]:
            # Pair each smoke claim with ALL deterministic chunks for manual review
            claim_entry = {
                "text": claim_data["text"],
                "semantic_score": claim_data["semantic_score"],
                "entailment_score": None,
                "evidence_refs": [],  # deterministic provider, no structured claims
                # Show all available chunks so the human labeler (Slice 2)
                # can pick the best-matching premise for each claim.
                "all_candidate_chunks": list(chunk_lookup.values()),
            }
            claim_entries.append(claim_entry)
            total_claims += 1

        results.append({
            "question_id": "smoke-2026-05-31",
            "question": question,
            "source_preference": entry.get("source_preference", "all"),
            "provider_name": resp.provider_name,
            "grounding_status": resp.grounding.status,
            "blocked_reason": resp.grounding.blocked_reason,
            "answer": resp.answer,
            "citations": [
                {"literature_id": c.literature_id, "chunk_id": c.chunk_id, "title": c.title}
                for c in resp.citations
            ],
            "claims": claim_entries,
        })
        print(f"    ✓ {len(claim_entries)} claims, {len(chunk_lookup)} candidate chunks", flush=True)

    meta = _build_capture_meta("offline_smoke_2026-05-31", len(results), total_claims)
    return _write_output(meta, results, "offline")


# ── output ───────────────────────────────────────────────────────────────────

def _write_output(meta: dict, results: list[dict], mode: str) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    out_path = RUNTIME_DIR / f"captured_real_claims_{mode}_{ts}.json"

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"capture_meta": meta, "questions": results}
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"\n✅ Captured {meta['total_claims']} claims from {meta['questions_captured']} questions",
          flush=True)
    print(f"   Output: {out_path}", flush=True)
    return out_path


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("  Capture Real Answer Claims — Slice 1")
    print("=" * 70)
    print()

    chunk_repo = _load_chunk_repo()

    api_key = os.getenv("QIYAN_OPENCODE_GO_API_KEY", "")
    llm_provider = os.getenv("QIYAN_LLM_PROVIDER", "deterministic")

    if api_key and llm_provider == "opencode_go":
        print("🔹 LIVE mode: opencode_go provider detected", flush=True)
        print(f"   Will capture up to {LIVE_QUESTION_LIMIT} eval questions.", flush=True)
        print()
        run_live_capture(chunk_repo)
    else:
        if api_key:
            print("⚠️  API key set but QIYAN_LLM_PROVIDER != opencode_go", flush=True)
            print(f"   Current: {llm_provider} — falling back to offline mode.", flush=True)
        else:
            print("🔹 No API key — offline mode (pre-recorded smoke claims)", flush=True)
        print()
        run_offline_capture(chunk_repo)

    print()
    print("Next step (Slice 2): review the output JSON and annotate each claim")
    print("  with support_label ∈ {supported, partial, unsupported}.")
    print("  Commit the annotated version to backend/data/evals/grounding_real_answer_pairs.json")


if __name__ == "__main__":
    main()
