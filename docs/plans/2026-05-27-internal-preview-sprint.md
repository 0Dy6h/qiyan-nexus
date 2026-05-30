# Internal Preview Sprint Plan

date: 2026-05-27
status: implemented as planning/checklist baseline; code transparency and hard-block grounding slices implemented

## Goal

把当前仓库收口为 1 周内部预览版本：默认 offline/deterministic 可演示，真实外部服务只做显式 smoke，文档事实源与代码一致。

## Scope

- 更新 `README.md` 与 `docs/current-state.md`，反映 MVP-A 内部走查、MVP-B mock 链路、C 阶段 provider/retrieval 底座。
- 在 `/rag` response、前端 UI 与 Markdown 导出中暴露 provider、retrieval strategy、grounding status 与 token usage。
- 固化内部 demo smoke checklist、LLM provider smoke runbook 与真实数据 smoke 记录模板。
- 记录本轮可验证结果：PubMed live parser smoke 成功；本地 PDF artifact 暴露乱码/无文本层/加密/坏文件风险；真实 LLM live smoke 因无本地 key 不默认执行。

## Implementation Slices

1. **事实源收敛**：`README.md`、`docs/current-state.md` 不再把项目描述为骨架，不再写 20 题 eval 当前态，页面列表加入 `/network`。
2. **RAG 透明度**：`RagAnswerResponse` 增加 `input_tokens` / `output_tokens`，前端 `RetrievalMetadata` 增加 `strategy`，`/rag` 与 Markdown export 展示 provider、strategy、token usage。
3. **内部走查脚本**：新增 `docs/checklists/internal-preview-smoke.md`，覆盖 `/literature`、PDF、`/rag`、`/evals/rag-ad`、`/network`。
4. **外部服务 smoke**：新增 `docs/checklists/llm-provider-smoke.md`，只记录本地显式 env smoke，不默认开放真实 LLM。
5. **证据记录**：新增 `docs/evaluations/2026-05-27-real-data-smoke.md`，记录 PubMed、PDF、LLM smoke 真实结果与缺口。
6. **交接**：新增 `docs/handoffs/2026-05-27-internal-preview-readiness.md`，给下一轮继续开发使用。
7. **Grounding hard-block v2**：真实外部 provider 草稿的每个事实句必须引用本次 citation 允许的证据 ID；缺失、未知证据 ID 或未带允许证据 ID 的事实句会被拦截展示，并在 `/rag`、Markdown export 与 eval report 中暴露 grounding metadata。

## Acceptance Criteria

- 默认 RAG 请求返回 `provider_name="deterministic"`、`retrieval.strategy="keyword"`、`grounding.status="skipped"`、`input_tokens=null`、`output_tokens=null`。
- OpenCode Go / Anthropic 成功路径返回 usage 时，RAG API 能把 token 字段冒泡到前端类型、UI 与 Markdown export。
- OpenCode Go / Anthropic 成功路径若未逐句引用本次允许证据 ID，RAG API 返回 HTTP 200 但替换为 hard-block answer，`grounding.status="blocked"`，citation cards 仍保留。
- `README.md` 与 `docs/current-state.md` 明确：`anthropic` / `opencode_go` / `vector` / `hybrid` 均为 opt-in，不是默认路径。
- 内部 demo 走查有明确操作和期望结果；不可自动验证的真实 PDF / live key 项必须标为 pending，不伪造证据。

## Verification

Backend:

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m ruff format --check app tests
& .\.uv-test-venv\Scripts\python.exe -m ruff check app tests
& .\.uv-test-venv\Scripts\python.exe -m mypy app
& .\.uv-test-venv\Scripts\python.exe -m pytest -q
```

Frontend:

```powershell
cd frontend
pnpm test
pnpm typecheck
pnpm build
```

Manual:

- Run `docs/checklists/internal-preview-smoke.md`.
- Run missing-key fallback from `docs/checklists/llm-provider-smoke.md`.
- Use `docs/evaluations/2026-05-27-real-data-smoke.md` to record any additional true PDFs or live provider runs.

## Assumptions

- No productionization in this sprint: no PostgreSQL, object storage, auth system, audit log, queue, deployment pipeline, OCR, Neo4j, or real embedding model.
- All AI output keeps byte-identical disclaimer: `非诊断结论、需结合临床。`
- Real external LLM providers stay blocked from default user paths until full tool-use citation grounding and semantic hallucination reject are implemented; hard-block v2 is only a lightweight sentence-level evidence-ID coverage gate.
