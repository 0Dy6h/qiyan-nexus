# 质量评分 — Harness Engineering 支柱三 · 熵管理

> 每次项目级对抗性 review、架构整改或事实源收口后更新。
> 评分体系：A = 无债务，B = 轻微债务（< 3 缺口），C = 中度债务（3-10 缺口），D = 严重债务

## 当前质量评分（2026-07-15 Gate 2 双侧 raw-artifact provenance）

| 领域 | 评分 | 缺口 | 最后更新 |
|------|------|------|---------|
| 产品需求 | C | 主轴已纠偏且双侧 artifact workflow 可用，但研究项目、逐边人工证据与真实最小科研闭环尚未完成 | 2026-07-15 |
| 技术架构 | B | 分层、安全、immutable disease/compound snapshot、双 trusted manifest、raw/canonical 双 hash、双侧 intersection refs 与独立复算已落地；多 worker claim 与科学验证仍未设计 | 2026-07-15 |
| 任务拆解 | B | Open Targets 与 ChEMBL offline raw-artifact slice 已收口；唯一下一切片为 owner-scoped 人工 adjudication，不再扩展 provider | 2026-07-15 |
| 前端设计 | A | `/network` 已支持疾病 artifact 与第二阶段 ChEMBL artifact 上传、immutable child task、来源区分和三集合审计表；既有页面壳与可访问性门禁保持全绿 | 2026-07-15 |
| 后端 API | B | strict multipart、owner-scoped parent lookup、双 server-controlled manifest、双 hash、immutable child task 与 fail-closed readiness 已落地；人工 adjudication API 与科学复核尚未实现 | 2026-07-15 |
| 合规 | A | 免责声明、mock 边界、reviewer 访问边界、客户端未验证路径与 `server_verified_raw_artifact` 中间态均明确 | 2026-07-15 |
| 领域文档 | B | ADR-0017、双侧 artifact guide、整改工作区与 handoff 已建立；历史“证据工作台主轴”表述仍需逐步归档 | 2026-07-15 |
| 科研就绪度 | D | 双侧 raw bytes 与 canonical snapshots 均有 hash 锚点，但 hash 不证明 release 选择、官方来源、映射正确性或靶点意义；人工作业判定与科学验证仍缺失 | 2026-07-15 |
| 可观测性 | A | Request ID、structured logging、nginx reviewer access log、disease/compound raw artifact hash 与 import payload hash 均有明确路径 | 2026-07-15 |

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
