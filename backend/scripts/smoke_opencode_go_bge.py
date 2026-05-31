"""OpenCode Go + BGE semantic grounding smoke test.

Tests the full RAG pipeline with:
- Real OpenCode Go LLM provider
- BGE semantic embeddings
- Semantic grounding gate at threshold 0.78

Usage:
    cd backend
    QIYAN_OPENCODE_GO_API_KEY=<your-key> \
    QIYAN_LLM_PROVIDER=opencode_go \
    QIYAN_EMBEDDING_BACKEND=bge \
    QIYAN_GROUNDING_SEMANTIC_THRESHOLD=0.78 \
    QIYAN_OPENCODE_GO_MAX_TOKENS=4000 \
    .venv/Scripts/python.exe scripts/smoke_opencode_go_bge.py

Note on max_tokens: deepseek-v4-flash runs in thinking mode and reserves a large
chunk of the completion budget for reasoning. The 1200 default silently produces
empty content (finish_reason=length) and degrades to deterministic fallback; use
>=4000 so the live opencode_go path actually engages. Forced tool_choice is also
unsupported by this model (HTTP 400), so grounding uses the structured-claims v3
path. See docs/evaluations/2026-05-31-opencode-go-bge-smoke.md.

Expected behavior:
- Makes real API call to OpenCode Go
- Uses BGE embeddings for semantic grounding
- Returns answer with grounding metadata
- May block answer if semantic scores are too low
"""

import os
import sys
from pathlib import Path

# Force UTF-8 stdout/stderr so the emoji + CJK output does not crash on a
# Windows GBK console (the default code page raises UnicodeEncodeError otherwise).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

# Add backend root to path
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from app.services.rag import answer_question


def main() -> None:
    print("=" * 80)
    print("OpenCode Go + BGE Semantic Grounding Smoke Test")
    print("=" * 80)
    print()

    # Check configuration
    llm_provider = os.getenv("QIYAN_LLM_PROVIDER", "deterministic")
    embedding_backend = os.getenv("QIYAN_EMBEDDING_BACKEND", "hashing")
    semantic_threshold = os.getenv("QIYAN_GROUNDING_SEMANTIC_THRESHOLD", "not set")
    api_key = os.getenv("QIYAN_OPENCODE_GO_API_KEY", "")

    print("Configuration:")
    print(f"  LLM Provider: {llm_provider}")
    print(f"  Embedding Backend: {embedding_backend}")
    print(f"  Semantic Threshold: {semantic_threshold}")
    print(f"  API Key: {'***' + api_key[-4:] if len(api_key) > 4 else 'NOT SET'}")
    print()

    # Validate configuration
    if llm_provider != "opencode_go":
        print("❌ ERROR: QIYAN_LLM_PROVIDER must be 'opencode_go'")
        print("   Set: QIYAN_LLM_PROVIDER=opencode_go")
        sys.exit(1)

    if not api_key:
        print("❌ ERROR: QIYAN_OPENCODE_GO_API_KEY is not set")
        print("   Set: QIYAN_OPENCODE_GO_API_KEY=<your-key>")
        sys.exit(1)

    if embedding_backend != "bge":
        print("⚠️  WARNING: QIYAN_EMBEDDING_BACKEND is not 'bge'")
        print(f"   Current: {embedding_backend}")
        print("   Recommended: QIYAN_EMBEDDING_BACKEND=bge")
        print()

    if semantic_threshold != "0.78" and embedding_backend == "bge":
        print("⚠️  WARNING: QIYAN_GROUNDING_SEMANTIC_THRESHOLD is not 0.78")
        print(f"   Current: {semantic_threshold}")
        print("   Recommended for BGE: QIYAN_GROUNDING_SEMANTIC_THRESHOLD=0.78")
        print()

    # Test questions
    questions = [
        "特应性皮炎和肠-脑-皮肤轴有什么关系？",
        "黄芩在治疗特应性皮炎中的作用机制是什么？",
        "中医药治疗特应性皮炎的临床证据有哪些？",
    ]

    print("Running smoke tests...")
    print("-" * 80)
    print()

    for i, question in enumerate(questions, 1):
        print(f"Test {i}/{len(questions)}: {question}")
        print()

        try:
            response = answer_question(question)

            # Print results
            print(f"✅ Provider: {response.provider_name}")
            print(f"✅ Answer length: {len(response.answer)} chars")
            print(f"✅ Citations: {len(response.citations)}")
            print(f"✅ Disclaimer: {'✓' if response.disclaimer else '✗'}")
            print()

            # Grounding metadata
            grounding = response.grounding
            print("Grounding:")
            print(f"  Status: {grounding.status}")
            print(f"  Policy: {grounding.policy}")
            print(f"  Checked: {grounding.checked}")
            print(f"  Tool: {grounding.tool_name} (calls={grounding.tool_call_count})")
            print(f"  Provider-native grounding: {grounding.provider_native_grounding}")
            print(f"  Claims: {grounding.claim_count}")
            print(f"  Cited Claims: {grounding.cited_claim_count}")

            if grounding.status == "blocked":
                print(f"  ⚠️  BLOCKED: {grounding.blocked_reason}")
                if grounding.unsupported_evidence_refs:
                    print(f"  Unsupported refs: {grounding.unsupported_evidence_refs}")

            # Semantic grounding details
            if grounding.semantic_threshold is not None:
                print()
                print("Semantic Grounding:")
                print(f"  Threshold: {grounding.semantic_threshold}")
                print(f"  Min Score: {grounding.min_semantic_score}")
                claim_scores = [
                    claim.semantic_score
                    for claim in grounding.structured_claims
                    if claim.semantic_score is not None
                ]
                if claim_scores:
                    print(f"  Max Score: {max(claim_scores):.3f}")
                    print(f"  Avg Score: {sum(claim_scores) / len(claim_scores):.3f}")
                for claim in grounding.structured_claims:
                    score = (
                        f"{claim.semantic_score:.3f}" if claim.semantic_score is not None else "n/a"
                    )
                    print(f"    [{score}] {claim.text[:80]}")

            # Token usage
            if response.input_tokens or response.output_tokens:
                print()
                print("Token Usage:")
                print(f"  Input: {response.input_tokens or 'N/A'}")
                print(f"  Output: {response.output_tokens or 'N/A'}")
                if response.input_tokens and response.output_tokens:
                    print(f"  Total: {response.input_tokens + response.output_tokens}")

            # Retrieval metadata
            print()
            print("Retrieval:")
            print(f"  Strategy: {response.retrieval.strategy}")
            print(f"  Source: {response.retrieval.applied_source}")
            print(f"  Top K: {response.retrieval.applied_top_k}")
            print(f"  Available citations: {response.retrieval.available_citation_count}")

            print()
            print("Answer Preview:")
            print(f"  {response.answer[:200]}...")
            print()

        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback

            traceback.print_exc()
            print()

        print("-" * 80)
        print()

    print("=" * 80)
    print("Smoke Test Complete")
    print("=" * 80)
    print()
    print("Next Steps:")
    print("1. Review grounding status (should be 'passed' or 'blocked')")
    print("2. Check semantic scores (should be > 0.78 for BGE)")
    print("3. Verify citations are relevant")
    print("4. Confirm disclaimer is present")
    print()
    print("If grounding status is 'blocked':")
    print("  - Review blocked claims and their scores")
    print("  - Check if threshold 0.78 is too strict")
    print("  - Consider expanding labeled fixture for validation")


if __name__ == "__main__":
    main()
