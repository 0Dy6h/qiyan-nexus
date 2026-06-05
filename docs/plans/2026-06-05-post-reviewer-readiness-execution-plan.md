# 暂缓人工走查后的执行方案 — 2026-06-05

date: 2026-06-05  
status: draft  
context: 2026-06-05 reviewer readiness sprint 已完成，但人工 reviewer 最近没空，暂缓走查

---

## 背景

### 当前状态
- ✅ MVP-A 证据工作台已 100% 收尾（2026-06-04）
- ✅ MVP-B 网络药理学 mock 起步链路已落地
- ✅ Reviewer readiness sprint 已完成（2026-06-05）
  - 后端 request logging + middleware（`backend/app/core/logging_middleware.py`）
  - 内部预览 reviewer checklist（`docs/checklists/internal-preview-reviewer-walkthrough.md`）
  - 前端 error boundary 已审计（已健全）
  - 所有质量指标达到 A 级
- ✅ 后端测试：474 passed, 1 skipped
- ✅ 前端测试：158 passed
- ✅ E2E 测试：4 specs passed

### 当前分支
- `feat/multilingual-bge-m3-backend`（未合并到 main）
- 工作目录有未提交修改：
  - 修改：`backend/app/api/rag.py`、`backend/app/main.py`、`backend/app/services/rag.py`、`docs/quality-score.md`
  - 新增：`backend/app/core/logging_middleware.py`、`docs/checklists/`、`docs/handoffs/2026-06-05-reviewer-readiness-sprint.md`
  - `.trae/` 目录（可能是临时文件）

### 阻塞点
- 正式医生/科研人员 reviewer 最近没空，无法进行人工走查

---

## 执行方案：三条并行路径

基于当前状态，建议采用三条可并行推进的路径，不互相阻塞：

### **路径 A：技术债清理与分支整理（优先级：高，工作量：小）**

**目标**：清理当前分支状态，准备合并到 main

**任务列表**：
1. **审查并提交 reviewer-readiness 修改**
   - 审查当前工作目录的修改（logging middleware、RAG API 修改、quality-score 更新）
   - 确认这些修改独立于 multilingual BGE-M3 特性
   - 创建独立 commit：`feat(observability): add request logging middleware for internal preview`
   - 包含文件：
     - `backend/app/core/logging_middleware.py`
     - `backend/app/main.py`
     - `backend/app/api/rag.py`
     - `backend/app/services/rag.py`
     - `docs/quality-score.md`
     - `docs/checklists/internal-preview-reviewer-walkthrough.md`
     - `docs/handoffs/2026-06-05-reviewer-readiness-sprint.md`

2. **评估 multilingual BGE-M3 分支状态**
   - 根据 `docs/current-state.md`：BGE-M3 结论是**不翻默认**，仅保留为 `QIYAN_EMBEDDING_BACKEND=multilingual_bge_m3` opt-in
   - 评估当前分支与 main 的差异（git diff main）
   - 决策：
     - 如果 BGE-M3 代码已完整且测试通过 → 合并到 main（作为 opt-in 特性）
     - 如果仍有未完成工作 → 拆分为两个 PR（reviewer-readiness 先合并，BGE-M3 后续继续）

3. **清理 `.trae/` 临时目录**
   - 确认是否需要保留
   - 如不需要 → 添加到 `.gitignore` 或删除

**验收标准**：
- 所有 pending 修改已分类提交
- 后端测试全绿（474+ passed）
- 前端测试全绿（158+ passed）
- 分支状态清晰（main 或独立 feature 分支）

**预计工作量**：2-3 小时

---

### **路径 B：PostgreSQL/pgvector Spike（优先级：中，工作量：中）**

**目标**：评估生产级数据库路径，为未来扩展做技术验证

**背景**：
- 当前默认 runtime backend 是 JSON
- 2026-06-02 已落地 SQLite runtime backend（`QIYAN_STATE_BACKEND="sqlite"`）
- PostgreSQL/pgvector 是后续候选方向

**Spike 范围**（时间盒：1 天）：
1. **环境准备**
   - 本地 Docker 启动 PostgreSQL 15+ with pgvector extension
   - 确认连接与权限配置

2. **Schema 迁移设计**
   - 基于当前 `app/repositories/protocols.py` 设计 PostgreSQL schema
   - 关键表：`literature`、`chunks`、`network_tasks`、`pdf_uploads`
   - pgvector：为 `chunks` 表添加 `embedding vector(384)` 列（BGE-small-zh-v1.5 维度）

3. **Repository 实现原型**
   - 实现 `PostgresLiteratureRepository` 符合 `LiteratureRepositoryProtocol`
   - 实现 `PostgresChunkRepository` 符合 `ChunkRepositoryProtocol`
   - 使用 `asyncpg` 或 `psycopg3` 异步驱动
   - 保留 JSON/SQLite backend 作为默认，PostgreSQL 为 opt-in

4. **性能基准测试**
   - 对比 JSON / SQLite / PostgreSQL 三种 backend 的读写延迟
   - 测试场景：
     - 50 题 RAG eval 检索性能
     - 单次 literature 插入/更新
     - Bulk chunk 插入（模拟 PDF 解析后批量写入）

5. **记录 Spike 结论**
   - 写入 `docs/evaluations/2026-06-05-postgresql-pgvector-spike.md`
   - 包含：性能数据、迁移复杂度评估、推荐决策（是否进入默认路径）

**不包含**（避免 scope creep）**：
- ❌ 不做完整数据迁移脚本
- ❌ 不接入生产级连接池（如 PgBouncer）
- ❌ 不做 Alembic 迁移自动化
- ❌ 不替换默认 backend（保持 JSON 或 SQLite）

**验收标准**：
- PostgreSQL + pgvector 本地可运行
- 至少 2 个 repository protocol 实现完成
- 性能基准数据记录在 spike 文档
- 决策建议：是否值得投入生产化

**预计工作量**：1 天（8 小时）

---

### **路径 C：PDF 抽取质量改进 Spike（优先级：中，工作量：小到中）**

**目标**：改善 PDF 文本抽取质量，降低 `quality_warning` fallback 比例

**背景**：
- 当前使用 `pypdf` 做文本抽取
- A5 中文 PDF 验收：4 份样本中 3 份干净抽取，1 份触发 quality_warning（数字/表格乱码）
- OCR 和表格重建属于独立 spike，不扩进默认路径

**Spike 范围**（时间盒：半天到 1 天）：
1. **抽取质量启发式改进**
   - 当前 `backend/app/services/pdf_parser.py` 的质量检测逻辑审计
   - 改进候选：
     - 检测表格区域并跳过（避免乱码混入正文）
     - 检测页眉页脚并过滤
     - 改进中文字符比例阈值（当前可能过于保守）
     - 检测连续数字/公式区域并标记为 "non-text content"

2. **备选库评估**（可选）
   - `pdfplumber`：表格抽取更友好
   - `PyMuPDF (fitz)`：性能更好，但 AGPL 许可证需评估
   - 对比 pypdf vs pdfplumber 在 A5 的 4 份样本上的抽取质量

3. **测试数据扩展**
   - 收集 3-5 份**匿名化**的真实 AD 文献 PDF（不同格式：单栏/双栏/含表格/含公式）
   - 记录每份的抽取质量（字符数、中文比例、是否触发 fallback）
   - 不提交原始 PDF 到 git，只提交抽取结果摘要

4. **记录 Spike 结论**
   - 写入 `docs/evaluations/2026-06-05-pdf-quality-spike.md`
   - 包含：改进效果、备选库对比、推荐方案

**不包含**：
- ❌ 不接入 OCR（Tesseract/PaddleOCR），那是更大的 spike
- ❌ 不做表格结构化解析（需要专门的表格理解模型）
- ❌ 不改变 PDF 上传/解析的 API 契约

**验收标准**：
- 质量启发式改进后，A5 的 4 份样本重新测试
- 至少 1 个具体改进点（如表格过滤、页眉页脚去除）落地并测试通过
- Spike 文档记录改进效果与推荐方案

**预计工作量**：半天到 1 天（4-8 小时）

---

### **路径 D：L2 Governance 准备材料（优先级：低，工作量：小）**

**目标**：为未来 L2 决策准备完整的治理材料，但不做工程翻转

**背景**：
- ADR-0012 已完成 L1 受控启用路径
- L2（默认预览使用真实 LLM）决策仍被阻塞：
  - ① retrieval 中英跨语匹配：已部分缓解（cross recall 0.76）
  - ② BGE 阈值重校准：BGE=0.3 + NLI=0.5 profile 需要治理决策
  - ③ LLM claim 质量：已有 v2 prompt，但需持续验证
- 当前有 4 个 passed claims 的 reviewer packet（6/6 supported）
- Price SLI baseline 已记录（10 题估算 $0.005042）

**任务列表**：
1. **整理 L2 决策所需的所有证据**
   - 收集所有相关 evaluations 文档：
     - `2026-06-01-nli-real-distribution.md`（NLI gate 验证）
     - `2026-06-02-claim-quality-v2-live-validation.md`（v2 prompt 效果）
     - `2026-06-02-l2-passed-claims-reviewer-packet.md`（6/6 supported）
     - `2026-06-02-opencode-go-price-sli-baseline.md`（成本基线）
     - `2026-06-01-cross-lingual-retrieval.md`（跨语检索改进）
   
2. **编写 L2 Governance Proposal（草稿）**
   - 文件：`docs/proposals/2026-06-05-l2-default-preview-proposal.md`
   - 内容框架：
     - **Proposal**：是否将 `BGE=0.3 + NLI=0.5` profile 作为 L2 默认预览配置
     - **Pros**：4/10 回答可穿透，6/6 claims 通过 verdict，成本可控
     - **Cons**：BGE 预筛降低可能增加 false positive 风险，NLI gate 仍拦截 60% 回答
     - **Alternative**：保持 L1（受控 smoke），等待更好的 retrieval 或 LLM claim 质量
     - **Decision required by**：待定（等 reviewer 有空后再决策）
     - **Rollback plan**：`QIYAN_LLM_PROVIDER=deterministic` 即时回滚

3. **准备 L2 Walkthrough Checklist**
   - 基于 `docs/checklists/internal-preview-reviewer-walkthrough.md`
   - 新增专门针对 L2 profile 的验证步骤：
     - BGE=0.3 配置确认
     - NLI gate 运行确认
     - Passed claims 人工复核
     - 成本/延迟可接受性评估

**不包含**：
- ❌ 不做工程翻转（不改变默认 provider）
- ❌ 不启动正式 reviewer 走查（等人工有空）
- ❌ 不做新的 live validation 采样

**验收标准**：
- L2 governance proposal 草稿完成
- 所有相关证据文档已整理并链接
- Walkthrough checklist 更新完成

**预计工作量**：2-3 小时

---

## 推荐执行顺序

### Week 1（本周，2026-06-05 开始）

**Day 1-2：路径 A（技术债清理）**
- 优先级最高，阻塞后续工作
- 清理当前分支状态，准备合并
- 预计 2-3 小时

**Day 2-3：路径 B（PostgreSQL Spike）或 路径 C（PDF 质量 Spike）**
- 二选一，根据业务优先级
- 如果未来预期用户量大、需要扩展性 → 选 PostgreSQL
- 如果当前 PDF 抽取质量反馈多 → 选 PDF 质量

**Day 4-5：另一条 Spike（B 或 C）**
- 完成另一条 Spike
- 或开始路径 D（L2 Governance 准备）

### Week 2（下周）

**根据 Week 1 结果调整**：
- 如果 PostgreSQL spike 结论是"值得投入" → 开始生产化实现
- 如果 PDF quality spike 有明确改进 → 落地到默认路径
- 如果两者都完成 → 进入路径 D，准备 L2 治理材料

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| multilingual BGE-M3 分支与 main 冲突严重 | 延迟合并 | 先合并 reviewer-readiness 修改，BGE-M3 后续 rebase |
| PostgreSQL spike 发现性能不理想 | 浪费时间 | 严格时间盒（1 天），不深入生产化 |
| PDF quality spike 无明显改进 | 浪费时间 | 聚焦启发式，不接入 OCR/表格解析 |
| Reviewer 长期不可用 | L2 决策延迟 | L2 governance 材料准备好即可，决策可异步进行 |

---

## 验收标准（整体）

**Week 1 结束时**：
- ✅ 当前分支状态清晰（已合并或独立 feature branch）
- ✅ 至少完成 1 条 Spike（PostgreSQL 或 PDF quality）
- ✅ Spike 结论文档已写入 `docs/evaluations/`
- ✅ 后端测试全绿（474+ passed）
- ✅ 前端测试全绿（158+ passed）

**Week 2 结束时**：
- ✅ 两条 Spike 均完成（PostgreSQL + PDF quality）
- ✅ L2 governance proposal 草稿完成（如果 Week 1 有余量）
- ✅ 技术债清零（无 pending 修改）

---

## 备选方向（如果上述都完成）

1. **CI/CD 接入**
   - 当前测试靠本地手跑，可考虑 GitHub Actions 或其他 CI
   - 门禁：ruff format/check + mypy + pytest + pnpm test/typecheck/build
   - E2E 可选（需要 Playwright runner）

2. **Network 模块增强**
   - GO/KEGG 富集分析改进（真实 API 或更大的本地字典）
   - 网络图导出为 PNG/SVG
   - 报告导出为 PDF/Word

3. **Anthropic Provider 接入**
   - 当前 opencode_go 是优先 provider
   - Anthropic 作为备选，需要订阅/key

4. **Real-time collaboration spike**
   - 多用户协同标注文献/网络图
   - WebSocket 或 SSE 实时推送

---

## 关键文档引用

- `docs/handoffs/2026-06-05-reviewer-readiness-sprint.md` — 今日完成的工作
- `docs/handoffs/2026-06-04-internal-preview-baseline.md` — 内部预览基线
- `docs/plans/2026-06-04-mvp-a-closeout.md` — MVP-A 收尾对账
- `docs/current-state.md` — 当前能力边界
- `docs/adr/0012-real-llm-enablement.md` — L2 治理决策框架
- `README.md` — API 示例

---

**生效日期**：2026-06-05  
**下次审查**：完成路径 A 后，根据 Spike 结果调整
