# C5 Network Report Export Enhancement Handoff

**日期**: 2026-06-01  
**状态**: 已完成  
**任务**: 增强网络药理学报告导出，包含富集分析结果

---

## 目标

在现有的 Markdown 报告导出功能基础上，添加富集分析结果章节，使导出的报告包含完整的分析结果（链条 + 富集分析 + 网络图占位符）。

## 已完成的工作

### 1. 报告生成逻辑增强

**修改文件**：`frontend/lib/network-report-export.ts`

**新增内容**：
- 富集分析结果章节（当 `result.enrichment` 存在时）
- 富集分析表格：Term ID、通路/功能、类别、重叠基因、P-value、校正后 P-value、基因列表
- 参数说明：超几何分布、Bonferroni 校正、过滤条件
- 网络图占位符：`![成分-靶点-通路网络图](placeholder-network-graph.png)`
- 更新边界说明：明确富集分析基于本地 JSON 字典（mock）

**报告结构**：
```markdown
# Qiyan Nexus 网络药理学报告导出

- 导出时间（UTC）：...
- task_id：...
- 分析对象：...
- 分析类型：...
- 链路数量：...

## 链路结果
[链条表格]

## 富集分析结果
- 输入基因数：...
- 背景基因数：...
- 分析类型：...
- 富集通路/功能数：...

[富集分析表格]

### 参数说明
- P-value：超几何分布计算的原始 p 值
- 校正后 P-value：Bonferroni 校正后的 p 值
- 重叠基因：输入基因与该通路/功能的交集数量
- 过滤条件：p < 0.05 且重叠基因数 >= 2

## 网络图
![成分-靶点-通路网络图](placeholder-network-graph.png)
*注：图片占位符，实际图片生成功能待后续实现*

## 边界说明
- 不是正式网络药理学计算。
- 富集分析基于本地 JSON 字典（mock），不代表真实 KEGG REST API 或 STRING 数据库。
- 不构成诊断或治疗建议...

---
非诊断结论、需结合临床。
```

### 2. 测试覆盖

**新增测试**（`frontend/tests/network-report-export.test.ts`）：
- `buildNetworkReportMarkdown includes enrichment analysis when available` - 验证富集分析章节包含在报告中
- `buildNetworkReportMarkdown skips enrichment section when not available` - 验证无富集分析时跳过该章节

**测试验证点**：
- 富集分析章节标题
- 输入基因数、背景基因数、分析类型
- 富集分析表格表头
- 富集术语数据（Term ID、中文名称、类别、重叠基因分数、P-value、基因列表）
- 参数说明章节
- 网络图占位符
- 边界说明更新

**测试结果**：
- 前端：137 个测试通过（从 135 增加到 137）
- 后端：293 个测试通过（无变化）

### 3. 前端 UI 集成

**现有功能**（无需修改）：
- `NetworkAnalysisClient` 组件已有"导出报告为 Markdown"按钮
- 点击按钮调用 `buildNetworkReportMarkdown()` 生成报告
- 使用 `Blob` 和 `URL.createObjectURL()` 下载为 `.md` 文件
- 文件名格式：`qiyan-network-report-{task_id}-{YYYYMMDD}-{HHmm}.md`

**自动包含富集分析**：
- 当 `result.enrichment` 存在时，报告自动包含富集分析章节
- 无需额外的 UI 交互或配置

---

## 技术细节

### 富集分析表格格式

```markdown
| Term ID | 通路/功能 | 类别 | 重叠基因 | P-value | 校正后 P-value | 基因列表 |
|---|---|---|---:|---:|---:|---|
| GO:0006954 | 炎症反应 | biological_process | 2/450 | 1.23e-4 | 2.96e-3 | IL6, TNF |
```

- **Term ID**：GO 或 KEGG 标识符
- **通路/功能**：优先显示中文名称（`term_name_zh`），回退到英文（`term_name`）
- **类别**：`biological_process`、`molecular_function`、`cellular_component`、`KEGG`
- **重叠基因**：分数形式（`overlap_count/gene_count`）
- **P-value**：科学计数法（`toExponential(2)`）
- **校正后 P-value**：Bonferroni 校正后的 p 值
- **基因列表**：逗号分隔的基因符号

### 表格单元格转义

使用 `escapeTableCell()` 函数处理特殊字符：
- 替换管道符 `|` 为 `\|`
- 压缩多个空格为单个空格
- Trim 前后空格
- 空值显示为"无"

---

## 已知限制

1. **网络图占位符**：仅显示占位符文本，未实现实际图片生成
2. **PDF/Word 导出**：仅支持 Markdown 格式，未实现 PDF 或 Word 导出
3. **报告模板**：硬编码在代码中，未实现可配置的报告模板

---

## 后续改进方向

1. **网络图可视化**：
   - 使用 D3.js 或 Cytoscape.js 生成基因-通路网络图
   - 导出为 PNG/SVG 并嵌入报告

2. **PDF/Word 导出**：
   - 使用 jsPDF 或 docx 库生成 PDF/Word 格式
   - 保留 Markdown 格式的表格和图片

3. **报告模板系统**：
   - 支持自定义报告模板（Handlebars、Mustache）
   - 允许用户选择报告章节和顺序

4. **后端报告生成**：
   - 将报告生成逻辑移到后端（`/api/network/report/{task_id}`）
   - 支持服务端渲染和缓存

---

## 验证步骤

### 自动化测试

```bash
cd frontend
pnpm test  # 包含 network-report-export.test.ts
pnpm typecheck
```

### 手动验收

1. 启动后端：`cd backend && .\.uv-test-venv\Scripts\fastapi.exe dev app/main.py`
2. 启动前端：`cd frontend && pnpm dev`
3. 访问 `/network`，输入"黄芩"，提交分析
4. 等待结果页面显示（包含链条和富集分析表格）
5. 点击"导出报告为 Markdown"按钮
6. 验证下载的 `.md` 文件包含：
   - ✅ 查询信息（query, analysis_type, task_id）
   - ✅ 链条列表（至少 3 条）
   - ✅ 富集分析结果章节
   - ✅ 富集分析表格（至少 3 个 terms）
   - ✅ 参数说明（超几何分布、Bonferroni 校正）
   - ✅ 网络图占位符
   - ✅ 边界说明
   - ✅ Disclaimer 声明
   - ✅ 时间戳
7. 使用 Markdown 预览工具验证格式正确

---

## 关键文件

### 前端
- `frontend/lib/network-report-export.ts` - 报告生成逻辑（已修改）
- `frontend/components/NetworkAnalysisClient.tsx` - 导出按钮 UI（无需修改）
- `frontend/tests/network-report-export.test.ts` - 报告导出测试（新增 2 个测试）

---

## 推荐阅读顺序

1. 本 handoff
2. `frontend/lib/network-report-export.ts` - 查看报告生成逻辑
3. `frontend/tests/network-report-export.test.ts` - 查看测试用例
4. 手动验收：实际导出报告并查看 Markdown 文件

---

## 下一步

C5 已完成，可以继续：
- **C6**: MVP-C 概念对象 schema 预留 - 1 天
