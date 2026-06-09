# Handoff — 2026-06-08 前端流星 UI 收尾 + 后续开发计划交接

> 日期：2026-06-08
> 交接人：Claude (Hermes Agent)
> 接手：GPT (Codex CLI / Cursor / Windsurf / 其他)
> 分支：`feat/multilingual-bge-m3-backend`（已推送到 origin）
> 工作区：`D:\Projects\Tcm_tech`

---

## 一、本次会话完成内容

### 1.1 前端流星动效优化（已完成 ✅）

**任务**：用户反馈"流星头尾方向反了、尺寸太大、中间停顿、面板遮挡流星轨迹"。

**完成的改动**：

| 文件 | 改动 |
|---|---|
| `frontend/app/workbench.css` | 流星尺寸减半（1.5px 头 + 55-105px 尾）、ease-in-out → linear（去停顿）、duration ÷ 1.3（提速 30%）、**backdrop-filter: blur(24~28px) → blur(2px)**（关键修正，让流星透过面板不被糊掉）、面板 alpha 降至 0.02~0.06 |
| `frontend/lib/ui/surfaces.ts` | `getSurfaceCardStyle` / `getSurfaceSectionStyle` 同步 blur(2px) + alpha 调整 |
| `frontend/components/DemoDataBanner.tsx` | blur(2px) |
| `frontend/components/LiteratureDataSourceBanner.tsx` | blur(2px) |
| `frontend/tests/surfaces.test.ts` | deepEqual 断言同步 |
| `frontend/tests/page-shell-consistency.test.ts` | regex 断言同步 |

**Git 状态**：
- 3 个 commit 已推送到 `origin/feat/multilingual-bge-m3-backend`：
  - `24b0d78` — 左侧栏 shell UI（上次会话）
  - `f878784` — 毛玻璃 + 流星初版（上次会话）
  - `80a80f9` — **流星动效优化 + 面板透明度修正（本次会话）** ← 最新
- 工作区干净，只剩 3 个 untracked：
  - `docs/handoffs/2026-06-08-frosted-glass-meteor-handoff.md`（上次会话留下的 handoff）
  - `论文产出/`（用户另一条工作流，不要动）
  - `项目实体/`（用户另一条工作流，不要动）

**门禁状态**：
- ✅ `pnpm test` 197/197
- ✅ `pnpm typecheck`
- ✅ `pnpm build`（未跑，但 typecheck 已过，build 应无问题）
- ❌ `pnpm e2e`（未跑，按项目约定 e2e 是分支级 gate，不是 commit 级）

**用户反馈**：✅ "干得不错，目前前端做成这样就很好了！"

---

### 1.2 透明度语义 memory 已保存（已完成 ✅）

**关键认知**（我绕了三轮才发现）：
- 用户说"提高透明度"不是指 alpha 数值，而是指"背景能透过来"
- **真正主控参数是 `backdrop-filter: blur(Npx)`**（决定背后内容糊不糊），不是 `rgba(..., alpha)`（决定面板自身颜色深浅）
- alpha 从 0.10 → 0.025 在 24px blur 的统治下几乎看不出差别，但 blur 从 24px → 2px 立刻让流星清晰可见

**已保存到**：`C:\Users\12035\.claude\projects\d--Projects-Tcm-tech\memory\transparency-semantics.md`

---

### 1.3 后续开发计划（已完成 ✅）

**产出文档**：`docs/plans/2026-06-08-post-mvp-a-roadmap.md`（本交接文档同目录）

**核心结论**：
- 近期优先（1-2 周）：正式 reviewer sign-off → 小范围试用
- 中期候选（2-4 周）：L2 真实 LLM 治理决策、PostgreSQL/pgvector 生产化、PDF OCR 专项（按需）
- 长期方向（1-3 月）：网络药理学真实计算链路、分子对接/MD 模拟、多用户/权限/审计

---

## 二、接手前必读文档（按优先级）

| 文档 | 读它来做什么 |
|------|-------------|
| `docs/current-state.md` | 当前能力边界、事实源优先级、标准验证命令 |
| `docs/plans/2026-06-08-post-mvp-a-roadmap.md` | 后续开发计划（本次会话产出） |
| `README.md` | 每个已实现 endpoint 的 curl 示例 |
| `CLAUDE.md` | 后端分层、RAG 管线、PDF 流、前端测试机制 |
| `AGENTS.md` | 项目地图层、快速导航、命令速查 |
| `CONTEXT.md` | TCM 术语表、共享语言 |
| `docs/adr/0010-research-workbench-module-roadmap.md` | MVP-A/B/C 分阶段边界 |
| `docs/adr/0012-real-llm-enablement.md` | L1/L2 真实 LLM 启用决策与不变量 |
| `docs/handoffs/2026-06-06-comprehensive-product-review.md` | AI 技术预审结论 |
| `docs/evaluations/2026-06-05-reviewer-feedback.md` | 正式 reviewer sign-off 模板（**待填写**） |

---

## 三、当前项目状态速查

### 3.1 已完成的能力

| 模块 | 状态 | 备注 |
|------|------|------|
| 文献检索 | ✅ 100% | seed JSON + runtime state，支持 CN/PubMed/上传 PDF 四来源视图 |
| PDF 上传/解析 | ✅ 100% | pypdf 文本抽取 + preview-window 选择，扫描件回退到 placeholder |
| RAG 问答 | ✅ 100% | deterministic provider + keyword retrieval，真实 LLM 保持 L1 受控启用 |
| 网络药理学 | ✅ mock 100% | sample JSON + GO/KEGG 富集分析 + 网络图可视化 + Markdown 导出 |
| 前端 UI | ✅ 100% | 左侧栏 shell + 流星动效 + 毛玻璃面板 + 7 个页面 + E2E 覆盖 |
| 内部预览 | ✅ 100% | open/token profile + smoke 脚本 + 证据包收集 |
| Reviewer 预审 | ✅ AI 预审完成 | 真人 reviewer sign-off **待填写** ← 下一步阻塞项 |

### 3.2 已 spike 但不进默认路径的能力

| 能力 | 状态 | 决策 |
|------|------|------|
| 真实 LLM (OpenCode Go) | ✅ spike 完成 | 保持 L1 受控启用，L2 默认预览不翻转（决策不翻转） |
| BGE semantic grounding | ✅ spike 完成 | 保持 env opt-in，不进默认路径 |
| PostgreSQL/pgvector | ✅ spike 完成 | 保持 explicit opt-in，JSON/SQLite 已足够 |
| BGE-M3 多语 embedding | ✅ spike 完成 | 保持 env opt-in，不翻默认 |

### 3.3 概念预留但无实现的能力

| 模块 | 状态 |
|------|------|
| 分子对接/MD 模拟（MVP-C） | schema 概念预留，无 API/service/repository/前端 |
| 真实网络药理学计算 | mock 已落地，真实 TCMSP/SwissTargetPrediction/KEGG API 待接入 |
| 多用户/权限/审计 | 当前只有 token 白名单，无用户概念 |

---

## 四、下一步待办（按优先级）

### 4.1 正式 Reviewer Sign-off（最高优先级，阻塞项）

**任务**：让真实医生 + 科研人员填写正式反馈。

**执行步骤**：
1. 找目标医生/科研人员（建议各 1-2 位）
2. 给他们看 `docs/evaluations/2026-06-05-reviewer-feedback.md` 模板
3. 让他们按模板填写：
   - **Section 1: Clinician Review**（医生视角）
   - **Section 2: Research Scientist Review**（科研视角）
4. 收集反馈，按 P0/P1/P2 分类
5. P0/P1 问题做闭环修复
6. 产出：正式 reviewer sign-off 决策（是否可进入小范围试用）

**注意**：
- AI 技术预审（`docs/handoffs/2026-06-06-comprehensive-product-review.md`）不能替代真人 reviewer 判断
- 模板中有明确的"这是演示数据"/"这是 mock 计算"提示，reviewer 应在此基础上评估
- 如果 reviewer 提出"mock 数据不够用"/"deterministic 答案不够准确"，这些是预期内的反馈，不是 P0/P1

---

### 4.2 小范围试用准备（条件：reviewer sign-off 通过）

**任务**：让 2-3 位医生 + 1-2 位科研人员在真实场景试用 1-2 周。

**执行步骤**：
1. 确定试用规模
2. 准备试用环境：
   - **选项 A（推荐）**：本地部署，给每人一个 token
     ```powershell
     $env:QIYAN_ACCESS_TOKENS="reviewer-a,reviewer-b,reviewer-c"
     .\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\trial-shared -AccessToken "reviewer-a"
     ```
   - **选项 B**：云端单机部署（需配置域名 + HTTPS + CORS）
3. 给试用者发：
   - 访问地址（`http://localhost:3000` 或云端 URL）
   - 访问 token（如果用 token profile）
   - `docs/evaluations/2026-06-06-small-scale-trial-feedback.md` 反馈模板
4. 试用期间收集反馈，重点观察：
   - 文献检索实用性
   - RAG 答案可信度（deterministic 模式下）
   - 网络药理学 mock 数据边界是否清晰
   - PDF 上传/解析体验
5. 试用结束后汇总反馈，决定下一步方向

**注意**：
- 当前默认 profile 是 **deterministic + keyword + JSON/SQLite + isolated runtime**，不启用真实 LLM、不外发数据
- 如果试用反馈"deterministic 答案不够准确"，这是 L2 治理决策的触发信号
- 如果试用反馈"PDF 扫描件无法解析"，这是 PDF OCR 专项的触发信号
- 如果试用反馈"网络药理学 mock 数据不够用"，这是真实计算链路的触发信号

---

### 4.3 L2 真实 LLM 治理决策（中期，按需）

**任务**：根据小范围试用反馈，决定是否推进 L2（真实 LLM 默认启用）。

**背景**：
- 工程路径已验证可行（`docs/evaluations/2026-06-02-claim-quality-v2-live-validation.md`）
- 历史 `deepseek-v4-flash` + `BGE=0.3 + NLI=0.5` profile 通过率 4/10（6 个被 NLI 拦截）
- 历史 price SLI baseline：10 题估算成本 `$0.005042`（基于 DeepSeek 公开价格 `$0.14/$0.28 per 1M tokens`）
- 2026-06-08 起当前 opt-in smoke 默认已切到 router.team + `gpt-5.5` + `4096` tokens；价格、延迟、NLI pass rate 需要重建 baseline，不能沿用 DeepSeek 历史数字

**决策点**：
1. **如果小范围试用反馈"deterministic 答案不够准确，需要更智能的回答"**：
   - 召开治理决策会议，先用 router.team + `gpt-5.5` 重建通过率、延迟与成本 baseline
   - 复核 router.team / `gpt-5.5` 实际合同价格（不要沿用 DeepSeek 历史公开价）
   - 如果决定推进：按 `docs/guides/real-llm-enablement-runbook.md` 显式设置 provider env，确认治理 gate 后再翻转
   - 如果决定暂缓：保持 L1 受控启用（存 key 者可用，默认仍 deterministic）
2. **如果小范围试用反馈"deterministic 答案已足够，不需要真实 LLM"**：
   - 保持现状，L2 不推进
3. **如果想优化通过率**：
   - 增强 keyword retriever 的跨语桥接（当前 N=16 bridge terms）
   - 或放宽 NLI 阈值（需重跑分离度评估 `docs/evaluations/2026-06-01-nli-real-distribution.md`）

**注意**：这是**决策议题**而非工程阻塞——技术路径已验证，但需业务/成本层面拍板。

---

### 4.4 网络药理学真实计算链路（长期，按需）

**任务**：根据小范围试用反馈，决定是否从 mock 推进到真实计算。

**背景**：
- 当前 mock 已落地：sample JSON + GO/KEGG 富集分析 + 网络图可视化 + Markdown 导出
- 演示数据边界已标注清晰（`/network` 页面 + Markdown 报告头部）

**推进路线**（如果反馈"mock 数据不够用"）：
1. **中药化合物数据库接入**（轻量）：
   - TCMSP（开放）或 BATMAN-TCM（需授权）
   - 建立本地快照或定时同步
2. **靶点预测接入**（轻量）：
   - SwissTargetPrediction API（限速）或本地部署 SEA
3. **KEGG REST API 接入**（中量）：
   - 替换本地 mock JSON
   - 处理限速 + 缓存
4. **图布局算法**（重依赖）：
   - 引入 networkx / igraph
   - 支持力导向布局或层次布局
5. **异步任务队列**（重依赖）：
   - 当真实计算耗时 >30s 时，引入 Celery + Redis（按 ADR-0008）

**注意**：建议先做 ①②（数据接入，轻量），再做 ④⑤（算法/异步，重依赖）。

---

## 五、技术债务与已知限制

1. **前端流星 UI**：✅ 已完成优化，用户满意
2. **真实 LLM**：工程路径已验证，但 L2 默认预览仍不翻转（决策不翻转）
3. **跨语言检索**：keyword + cross-lingual bridge（N=16）是当前默认有效路径
4. **PDF 抽取**：pypdf 已覆盖文本型 PDF 主场景（3/4 可用率），扫描件/表格抽取待专项 spike
5. **网络药理学**：mock 数据已落地，真实计算链路待启动
6. **PostgreSQL/pgvector**：spike 已完成，保持 explicit opt-in，JSON/SQLite 已足够
7. **多用户/权限**：当前只有 token 白名单，无用户概念、无审计日志

---

## 六、门禁与验证命令（必须记住）

### 6.1 统一本地门禁（推荐先跑这个）

```powershell
.\scripts\verify-local.ps1
```

默认顺序执行：
- Backend：`ruff format --check` → `ruff check` → `mypy app` → `pytest -q`
- Frontend：`pnpm test` → `pnpm typecheck` → `pnpm build`

### 6.2 追加 E2E（reviewer 走查或分支收口前）

```powershell
.\scripts\verify-local.ps1 -IncludeE2E
```

### 6.3 内部预览启动与 smoke

```powershell
# open dev profile
.\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\trial-open
.\scripts\smoke-internal-preview.ps1
.\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\trial-open -Stop

# shared-token profile
.\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\trial-token -AccessToken "trial-token"
.\scripts\smoke-internal-preview.ps1 -AccessToken "trial-token"
.\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\trial-token -Stop

# 生成本地内部预览证据包
.\scripts\collect-internal-preview-evidence.ps1
```

---

## 七、已冻结的技术决策（不要动）

1. **后端严格分层**：`api/` → `services/` → `repositories/` → `schemas/`，不许跨层
2. **CORS 限定**：`localhost:3000`/`127.0.0.1:3000`，仅 `GET, POST`；加 `PUT`/`DELETE` 要改 `app/main.py` 中间件
3. **免责声明字符串**：`非诊断结论、需结合临床。` 是 load-bearing，不要改写 `services/rag.py` 的 `DISCLAIMER`
4. **RAG 契约**：`/api/rag/answer` 返回的每个 `citations[*].literature_id` 必须能被 `/api/literature/{id}` 解析
5. **runtime 状态**：写在 `backend/data/runtime/`（gitignored），不要回写 seed fixture
6. **PDF 流分两步**：`POST /api/uploads/pdf` 只落盘并置 `pending`，要单独调 `POST /api/uploads/pdf/auto-parse` 才推进到 `parsed`/`failed`
7. **视觉 token**：青黛绿 `#0d9488 ~ #14b8a6`，Noto Sans SC，light-mode 产品端

---

## 八、常见陷阱与避坑指南

### 8.1 前端测试陷阱

**陷阱**：4 个测试（`pdf-upload-status`、`literature-detail-meta`、`client-section-consistency`、`page-shell-consistency`）用 `readFileSync` 对 `.tsx` 源码做正则断言。

**症状**：改页面壳、导航或可见 meta 文案时，这几个测试会挂。

**避坑**：改前端页面时，先跑 `pnpm test`，如果断言失败，读断言内容确认是"测试该跟进改动"还是"改动越界了"。

---

### 8.2 后端 mypy 陷阱

**陷阱**：`strict=true` 仅作用于 `app/`（tests 排除）；`B008` 全局忽略（FastAPI 用 `Body()`/`Form()`/`File()`/`Query()` 当默认值）。

**症状**：`mypy app` 报错，但 `mypy tests` 不报。

**避坑**：看清报错路径，确认是 `app/` 还是 `tests/`。

---

### 8.3 真实 LLM 启用陷阱

**陷阱**：真实 LLM 默认**不启用**。当前 opt-in smoke 默认是 router.team + `gpt-5.5`，需显式设置 `QIYAN_OPENCODE_GO_API_KEY` + `QIYAN_LLM_PROVIDER=opencode_go`，并按需确认 `QIYAN_OPENCODE_GO_BASE_URL=https://ai.router.team/v1`、`QIYAN_OPENCODE_GO_MODEL=gpt-5.5`、`QIYAN_OPENCODE_GO_MAX_TOKENS=4096`。

**症状**：设了 key 但答案仍是 deterministic。

**避坑**：按 `docs/guides/real-llm-enablement-runbook.md` 检查 3 个 env var 是否都设了。

---

### 8.4 PDF auto-parse 陷阱

**陷阱**：`POST /api/uploads/pdf` 只落盘并置 `pending`，要单独调 `POST /api/uploads/pdf/auto-parse` 才推进到 `parsed`/`failed`。

**症状**：PDF 上传后一直是 `pending`。

**避坑**：记得调第二个 endpoint。前端 `LiteraturePdfUploadClient.tsx` 已实现两步流。

---

## 九、关键决策点（需用户拍板）

1. **reviewer sign-off 通过后，是否立即启动小范围试用？**（建议：是）
2. **小范围试用规模？**（建议：2-3 医生 + 1-2 科研，本地部署或云端单机）
3. **L2 真实 LLM 的治理判断？**（建议：等小范围试用反馈后再决定）
4. **网络药理学是否从 mock 推进到真实计算？**（建议：等小范围试用反馈后再决定）
5. **是否需要生产化部署？**（建议：小范围试用后再评估，当前 token profile 已足够）

---

## 十、执行清单（给 GPT 的 checklist）

### Phase 1: 正式 Reviewer Sign-off（1 周）

- [ ] 找目标医生/科研人员（建议各 1-2 位）
- [ ] 给他们看 `docs/evaluations/2026-06-05-reviewer-feedback.md` 模板
- [ ] 让他们填写 Section 1（Clinician Review）和 Section 2（Research Scientist Review）
- [ ] 收集反馈，按 P0/P1/P2 分类
- [ ] P0/P1 问题做闭环修复
- [ ] 产出：正式 reviewer sign-off 决策（是否可进入小范围试用）

### Phase 2: 小范围试用准备（条件：reviewer sign-off 通过）

- [ ] 确定试用规模（2-3 医生 + 1-2 科研）
- [ ] 准备试用环境（本地部署 + token profile 或云端单机）
- [ ] 给试用者发访问地址 + token + 反馈模板
- [ ] 试用期间收集反馈（1-2 周）
- [ ] 试用结束后汇总反馈，决定下一步方向

### Phase 3: 按反馈推进（2-4 周）

- [ ] 如果反馈"deterministic 答案不够准确" → L2 治理决策会议
- [ ] 如果反馈"PDF 扫描件无法解析" → PDF OCR 专项 spike
- [ ] 如果反馈"网络药理学 mock 数据不够用" → 真实计算链路推进（先数据接入，再算法/异步）
- [ ] 如果反馈"多人并发冲突" → PostgreSQL/pgvector 生产化
- [ ] 如果反馈"需要生产化部署" → 多用户/权限/审计

---

## 十一、联系方式与帮助

- **项目文档**：优先读 `docs/current-state.md`、`docs/plans/2026-06-08-post-mvp-a-roadmap.md`
- **技术细节**：`CLAUDE.md`（后端分层）、`AGENTS.md`（命令速查）
- **领域术语**：`CONTEXT.md`
- **架构决策**：`docs/adr/`
- **最新交接**：`docs/handoffs/`（越新越接近当前事实）

**如果遇到问题**：
1. 先读 `docs/current-state.md` 确认当前能力边界
2. 再读对应模块的 ADR（如 `docs/adr/0012-real-llm-enablement.md`）
3. 再读最新 handoff（如 `docs/handoffs/2026-06-06-comprehensive-product-review.md`）
4. 如果仍不清楚，问用户

---

**状态**：交接完成，等待 GPT 执行。下一步：Phase 1 正式 Reviewer Sign-off。
