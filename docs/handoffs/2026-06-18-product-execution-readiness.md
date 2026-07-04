# Product Execution Readiness Handoff

日期：2026-06-18

## Goal

本交接用于保障后续主开发者执行“用户/产品经理反馈后的整改与优化”。本轮不直接改业务代码；重点完成本地依赖/验证环境确认、外部相似项目调研、后续执行 skills 编排，以及主开发者可直接采用的执行顺序和门禁。

## Current State

- 本地仓库仍处于内部预览/小范围试用准备阶段：MVP-A 证据工作台已收口，MVP-B 网络药理学 mock/live opt-in 链路已落地。
- 当前默认路径保持离线 deterministic + keyword，不默认启用真实 LLM、真实 embedding、生产数据库或真实网络药理学重计算。
- 用户/PM 最新产品建议已明确：下一阶段应优先收紧“查文献 -> 上传/归档证据 -> 提问 -> 查看引用 -> 导出可审阅材料 -> 机制线索探索”的核心工作流，而不是继续横向扩模块。
- 工作区已有用户/前序改动，不应覆盖：
  - `docs/checklists/reviewer-walkthrough-task-card.md`
  - `docs/evaluations/2026-06-05-reviewer-feedback.md`
  - `docs/evaluations/2026-06-06-small-scale-trial-feedback.md`
  - `docs/plans/2026-06-18-core-evidence-workflow-validation.md`

## Dependency / Tooling Readiness

已确认并配置：

- Node: `v24.13.1`
- pnpm: `10.33.0`
- Frontend dependencies: `pnpm install --frozen-lockfile` 已完成，lockfile 无需更新。
- Next.js: `v16.2.4`
- Playwright CLI: `1.60.0`
- Playwright Chromium: 已通过 `pnpm exec playwright install chromium` 下载到本机 Playwright cache，后续 `pnpm e2e` 不应再卡首次浏览器下载。
- Backend venv: `backend/.uv-test-venv` 存在，项目实际门禁工具可用：
  - Python: `3.13.12`
  - ruff: `0.15.14`
  - mypy: `2.1.0`
  - pytest: `9.0.3`
- Backend import smoke 已通过：
  - `fastapi`
  - `pydantic`
  - `httpx`
  - `pypdf`
  - `scipy`
  - `numpy`

注意：

- `backend/.uv-test-venv` 当前无 `pip` 模块，因此不要把 `python -m pip check` 作为本项目门禁。后端依赖健康以项目既有 `ruff/mypy/pytest` 和 import smoke 为准。
- 运行 `next typegen` / `pnpm build` 可能刷新 `.next` 产物；若 `frontend/next-env.d.ts` 仅出现无文本 diff 的假修改，可用 `git update-index --refresh -- frontend/next-env.d.ts` 清理索引状态。

## Verification Completed

已运行：

```powershell
.\scripts\verify-local.ps1
```

结果：

- backend `ruff format --check`: passed
- backend `ruff check`: passed
- backend `mypy app`: passed
- backend `pytest -q`: `566 passed, 1 skipped`
- frontend `pnpm test`: `207 passed`
- frontend `pnpm typecheck`: passed
- frontend `pnpm build`: passed
- E2E 未在本轮跑；浏览器依赖已安装，reviewer 走查或收口前可运行：

```powershell
.\scripts\verify-local.ps1 -IncludeE2E
.\scripts\verify-local.ps1 -IncludeE2E -E2ETokenProfile
```

## External Research Summary

### Scientific RAG / Literature Workbench Projects

Key sources:

- PaperQA / PaperQA2 GitHub: https://github.com/Future-House/paper-qa
- PaperQA arXiv paper: https://arxiv.org/html/2312.07559v2
- ASReview GitHub: https://github.com/asreview
- ASReview docs: https://asreview.readthedocs.io/en/stable/lab/about.html
- RAGFlow GitHub: https://github.com/infiniflow/ragflow
- RAGFlow docs: https://ragflow.io/docs/
- Haystack GitHub: https://github.com/deepset-ai/haystack
- Haystack site/docs: https://haystack.deepset.ai/

Experience to borrow:

- PaperQA validates the direction of scientific RAG with in-text citations and source-grounded answers. Qiyan should keep citations as the primary product object, not treat them as metadata decoration.
- ASReview is a useful pattern for human-in-the-loop research tooling: prioritize review decisions, stopping rules, and auditability over “fully automatic literature conclusion”.
- RAGFlow reinforces that document ingestion quality matters. For Qiyan, PDF parser status, preview quality warnings, OCR/table limitations, and parse provenance should remain explicit product surfaces.
- Haystack’s pipeline framing supports Qiyan’s current separation of retrieval/provider/grounding. Keep provider opt-in and retrieval strategy observable; avoid burying pipeline decisions in UI copy that users cannot audit.

### Literature / Evidence Data APIs

Key sources:

- NCBI E-utilities official guide: https://www.ncbi.nlm.nih.gov/books/NBK25497/
- OpenAlex API docs: https://developers.openalex.org/
- Semantic Scholar API: https://www.semanticscholar.org/product/api
- Zotero Web API: https://www.zotero.org/support/dev/web_api/v3/basics

Experience to borrow:

- PubMed / NCBI rate limits are explicit: without an API key, more than 3 requests/sec can error; with API key default is 10 requests/sec. Qiyan’s PubMed sync should keep rate limiting, retry, request id, and source timestamp visible.
- OpenAlex and Semantic Scholar are good later candidates for broader scholarly metadata, but they should be opt-in additions with provenance labels and rate-limit handling, not silent replacement of current PubMed source.
- Zotero Web API is relevant if users want to bring their own library. A later “Zotero import” slice could be higher value than building a custom bibliography manager, but only after reviewer feedback confirms upload/library workflows matter.

### Network Pharmacology / Bio Data APIs

Key sources:

- PubChem PUG REST: https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest
- ChEMBL web services: https://chembl.gitbook.io/chembl-interface-documentation/web-services/chembl-data-web-services
- UniProt ID mapping: https://www.uniprot.org/help/api_idmapping
- STRING API: https://string-db.org/help/api/

Experience to borrow:

- The repo’s current live network provider direction is aligned with real source order: compound lookup, activity/target evidence, target normalization, PPI/network, enrichment.
- For formalizing live network mode, every edge/result should carry source, source record id, retrieval time, database/API version if available, and warning/error provenance.
- Do not call mock GO/KEGG enrichment “formal analysis”. Keep product language as “机制线索探索” until real database, parameters, multiple-test correction/FDR policy, and reproducible task records are in place.

### Medical AI Evaluation / Reporting Guidelines

Key sources:

- DECIDE-AI Nature Medicine / guideline: https://www.nature.com/articles/s41591-022-01772-9
- DECIDE-AI EQUATOR: https://www.equator-network.org/reporting-guidelines/reporting-guideline-for-the-early-stage-clinical-evaluation-of-decision-support-systems-driven-by-artificial-intelligence-decide-ai/
- CONSORT-AI BMJ: https://www.bmj.com/content/370/bmj.m3164
- SPIRIT-AI BMJ: https://www.bmj.com/content/370/bmj.m3210
- TRIPOD+AI BMJ: https://www.bmj.com/content/385/bmj-2023-078378

Experience to borrow:

- Qiyan is not currently a clinical trial or prediction-model product, but these guidelines are still useful as a safety vocabulary: report intended use, user expertise, data sources, model/provider version, human oversight, error handling, update policy, and evidence limitations.
- DECIDE-AI is particularly relevant to early-stage evaluation of AI decision-support systems. The small-scale trial feedback packet should ask reviewers about context of use, failure modes, trust calibration, and whether users understood the system’s limitations.
- CONSORT-AI / SPIRIT-AI / TRIPOD+AI should not be over-applied as checklists now, but they provide a future governance reference if Qiyan moves toward prospective evaluation or model-performance claims.

### Product Benchmarking

Key sources:

- Elicit: https://elicit.com/
- Elicit systematic review page: https://elicit.com/solutions/systematic-review
- OpenEvidence: https://www.openevidence.com/
- Consensus: https://consensus.app/search/
- Rayyan: https://www.rayyan.ai/

Experience to borrow:

- Elicit’s strongest product pattern is structured research reports and data extraction supported by quotes/figures from source. Qiyan should strengthen export templates and evidence tables before adding more AI autonomy.
- OpenEvidence positions around clinician verification and cited/grounded medical answers. Qiyan should keep clinician/researcher access boundaries clear and avoid patient-facing claims.
- Consensus narrows search to scholarly/peer-reviewed sources and makes evidence synthesis the point. Qiyan should keep “evidence-backed answer” more prominent than “chat”.
- Rayyan and ASReview both show that systematic review users value screening, deduplication, tags, and collaboration. Qiyan should not build these yet, but reviewer feedback should test whether “evidence table / screening queue” is more valuable than additional generative answer polish.

## Recommended Skills For Main Developer

Use these as the default execution stack:

1. `project-grill`
   - Use before coding each product slice to clarify whether it is meant for clinician, research reviewer, or internal operator.
   - Especially useful for language changes such as “网络药理学分析” vs “机制线索探索”.

2. `qiyan-ui-defaults` + `ui-ux-pro-max`
   - Use for all frontend/page/copy/hierarchy changes.
   - Keep Qiyan as a clinical research workbench: restrained, evidence-first, dense but readable, no marketing/consumer-health tone.

3. `vertical-slice-planning`
   - Use to split product feedback into independently verifiable slices.
   - Recommended first slice should be user-visible and narrow, not a layer-only refactor.

4. `test-driven-development`
   - Use for behavior or contract changes.
   - For frontend polish in this repo, source-level tests under `frontend/tests/*.test.ts` are acceptable when the UX contract is wording/structure.

5. `systematic-debugging`
   - Use for any failing local gate, E2E instability, provider fallback surprise, or PDF/parser issue.
   - Start with a repeatable loop, then root cause; no speculative fixes.

6. `dogfood`
   - Use before reviewer handoff to run exploratory browser QA on `/literature`, `/literature/[id]`, `/rag`, `/network`, export flows, and token profile.
   - Save evidence under `.tmp/` or a local QA output directory unless user asks to commit a report.

7. `github-code-review`
   - Use before committing a product slice.
   - For local review, prioritize correctness, safety/copy risk, test coverage, and accidental fixture/runtime pollution.

8. `session-handoff`
   - Use after any multi-step implementation or reviewer-readiness pass.
   - Store continuation notes under `docs/handoffs/YYYY-MM-DD-<topic>.md`.

Optional later:

- `codebase-map` / `codegraph` if a future developer is unfamiliar with a module and needs map-first orientation.
- `requesting-code-review` if a branch needs an automated pre-commit review pass.
- `github-pr-workflow` only if user explicitly wants branch/PR creation.
- `subagent-driven-development` only if the user explicitly authorizes multi-agent delegation; do not assume delegation merely because the task is large.

## Recommended Execution Slices

### Slice 1: Core Workflow Home / Navigation Copy

- Type: AFK
- Goal: Make the first screen and nav communicate the real product loop: 查证据 / 问证据 / 看机制线索.
- Acceptance:
  - 首页 primary cards use workflow language, not module inventory language.
  - Network is framed as “机制线索探索” unless live/formal mode is explicitly enabled.
  - No change to backend behavior.
- Verification:
  - `cd frontend; pnpm test; pnpm typecheck; pnpm build`

### Slice 2: RAG Default View Evidence-First Hierarchy

- Type: AFK with reviewer copy review recommended.
- Goal: Default RAG result emphasizes answer, evidence source scope, citation support, disclaimer, and export; technical metadata becomes advanced/audit detail.
- Acceptance:
  - Provider, token, grounding internals remain available but no longer dominate first scan.
  - Blocked/fallback states remain explicit.
  - Existing grounding/citation tests are updated, not weakened.
- Verification:
  - Focused frontend tests for `RagAnswerClient`
  - Full frontend gates

### Slice 3: Unified Data-Mode Labels

- Type: AFK
- Goal: Introduce user-facing labels for 演示样本 / PubMed 实时同步 / 用户上传 PDF / 本地生成 / 外部模型 / 探索性网络分析.
- Acceptance:
  - Literature cards, detail metadata, RAG citation cards, network result/report copy use consistent terms.
  - No seed/runtime fixture mutation.
- Verification:
  - Frontend source-level copy tests
  - Existing backend tests remain green if API labels are untouched

### Slice 4: Reviewer Trial Task Success Metrics

- Type: HITL
- Goal: Convert reviewer forms into measurable trial criteria: completion, trust, usefulness, confusion, safety issue severity.
- Acceptance:
  - Reviewer task card has 5-7 concrete tasks.
  - Feedback form captures 1-5 ratings plus P0/P1 safety comments.
  - Small-scale trial template defines pass/fail thresholds for readiness.
- Verification:
  - Markdown review by user/product owner
  - No code gate required unless docs tests are added later

### Slice 5: Export Template Productization

- Type: AFK/HITL mixed
- Goal: Improve RAG/network Markdown exports toward meeting notes / evidence brief templates.
- Acceptance:
  - Export contains source scope, generation mode, citations, limitations, and reviewer-friendly sections.
  - Backend remains single source of truth for export body.
- Verification:
  - Backend export tests
  - Frontend export tests
  - `.\scripts\verify-local.ps1`

## Recommended Reading Order For Next Developer

1. `docs/current-state.md`
2. `README.md`
3. `AGENTS.md`
4. `docs/plans/2026-06-18-core-evidence-workflow-validation.md`
5. This file: `docs/handoffs/2026-06-18-product-execution-readiness.md`
6. `frontend/components/RagAnswerClient.tsx`
7. `frontend/components/LiteratureSearchClient.tsx`
8. `frontend/components/LiteraturePdfUploadClient.tsx`
9. `frontend/components/NetworkAnalysisClient.tsx`
10. `frontend/tests/client-section-consistency.test.ts`
11. `frontend/tests/page-shell-consistency.test.ts`

## Guardrails

- Do not revert the existing uncommitted doc changes unless explicitly asked.
- Do not rename or rewrite the load-bearing disclaimer: `非诊断结论、需结合临床。`
- Do not default-enable real LLM, real embedding, live network provider, PostgreSQL, pgvector, Neo4j, Celery, Redis, MinIO, or NextAuth.
- Do not treat mock/sample network output as formal network pharmacology analysis.
- Do not commit runtime state, uploaded PDFs, `.tmp/`, or parser artifacts.
- For frontend UI changes, keep section hierarchy and source-level tests in sync; several tests use regex assertions over `.tsx`.
- For PDF work, preserve honest parser boundaries: text-layer PDFs can preview; OCR/table reconstruction remains separate future spike.

## Recommended Next Step

Start with Slice 1 or Slice 2, not a broad redesign. The highest-value first execution step is a narrow frontend/product language slice that makes the core workflow obvious while preserving all existing gates:

```powershell
cd frontend
pnpm test
pnpm typecheck
pnpm build
```

Then run reviewer-prep E2E only after the first product slice is merged locally:

```powershell
.\scripts\verify-local.ps1 -IncludeE2E
```

