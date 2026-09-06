# 2026-09-06 交接：writer 消费原语实现切片（候选装配计划 → 一次性消费契约）

## 今日工作概览

1. **writer 消费契约从「已拍板未实现」推进到「已落地」**。决策包 `docs/plans/2026-08-14-writer-consumption-contract-decision-pack.md`（2026-08-16 研究者逐条确认 D1-D9 + 附加条件）是本切片的全部决策依据，本次零新增拍板；契约草案 status 已改为 `approved`。实现切片计划见 `docs/plans/2026-09-06-writer-consumption-primitive.md`。
   - 新端点 `POST /api/network/result/{task_id}/assembly-plans/{plan_id}/consume`：服务层按 D3 固定优先级预检（404 → 422 呈现哈希不符 → R3 已消费/重放 → R4 `plan_superseded` → R6 `adjudication_changed` → R7 `broken_parent_link` → 500 integrity 汇总 checks → 429 容量），仓储层在同一临界区/事务内重验可变通道（判定流元组、lineage 重算 hash、latest sequence、exactly-once）后原子写输出信封 + 消费记录。
   - D5 幂等重放：同 `writer_id + plan_id + output_sha256` → `200 existing` 返回原消费记录；不同输出或不同 writer → `409 plan_already_consumed`。
   - D8 容量：`QIYAN_CONSUMPTION_RECORD_LIMIT`（默认 1000/task）触发 `429 consumption_limit_reached`。
   - D7 预览边界：响应信封 `backend_fidelity="preview"/"production"`；JSON 输出/消费文件（`*.assembly-outputs.json` / `*.assembly-consumptions.json`，新格式 `{"process_token","records"}`）记录写者进程 token，检出异进程写入即 `409 json_backend_multi_process_blocked`；JSON 只承诺同进程同实例 exactly-once（API 路径走 runtime_storage 单例）。
   - D2/D6 只读投影：plan 审计视图（GET 单计划改为 `NetworkAssemblyPlanAuditView`：plan + `is_latest_plan`/`is_consumed`/`is_superseded_by` + consumption 投影）、result 信封 `latest_plan.is_consumed`、报告新增「消费状态」行。superseded 输出保留为审计历史，永不删除。
   - D9=B：独立 validator 本切片不扩展，只定义输出信封最小 schema 预留接口。
2. **跨层共享**：`app/core/canonical_json.py`（qiyan_canonical_json_v1）由 service `_canonical_sha256` 与 JSON/SQLite/PG 三仓储共用，保证写时与消费时 hash 重算逐字节一致；独立 validator 的零共享副本不变。
3. **SQLite**：新增 `network_assembly_output` / `network_assembly_consumption` 两表（同库文件，`BEGIN IMMEDIATE` 单事务覆盖两表）；**PG**：`postgres_schema.sql` 新增 `network_assembly_outputs` / `network_assembly_consumptions`（FOR UPDATE 与判定/seal 同一行锁）。PG 活库 parity 仍不做（契约 §6 排除项）。
4. **前端同步**：`NetworkAssemblyPlanSummary` 拆出 base 类型，信封投影类型带 `is_consumed: boolean`（seal 响应的裸 plan 不含该字段，类型上如实区分）；`/network` 最新计划行显示「已被 writer 消费（审计记录）/尚未消费」；新增信封流转断言测试。跨端字段两侧断言各一（后端 `test_consume_creates_output_and_consumption_atomically`，前端 `fetchNetworkResult surfaces the latest plan consumption projection`）。
5. **脚本**：`run-internal-preview.ps1` 新增 `-ChEMBLManifestPath`（与既有 OpenTargets 参数对称），verified 疾病+成分双侧导入流程在预览 runtime 可完整走查。

## 测试与门禁状态

- 后端 913 → **950 passed + 1 skipped**（新增 32：repo 级 `test_network_assembly_consumption_repo.py` 21 个——json/sqlite 参数化 created/existing/already_consumed/superseded/conflict/integrity/capacity/not_found + 双 writer 并发 + JSON token + 写失败回滚；API 级 `test_network_assembly_consumption_api.py` 11 个——全失败码 + 重放 + 判定追加/重封存 + 文件篡改 500/409 + sqlite production fidelity）。
- **变异验证**（AGENTS.md 硬约束）：分别移除 JSON 仓储锁内 R3/R4/R6 守卫，对应测试全部变红后还原；守卫真实可观测。
- 前端 **302 tests** + typecheck + build；`verify-local.ps1` 全绿（111.4s）；`verify-local.ps1 -IncludeE2E -E2eBackendPort 8010 -E2eFrontendPort 3000` 全绿（backend 950 + E2E 4 passed）。
- 隔离预览 smoke 全过；并用真实 verified 双侧导入 → 全行判定 → seal → consume → replay → 他者 409 → 三处投影核验的完整 curl 走查（8010/3000），全部符合契约。

## 实现要点（下会话改这块前必读）

- 消费失败码是**确定性的**：改服务层预检顺序等于改 D3 拍板，必须先改契约文档再动代码。当前顺序陷阱：R6 语义预检必须在 R4 之后（`test_resealed_plan_supersedes_the_old_plan` 锁定）。
- 仓储层 R3 在 R4 之前（D3「先查消费记录快速失败」），且 already_consumed 优先于 superseded（同 writer 重试已消费又被 supersede 的 plan 时报 already_consumed）。
- 消费记录 `owner_id` 持久化但 API 投影丢弃（与 adjudication reviewer_id 同规）；输出信封 schema 钉死 `formal_network_ready: Literal[False]`。
- `NetworkAssemblyOutput.disclaimer` 由 service 层从 `services.rag.DISCLAIMER` 注入，byte-identical 断言在测试里。

## 遗留 / 下一步候选

- **writer 的装配计算逻辑**（消费契约 §1.3 明确排除）：下一个自然切片是定义 writer 如何从 `selected_intersections` 生成边/链并经消费原语落盘。
- **D9 独立 validator 扩展**：writer 输出信封 schema 已定，可做零共享重算 validator（扩展 `validate_network_assembly_plan.py` 输入包）。
- PostgreSQL 消费原语的活库 parity 验证（沿用既有 PG spike 边界）。
- 转人工（不变）：真人 domain reviewer 判定记录、Track A HITL 150 标签——能力落地不等于有人判定，`formal_network_ready` 恒 false。

## 环境备注

- 预览 runtime `.tmp/writer-consume-preview/`（backend 8010 / frontend 3000）收尾已 `-Stop`，内含走查产生的 verified 双侧任务与已消费计划，可复查；重启：
  `.\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp/writer-consume-preview -BackendPort 8010 -FrontendPort 3000 -OpenTargetsManifestPath .tmp/writer-consume-preview/ot-manifest.json -ChEMBLManifestPath .tmp/writer-consume-preview/chembl-manifest.json`
- 8000 被另一项目常驻占用，全程不可触碰；CORS 固定 3000（+127.0.0.1:3100）。
- 操作坑（本次实证）：**对含未提交实现的文件跑 `git checkout --` 会把实现一起冲掉**——变异验证请用文件备份（cp）还原，不要用 git checkout；Git Bash 的 `/tmp` 与 Windows python 解析的 `/tmp` 不是同一目录，跨 bash/python 的文件交换一律放仓库 `.tmp/`；中文 metadata 过 `curl -F` 会被截断，用 `-F "metadata=<文件"`；Python 文本模式写出的行尾是 CRLF，bash `read` 后要剥 `\r`。
