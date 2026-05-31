# OpenCode Go + BGE Smoke Test Guide

**Date**: 2026-05-31  
**Purpose**: Validate real LLM integration with BGE semantic grounding  
**Status**: Ready to run (requires API key)

---

## Prerequisites

1. **OpenCode Go API Key**
   - Obtain from: https://opencode.ai/
   - Required for making real LLM calls

2. **BGE Model Downloaded**
   - Already cached at: `~/.cache/huggingface/hub/models--BAAI--bge-small-zh-v1.5/`
   - Downloaded during BGE evaluation (2026-05-31)

3. **Backend Environment**
   - Python 3.11+
   - All dependencies installed: `.venv/Scripts/python.exe -m pip install -e ".[dev]"`

---

## Quick Start

### Option 1: Using Environment Variables (Recommended)

```bash
cd backend

# Set configuration
export QIYAN_LLM_PROVIDER=opencode_go
export QIYAN_OPENCODE_GO_API_KEY=<your-api-key>
export QIYAN_EMBEDDING_BACKEND=bge
export QIYAN_GROUNDING_SEMANTIC_THRESHOLD=0.78

# Run smoke test
.venv/Scripts/python.exe scripts/smoke_opencode_go_bge.py
```

### Option 2: Using .env File

```bash
cd backend

# Create .env file (not committed to git)
cat > .env << EOF
QIYAN_LLM_PROVIDER=opencode_go
QIYAN_OPENCODE_GO_API_KEY=<your-api-key>
QIYAN_EMBEDDING_BACKEND=bge
QIYAN_GROUNDING_SEMANTIC_THRESHOLD=0.78
EOF

# Run smoke test
.venv/Scripts/python.exe scripts/smoke_opencode_go_bge.py
```

### Option 3: One-liner (Windows PowerShell)

```powershell
cd backend
$env:QIYAN_LLM_PROVIDER="opencode_go"; $env:QIYAN_OPENCODE_GO_API_KEY="<your-key>"; $env:QIYAN_EMBEDDING_BACKEND="bge"; $env:QIYAN_GROUNDING_SEMANTIC_THRESHOLD="0.78"; .\.venv\Scripts\python.exe scripts\smoke_opencode_go_bge.py
```

---

## What the Smoke Test Does

The script (`backend/scripts/smoke_opencode_go_bge.py`) runs 3 test questions through the full RAG pipeline:

1. **Question 1**: "特应性皮炎和肠-脑-皮肤轴有什么关系？"
2. **Question 2**: "黄芩在治疗特应性皮炎中的作用机制是什么？"
3. **Question 3**: "中医药治疗特应性皮炎的临床证据有哪些？"

For each question, it:
- ✅ Retrieves relevant citations from the knowledge base
- ✅ Calls OpenCode Go API to generate an answer
- ✅ Uses BGE embeddings to compute semantic similarity
- ✅ Applies grounding gate at threshold 0.78
- ✅ Reports grounding status (passed/blocked)
- ✅ Shows token usage and semantic scores

---

## Expected Output

### Successful Run (Grounding Passed)

```
================================================================================
OpenCode Go + BGE Semantic Grounding Smoke Test
================================================================================

Configuration:
  LLM Provider: opencode_go
  Embedding Backend: bge
  Semantic Threshold: 0.78
  API Key: ***xyz1

Running smoke tests...
--------------------------------------------------------------------------------

Test 1/3: 特应性皮炎和肠-脑-皮肤轴有什么关系？

✅ Provider: opencode_go
✅ Answer length: 456 chars
✅ Citations: 3
✅ Disclaimer: ✓

Grounding:
  Status: passed
  Policy: provider_native_tool_grounding
  Checked: True
  Claims: 5
  Cited Claims: 5

Semantic Grounding:
  Backend: bge
  Threshold: 0.78
  Min Score: 0.812
  Max Score: 0.891
  Avg Score: 0.847

Token Usage:
  Input: 1234
  Output: 567
  Total: 1801

Retrieval:
  Strategy: keyword
  Source: all
  Top K: 5

Answer Preview:
  特应性皮炎与肠-脑-皮肤轴密切相关。研究表明，肠道菌群失调可能通过免疫调节影响皮肤屏障功能...

--------------------------------------------------------------------------------
```

### Blocked Run (Grounding Failed)

```
Grounding:
  Status: blocked
  Policy: provider_native_tool_grounding
  Checked: True
  Claims: 5
  Cited Claims: 3
  ⚠️  BLOCKED: semantic_low_support
  Blocked Claims: 2
    - 该复方已被国家药监局批准用于特应性皮炎治疗...
      Score: 0.654, Threshold: 0.78
    - 临床试验显示有效率达到95%以上...
      Score: 0.721, Threshold: 0.78

Semantic Grounding:
  Backend: bge
  Threshold: 0.78
  Min Score: 0.654
  Max Score: 0.891
  Avg Score: 0.782
```

---

## Interpreting Results

### Grounding Status

| Status | Meaning | Action |
|--------|---------|--------|
| `passed` | All claims have semantic score ≥ 0.78 | ✅ Answer is safe to show |
| `blocked` | Some claims have semantic score < 0.78 | ⚠️ Answer contains potential hallucinations |
| `skipped` | Grounding not enabled (deterministic provider) | N/A |

### Semantic Scores

- **Score ≥ 0.78**: Claim is well-supported by cited chunk (PASS)
- **Score < 0.78**: Claim may be fabricated or poorly supported (BLOCK)
- **Min/Max/Avg**: Distribution of scores across all claims

### Token Usage

- **Input tokens**: Context sent to LLM (citations + question)
- **Output tokens**: Generated answer
- **Total**: Input + Output (used for cost estimation)

---

## Troubleshooting

### Error: "QIYAN_OPENCODE_GO_API_KEY is not set"

**Solution**: Set the API key environment variable:
```bash
export QIYAN_OPENCODE_GO_API_KEY=<your-key>
```

### Error: "We couldn't connect to 'https://hf-mirror.com'"

**Solution**: BGE model is not cached. Re-download:
```bash
cd backend
.venv/Scripts/python.exe -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-zh-v1.5')"
```

### Warning: "QIYAN_EMBEDDING_BACKEND is not 'bge'"

**Solution**: Set the embedding backend:
```bash
export QIYAN_EMBEDDING_BACKEND=bge
```

### Warning: "QIYAN_GROUNDING_SEMANTIC_THRESHOLD is not 0.78"

**Solution**: Set the threshold:
```bash
export QIYAN_GROUNDING_SEMANTIC_THRESHOLD=0.78
```

### All Claims Blocked (Status: blocked)

**Possible causes**:
1. **Threshold too strict**: Try lowering to 0.75 or 0.70
2. **LLM generating poor citations**: Check if LLM is using tool calls correctly
3. **Retrieval quality**: Check if retrieved chunks are relevant

**Debug steps**:
1. Review blocked claims and their scores
2. Check if blocked claims are actually hallucinations
3. If legitimate claims are blocked, lower threshold
4. If hallucinations pass, raise threshold

### No Claims Blocked (All Pass)

**This is expected** if:
- LLM is generating well-grounded answers
- Citations are relevant and comprehensive
- Threshold 0.78 is appropriate

**Verify**:
- Read the generated answers manually
- Check if any obvious fabrications slipped through
- If suspicious, expand labeled fixture and re-evaluate

---

## Next Steps After Smoke Test

### If Grounding Works Well (Most Claims Pass)

1. **Document Results**
   - Record grounding status for all 3 questions
   - Note any blocked claims and whether they were legitimate
   - Save output to `docs/evaluations/2026-05-31-opencode-go-bge-smoke.md`

2. **Enable for Internal Preview**
   - Update `.env.example` with validated configuration
   - Add smoke test results to `docs/current-state.md`
   - Mark OpenCode Go + BGE as validated

3. **Monitor in Production**
   - Track false reject rate (legitimate claims blocked)
   - Track false accept rate (hallucinations passing)
   - Adjust threshold if needed

### If Too Many Claims Blocked (False Rejects)

1. **Lower Threshold**
   - Try 0.75, then 0.70
   - Re-run smoke test
   - Find threshold with acceptable false reject rate

2. **Expand Labeled Fixture**
   - Add blocked claims to `grounding_semantic_pairs.json`
   - Label as faithful/hallucinated
   - Re-run BGE evaluation to find optimal threshold

3. **Consider Stronger Model**
   - Try `bge-base-zh-v1.5` (768-dim)
   - Try `bge-large-zh-v1.5` (1024-dim)
   - Trade-off: larger model = slower inference

### If Hallucinations Pass (False Accepts)

1. **Raise Threshold**
   - Try 0.80, then 0.85
   - Re-run smoke test
   - Find threshold with acceptable false accept rate

2. **Improve Retrieval**
   - Check if retrieved chunks are relevant
   - Consider hybrid retrieval (keyword + vector)
   - Expand knowledge base coverage

3. **Improve LLM Prompting**
   - Strengthen citation instructions
   - Add examples of well-grounded answers
   - Use stricter system prompt

---

## Configuration Reference

### Recommended Production Config

```bash
# LLM Provider
QIYAN_LLM_PROVIDER=opencode_go
QIYAN_OPENCODE_GO_API_KEY=<your-key>
QIYAN_OPENCODE_GO_BASE_URL=https://opencode.ai/zen/go/v1
QIYAN_OPENCODE_GO_MODEL=deepseek-v4-flash
QIYAN_OPENCODE_GO_MAX_TOKENS=1200
QIYAN_OPENCODE_GO_TEMPERATURE=0.2

# Semantic Grounding (BGE)
QIYAN_EMBEDDING_BACKEND=bge
QIYAN_GROUNDING_SEMANTIC_THRESHOLD=0.78

# Retrieval
QIYAN_RETRIEVAL_PROVIDER=keyword  # or hybrid
```

### Conservative Config (Hashing)

```bash
# LLM Provider
QIYAN_LLM_PROVIDER=opencode_go
QIYAN_OPENCODE_GO_API_KEY=<your-key>

# Semantic Grounding (Hashing)
QIYAN_EMBEDDING_BACKEND=hashing  # or omit (default)
QIYAN_GROUNDING_SEMANTIC_THRESHOLD=0.40

# Retrieval
QIYAN_RETRIEVAL_PROVIDER=keyword
```

---

## Key Files

- `backend/scripts/smoke_opencode_go_bge.py` — Smoke test script
- `backend/.env.example` — Configuration template
- `docs/evaluations/2026-05-31-bge-semantic-evaluation.md` — BGE validation
- `docs/handoffs/2026-05-31-bge-semantic-evaluation-complete.md` — BGE handoff
- `backend/app/services/llm/opencode_go_provider.py` — OpenCode Go implementation
- `backend/app/services/grounding.py` — Semantic grounding logic
- `backend/app/services/retrieval/embedding.py` — BGE backend

---

## Cost Estimation

Based on OpenCode Go pricing (example, verify current rates):

- **Input**: ~$0.10 per 1M tokens
- **Output**: ~$0.30 per 1M tokens

**Smoke test (3 questions)**:
- Input: ~3,000 tokens (~$0.0003)
- Output: ~1,500 tokens (~$0.0005)
- **Total**: ~$0.0008 per run

**Production (1000 questions/day)**:
- Input: ~1M tokens (~$0.10)
- Output: ~500K tokens (~$0.15)
- **Total**: ~$0.25 per day = ~$7.50 per month

---

## Summary

This smoke test validates the full RAG pipeline with:
- ✅ Real LLM (OpenCode Go)
- ✅ True semantic embeddings (BGE)
- ✅ Validated threshold (0.78)
- ✅ Grounding gate (hallucination detection)

**Run the test, review results, and document findings before enabling for internal preview.**
