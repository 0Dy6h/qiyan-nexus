# 2026-06-15 Session Closeout：试用就绪 + 生产配置校验修复

> Session Date: 2026-06-15
> Branch: `chore/preview-trial-readiness`（PR [#17](https://github.com/0Dy6h/qiyan-nexus/pull/17) → `main`，OPEN，可干净合并）
> 起点诉求：读取项目进度并为下一步开发制定高质量执行方案
> Status: ✅ Phase 0（仓库卫生）+ Phase 1.1/1.2（试用就绪工程）完成；后续 gate 转为真人 reviewer 招募

---

## 一、今日目标与完成情况

| 项 | 状态 | 产出 |
|---|---|---|
| 核清真实项目状态 | ✅ | 发现本地分支与 `origin/main` 严重偏离，docs 来自陈旧分支 |
| 🔴 凭证泄漏补救 | ✅ | 旧 key 已轮换，泄漏 commit 清除（详见二.2） |
| 🔴 HIGH bug 修复 | ✅ | 生产配置校验死代码 → TDD 修复，commit `8346ec9` |
| 绿色基线确认 | ✅ | `verify-local.ps1` 全绿（backend 562→566 / frontend 207 / build），187.8s |
| 1.1 内部预览证据包 | ✅ | open+token 全流程通过，request-id 齐全 |
| 1.2 云端+token 部署 runbook | ✅ | `docs/guides/cloud-trial-deployment-runbook.md`，commit `3a75aec` |
| 推送 + 开 PR | ✅ | PR #17 OPEN against main |
| 方向决策 | ✅ | shadcn 暂存不采用；主线走 reviewer sign-off + 小范围试用 |

---

## 二、关键发现与决策

### 1. 真实状态核清（重要：之前在陈旧分支上看 docs）
- **权威态 = `origin/main @ 2c19297`**（已含安全 PR #16）。docs（current-state / roadmap）与之一致。
- 之前的工作分支 `fix/security-fixes-clean` 是 PR #16 合并前的旧分支，其安全 commit 已被 squash 进 main，**内容冗余**。
- 本地 `main` 曾严重偏离 `origin/main`（7 个未推送 commit，含一次 **shadcn/ui + Tailwind v4 前端迁移** 0bf0b41）。已 reset 回 `origin/main`。
- **shadcn 迁移决策：停到 `spike/shadcn-tailwind` 分支保留，暂不采用**（与 CLAUDE.md 锁定的 AntD 6 + 内联样式基线冲突）。该 spike 分支同时保住了本地 main 偏离的其余 commit（多语 embedding spike 9296164、CORS/NLI 修复 1866b38、dedup refactor 6ad8cd8），未来可按需 cherry-pick。

### 2. 凭证泄漏补救（已闭环）
- 旧 DeepSeek key 曾明文写进 `fix/security-fixes-clean` 的 commit `3f6ab04`（DeepSeek 集成 handoff 文档），**但从未推送到 GitHub**（已确认不在任何 remote ref）。
- 处理：用户已在 DeepSeek 控制台**轮换** key；删除 `fix/security-fixes-clean`（本地+远程），泄漏 commit 已不可达；新 key **仅**存入 gitignored `backend/.env`（**值不写入任何被跟踪文件 / 文档 / 本 handoff**）。
- 加了 `.git/hooks/pre-commit` secret guard（grep `sk-[A-Za-z0-9]{20,}`，已实测拦截）。注意它在 `.git/hooks/` 下、不随仓库分发；换机器需重装。

### 3. 🔴 HIGH bug：生产配置校验从未执行（已修）
- `backend/app/core/config.py` 的 `Settings.__post_init__` 被错误缩进进 `_bool_env` 函数体、且在 `return` 之后 → **不可达死代码，不是 dataclass 方法**。
- 后果：安全审查 HIGH-6"环境变量验证"（要求 ≥1 个 LLM key、upload 目录存在可写、grounding 阈值 ∈ [0,1]）**在 #16 上线后一直 fail-open**。`mypy --strict` 与 `pytest` 都没抓到（语法合法 + 无测试覆盖）。
- 修复：把 `__post_init__` 移回 `Settings` 类体；新增 4 个生产校验测试（RED：2 个 DID-NOT-RAISE → GREEN）。全门禁绿（566 passed）。
- **副作用（务必知悉）**：现在设 `ENVIRONMENT=production` 会**真的**执行这三项校验。deterministic 试用不需要 LLM，但校验仍要求 key 非空 → runbook 用占位 key 满足（provider 留 deterministic 故永不调用）。

---

## 三、交付物与验证

- **Commits**（在 `chore/preview-trial-readiness`，PR #17）：
  - `8346ec9` fix(security): production config validation never ran (dead __post_init__)
  - `3a75aec` docs(guides): cloud single-machine + token trial deployment runbook
  - （本 handoff 为第 3 个 commit）
- **证据包**：`.tmp/internal-preview-evidence/20260615-211935/`（gitignored）。open+token 两 profile：literature 检索/过滤、PDF 上传(201)→auto-parse(pypdf-text-preview)、rag_answer(citations=2)、rag_export、network analyze/result/report(mock, chains=5, enrichment=14) 全 200/201，request-id 齐全。
- **门禁**：`ruff format/check`、`mypy app`（strict, 66 files）、`pytest -q`（566 passed/1 skipped）、frontend test 207 / typecheck / build 全绿。

---

## 四、下一步 / 交接

### 真正的 gate（在用户侧，工程替代不了）
- **1.3 招募 2-5 位真人 reviewer**（医生 + 科研），按 `docs/evaluations/2026-06-05-reviewer-feedback.md` 填正式反馈。路线图把 L2 治理、网络真实计算、生产化全压在这道真人 sign-off 上。

### 可不依赖 reviewer 推进的（下次入口）
- **1.4 reviewer 走查任务单**（未做）：4 条场景（文献四来源检索 / PDF 上传→解析→RAG 引用 / RAG 答案+免责声明 / 网络药理学 mock 边界），对齐 `docs/evaluations/2026-06-06-small-scale-trial-feedback.md`。**这是下次最直接的续接任务。**
- 合并 PR #17（用户自行 merge）让生产校验修复落 main。

### 注意事项 / 踩过的坑
1. **跑含中文路径的 .ps1 用 `pwsh`（PS7）不要 `powershell.exe`（5.1）** —— 脚本 UTF-8 无 BOM，5.1 按 GBK 读中文字面量会乱码（`collect-internal-preview-evidence.ps1` 默认 PdfPath 指向中文 PDF 名就栽过）。`collect-...ps1 -PdfPath ""` 可触发 `local-review-pdfs` 自动选最大 PDF 兜底。
2. **应用不读 `.env`**（代码无 `load_dotenv`）。本地 demo 要手动 export env；生产用 systemd `EnvironmentFile`。`backend/.env` 仅作本地存放，当前不被任何代码自动加载。
3. **CORS 硬编码** `localhost:3000`/`127.0.0.1:3000`（`app/main.py`）。runbook 用同源 nginx 反代规避；分域名部署须改代码。
4. **前端只烤一个 token**（`NEXT_PUBLIC_QIYAN_ACCESS_TOKEN`，构建期）。无法按人做 API 归因，靠反馈表。
5. **试用必须 deterministic profile**：别让历史 `QIYAN_GROUNDING_SEMANTIC_THRESHOLD=0`（grounding 绕过）溜进试用环境。

### 分支地图
- `chore/preview-trial-readiness` — 当前工作分支 = origin/main + 安全修复 + runbook（+ 本 handoff）。PR #17。
- `spike/shadcn-tailwind` — 暂存的 shadcn 迁移 + 其余本地 main 偏离 commit，未采用。
- `main` / `origin/main @ 2c19297` — 权威态；PR #17 合并后含生产校验修复。
- 已删除：`fix/security-fixes-clean`（本地+远程，含已清除的泄漏 commit）。

---

## 五、给下一位开发者
1. 先 `git fetch` 看 PR #17 是否已合并；若已合并，从 `origin/main` 开新分支。
2. 最直接的续接任务是 **1.4 走查任务单**（无外部依赖）。
3. 真人 reviewer sign-off 是进入 L2/网络真实计算/生产化的**唯一前置**，AI 预审与内部代走都不能替代。
4. 默认运行边界不变：deterministic provider + keyword retrieval，不接真实 LLM / pgvector / Neo4j / Celery。
