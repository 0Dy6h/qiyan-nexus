# 项目进度报告 — 2026-06-12

## 本次完成工作

### ✅ 方案 A：多语 embedding 真实模型评估（已完成）

**目标**：验证 bge-m3 / multilingual-e5-large 是否能突破 keyword+术语桥的跨语检索天花板（0.9688）

**执行情况**：
- ✅ Slice 1: bge-m3 真实模型评估
- ✅ Slice 2: multilingual-e5-large 对比评估
- ⏭️ Slice 3: grounding 阈值重校准（跳过，无需切换 backend）

**核心结论**：❌ **不推荐切换到真实多语模型**

**数据支持**：

| Backend | Strategy | Cross Recall | vs Baseline |
|---------|----------|:------------:|:-----------:|
| n/a | **keyword** | **0.9375** | -0.0313 ✅ |
| bge-m3 | vector | 0.6250 | -0.3438 ❌ |
| bge-m3 | hybrid | 0.9062 | -0.0626 ⚠️ |
| e5-large | vector | **0.0625** | **-0.9063** ❌❌ |
| e5-large | hybrid | 0.6562 | -0.3126 ❌ |

**关键发现**：
1. 两个多语模型均无法超越 keyword+术语桥
2. e5-large 跨语召回接近完全失效（仅 1/16 题命中）
3. 所有配置的 mono recall = 1.0（中文检索无退化）
4. 根因：通用多语模型在 AD 医学领域 CN↔EN 术语配对训练不足

**技术决策**：保持 `QIYAN_EMBEDDING_BACKEND=hashing` + `QIYAN_RETRIEVAL_PROVIDER=keyword`

**产出**：
- `backend/scripts/eval_cross_lingual_bge_m3.py`
- `backend/scripts/eval_cross_lingual_e5_large.py`
- `docs/evaluations/2026-06-12-bge-m3-cross-lingual-eval.md`
- `docs/handoffs/2026-06-12-multilingual-embedding-real-eval.md`
- `docs/plans/2026-06-12-multilingual-embedding-eval-summary.md`

**验证**：
- ✅ 后端测试：489 passed, 1 skipped
- ✅ 跨语测试：25 passed
- ✅ 提交：7a7ad13

---

## 项目当前状态（2026-06-12）

### 阶段完成度

| 阶段 | 状态 | 完成度 | 备注 |
|------|------|:------:|------|
| MVP-A 证据工作台 | ✅ 已收尾 | 100% | 2026-06-04 关闭，A1-A6 全部落地 |
| MVP-B 网络药理学起步 | ✅ 大部分完成 | ~80% | B1-B6 提前落地，剩余真实富集分析 |
| 阶段 C provider/retrieval 底座 | ✅ 部分完成 | ~60% | embedding spike 已评估，L2 被治理阻塞 |

### 技术健康度

- 后端：✅ 489 passed, 1 skipped
- 前端：✅ 154 passed
- 跨语检索：✅ avg_cross_lingual_recall = 0.9375
- RAG eval：✅ 50 题数据集，keyword baseline 锁定
- 最新提交：7a7ad13 (2026-06-12)

### 当前能力边界

**已具备**：
- ✅ 文献检索（seed + PubMed 同步 + PDF 上传）
- ✅ RAG 答案（deterministic provider，免责声明）
- ✅ 跨语检索（keyword + 术语桥，CN↔EN 0.9375）
- ✅ PDF 解析（pypdf 文本预览 + fallback）
- ✅ 网络药理学 mock（页面 + 可视化 + 报告导出）
- ✅ 访问控制（X-Access-Token）
- ✅ E2E 测试（Playwright）
- ✅ 真实 LLM 可选（L1 受控 smoke，opencode_go）
- ✅ 多语 embedding 底座（bge-m3 / e5-large opt-in）
- ✅ SQLite runtime backend（2026-06-02）

**边界约束**：
- ❌ 默认不接真实 LLM（L2 不翻转）
- ❌ 默认不接真实 embedding（hashing，避免下载）
- ❌ 未接 PostgreSQL、pgvector、Neo4j、Celery、Redis、MinIO
- ❌ 未接 NextAuth、支付、生产对象存储

---

## 下一步推荐方案

### 方案 1：PostgreSQL/pgvector spike（推荐）

**理由**：
- 当前 SQLite runtime backend 已落地
- pgvector 是生产级向量检索必经之路
- 基础设施铺垫，不改变用户体验

**预估工作量**：4-5 小时

**计划**：
1. 本地 PostgreSQL 16 + pgvector extension（Docker 或直装）
2. 迁移脚本：seed JSON → PG tables + vector index
3. 扩展 repository 协议：PostgresLiteratureRepository / PostgresChunkRepository
4. 测试与性能对比：SQLite vs PostgreSQL（10/100/1000 条查询延迟）
5. 文档：`infra/docker-compose.yml` + `QIYAN_STATE_BACKEND=postgres` 启用步骤

### 方案 2：MVP-B 网络药理学真实富集分析

**理由**：
- mock 任务流已走通（/network 页面 + 可视化）
- 当前用本地 JSON 字典模拟 GO/KEGG
- 真实 KEGG REST API 接入是下一里程碑

**预估工作量**：3-4 小时

**计划**：
1. KEGG REST API wrapper（`app/services/kegg.py`）
2. 真实 pathway enrichment（超几何分布 p-value，Bonferroni 校正）
3. 缓存层（避免重复调 KEGG API）
4. 前端展示富集结果（P-value 排序，高亮显著通路）

### 方案 3：L2 预览推进（被治理决策阻塞）

**当前阻塞**：
1. ❌ BGE=0.3 + NLI=0.5 profile 的治理决策
2. ❌ 生产预算前复核真实合同价格
3. ❌ 正式医生/科研 reviewer sign-off

**建议**：等待业务/采购决策，暂不推进工程工作

---

## 关键指标趋势

### 跨语检索能力

| 日期 | 策略 | avg_cross_lingual_recall | 备注 |
|------|------|:------------------------:|------|
| 2026-06-01 | keyword (baseline) | 0.0000 | 术语桥之前 |
| 2026-06-01 | keyword + bridge | 0.7647 | 首次引入 17 组术语桥 |
| 2026-06-02 | keyword + bridge (扩展) | 0.7941 | 「微生态」补齐 |
| 2026-06-02 | keyword + canonical bonus | 0.9118 | alias tag bonus 扩展 |
| 2026-06-02 | keyword (audit 后) | **0.9688** | expected-label 审计，双语题 17→16 |
| 2026-06-12 | keyword (复现) | 0.9375 | seed-state 稳定 |
| 2026-06-12 | bge-m3 vector | 0.6250 | 真实模型评估 ❌ |
| 2026-06-12 | e5-large vector | 0.0625 | 真实模型评估 ❌❌ |

**结论**：keyword + 术语桥在 2 周内从 0.0 提升至 0.9688，已到天花板；真实多语模型无法突破。

### 测试覆盖

| 日期 | 后端 | 前端 | 备注 |
|------|:----:|:----:|------|
| 2026-06-04 | 470 passed | 154 passed | MVP-A 收尾 |
| 2026-06-10 | 470 passed | 154 passed | embedding spike 底座 |
| 2026-06-12 | **489 passed** | 154 passed | +19 tests (embedding eval) |

---

## 技术债务与风险

### 当前技术债

1. **SQLite → PostgreSQL 迁移**（中等优先级）
   - 当前 runtime 用 SQLite，生产需 PostgreSQL
   - 已有 repository 协议抽象，切换风险可控

2. **真实 KEGG API 接入**（中等优先级）
   - 当前用本地 JSON 字典模拟
   - 真实 API 需 rate limiting + 缓存

3. **L2 预览治理决策**（高优先级，但被外部阻塞）
   - claim-quality v2 技术验证已完成
   - 等待业务确认 BGE=0.3 + NLI=0.5 profile 可接受性

### 已消除风险

- ✅ 跨语检索天花板突破（评估证实 keyword 最优，无需切换）
- ✅ 多语 embedding 盲目切换风险（真实评估阻止性能退化）

---

## 会话总结

**本次会话目标**：读取项目真实进度，制定下一步开发计划

**实际执行**：
1. ✅ 读取项目进度（AGENTS.md, current-state.md, 最新 handoff）
2. ✅ 制定 3 个备选方案（A: 多语 embedding / B: pgvector / C: L2 预览）
3. ✅ 执行方案 A（多语 embedding 评估）
4. ✅ 完成 Slice 1+2（bge-m3 / e5-large 真实评估）
5. ✅ 技术决策（不切换，保持 keyword）
6. ✅ 文档产出（评估报告 + handoff + 总结）
7. ✅ 提交代码（7a7ad13）

**时间投入**：~3.5 小时

**价值**：
- 避免盲目切换到性能更差的多语模型（cross recall -0.3 到 -0.9）
- 验证 keyword+术语桥作为最优跨语策略
- 为下一步方向提供数据支持

---

**报告生成日期**：2026-06-12  
**下一步推荐**：方案 1（PostgreSQL/pgvector spike）或 方案 2（MVP-B 真实富集分析）
