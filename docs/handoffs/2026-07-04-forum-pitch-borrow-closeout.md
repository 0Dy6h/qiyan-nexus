# 2026-07-04 论坛路演三方对比借鉴收口 Handoff

## Goal

用第一性原理，把北京中医药大学「数智医研·融合未来」论坛路演幻灯片（行业痛点/三方对比/应用边界与合规性）里**诚实、可落地**的内核借鉴进仓库，剥离「定量药效排序」这类会造假精度的过度宣称。分三个可验证切片：① 网络药理学证据分级层、② RAG 透明检索匹配度、③ 合规可信原则对齐。

## Current state

- 默认路径不变：deterministic provider + keyword retrieval，不启用真实 LLM / embedding / 生产数据库 / live 网络 provider。
- 三个切片全部落地并本地全绿；未 push。
- 免责声明 `非诊断结论、需结合临床。` 保持 byte-identical。

## Completed in this session

### ① 网络药理学证据分级层（ADR-0015）

第一性原理：幻灯片「内嵌《网络药理学评价方法指南》」在仓库无任何实现，是空头承诺；指南三原则（可靠性/规范性/可解释性）恰好对齐仓库已有 provenance/determinism/citation 脊柱。只需补「每条机制链一个证据支持等级」这 10%。

- `NetworkChain.evidence_level`：`mock_inferred` / `predicted` / `literature_supported` / `experimental`（`backend/app/schemas/network.py`）。
- `derive_chain_evidence_level` / `grade_chains_evidence`：确定性纯函数，仅由 `data_mode` + `target_evidence_type` + `evidence_refs` 推导；在 `_advance` 装配处统一打分（`backend/app/services/network.py`）。
- **诚实护栏（测试锁定）**：`data_mode="mock"` 的链恒为 `mock_inferred`，任何字段都升不上去。
- 报告新增「## 证据分级」段 + mock 边界提示；`/network` 每条链卡片渲染「证据分级 · <label>」pill（前端 `getNetworkEvidenceLevelLabel`）。

### ② RAG 透明检索匹配度（ADR-0016）

第一性原理：引用卡片显示的「置信度」是 `CONFIDENCE_BY_SOURCE_TYPE` 常量（只看来源类型），把常量叫置信度=假精度；而真实相关度信号（`ScoredCandidate.score`）本就存在、只是没暴露。

- 新增 `CitationCard.match_score`：按本次结果集最高检索得分归一，top 命中饱和到 1.0（`backend/app/services/rag.py`）。确定性，来自既有 keyword ranker。
- 导出与前端：新增「检索匹配度」，常量降格为「来源类型先验」，显式声明「非概率、非疗效或置信判断」。
- `confidence` 字段保留（向后兼容 prompt / grounding / ~20 处测试）。

### ③ 合规可信原则对齐（无 ADR，纯定位/文案）

把幻灯片「应用边界与合规性」5 条可信原则 + 能做/不替代边界，落成 `/compliance` 与 README，且每条标注**代码落地方式**（非口号）。

- `getComplianceTrustPrinciples()`（5 原则）、`getCompliancePlatformScope()`（能做✓/不替代✗）（`frontend/lib/compliance-page.ts`），页面新增两段渲染。
- 既有 6 段 `getComplianceHighlights()` 未动（被 deepEqual 锁定）。
- README「合规底线」新增可信原则表 + 能做/不替代。

## Still open / blocked

- 未 push；未跑 Playwright E2E（`.\scripts\verify-local.ps1 -IncludeE2E`），reviewer 走查或分支收口前再跑。
- 正式 clinician / research reviewer sign-off 仍未完成。
- 幻灯片「统一知识源 / 图谱化（Neo4j）」「通用中药研发平台」刻意未借（属路线图 / AD-only 保守边界）。
- `.mcp.json` / `components.json` 是 parked shadcn-MCP browse-only shim，**不提交**。

## Key files and artifacts

- `docs/adr/0015-网络药理学证据分级与指南一致性层.md`
- `docs/adr/0016-RAG引用透明检索匹配度.md`
- `backend/app/schemas/network.py`、`backend/app/services/network.py`
- `backend/app/schemas/rag.py`、`backend/app/services/rag.py`
- `backend/tests/test_network_evidence_level.py`、`backend/tests/test_rag_match_score.py`
- `frontend/lib/api/network.ts`、`frontend/components/NetworkAnalysisClient.tsx`
- `frontend/lib/api/rag.ts`、`frontend/components/RagAnswerClient.tsx`
- `frontend/lib/compliance-page.ts`、`frontend/app/compliance/page.tsx`
- `frontend/tests/network-evidence-grading-ui.test.ts`
- `README.md`、`docs/current-state.md`

## Verification

- Backend：`ruff format --check` / `ruff check` / `mypy app` 全绿；`pytest -q` → `598 passed, 1 skipped`。
- Frontend：`pnpm test` → `219 passed`；`pnpm typecheck` 通过；`pnpm build` 通过。
- E2E：未跑。

## Recommended next step

1. `.\scripts\verify-local.ps1`（可选 `-IncludeE2E`）复核统一门禁。
2. 若继续借鉴：幻灯片「统一知识源 / 图谱化」需 ADR 决策（Neo4j 属重依赖，默认路径外）；不建议默认翻转。
3. 正式 reviewer sign-off 仍是进入小范围试用前的人工阻塞点。

## Recommended reading order

1. `docs/current-state.md`
2. `docs/adr/0015-网络药理学证据分级与指南一致性层.md`
3. `docs/adr/0016-RAG引用透明检索匹配度.md`
4. `backend/app/services/network.py`（`derive_chain_evidence_level` / `grade_chains_evidence`）
5. `backend/app/services/rag.py`（`match_score` 装配）
6. `frontend/lib/compliance-page.ts`
