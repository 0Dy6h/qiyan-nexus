# Post AI Review - Next Steps Plan

date: 2026-06-06  
status: ready for human trial execution  
context: AI technical pre-review completed; no P0/P1 issues found; formal human sign-off still pending

---

## 审查完成状态

### ✅ AI Technical Review 完成

**审查日期**：2026-06-06  
**审查范围**：全面产品安全审查（临床与科研双视角）  
**审查方法**：系统性阅读种子数据、前端页面、后端逻辑、文档

**核心结论**：
- ✅ 医学安全与合规：A级
- ✅ 术语准确性：A级（中医 + 免疫学）
- ✅ 科学准确性：A级（靶点-通路关系）
- ✅ 数据透明度：A级（演示样本清晰标注）
- ✅ 证据链完整性：A级（完整溯源）

**发现的问题**：
- P0 问题：0
- P1 问题：0
- P2 问题：1（网络药理学前端 mock 边界标注可增强）
- P3 问题：1（英文样本作者姓名可优化）

**推荐结论**：✅ **可进入小范围试用**

详细报告：
- `docs/handoffs/2026-06-06-comprehensive-product-review.md`
- `docs/evaluations/2026-06-05-reviewer-feedback.md`（正式真人 reviewer packet，仍待填写）

---

## 下一步执行方案

### 方案 A：启动小范围试用（推荐）

**目标**：让真实用户在实际场景中验证产品，收集第一手反馈

#### 第一批试用用户（建议 3-5 人）

1. **皮肤科医生** × 1-2 名
   - 关注点：临床视角、术语准确性、免责声明适当性
   - 试用范围：文献检索、RAG 问答、PDF 上传、合规页面
   
2. **中医药科研人员** × 1-2 名
   - 关注点：证据质量、引用溯源、数据来源透明度
   - 试用范围：文献数据源切换、RAG citation cards、Markdown 导出
   
3. **方法学专家** × 1 名
   - 关注点：网络药理学表述、mock 边界清晰度
   - 试用范围：网络分析、富集分析、报告导出

#### 试用流程

1. **环境准备**（30 分钟）
   ```powershell
   # 启动隔离环境
   .\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\trial-user1
   
   # 验证环境健康
   .\scripts\smoke-internal-preview.ps1
   ```

2. **用户走查**（每人 1-2 小时）
   - 提供 `docs/checklists/internal-preview-reviewer-walkthrough.md`
   - 记录屏幕或笔记
   - 实时收集口头反馈

3. **反馈收集**
   - 填写 `docs/evaluations/2026-06-06-small-scale-trial-feedback.md`
   - 重点：
     - 术语表述是否符合临床/科研习惯
     - Mock 边界是否足够清晰
     - 引用溯源是否满足科研需求
     - 是否有误导性表述

4. **反馈闭环**
   - P0/P1：立即修复并复测
   - P2：进入下一 sprint
   - P3：进入 backlog

#### 试用边界

**包含**：
- ✅ 文献检索（四数据源）
- ✅ RAG 问答与引用
- ✅ PDF 上传与解析
- ✅ 网络药理学 mock 演示
- ✅ Markdown 报告导出

**不包含**：
- ❌ 真实 LLM（默认 deterministic）
- ❌ 真实 embedding 模型
- ❌ PostgreSQL/pgvector
- ❌ 生产级认证
- ❌ 真实 KEGG/STRING API

---

### 方案 B：可选技术改进（不阻塞试用）

如果在准备试用环境期间有额外时间，可处理以下 P2/P3：

#### Task B-1: 增强网络药理学 mock 边界标注（P2） — 已完成

**问题**：前端页面 mock 标注不够突出

**处理结果**：
- `/network` 页面新增 `演示数据边界` note，说明当前网络分析使用本地 mock seed graph 与本地 GO/KEGG 演示字典。
- 后端 network Markdown 报告头部新增数据说明，明确不可作为科研发表、临床决策或真实数据库分析结果。
- 已补 focused regression tests：`backend/tests/test_network_report_service.py` 与 `frontend/tests/network-report-ui.test.ts`。

#### Task B-2: 优化英文样本作者姓名（P3）

**问题**：部分英文样本作者姓名较为通用

**方案**：
1. 更新 `backend/data/literature/sample_ad_literature.json`
2. 使用更学术化的姓名组合（如多音节姓氏、中间名）
3. 确保不使用真实研究者姓名（避免误解）

**工作量**：30 分钟  
**优先级**：低（不影响功能）

---

## 需要真实用户验证的领域

以下无法通过 AI 审查完全覆盖，**必须在小范围试用中验证**：

1. **临床语境准确性**
   - 中医证候表述在实际临床场景的适用性
   - 辨证施治表述是否符合临床思维习惯
   
2. **科研工作流适配性**
   - 网络药理学 mock 是否符合真实科研需求
   - 引用溯源的详细程度是否足够
   
3. **用户认知边界**
   - 真实用户是否会误解 mock 数据
   - 演示样本标注是否足够清晰
   
4. **术语细节**
   - 某些专业术语的细微表述差异
   - 跨学科（中医+现代医学）术语衔接

---

## 推荐执行顺序

### Week 1（本周）

**Day 1-2：准备试用环境**
- [x] AI 审查完成
- [x] 创建 `docs/evaluations/2026-06-06-small-scale-trial-feedback.md` 模板
- [x] 补强网络药理学 mock 边界提示
- [ ] 确认试用用户名单（3-5 人）
- [ ] 准备演示环境（可选多个隔离 runtime）

**Day 3-5：执行试用**
- [ ] 用户 1（皮肤科医生）走查
- [ ] 用户 2（中医药科研）走查
- [ ] 用户 3（方法学专家）走查
- [ ] 收集并整理反馈

### Week 2（下周）

**Day 1-2：反馈闭环**
- [ ] 分级所有反馈（P0/P1/P2/P3）
- [ ] 修复 P0/P1（如果有）
- [ ] 复测受影响流程

**Day 3-5：迭代或扩展**
- [ ] 如果无 P0/P1 → 准备扩大试用范围
- [ ] 如果有 P0/P1 → 修复后重新小范围试用
- [ ] 处理 P2（如网络 mock banner）

---

## 成功标准

**小范围试用成功**的标志：

1. ✅ 所有用户完成核心流程走查
2. ✅ 无 P0 问题（医学安全/合规阻塞）
3. ✅ 无 P1 问题（核心功能严重受损）
4. ✅ 用户反馈"可以进入更大范围试用"
5. ✅ 术语准确性获得领域专家认可
6. ✅ Mock 边界清晰，无误导风险

**如果出现以下情况需重新评估**：

- ❌ 用户报告医学安全问题
- ❌ 用户误解 mock 数据为真实数据
- ❌ 术语表述引起专业质疑
- ❌ 核心流程无法完成

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 找不到合适的试用用户 | 试用延迟 | 先用项目团队内部专业人员替代 |
| 用户误解 mock 数据 | 信任度下降 | 立即增强前端 banner（Task B-1） |
| 发现 P0 医学安全问题 | 试用暂停 | 立即修复，重新 AI 审查，再试用 |
| 真实工作流不匹配 | 重新设计 | 收集详细需求，编写新实现计划 |

---

## 关键文档

- ✅ AI 技术预审报告：`docs/handoffs/2026-06-06-comprehensive-product-review.md`
- ✅ Formal reviewer packet：`docs/evaluations/2026-06-05-reviewer-feedback.md`（待真人填写）
- ✅ 审查完成 handoff：已生成
- ✅ Current state：已更新
- ✅ 小范围试用反馈模板：`docs/evaluations/2026-06-06-small-scale-trial-feedback.md`
- [ ] 试用结果 handoff：待试用后生成

---

**当前推荐行动**：联系 3-5 名真实用户，准备试用环境，按上述流程执行小范围试用。
