# 质量评分 — Harness Engineering 支柱三 · 熵管理

> 每次 `improve-codebase-architecture` 运行后更新。
> 评分体系：A = 无债务，B = 轻微债务（< 3 缺口），C = 中度债务（3-10 缺口），D = 严重债务

## 当前质量评分（MVP-A 内部预览基线完成）

| 领域 | 评分 | 缺口 | 最后更新 |
|------|------|------|---------|
| 产品需求 | A | MVP-A 已收口，边界清晰；MVP-B mock 链路已落地 | 2026-06-05 |
| 技术架构 | A | 后端分层严格，前端测试覆盖完整，真实 LLM/embedding 可 opt-in | 2026-06-05 |
| 任务拆解 | A | 不再有模块级大任务，剩余是 spike 或 governance | 2026-06-05 |
| 前端设计 | A | 完整 error boundary，loading state 健全，Suspense fallback 覆盖全部异步组件 | 2026-06-05 |
| 后端 API | A | 505 passed / 1 skipped，SLI 已落地，request logging 与 trace ID 已补齐 | 2026-06-06 |
| 合规 | A | 免责声明、隐私政策、数据来源、PDF 版权均已完整 | 2026-06-05 |
| 领域文档 | A | ADR、handoff、current-state、reviewer checklist 均已同步 | 2026-06-05 |
| 可观测性 | A | Request ID、structured logging、前端 error boundary 均已落地 | 2026-06-05 |

## 开发启动后需追踪的领域

| 领域 | 关注项 |
|------|--------|
| 前端 | 组件重用率、页面性能、可访问性 WCAG AA |
| 后端 API | 响应时间 SLI、错误率、测试覆盖率 |
| 数据 | pgvector 查询延迟、Neo4j Cypher 性能、R2 可用性 |
| AI | LLM 调用成功率、语义缓存命中率、配额使用率；RAG provider 延迟/成本 SLI 已落地（`/api/rag/answer.sli` + `rag_sli` 日志，2026-05-31）；真实 provider 启用按 ADR-0012 L1/L2 分级 |
| 合规 | 免责声明覆盖率、PIPL 合规检查；外发数据流向已记录（ADR-0011） |

## 定期清理任务

| 任务 | 频率 | 工具 |
|------|------|------|
| 文档一致性扫描 | 每周 | `grill-with-docs` 检查代码 vs CONTEXT.md |
| 架构约束违规扫描 | 每次 PR | ESLint + Ruff 自定义规则 |
| 代码质量评分更新 | 每周 | `improve-codebase-architecture` |
| 依赖审计 | 每两周 | `pnpm outdated` / `pip list --outdated` |
| 死代码清理 | 每月 | 手动审查 + 删除未使用模块 |

## 熵积累预警信号

以下信号出现时，立即运行 `improve-codebase-architecture`：
- 同一概念在多个文件中以不同名称出现
- 新增功能需要修改 3+ 个不相关文件
- 测试覆盖率连续 2 周下降
- TypeScript `any` 类型数量增加
