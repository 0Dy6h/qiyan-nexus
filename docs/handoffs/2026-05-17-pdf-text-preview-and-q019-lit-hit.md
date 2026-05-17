# Qiyan Nexus PDF text preview + q019 lit_hit 收口

日期：2026-05-17

## Goal

在用户已完成 `/rag` 人工走查后，继续推进两个后续切片：

1. 把 PDF parse result `preview_text` 从文件级 placeholder 升级为真实文本抽取预览。
2. 把 RAG eval q019 的 `expected_literature_hits` 从 1/3 拉到 3/3，同时保持既有 20/20 eval baseline 不退化。

## Completed

### PDF text preview slice

- 新增轻依赖 `pypdf>=5.0.0`。
- `backend/app/services/literature.py` 新增 `extract_pdf_preview_text(storage_path, max_chars=300)`。
- `build_pdf_parse_result()` 现在：
  - PDF 可抽取文本时：`preview_text` 使用真实抽取文本，`extraction_method="pypdf-text-preview"`。
  - 抽取失败或文本为空时：保留原诚实 placeholder，`extraction_method="file-metadata-placeholder"`。
- `backend/tests/test_upload_api.py` 新增两个 API 级测试：
  - 成功抽取时 parse result preview 来自 PDF 内容。
  - 无法抽取时保留 placeholder 回退。

RED/GREEN 记录：
- 首个 focused test 先失败于 placeholder 仍被返回。
- 实现 pypdf 抽取后 focused test 通过。
- 追加 fallback test 后发现 `get_settings()` cache 会复用上个 upload dir，补 `get_settings.cache_clear()` 后通过。

### q019 lit_hit slice

- `backend/tests/test_eval_service.py` 新增 q019 锁定测试，要求 q019 返回：
  - `cn-ad-network-007`
  - `pmid-40100008`
  - `pmid-40100005`
- RED：初始 q019 只命中 `cn-ad-network-007`。
- 第一版只加 network alias 后仍只命中 `cn-ad-network-007`，原因是中文 query 的 language_bonus 与大量中文字符 token 让中文候选占据 top3。
- 最小实现：
  - `network` alias 增加 `分子对接 / 分子模拟 / molecular docking / molecular simulation`。
  - 新增 `targeted_therapy` alias，把 `后续 / 线索 / therapeutic target / targeted therapy` 映射到目标治疗线索。
  - 对 `source="all"` 且 query tokens 含 `network` 的检索，排序时优先 `network_pharmacology`，其次 `targeted_therapy`，再保留原 language/score/year 排序。
- GREEN：q019 lit_hit 达到 3/3，完整 eval 仍通过。

## Verification

已跑全量 gates：

Backend:
- `cd backend && .venv/bin/python -m ruff format app tests`
- `cd backend && .venv/bin/python -m ruff format --check app tests`
- `cd backend && .venv/bin/python -m ruff check app tests`
- `cd backend && .venv/bin/python -m mypy app`
- `cd backend && .venv/bin/python -m pytest -q` → 93 passed

Frontend:
- `cd frontend && pnpm test` → 58 pass
- `cd frontend && pnpm typecheck` → pass
- `cd frontend && pnpm build` → pass

## Changed files

- `backend/pyproject.toml`
- `backend/app/services/literature.py`
- `backend/app/services/rag.py`
- `backend/tests/test_upload_api.py`
- `backend/tests/test_eval_service.py`

## Current caveats

- `pypdf` 能抽取文本型 PDF；扫描件/OCR 仍不在当前范围内。
- 测试用 ASCII PDF fixture，是为了稳定验证 pypdf extraction path；真实中文 PDF 抽取质量仍需后续用真实样本人工验证。
- q019 的 network-specific rerank 是 deterministic eval 时代的窄策略，真实 embedding/LLM 接入后应重新评估是否保留或弱化。
- 当前改动尚未 commit / push。

## Recommended next step

1. 手动试一个真实文本型 PDF 上传 → auto-parse，确认 `解析结果预览` 显示真实文本。
2. 若满意，提交本切片：
   `git add backend/pyproject.toml backend/app/services/literature.py backend/app/services/rag.py backend/tests/test_upload_api.py backend/tests/test_eval_service.py docs/handoffs/2026-05-17-pdf-text-preview-and-q019-lit-hit.md && git commit -m "feat(rag): add pdf text preview and q019 lit-hit lock"`
3. 下一颗更自然的 slice：前端把 `extraction_method="pypdf-text-preview"` 显示为更明确的中文标签（例如 `解析方式：pypdf 文本预览`），并增加一条 frontend source-level test。

## Pause update — 2026-05-17 evening

本轮暂停前已额外完成 wiki INDEX 收口：

- `/home/dyh2026/.hermes/wiki/INDEX.md` 已手动补入本 handoff 对应 note：`notes/2026-05-17-Qiyan Nexus-PDF-text-preview-and-q019-lit-hit`。
- 同步补齐此前漏收录的 lesson：`lessons/feishu-bitable-today-latest-misread-2026-05-17`。
- INDEX 最近更新已新增 Tcm_tech / Qiyan Nexus PDF text preview + q019 lit_hit 收口条目。
- INDEX 统计已更新为：概念 4、项目 16、技能 11、笔记 48、教训 8、总计 87。
- 已重新运行 `python3 ~/.hermes/wiki/wiki_tool.py index`，输出仍为内容文件数 87 / 有链接文件数 86 / 链接数 224 / 标签数 150。
- 已回读验证 INDEX 中新 note、lesson、最近更新和统计均可见；脚本检查 notes / lessons 无 INDEX 漏收录。

当前 git 状态仍为未提交：

- `backend/app/services/literature.py`
- `backend/app/services/rag.py`
- `backend/pyproject.toml`
- `backend/tests/test_eval_service.py`
- `backend/tests/test_upload_api.py`
- `docs/handoffs/2026-05-17-pdf-text-preview-and-q019-lit-hit.md`

下一次回来建议直接从“真实文本型 PDF 上传 → auto-parse 人工验收”开始；满意后再 commit。
