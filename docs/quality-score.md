# 质量评分 — Harness Engineering 支柱三 · 熵管理

> 每次项目级对抗性 review、架构整改或事实源收口后更新。
> 评分体系：A = 无债务，B = 轻微债务（< 3 缺口），C = 中度债务（3-10 缺口），D = 严重债务

## 当前质量评分（2026-07-11 对抗性加固收口）

| 领域 | 评分 | 缺口 | 最后更新 |
|------|------|------|---------|
| 产品需求 | A | MVP-A 已收口；MVP-B 保持 mock/opt-in live 边界 | 2026-07-11 |
| 技术架构 | A | 分层严格；RAG export 完整性、network owner isolation 与终态只读 report 已落地 | 2026-07-11 |
| 任务拆解 | A | 下一工程主线已收敛为 PDF 全链路 owner isolation | 2026-07-11 |
| 前端设计 | A | 浏览器公开 token 路径已删除；既有页面壳与可访问性测试保持全绿 | 2026-07-11 |
| 后端 API | A | 629 passed / 1 skipped；ruff、mypy、并发与跨 owner 回归全绿 | 2026-07-11 |
| 合规 | A | 免责声明、数据来源、mock 边界与 reviewer 访问边界明确 | 2026-07-11 |
| 领域文档 | B | 当前事实源已同步；部分 2026-05/06 历史 plans/低优先快照仍待批量归档或加 superseded banner | 2026-07-11 |
| 可观测性 | A | Request ID、structured logging、nginx reviewer access log 均有明确路径 | 2026-07-11 |

## 开发启动后需追踪的领域

| 领域 | 关注项 |
|------|--------|
| 前端 | 组件重用率、页面性能、可访问性 WCAG AA |
| 后端 API | 响应时间 SLI、错误率、测试覆盖率 |
| 数据 | runtime/seed 隔离、对象 ownership、SQLite 并发与 orphan upload 清理；pgvector/Neo4j/R2 仅在显式生产化 ADR 后再增加指标 |
| AI | deterministic 检索正确性、citation 可解析率、免责声明覆盖率；真实 provider 仅在 opt-in smoke 时追踪成功率、延迟、成本与配额 |
| 合规 | 免责声明覆盖率、PIPL 合规检查；外发数据流向已记录（ADR-0011） |

## 定期清理任务

| 任务 | 频率 | 工具 |
|------|------|------|
| 文档一致性扫描 | 每周 | `neat-freak` 流程检查代码、current-state、CONTEXT 与 handoff |
| 架构约束违规扫描 | 每次 PR | ESLint + Ruff 自定义规则 |
| 代码质量评分更新 | 每周 | `requesting-code-review` + `scripts/verify-local.ps1` |
| 依赖审计 | 每两周 | `pnpm outdated` / `pip list --outdated` |
| 死代码清理 | 每月 | 手动审查 + 删除未使用模块 |

## 熵积累预警信号

以下信号出现时，立即做一次对抗性 code review 与文档一致性检查：
- 同一概念在多个文件中以不同名称出现
- 新增功能需要修改 3+ 个不相关文件
- 测试覆盖率连续 2 周下降
- TypeScript `any` 类型数量增加
