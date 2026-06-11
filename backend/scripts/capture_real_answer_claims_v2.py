"""capture_real_answer_claims_v2.py — T2 F5 fixture 采样（多温度+增量NDJSON+去重）

扩展 Slice 1 的 capture_real_answer_claims.py，支持：
- 多轮多温度采样（每题 × N轮 × M温度 = N×M个answer）
- 增量NDJSON写入（断点续跑）
- claim去重（dedup_key hash）
- 强制关闭NLI gate（让fabrication进数据）
- 失败重试

Usage:
  cd backend
  QIYAN_OPENCODE_GO_API_KEY=<key> python scripts/capture_real_answer_claims_v2.py \\
    --target-count 600 \\
    --max-questions 50 \\
    --rounds 3 \\
    --temperatures 0.0,0.5,0.9 \\
    --output-dir data/runtime/f5 \\
    --resume

按 论文产出/07-T2-F5-fixture-implementation-plan.md 设计。
"""

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

# app.core.config reads os.environ directly and does NOT auto-load .env, so the
# OpenCode Go provider would silently fall back to deterministic (0 claims)
# without this. override=True so .env wins over any stale key exported in the
# shell (e.g. a previous gateway's key). Load before any get_settings() call.
from dotenv import load_dotenv  # noqa: E402

load_dotenv(BACKEND_ROOT / ".env", override=True)

from app.core.config import get_settings  # noqa: E402
from app.repositories.chunk import InMemoryChunkRepository  # noqa: E402
from app.repositories.runtime_storage import resolve_chunk_storage_path  # noqa: E402
from app.services.rag import answer_question  # noqa: E402

EVAL_PATH = BACKEND_ROOT / "data" / "evals" / "rag_ad_eval_questions.json"


def claim_hash(question_id: str, claim_text: str) -> str:
    return hashlib.sha256(f"{question_id}|||{claim_text}".encode()).hexdigest()[:16]


def setup_env_for_capture():
    """关闭NLI gate，cosine阈值设0（不阻断）"""
    os.environ["QIYAN_NLI_BACKEND"] = ""
    os.environ["QIYAN_NLI_THRESHOLD"] = "0"
    os.environ["QIYAN_GROUNDING_SEMANTIC_THRESHOLD"] = "0"
    get_settings.cache_clear()


def load_resume_state(output_file: Path) -> set[tuple[str, int, float]]:
    """读已有NDJSON，返回 (question_id, round_idx, temp) 集合"""
    if not output_file.exists():
        return set()
    seen = set()
    with output_file.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            entry = json.loads(line)
            seen.add((entry["question_id"], entry["round_idx"], entry["temperature"]))
    return seen


def capture_one_question(
    question: dict, round_idx: int, temp: float, chunk_repo, max_retries: int
) -> list[dict]:
    """单题采样，返回claim列表"""
    for attempt in range(max_retries + 1):
        try:
            resp = answer_question(
                question=question["question"],
                source=question.get("source_preference", "all"),
            )
            claims = []
            for idx, claim in enumerate(resp.grounding.structured_claims):
                cited_chunks = [
                    {
                        "chunk_id": ref,
                        "text": chunk_repo.get_chunk_by_id(ref).text
                        if chunk_repo.get_chunk_by_id(ref)
                        else "",
                    }
                    for ref in claim.evidence_refs
                ]
                claims.append(
                    {
                        "dedup_key": claim_hash(question["id"], claim.text),
                        "captured_at": datetime.now(UTC).isoformat(),
                        "question_id": question["id"],
                        "question": question["question"],
                        "source_preference": question.get("source_preference", "all"),
                        "round_idx": round_idx,
                        "temperature": temp,
                        "provider_name": resp.provider_name,
                        "claim_text": claim.text,
                        "claim_evidence_refs": claim.evidence_refs,
                        "claim_index_in_answer": idx,
                        "claim_count_in_answer": len(resp.grounding.structured_claims),
                        "cosine_score": getattr(claim, "semantic_score", None),
                        "answer_provider_latency_ms": resp.sli.provider_latency_ms
                        if resp.sli
                        else None,
                        "answer_input_tokens": resp.input_tokens,
                        "answer_output_tokens": resp.output_tokens,
                        "cited_chunks": cited_chunks,
                        "annotation_TODO": {
                            "support_label": None,
                            "label_note": None,
                            "failure_mode": None,
                            "annotator_id": None,
                            "annotated_at": None,
                        },
                    }
                )
            return claims
        except Exception as e:
            if attempt < max_retries:
                print(f"  ⚠️  重试 {attempt + 1}/{max_retries}: {e}")
                time.sleep(5)
            else:
                print(f"  ❌ 失败 (max retries): {e}")
                return []
    return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-count", type=int, default=600, help="目标claim数（去重前）")
    parser.add_argument("--max-questions", type=int, default=50, help="最多用几题")
    parser.add_argument("--rounds", type=int, default=3, help="每题跑几轮")
    parser.add_argument("--temperatures", default="0.0,0.5,0.9", help="逗号分隔温度列表")
    parser.add_argument("--output-dir", default="data/runtime/f5", help="输出目录")
    parser.add_argument("--resume", action="store_true", help="断点续跑")
    parser.add_argument("--max-retries", type=int, default=2, help="每次LLM调用重试次数")
    args = parser.parse_args()

    temps = [float(t) for t in args.temperatures.split(",")]
    output_dir = BACKEND_ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "captured_claims.ndjson"

    setup_env_for_capture()

    questions = json.loads(EVAL_PATH.read_text(encoding="utf-8"))[: args.max_questions]
    chunk_repo = InMemoryChunkRepository(resolve_chunk_storage_path())

    seen = load_resume_state(output_file) if args.resume else set()
    total_claims = 0

    print(f"📝 采样配置: {args.max_questions}题 × {args.rounds}轮 × {len(temps)}温度")
    print(f"   输出: {output_file}")
    if args.resume:
        print(f"   续跑: 已跳过 {len(seen)} 个 (question, round, temp)")

    with output_file.open("a", encoding="utf-8") as f:
        for round_idx in range(args.rounds):
            temp = temps[round_idx % len(temps)]
            os.environ["QIYAN_OPENCODE_GO_TEMPERATURE"] = str(temp)
            get_settings.cache_clear()

            print(f"\n🔁 Round {round_idx + 1}/{args.rounds} (temp={temp})")

            for q in questions:
                if (q["id"], round_idx, temp) in seen:
                    continue

                print(f"  [{q['id']}] ", end="", flush=True)
                claims = capture_one_question(q, round_idx, temp, chunk_repo, args.max_retries)

                for claim in claims:
                    f.write(json.dumps(claim, ensure_ascii=False) + "\n")
                    f.flush()
                    total_claims += 1

                print(f"{len(claims)} claims (总计 {total_claims})")

                if total_claims >= args.target_count:
                    print(f"\n✅ 达到目标 {args.target_count} claims，停止")
                    return

    print(f"\n✅ 采样完成！共 {total_claims} claims → {output_file}")


if __name__ == "__main__":
    main()
