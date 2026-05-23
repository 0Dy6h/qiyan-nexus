# B6 — 数据来源切换面板（2026-05-23）

> 阶段 B 第六颗 slice（roadmap §3.2 estimate 0.5d）。把 `/literature` 的「文献来源」过滤从既有的 3 档（全部 / 中文文献 / PubMed）扩成 4 档合规口径（全部来源 / PubMed 实时 / CNKI sample / 上传 PDF），并让一条 view-aware 提示卡随选择切换 tone + 文案，与 `/compliance` 上 A6 已落的「数据来源说明」章节口径对齐。
> 前置 slice：A6 合规章节扩展（`docs/handoffs/2026-05-21-a6-compliance-data-source-and-pdf-copyright.md`）。
> 分支：`feat/b6-literature-data-source-switcher`（3 commit，**独立于 B2-B5 stack，基于 main**）。

## 落地点

3 个 vertical slice，每颗一个 commit、TDD red → green：

### Slice 1 — 后端 `has_pdf_upload` 过滤（commit `fcfc621`）

- `backend/app/services/literature.py:126` `search_literature(...)` 加 `has_pdf_upload: bool | None = None` 参数；`has_pdf_upload is True` → 过滤 `item.pdf_upload_id` 为真的；`False` → 过滤为 falsy 的；`None` → 不过滤（既有行为）
- `backend/app/api/literature.py:24` `/search` 端点加 `has_pdf_upload: bool | None = Query(default=None)`，透传到 service
- `backend/tests/test_literature_search.py` 加 3 条：true / false / 省略；新增 `_seed_one_pdf_upload(monkeypatch, tmp_path)` helper，复用 `/api/literature/pdf-metadata` 端点把一份 fake PDF 挂到 `cn-ad-gbs-001` 做隔离 runtime fixture

### Slice 2 — 前端 lib helpers（commit `4490f45`）

- `frontend/lib/api/literature.ts`：
  - 新增 `LiteratureDataSourceView = "all" | "pubmed_live" | "cnki_sample" | "uploaded_pdf"`
  - 新增 `LiteratureDataSourceFilter = { source: LiteratureSource; hasPdfUpload?: boolean }`
  - 新增 `LiteratureDataSourceBanner = { tone: "info" | "live" | "sample" | "upload"; title: string; summary: string }`
  - `getLiteratureDataSourceLabel(view)` → 4 档显示文本
  - `getLiteratureDataSourceFilter(view)` → view → `{source, hasPdfUpload?}` 映射（`uploaded_pdf` 映射到 `{source: "all", hasPdfUpload: true}`）
  - `getLiteratureDataSourceBanner(view)` → 4 档 banner copy；CNKI sample 文案含 `seed/sample/演示/示例` 关键词，上传 PDF 文案含 `本地/不公开/不分发`，PubMed 文案含 `PubMed/NCBI`（与 A6 合规章节口径对齐）
  - `buildLiteratureSearchUrl(query, source, page, pageSize, sort, hasPdfUpload?)` 末位加可选参数，set 时序列化为 `&has_pdf_upload=true|false`
  - `searchLiterature(...)` 同步加 `hasPdfUpload?` 透传
- `frontend/tests/literature-api.test.ts` 加 5 条：URL append/omit `has_pdf_upload`、4 档 label、4 档 filter 映射、4 档 banner copy 关键词

### Slice 3 — UI 接线（commit `8324957`）

- `frontend/components/LiteratureDataSourceBanner.tsx`（**新建**）：props `{ view: LiteratureDataSourceView }`；4 tone 各自的 `{background, border, badgeBackground, badgeColor, titleColor, bodyColor}` 表（info 青绿 / live 蓝 / sample 橙 / upload 紫）；`aria-label="数据来源说明"` 与 `DemoDataBanner` 的 "演示数据提示" 区分开
- `frontend/components/LiteratureSearchClient.tsx`：
  - `SearchState.source: LiteratureSource` → `SearchState.view: LiteratureDataSourceView`
  - 表单 `<select name="source">` → `<select name="view">`，options 改 4 档（`all` / `pubmed_live` / `cnki_sample` / `uploaded_pdf`）；label `文献来源` 保留不变（被 `client-section-consistency.test.ts:21` 锁定）
  - `onSubmit` 用 `getLiteratureDataSourceFilter(view)` 派生 `{source, hasPdfUpload}` 传给 `searchLiterature(...)`
  - 在 `<section>` 上方插入 `<LiteratureDataSourceBanner view={state.view} />`；翻页按钮同步用 `state.view` 而不是 `state.source`
- `app/literature/page.tsx`：**未改动**。`DemoDataBanner`（站点级橙色「演示数据」提示）仍在；新 view-aware banner 嵌在 `LiteratureSearchClient` 内部、随 form state 切换
- `frontend/tests/literature-data-source-switcher.test.ts`（**新建**，3 条）：源码字符串断言 banner 组件契约、客户端 4 档 view selector + 不再含 legacy 3 档 option、page 上 `DemoDataBanner` 与 `LiteratureDataSourceBanner` 的层级分工

## 行为契约（B6 后）

| 维度 | 行为 |
|---|---|
| `GET /api/literature/search?has_pdf_upload=true` | 只返回 `pdf_upload_id` 为真的条目 |
| `GET /api/literature/search?has_pdf_upload=false` | 排除 `pdf_upload_id` 为真的条目 |
| `GET /api/literature/search`（省略参数） | 不过滤，行为同 B6 之前 |
| `/literature` `<select name="view">` | 4 档：`all` / `pubmed_live` / `cnki_sample` / `uploaded_pdf`，submit 时派生 `{source, hasPdfUpload?}` |
| `LiteratureDataSourceBanner` | view = `all` → info 青绿；`pubmed_live` → live 蓝；`cnki_sample` → sample 橙；`uploaded_pdf` → upload 紫；title + summary 同步切换 |
| `DemoDataBanner` | 仍保留在 `app/literature/page.tsx` 站点级位置，不随 view 切换 |
| 表单 label 「文献来源」 | byte-identical 保留（既有断言锁定） |
| 结果卡片 metadata | `来源 ${getLiteratureSourceLabel(item.source_type)}` 不变（仍是后端 source_type 2 值） |
| disclaimer | 仍 `非诊断结论、需结合临床。` byte-identical |

## 调试痕迹

1. **runtime chunk_state 残留炸 `test_rag_api`**：Slice 1 跑全套 backend gauntlet 时 `test_rag_answer_endpoint_returns_ranked_citations_for_gut_skin_axis_question` 失败，`available_citation_count` 是 17 而非 16。原因：`data/runtime/chunk_state.json` 历史残留 20 条（seed 12 条），上次 dev 跑 PDF 上传链路时写进去的。修法同 B5 slice 1：`rm data/runtime/{literature_state,chunk_state}.json` 重 bootstrap。memory `runtime-state-bootstrap-stale-on-seed-change` 已经覆盖这条踩坑。
2. **`pnpm typecheck` 假阳性**：第一遍跑联合 gauntlet 时 typecheck 报 `.next/types/app/network/page.ts` 找不到模块 —— 这是从 B5 分支切回时 `.next` 缓存残留的产物（B6 分支上不存在 `/network` 路由）。重跑 `pnpm typecheck` 后 silent OK。
3. **`client-section-consistency.test.ts` 锁 `文献来源`**：第一版想把 label 改成「数据来源」，被既有断言挡下。最终决策：label 保留 `文献来源`（中文用户语义没问题），只改下拉选项集与底层 state 名。
4. **表单 select `name` 从 `source` 改 `view`**：保留 `name="source"` 会让 `new FormData(form).get("source")` 拿到的是 view 字符串（如 `cnki_sample`），与 backend 真实 `source` 枚举类型混淆。改 `name="view"` 后 `form.get("view")` 语义清晰，submit 时再走 `getLiteratureDataSourceFilter` 派生 backend 参数。

## 不在 B6 范围

- 不引入 KEGG / STRING / TCMSP / TCM-IDmap / 真实知网授权
- 不在 `/literature/[id]` 详情页加 view-aware banner（详情页已有 `DemoDataBanner compact`）
- 不动 `/rag` 页面的数据来源 banner（RAG 有自己的「应用来源」回显）
- 不把 view 状态写回 URL query param（保留为 React state，不支持 deep link 分享）
- 不为「上传 PDF」view 提供占位 seed（默认空列表 + 提示文案）
- 不改后端 source 枚举（仍是 `all / cn_literature / pubmed`；view 概念只活在前端）

## 验证

```bash
cd backend
.venv/bin/python -m ruff format --check app tests \
  && .venv/bin/python -m ruff check app tests \
  && .venv/bin/python -m mypy app \
  && .venv/bin/python -m pytest -q \
  && echo "BACKEND GAUNTLET GREEN"
# 145 passed（142 main baseline + 3 slice 1 新增；注意 B6 是基于 main 的，不含 B2-B5 累计）

cd frontend
pnpm test       # 89 passed (86 main baseline + 3 新增)
pnpm typecheck  # silent OK
pnpm build      # 5 routes（main baseline）；与 B5 合并后会回到 8 routes
```

**人工 smoke 路径**：

1. `fastapi dev` + `pnpm dev` 同启
2. `/literature` 默认 view = `all` → banner 青绿色「全部来源」
3. 切 view = `PubMed 实时` → banner 蓝色 + 文案含 NCBI 条款
4. 切 view = `CNKI sample` → banner 橙色 + 文案含 "seed 样本 / 未对接知网真实授权"
5. 切 view = `上传 PDF` → banner 紫色 + 文案含 "仅在本地 / 不公开 / 不分发"；结果列表为空（除非已上传过 PDF）
6. `curl -sS 'http://127.0.0.1:8000/api/literature/search?q=%E7%89%B9%E5%BA%94%E6%80%A7%E7%9A%AE%E7%82%8E&has_pdf_upload=true'` → 默认应返回 `total: 0`（seed 上没有挂 PDF）
7. 先走 `POST /api/uploads/pdf` 上传一份 PDF，然后重跑 #6 → `total: 1`

## 与 B5 的合并交互

B6 分支基于 main、不含 B2-B5。最终合并到 main 时建议：

- 先合 B2 → B3 → B4 → B5（线性 stack）让 main 累积到 163/99
- 再合 B6（独立线，rebase 后 push）；B6 改的文件（`backend/app/services/literature.py`、`app/api/literature.py`、`frontend/lib/api/literature.ts`、`frontend/components/LiteratureSearchClient.tsx`）与 B5 无 overlap，rebase 应该无冲突
- 合并后主干测试基数：≥ 168 backend / ≥ 102 frontend / 8 routes

## 下一颗候选 / 后续

- **C1 真实 Anthropic Claude API**（roadmap §3.3，3d）
- 修补项（不阻塞 B6 验收）：
  - 给「上传 PDF」view 在空列表时提供更显眼的 "如何上传 PDF" CTA（链到 `/literature/[id]` 上传面板）
  - view 状态写回 URL `?view=...` 以支持分享
  - banner copy 走 i18n 抽取（A 阶段尚未落地）
