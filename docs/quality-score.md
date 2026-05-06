# 质量评分 — Harness Engineering 支柱三 · 熵管理

> 每次 `improve-codebase-architecture` 运行后更新。
> 评分体系：A = 无债务，B = 轻微债务（< 3 缺口），C = 中度债务（3-10 缺口），D = 严重债务

## 当前质量评分（规划期 · 无代码）

| 领域 | 评分 | 缺口 | 最后更新 |
|------|------|------|---------|
| 产品需求 | A | 无 — `spec.md` 完整覆盖 FR/NFR/AC | 2026-05 |
| 技术架构 | A | 无 — `tcm-tech-plan.html` V2.1 已冻结 | 2026-05 |
| 任务拆解 | B | `tasks.md` 8 大任务偏粗，待 `to-issues` 细化 | 2026-05 |
| 前端设计 | B | 低保真原型已完成，待高保真设计 | 2026-05 |
| 领域文档 | B | CONTEXT.md 已建立，待 ADR 补充 | 2026-05 |

## 开发启动后需追踪的领域

| 领域 | 关注项 |
|------|--------|
| 前端 | 组件重用率、页面性能、可访问性 WCAG AA |
| 后端 API | 响应时间 SLI、错误率、测试覆盖率 |
| 数据 | pgvector 查询延迟、Neo4j Cypher 性能、R2 可用性 |
| AI | LLM 调用成功率、语义缓存命中率、配额使用率 |
| 合规 | 免责声明覆盖率、PIPL 合规检查 |

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
