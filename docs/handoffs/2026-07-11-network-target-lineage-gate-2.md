# 网络靶点 Lineage Gate 2 结构基础交接

date: 2026-07-11  
status: partial foundation completed  
scientific_readiness: false

## 本轮结果

本轮按第一性原则建立了一个不可绕过的科研边界：疾病靶点、成分靶点与两者交集是三个不同集合；在没有独立疾病靶点来源时，系统必须输出空 disease/intersection，而不能用成分靶点集合自身制造“疾病相关交集”。

- 后端新增 `NetworkTargetLineageRow` 与 `NetworkTargetLineage`，结果按 source record 保留逐行来源。
- 每行携带 raw identifier、canonical symbol、source database/version、query date、species、score/threshold、identifier mapping、evidence origin、source record IDs 与 adjudication 字段。
- 相同 canonical symbol 的不同来源记录不折叠；unique target count 与 lineage row count 分开。
- 自动提取默认 `automatic_status=extracted`、`adjudication_status=pending`、`decision=unreviewed`；不存在虚构 reviewer、时间或理由。
- 当前 pipeline 仅从 chain 提取 `compound_targets`；`disease_targets=[]`、`intersection_targets=[]`，并输出明确 warning。
- readiness 新增疾病靶点缺失、数据库版本缺失和人工判定未完成等 blocker，`formal_network_ready` 保持 false。
- Markdown 报告和 `/network` 前端新增三个集合、计数、warning、空态与高密度 lineage 审计表。
- 新增独立 stdlib validator，拒绝 declared intersection 与疾病/成分 canonical-symbol 真实交集不一致的 artifact。

## 独立验证器

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe scripts\validate_network_target_lineage.py C:\path\to\network-result.json
```

输入可以是直接 result 对象，也可以是 `{ "result": ... }`。验证器不 import `app.services.network`，会独立复算：

- disease/compound/intersection 的 unique symbol count；
- 三个集合的 lineage row count；
- `disease symbols ∩ compound symbols`；
- 每行 query date/species 与 research protocol 的一致性。

一致时输出 `artifact_consistency_pass=true` 并退出 0；不一致或输入无效时退出 2。它不验证外部数据库真伪、阈值合理性或靶点生物学意义。

## 关键文件

- schema：`backend/app/schemas/network.py`
- lineage/readiness/report：`backend/app/services/network.py`
- 独立 validator：`backend/scripts/validate_network_target_lineage.py`
- 后端测试：`backend/tests/test_network_api.py`、`test_network_service.py`、`test_network_report_service.py`、`test_validate_network_target_lineage.py`
- 前端类型与 UI：`frontend/lib/api/network.ts`、`frontend/components/NetworkAnalysisClient.tsx`
- 前端契约测试：`frontend/tests/network-report-ui.test.ts`
- 审计状态：`docs/audits/2026-07-11-network-pharmacology-realignment/`

## 验证结果

- RED/GREEN focused backend：47 passed。
- backend full gate：ruff format/check、mypy 通过；648 passed / 1 skipped。
- frontend：231 tests、typecheck、production build 通过。
- `./scripts/verify-local.ps1`：通过。
- `./scripts/verify-local.ps1 -IncludeE2E`：通过；Playwright 4/4。
- `pnpm audit --prod`：0 known vulnerabilities。
- protected smoke：reviewer-a 与 reviewer-b 均通过。
- owner isolation：reviewer-b 读取 reviewer-a 的 result/report 均为 404；owner report 为 200。
- protected smoke 结果确认 disease=0、compound unique=3、intersection=0。

## 不能宣称的内容

- 不能宣称 Gate 2 科学完成；目前只是可审计的数据结构与失败关闭基础。
- 不能宣称现有成分靶点就是 AD 疾病靶点。
- 不能宣称存在可信交集、核心靶点或机制结论。
- 不能把 mock source、空 database version、无 threshold、pending adjudication 描述为正式网络药理学证据。
- 自动化门禁只证明 artifact consistency，不替代领域专家判定。

## 唯一推荐下一切片

实现显式“独立疾病靶点导入”契约：只选一个方剂和一个明确 AD 表型，冻结 source/database version/query date/species/threshold/identifier mapping，逐行保留 source record。intersection 只能由导入疾病行与现有成分行的 canonical symbol 交集计算产生；导入与交集生成继续保持自动抽取和人工 adjudication 分离。

## 收工检查点

- 会话于 2026-07-11 在 Gate 2 partial foundation 完成后主动暂停，不是 blocked，也没有把 scientific readiness 标为完成。
- 当前分支为 `feat/pillar2-real-evidence-ranking`，工作树包含本轮 Gate 1/Gate 2 与用户既有 Track A 检索验证改动；没有 stage、commit 或 push。
- 不要清理或覆盖用户既有 Track A 文件，也不要提交 `.mcp.json`、`components.json`、runtime、uploads、`.tmp` 或 secrets。
- `frontend/next-env.d.ts` 已恢复 tracked 的 `./.next/types/routes.d.ts` 内容；再次运行 E2E 后若变成 `.next/dev/types/routes.d.ts`，收口前要恢复。
- 项目记忆已补充到 `AGENTS.md` 与 `CONTEXT.md`；`qiyan-adversarial-hardening` Skill 已加入科研集合完整性、lineage 行/unique count 分离、自动抽取/人工判定分离和独立 validator 规则。

## 下次阅读顺序

1. `AGENTS.md`
2. `docs/current-state.md`
3. `docs/adr/0017-network-pharmacology-first-product-contract.md`
4. 本 handoff
5. `docs/audits/2026-07-11-network-pharmacology-realignment/STATUS.md` 与 `issues.csv`
6. `backend/app/schemas/network.py`、`backend/app/services/network.py`
7. `backend/scripts/validate_network_target_lineage.py`

## 下次推荐 Skill 与执行方式

- 先使用 `qiyan-adversarial-hardening` 定义疾病靶点导入的受保护科研资产、可信来源和失败关闭行为。
- 使用 `test-driven-development` 从“无独立来源不得生成 disease/intersection”与“导入后只按 canonical symbol 复算交集”的 RED 测试开始。
- 如果导入格式或来源选择仍有歧义，先用 `project-grill` 收紧契约；设计清楚后再写单一纵向切片计划。
