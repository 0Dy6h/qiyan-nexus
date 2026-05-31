# C4 Network Enrichment Analysis Handoff

**日期**: 2026-06-01  
**状态**: 已完成  
**任务**: 实施网络药理学 GO/KEGG 富集分析（mock）

---

## 目标

在现有网络药理学任务基础上，添加 GO/KEGG 富集分析能力，使用本地 JSON 字典模拟真实富集数据库，通过 scipy 超几何分布计算统计显著性。

## 已完成的工作

### 1. 数据模型设计

**新增 sample 数据**：
- `backend/data/network/sample_go_terms.json` - 24 个 GO 术语（biological_process、molecular_function、cellular_component）
- `backend/data/network/sample_kegg_pathways.json` - 20 个 KEGG 通路（炎症、免疫、信号通路）

**Schema 扩展**（`backend/app/schemas/network.py`）：
- `EnrichmentTerm` - 单个富集术语（term_id、term_name、term_name_zh、category、gene_count、overlap_count、p_value、adjusted_p_value、genes）
- `EnrichmentResult` - 富集分析结果（analysis_type、input_gene_count、background_gene_count、terms、timestamp）
- `NetworkAnalysisResult.enrichment` - 可选字段，向后兼容

### 2. 富集分析算法实现

**新增服务**（`backend/app/services/enrichment.py`）：
- `calculate_enrichment()` - 使用 scipy.stats.hypergeom 计算超几何分布 p-value
- `run_go_enrichment()` - GO 富集分析，过滤 p < 0.05 且 overlap >= 2 的 terms
- `run_kegg_enrichment()` - KEGG 富集分析，同样的过滤条件
- `build_enrichment_result()` - 合并 GO + KEGG 结果，返回 top 20

**统计方法**：
- 超几何分布：P(X >= k) = hypergeom.sf(k-1, M, n, N)
  - M: 背景基因总数（默认 20000）
  - n: 该 term 的基因数
  - N: 输入基因数
  - k: 重叠基因数
- Bonferroni 校正：adjusted_p_value = min(p_value * term_count, 1.0)

**集成到 network service**（`backend/app/services/network.py`）：
- 在 `_advance()` 中从 chains 提取 target symbols
- 加载 GO/KEGG 数据并调用 `build_enrichment_result()`
- 当 target_symbols < 2 时跳过富集分析（enrichment = None）

### 3. 前端展示

**类型定义**（`frontend/lib/api/network.ts`）：
- `EnrichmentTerm` - 富集术语类型
- `EnrichmentResult` - 富集结果类型
- `NetworkAnalysisResult.enrichment` - 可选字段

**UI 组件**（`frontend/components/NetworkAnalysisClient.tsx`）：
- 在链条列表之后添加富集分析表格
- 显示：Term ID、通路/功能（优先中文）、类别、重叠基因（分数形式）、P-value（科学计数法）、基因列表
- 限制显示前 10 条，超过时显示总数提示
- 表格样式：斑马纹、响应式、overflow-x: auto

### 4. 测试覆盖

**后端测试**（21 个新增测试）：
- `test_network_enrichment_schema.py` - 5 个 schema 验证测试
- `test_enrichment_service.py` - 12 个算法测试（超几何分布、过滤、排序、Bonferroni 校正）
- `test_network_enrichment_integration.py` - 4 个集成测试（端到端验证）

**前端测试**（6 个新增测试）：
- `test_network_enrichment_ui.test.ts` - UI 组件源码断言（表格列、格式化、限制显示）

**测试结果**：
- 后端：293 个测试通过（从 272 增加到 293）
- 前端：135 个测试通过（从 129 增加到 135）

### 5. 文档更新

- `README.md` - 添加富集分析说明和 API 响应示例
- `docs/current-state.md` - 更新网络药理学能力边界
- `backend/pyproject.toml` - 添加 scipy>=1.11.0 依赖

---

## 技术细节

### 富集分析流程

1. 从 network chains 提取唯一的 target symbols
2. 如果 target_symbols < 2，跳过富集分析
3. 加载 GO terms 和 KEGG pathways（JSON 文件）
4. 对每个 term 计算超几何分布 p-value
5. 过滤：p_value < 0.05 且 overlap_count >= 2
6. 应用 Bonferroni 校正
7. 按 p-value 排序，返回 top 20

### 数据来源

- GO terms: 24 个常见 AD 相关术语（炎症反应、免疫反应、细胞增殖等）
- KEGG pathways: 20 个免疫/炎症通路（TNF 信号通路、JAK-STAT 通路等）
- 每个 term/pathway 包含 5-13 个基因符号

### 前端展示策略

- 只显示前 10 条（避免表格过长）
- 使用科学计数法显示 p-value（如 1.23e-04）
- 重叠基因显示为分数（如 5/450）
- 优先显示中文名称，回退到英文

---

## 已知限制

1. **Mock 数据**：使用本地 JSON 字典，不是真实的 GO/KEGG 数据库
2. **简化的 Bonferroni 校正**：真实场景应使用 FDR（Benjamini-Hochberg）
3. **固定背景基因集**：默认 20000，真实场景应根据物种和芯片平台调整
4. **无网络图可视化**：仅表格展示，未实现基因-通路网络图

---

## 后续改进方向

1. **真实 KEGG REST API 接入**：替换本地 JSON，获取最新通路数据
2. **FDR 校正**：使用 statsmodels.stats.multitest.multipletests
3. **更大的 GO 字典**：扩展到数百个 terms，覆盖更多生物学过程
4. **网络图可视化**：使用 D3.js 或 Cytoscape.js 绘制基因-通路网络
5. **导出增强**：在 Markdown 报告中包含富集分析结果

---

## 验证步骤

### 后端验证

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m pytest tests/test_network_enrichment_schema.py -v
& .\.uv-test-venv\Scripts\python.exe -m pytest tests/test_enrichment_service.py -v
& .\.uv-test-venv\Scripts\python.exe -m pytest tests/test_network_enrichment_integration.py -v
& .\.uv-test-venv\Scripts\python.exe -m pytest -q  # 全部测试
```

### 前端验证

```bash
cd frontend
pnpm test  # 包含 network-enrichment-ui.test.ts
pnpm typecheck
pnpm build
```

### 手动验收

1. 启动后端：`cd backend && .\.uv-test-venv\Scripts\fastapi.exe dev app/main.py`
2. 启动前端：`cd frontend && pnpm dev`
3. 访问 `/network`，输入"黄芩"，提交分析
4. 验证结果页面显示：
   - 成分-靶点-通路链条（现有功能）
   - 富集分析表格（新增功能）
   - 至少 3 个 GO/KEGG terms
   - P-value 以科学计数法显示（如 1.23e-04）
   - 基因列表正确展示（如 "IL6, TNF, IL1B"）
   - 重叠基因数显示为分数（如 "5/450"）

---

## 关键文件

### 后端
- `backend/app/services/enrichment.py` - 富集分析核心算法
- `backend/app/services/network.py` - 集成富集分析到 network service
- `backend/app/schemas/network.py` - EnrichmentTerm、EnrichmentResult schema
- `backend/data/network/sample_go_terms.json` - GO 术语数据
- `backend/data/network/sample_kegg_pathways.json` - KEGG 通路数据
- `backend/tests/test_enrichment_service.py` - 算法测试
- `backend/tests/test_network_enrichment_integration.py` - 集成测试

### 前端
- `frontend/components/NetworkAnalysisClient.tsx` - 富集分析表格 UI
- `frontend/lib/api/network.ts` - EnrichmentTerm、EnrichmentResult 类型
- `frontend/tests/network-enrichment-ui.test.ts` - UI 测试

---

## 推荐阅读顺序

1. 本 handoff
2. `backend/app/services/enrichment.py` - 理解算法实现
3. `backend/tests/test_enrichment_service.py` - 查看测试用例
4. `frontend/components/NetworkAnalysisClient.tsx` - 查看 UI 实现
5. `backend/data/network/sample_go_terms.json` - 查看数据结构

---

## 下一步

C4 已完成，可以继续：
- **C5**: 分析报告导出（Markdown + 图片占位）- 2 天
- **C6**: MVP-C 概念对象 schema 预留 - 1 天
