# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project identity

Qiyan Nexus — 面向特应性皮炎（AD）医生与科研人员的中医药证据与科研工作台。仅医生/研究人员端，**不面向 C 端患者**，**不替代诊断**。所有 AI 输出必须附带免责声明 `非诊断结论、需结合临床。`

仓库当前处于可运行的 MVP-A 证据工作台阶段：后端用本地 JSON seed + runtime state + deterministic retrieval 模拟 RAG；PDF 解析支持 `pypdf` 文本预览，无法抽取时回退到文件级占位说明。**当前不接真实 LLM、embedding、pgvector、Neo4j、Celery、Redis、MinIO、对象存储或支付**；新工作不要绕过这条边界。

## Commands

### Backend (Python 3.11+, FastAPI)

```bash
# First-time install (now includes dev tooling: ruff, mypy)
cd backend && python3 -m venv .venv && .venv/bin/python -m pip install -U pip && .venv/bin/python -m pip install -e ".[dev]"

# Dev server (http://127.0.0.1:8000)
cd backend && .venv/bin/fastapi dev app/main.py

# Tests
cd backend && .venv/bin/python -m pytest -q

# Single test file / single test
cd backend && .venv/bin/python -m pytest tests/test_rag_service.py -q
cd backend && .venv/bin/python -m pytest tests/test_rag_service.py::test_name -q

# Lint / format / type-check (must all be green before commit)
cd backend && .venv/bin/python -m ruff format app tests           # apply formatting
cd backend && .venv/bin/python -m ruff format --check app tests   # CI-style check
cd backend && .venv/bin/python -m ruff check app tests            # lint
cd backend && .venv/bin/python -m mypy app                        # strict type check

# Windows variant the README still references
cd backend && .\.venv\Scripts\python.exe -m pytest -q --basetemp .\.pytest-tmp
```

### Frontend (Next.js 16 + React 19 + Ant Design 6, pnpm)

```bash
cd frontend && pnpm install
cd frontend && pnpm dev            # http://localhost:3000, expects backend at 127.0.0.1:8000
cd frontend && pnpm test           # node --import tsx --test tests/*.test.ts
cd frontend && pnpm typecheck      # tsc --noEmit (includes tests/)
cd frontend && pnpm build          # next build --webpack

# Single test file
cd frontend && node --import tsx --test tests/literature-api.test.ts

# Override API base
cd frontend && NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 pnpm dev

# E2E (A4 — Playwright). One-time host setup: pnpm exec playwright install chromium
# plus sudo install-deps for libnspr4/libnss3/etc. See frontend/e2e/README.md.
cd frontend && pnpm e2e            # spins up backend + frontend webServer, runs e2e/*.spec.ts
```

## Architecture

### Backend layering (strict)

`app/api/*.py` (FastAPI routers under `/api/...`) → `app/services/*.py` (business logic, disclaimer composition, ranking) → `app/repositories/*.py` (in-memory JSON-file I/O) → `app/schemas/*.py` (Pydantic models). Don't bypass layers — routers should not read JSON directly, services should not import `FastAPI`.

Routers are wired in `app/main.py`. CORS is restricted to `localhost:3000` / `127.0.0.1:3000`, methods `GET, POST` only — adding a `DELETE` or `PUT` route requires editing the middleware.

### Sample-data substrate

Authoritative mock data lives in `backend/data/`, while runtime mutations are written under `backend/data/runtime/`:
- `literature/sample_ad_literature.json` — seed literature records (zh + en)
- `literature/sample_ad_chunks.json` — seed chunk-level evidence
- `evals/rag_ad_eval_questions.json` — 20-question AD eval set with expected literature/chunk hits, forbidden phrases, required disclaimer
- `runtime/literature_state.json` — runtime literature state generated from seed data; gitignored

Repositories bootstrap from seed JSON and write runtime state on update (e.g. `update_pdf_metadata`, `update_pdf_parse_status`). Do not commit runtime state or uploaded PDFs as fixtures unless a task explicitly asks for new source data.

### RAG pipeline (deterministic, no LLM)

`app/services/rag.py` does keyword tokenization with Chinese-char-per-token + an alias table (`gut`, `skin_barrier`, `immune`, `pruritus`, `formula`, `network`, `pediatric`). Scoring runs against `title + snippet + abstract + keywords + evidence_tags + chunk text + chunk evidence_tags`. Language detection picks a `preferred_source_type` tie-breaker (zh → `cn_literature`, otherwise `pubmed`). Confidence is a constant per source type, **not** computed.

Two non-obvious invariants enforced by tests:
1. Every `citations[*].literature_id` returned by `/api/rag/answer` must resolve via `/api/literature/{id}` (`test_rag_literature_contract.py`).
2. Responses always carry the disclaimer string; the eval scans for forbidden phrases. Don't soften or rewrite `DISCLAIMER` in `services/rag.py`.

### PDF upload → RAG citation flow

`POST /api/uploads/pdf` (multipart) writes the file under `UPLOAD_STORAGE_DIR` (default `backend/uploads/`, gitignored) and sets literature metadata to `pdf_parse_status=pending`. **The upload endpoint does not do heavy parsing** — call `POST /api/uploads/pdf/auto-parse` separately to transition `pending → parsed`/`failed`. Auto-parse builds `pdf_parse_result`: text-layer PDFs use `pypdf-text-preview`; scanned/empty/unreadable PDFs fall back to `file-metadata-placeholder`. On success the parser writes an `uploaded_pdf` chunk into runtime state so RAG retrieval can cite it; on failure it only flips status and bumps `parse_attempt_count`.

Stable upload IDs are derived from `literature_id + file_name` so `GET /api/uploads/pdf/{pdf_upload_id}` is idempotent.

### Frontend test setup

`pnpm test` runs `node --import tsx --test tests/*.test.ts` — the `tsx` loader compiles TypeScript on the fly so tests import directly from `lib/*.ts` without a build step. Tests use only `node:test` + `node:assert/strict` (no Vitest, no jsdom). Four tests (`pdf-upload-status`, `literature-detail-meta`, `client-section-consistency`, `page-shell-consistency`) read `.tsx` files via `readFileSync` and assert against the source text — when you change page shells, navigation, or visible metadata copy in `app/` or `components/`, these regex assertions are the things most likely to fail.

`pnpm typecheck` (`tsc --noEmit`) covers `tests/**` as well; the fetch-mock pattern in `evals-api.test.ts` / `literature-detail-api.test.ts` uses explicit `as typeof globalThis.fetch` casts because `node:test` has no built-in fetch mocking.

Pages: `/` `/literature` `/literature/[id]` `/rag` `/evals/rag-ad` `/compliance`. Shared shell helpers live in `lib/ui/` (`surfaces`, `states`, `card-meta`, `status-card`) and `lib/compliance-page.ts` — `page-shell-consistency.test.mjs` and `client-section-consistency.test.mjs` lock these contracts.

### Module roadmap (ADR-0010)

Only MVP-A (evidence workbench) is in scope right now. Concepts for MVP-B (network pharmacology) and MVP-C (molecular docking / MD) — `herb`, `formula`, `compound`, `target`, `pathway`, `disease`, `protein`, `ligand`, `simulation_task` — may appear as type/name placeholders, but **do not wire real computation for them**.

## Conventions

- **Language**: docs and user-facing copy in Simplified Chinese; code identifiers, API paths, file names in English; comments may mix.
- **Disclaimer string**: `非诊断结论、需结合临床。` is load-bearing — referenced by tests, eval, and frontend assertions. Keep it byte-identical.
- **Visual tokens**: 青黛绿 `#0d9488` ~ `#14b8a6` as primary; light-mode product surfaces; Noto Sans SC. Existing pages use inline styles with `clamp(20px, 4vw, 48px)` page padding — match that rather than introducing a new styling layer mid-slice.
- **Lint/type gate**: every backend change must leave `ruff format --check app tests`, `ruff check app tests`, `mypy app`, and `pytest -q` all green. `[tool.mypy].strict = true` is enforced on `app/`; tests are excluded. `B008` is globally ignored because FastAPI uses `Body()` / `Form()` / `File()` / `Query()` as defaults.
- **E2E gate (A4)**: `pnpm e2e` is the third frontend gauntlet stage but is NOT part of the per-commit gauntlet — it requires `playwright install chromium` + system libs (sudo). Run it before closed-beta walkthroughs and CI; treat failures as branch-level blockers, not commit-level.
- **Secrets**: only `.env.example` is committed. `.env*` and `backend/uploads/` are gitignored.
- **Access control (A2)**: `QIYAN_ACCESS_TOKENS` env (comma-separated allowlist) gates every API path except `/health` and CORS preflight. Empty value = open (dev default); set value requires `X-Access-Token` header. Middleware lives in `app/core/access_control.py`.
- **TDD slice cadence**: per `AGENTS.md`, write failing test → implement → refactor; commit small vertical slices rather than batched refactors.

## Where to look for context

- `AGENTS.md` — project map, frozen tech decisions, current dev principles
- `CONTEXT.md` — domain glossary (AD, GBS-Axis, Evidence-Chain, etc.); use these terms verbatim
- `README.md` — full API examples (curl) for every endpoint currently implemented
- `docs/adr/` — 10 ADRs covering literature indexing strategy, model routing, embedding split, MinIO storage, Celery, frontend baseline, module roadmap
- `docs/handoffs/` — recent session handoffs; the newest is the most reliable "what's actually done" source
- `docs/plans/` — slice plans (literature data slice, PDF→RAG slice, RAG eval slice)
