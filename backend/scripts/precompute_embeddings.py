"""precompute_embeddings.py — 为文献和chunk预计算embedding向量（bge-m3）

为 sample_ad_literature.json + sample_ad_chunks.json 生成 embedding，
存成 .npz 供未来 MVP-B 直接加载（当前 MVP-A 用 keyword 匹配，此脚本为未来攒数据）。

输出：
  backend/data/runtime/embeddings/literature_bge-m3.npz  — 文献 embedding
  backend/data/runtime/embeddings/chunks_bge-m3.npz      — chunk embedding
  backend/data/runtime/embeddings/metadata.json          — ID映射表

Usage（需GPU）：
  cd backend
  python scripts/precompute_embeddings.py --model BAAI/bge-m3 --device cuda:0

Usage（CPU fallback）：
  cd backend
  python scripts/precompute_embeddings.py --model BAAI/bge-m3 --device cpu --batch-size 4
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

LIT_PATH = BACKEND_ROOT / "data" / "literature" / "sample_ad_literature.json"
CHUNKS_PATH = BACKEND_ROOT / "data" / "literature" / "sample_ad_chunks.json"
OUTPUT_DIR = BACKEND_ROOT / "data" / "runtime" / "embeddings"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="BAAI/bge-m3", help="HuggingFace model ID")
    parser.add_argument("--device", default="cuda:0", help="cuda:0 / cpu")
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[1/5] 加载模型 {args.model} (device={args.device})...")
    model = SentenceTransformer(args.model, device=args.device)

    print("[2/5] 读取文献...")
    literature = json.loads(LIT_PATH.read_text(encoding="utf-8"))
    lit_texts = [
        f"{lit['title']} {lit.get('abstract', '')} {lit.get('snippet', '')}" for lit in literature
    ]
    lit_ids = [lit["id"] for lit in literature]
    print(f"  文献数: {len(literature)}")

    print("[3/5] 读取chunks...")
    chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    chunk_texts = [c["text"] for c in chunks]
    chunk_ids = [c["chunk_id"] for c in chunks]
    print(f"  Chunk数: {len(chunks)}")

    print(f"[4/5] 计算embedding (batch_size={args.batch_size})...")
    lit_embeddings = model.encode(
        lit_texts, batch_size=args.batch_size, show_progress_bar=True, normalize_embeddings=True
    )
    chunk_embeddings = model.encode(
        chunk_texts, batch_size=args.batch_size, show_progress_bar=True, normalize_embeddings=True
    )

    print("[5/5] 保存...")
    model_slug = args.model.replace("/", "_")
    lit_path = OUTPUT_DIR / f"literature_{model_slug}.npz"
    chunks_path = OUTPUT_DIR / f"chunks_{model_slug}.npz"
    meta_path = OUTPUT_DIR / "metadata.json"

    np.savez_compressed(lit_path, embeddings=lit_embeddings, ids=np.array(lit_ids))
    np.savez_compressed(chunks_path, embeddings=chunk_embeddings, ids=np.array(chunk_ids))

    metadata = {
        "model": args.model,
        "device": args.device,
        "created_at": datetime.now(timezone.utc).isoformat(),  # noqa: UP017 (Python 3.10 compat)
        "literature_count": len(lit_ids),
        "chunk_count": len(chunk_ids),
        "embedding_dim": lit_embeddings.shape[1],
        "files": {
            "literature": str(lit_path.name),
            "chunks": str(chunks_path.name),
        },
    }
    meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n✅ 完成！输出目录: {OUTPUT_DIR}")
    print(f"  文献: {lit_path.name} ({lit_embeddings.shape})")
    print(f"  Chunks: {chunks_path.name} ({chunk_embeddings.shape})")
    print(f"  元数据: {meta_path.name}")


if __name__ == "__main__":
    main()
