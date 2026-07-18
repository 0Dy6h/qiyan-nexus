# 网络药理学主轴纠偏与 Gate 1 交接

date: 2026-07-11  
status: completed  
decision: ADR-0017 accepted

## 结果

本次没有停留在评审报告层，而是直接完成了第一轮产品与代码纠偏：

- 产品唯一主轴改为“特应性皮炎中医药窄领域网络药理学自动化科研辅助平台”；
- 文献检索、PDF、RAG、引用与导出明确为证据服务层；
- 首页、侧栏和 `/network` 已按科研工作流重排；
- `POST /api/network/analyze` 新增必填 `research_protocol`；
- 研究协议包含 disease、明确 phenotype、`Homo sapiens`、evidence policy、query date；
- 协议在 JSON/SQLite/PostgreSQL task repository 中持久化并进入 result/report；
- 新增 `protocol_complete`、`formal_network_ready`、`blocking_reasons`；
- mock 或缺少来源版本/阈值/逐边人工判定时，formal readiness 失败关闭；
- 网络 Markdown 报告新增“研究协议与科研门禁”章节；
- 质量评分新增科研就绪度 D，撤销对核心产品完成度的过度乐观 A 级叙事。

## 关键文件

- 决策：`docs/adr/0017-network-pharmacology-first-product-contract.md`
- 整改状态：`docs/audits/2026-07-11-network-pharmacology-realignment/STATUS.md`
- 问题台账：`docs/audits/2026-07-11-network-pharmacology-realignment/issues.csv`
- 基线哈希：`docs/audits/2026-07-11-network-pharmacology-realignment/evidence_manifest.csv`
- 协议 schema：`backend/app/schemas/network.py`
- readiness 与报告：`backend/app/services/network.py`
- 研究 UI：`frontend/components/NetworkAnalysisClient.tsx`
- 产品入口：`frontend/app/page.tsx`、`frontend/components/WorkbenchShell.tsx`

## 验证

- `./scripts/verify-local.ps1`：通过。
- `./scripts/verify-local.ps1 -IncludeE2E`：通过。
- backend：643 passed / 1 skipped；ruff format/check、mypy 全绿。
- frontend：230 tests、typecheck、production build 全绿。
- Playwright：4/4 passed。
- `pnpm audit --prod`：0 vulnerabilities。
- `scripts/smoke-internal-preview.ps1`：reviewer-a 与 reviewer-b token profile 均通过。
- owner isolation：reviewer-b 读取 reviewer-a 的 result/report 均为 404。
- PowerShell parser：changed smoke script parse OK。
- `git diff --check`：通过（仅行尾转换提示）。

## 科研结论处置

- 保留：工程具备可审计任务、mock/live provider、网络图、报告与证据服务底座。
- 纠正：产品不再定义为“证据工作台优先、网络药理学后续探索”。
- 降级：现有 mock 网络与本地 GO/KEGG 字典只能证明工作流和 artifact 结构，不能证明科学有效性。
- 阻断：真实机制、核心靶点、通路富集、疗效或临床相关 claim 均未达到 scientific readiness。

## 未完成的人工工作

- 真实网络药理学研究协议需领域专家签字。
- compound-target 边需逐行人工判定及理由。
- Track A 150 个 blinded 文献相关性标签仍需独立真人 reviewer 完成。
- 本次代码/方向整改仍需未参与实现的独立 reviewer 搜索 fail-open、科研过度声明和数据 lineage 缺口。

## 唯一推荐下一切片

实现 Gate 2 row-level target lineage：分别输出 disease targets、compound targets 和交集集合；每行冻结 source、database version、query date、species、score/threshold、identifier mapping、automatic/manual 状态与 exclusion rationale。首个真实闭环只选择一个方剂和一个明确 AD 表型。
