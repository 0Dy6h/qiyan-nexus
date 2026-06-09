# Qiyan Nexus 后续开发计划

> 制定日期：2026-06-08
> 基于状态：MVP-A 已收尾，MVP-B 网络药理学 mock 已落地，前端流星 UI 已优化完成
> 分支：`feat/multilingual-bge-m3-backend`（已推送 3 个 commits）

---

## 一、近期优先（1-2 周内，高价值/低风险）

### 1.1 正式 Reviewer Sign-off（阻塞项）

**现状**：
- ✅ 内部代走彩排已完成（`docs/handoffs/2026-06-05-internal-reviewer-rehearsal.md`）
- ✅ AI 技术预审已完成（`docs/handoffs/2026-06-06-comprehensive-product-review.md`，未发现 P0/P1）
- ❌ 真实医生 + 科研 reviewer 的正式反馈仍待填写

**下一步**：
1. 让目标医生/科研人员按 `docs/evaluations/2026-06-05-reviewer-feedback.md` 模板填写正式反馈
2. 对 P0/P1 问题（如有）做闭环修复
3. 产出：正式 reviewer sign-off 决策（是否可进入小范围试用）

**优先级理由**：所有后续推进（L2 治理决策、小范围试用、功能增强）的前提是真实用户已验证基线可用性。AI 预审不能替代领域专家判断。

---

### 1.2 小范围试用准备（条件：reviewer sign-off 通过）

**现状**：
- ✅ 内部预览脚本已齐全（`scripts/run-internal-preview.ps1`、`scripts/smoke-internal-preview.ps1`、`scripts/collect-internal-preview-evidence.ps1`）
- ✅ open/token profile 均可用
- ❌ 尚未进入真实医生/科研场景的小范围试用

**下一步**：
1. 确定试用规模（建议 2-3 位医生 + 1-2 位科研人员）
2. 准备试用环境（可用当前 token profile + 本地部署，或云端单机部署）
3. 按 `docs/evaluations/2026-06-06-small-scale-trial-feedback.md` 收集反馈
4. 重点观察：
   - 文献检索实用性
   - RAG 答案可信度（deterministic 模式下）
   - 网络药理学 mock 数据边界是否清晰
   - PDF 上传/解析体验

**优先级理由**：早期真实场景反馈能发现 AI 预审/内部代走无法触及的实际痛点（如术语不匹配、工作流断点、信任边界），避免后续方向性返工。

---

## 二、中期候选（2-4 周，需治理决策或专项 spike）

### 2.1 L2 真实 LLM 治理决策（治理议题，非工程翻转）

**现状**：
- ✅ 工程前置已完成：claim-quality v2 真实采样（历史 `deepseek-v4-flash` 10 题，4 passed / 6 NLI blocked）
- ✅ 技术验证已完成：delta-only reviewer packet 显示 6/6 passed claims 为 supported
- ✅ 历史 price SLI baseline 已建立：10 题估算成本 `$0.005042`（DeepSeek 公开价）
- ❌ 当前阻塞：2026-06-08 已切到 router.team + `gpt-5.5` opt-in smoke；需重建该 profile 的价格、延迟、NLI pass rate baseline，并在生产预算前复核真实合同价格

**下一步**：
1. **治理决策会议**：先用 router.team + `gpt-5.5` 重跑通过率、blocked 原因、延迟与成本采样
2. **价格复核**：确认 router.team / `gpt-5.5` 实际合同价格；DeepSeek `$0.14/$0.28 per 1M tokens` 只作为历史参考
3. **如果决定推进 L2**：更新 `docs/guides/real-llm-enablement-runbook.md` 与 baseline 记录，显式设置 provider env 后再全局翻转
4. **如果决定暂缓**：保持 L1 受控启用
5. **如果决定优化通过率**：增强 keyword retriever 跨语桥接或放宽 NLI 阈值（需重跑分离度评估）

**优先级理由**：这是决策议题而非工程阻塞。建议在小范围试用收集反馈后再决定（用户可能对 deterministic 模式已足够满意，或反而要求更高质量）。

---

### 2.2 PostgreSQL/pgvector 生产化（可选，spike 已完成）

**现状**：
- ✅ spike 已完成：`docs/evaluations/2026-06-05-postgresql-pgvector-spike.md`
- ✅ 当前结论：实测不支持切换默认，默认仍为 JSON，SQLite 仍是当前可选本地持久化推荐
- 适用场景：多人并发、真实 pgvector ANN 检索、生产数据库治理需求

**下一步**：
- **如果出现以下需求之一，再启动生产化 ADR**：
  - 多人同时上传 PDF 冲突（小范围试用反馈）
  - 需要 pgvector ANN 检索（vector/hybrid retrieval 成为主推荐）
  - 需要生产数据库治理（PITR、replica、audit log）
- **否则保持现状**：JSON/SQLite 已足够支撑单用户/小团队内部预览

**优先级理由**：spike 已闭环，无技术阻塞。按需启动，避免过早优化。

---

### 2.3 PDF 抽取质量专项（可选，spike 已完成）

**现状**：
- ✅ A5 中文 PDF 验收已完成：4 份真实样本，3/4 干净中文抽取 + 1/4 quality_warning fallback
- ✅ 抽取质量 spike 已完成：pypdf 启发式增强无 regression，pdfplumber 对照不支持切换默认
- 后续候选：OCR（扫描件/图片型 PDF）、表格重建（结构化数据抽取）、preview-window 选择优化

**下一步**：
- **如果小范围试用反馈"扫描件 PDF 无法解析"成为高频痛点**：
  - 启动 OCR 专项（可选方案：Tesseract、PaddleOCR、商业 API）
- **如果需要表格数据抽取**：
  - 启动表格重建专项（camelot-py、tabula-py）
- **否则保持现状**：当前 pypdf preview-window 已覆盖文本型 PDF 主场景

**优先级理由**：当前 3/4 文本型 PDF 可用率已足够内部预览；扫描件/表格抽取是专项增强，应在真实需求驱动下启动。

---

## 三、长期方向（1-3 月，需架构设计或重依赖）

### 3.1 网络药理学真实计算链路（MVP-B 深化）

**现状**：
- ✅ 当前是 mock：使用本地 JSON seed（`backend/data/network/sample_*.json`）
- ✅ 已落地：GO/KEGG 富集分析、network graph 可视化、Markdown 报告导出、演示数据边界 note
- ❌ 未落地：真实中药化合物数据库、真实靶点预测、真实通路数据库、Cytoscape 风格图布局算法

**下一步**（选择其一或按序推进）：
1. **中药化合物数据库接入**：TCMSP（开放）或 BATMAN-TCM（需授权）
2. **靶点预测接入**：SwissTargetPrediction API（限速）或本地部署 SEA
3. **KEGG REST API 接入**：替换本地 mock JSON（需处理限速 + 缓存）
4. **图布局算法**：引入 networkx / igraph，支持力导向布局或层次布局
5. **异步任务队列**：当真实计算耗时 >30s 时，引入 Celery + Redis（按 ADR-0008）

**优先级理由**：当前 mock 已足够演示工作流；真实计算链路是科研级增强，应在小范围试用反馈"mock 数据不够用"后再启动。建议先做 ①②（数据接入，轻量），再做 ④⑤（算法/异步，重依赖）。

---

### 3.2 分子对接/分子动力学模拟（MVP-C，概念预留阶段）

**现状**：
- ✅ 当前只做 schema 概念预留：protein、ligand、simulation_task 等数据结构已定义（见 ADR-0010）
- ❌ 无实际功能：无 API、无 service、无 repository、无前端页面

**下一步**（长期路线图，需分阶段推进）：
1. **技术选型**：AutoDock Vina（分子对接）、GROMACS（分子动力学）、RDKit（分子处理）
2. **基础设施**：GPU 计算节点、任务队列（Celery）、结果存储（MinIO 或 S3）
3. **API 设计**：`POST /api/docking/submit`、`GET /api/docking/result/{task_id}`、`POST /api/md/submit`、`GET /api/md/result/{task_id}`
4. **前端页面**：`/docking`、`/md`、分子结构可视化（3Dmol.js 或 NGL Viewer）

**优先级理由**：这是科研工作台的最重计算模块，需 GPU、专业软件、大量计算资源。建议在 MVP-A（文献）+ MVP-B（网络药理学）真实场景验证后再启动，避免过早投入。

---

### 3.3 多用户/权限/审计（生产化必备）

**现状**：
- ✅ 当前只有 token 白名单：`QIYAN_ACCESS_TOKENS` 提供最小共享 token 门禁
- ❌ 无用户概念、无角色、无审计日志
- 适用场景：内部预览、小范围试用（<10 人）
- 不适用场景：多租户、细粒度权限（医生 vs 科研）、合规审计

**下一步**（如果需要生产化部署）：
1. **认证**：按 ADR-0006（NextAuth 魔法链接）或改用 OAuth2/OIDC
2. **授权**：基于角色的访问控制（clinician / researcher / admin）
3. **审计日志**：所有 API 调用记录到 PostgreSQL 或专用日志服务
4. **多租户隔离**：如果需要跨机构部署，租户级数据隔离

**优先级理由**：当前 token profile 已足够内部预览；多用户/权限是生产化门槛，应在小范围试用后、确定推广路径时再启动。

---

## 四、不推荐近期启动的方向

1. **移动端适配**：ADR-0002 已明确 MVP 仅桌面端，移动端需独立 ADR
2. **付费/导出增强**：ADR-0003 已明确 MVP 不集成付费，当前 Markdown 导出已足够
3. **自训大模型**：项目边界已明确不自训，外部 LLM API 已足够
4. **Neo4j 图数据库**：当前 mock network 数据用 JSON 已足够，真实 Neo4j 应在网络药理学真实计算链路启动后再评估

---

## 推荐执行路径

### 路径 A：稳健推进（适合资源有限 / 风险厌恶）

1. ✅ **正式 reviewer sign-off**（1 周）—— 真实用户验证基线
2. ✅ **小范围试用**（2-3 周）—— 收集真实场景反馈
3. 根据反馈决定：
   - 如果反馈"PDF 扫描件无法解析"高频 → **PDF OCR 专项**
   - 如果反馈"deterministic 答案不够准确" → **L2 治理决策**（真实 LLM）
   - 如果反馈"网络药理学 mock 数据不够用" → **网络药理学真实计算链路**
4. 保持当前架构（JSON/SQLite + deterministic + keyword），增量优化

### 路径 B：激进推进（适合资源充足 / 快速验证）

1. ✅ **正式 reviewer sign-off**（1 周）
2. **并行启动**（2-3 周）：
   - 小范围试用（收集反馈）
   - L2 治理决策（真实 LLM）
   - 网络药理学数据接入（TCMSP + SwissTargetPrediction）
3. 根据试用反馈调整：
   - 如果 L2 通过率不够 → 增强 keyword retriever 或放宽 NLI 阈值
   - 如果网络药理学计算耗时 >30s → 引入 Celery 异步任务
4. 3 个月内完成 MVP-A（文献）+ MVP-B（网络药理学真实计算）+ L2（真实 LLM）三条主线

---

## 关键决策点（需用户拍板）

1. **reviewer sign-off 通过后，是否立即启动小范围试用？**（建议：是）
2. **小范围试用规模？**（建议：2-3 医生 + 1-2 科研，本地部署或云端单机）
3. **L2 真实 LLM 的治理判断？**（建议：等小范围试用反馈后再决定）
4. **网络药理学是否从 mock 推进到真实计算？**（建议：等小范围试用反馈后再决定）
5. **是否需要生产化部署？**（建议：小范围试用后再评估，当前 token profile 已足够）

---

## 当前技术债务与已知限制

1. **前端流星 UI**：已完成优化（1.5px 头 + 55-105px 尾 + linear 匀速 + blur(2px) 面板），用户已确认满意
2. **真实 LLM**：工程路径已验证，但 L2 默认预览仍不翻转（决策不翻转，保持 L1 受控启用）
3. **跨语言检索**：keyword + cross-lingual bridge 是当前默认有效路径，bilingual cohort N=16
4. **PDF 抽取**：pypdf 已覆盖文本型 PDF 主场景，扫描件/表格抽取待专项 spike
5. **网络药理学**：mock 数据已落地，真实计算链路待启动

---

## 附：门禁与验证命令

```powershell
# 统一本地门禁（推荐）
.\scripts\verify-local.ps1

# reviewer 走查或分支收口前追加 Playwright E2E
.\scripts\verify-local.ps1 -IncludeE2E

# 内部预览 isolated runtime 启动与 API smoke
.\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\trial-open
.\scripts\smoke-internal-preview.ps1
.\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\trial-open -Stop

# 生成本地内部预览证据包
.\scripts\collect-internal-preview-evidence.ps1
```

---

**状态**：计划已确认，等待执行。下一步：正式 reviewer sign-off。
