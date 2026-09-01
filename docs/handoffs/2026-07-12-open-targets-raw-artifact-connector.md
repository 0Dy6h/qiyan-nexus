# Handoff：Open Targets 离线 raw-artifact 服务端核验

date: 2026-07-12
branch: `feat/pillar2-real-evidence-ranking`
status: completed locally; not staged/committed/pushed
issue: NP-009（以窄工程语义关闭）

## 本次完成

- 新增 `POST /api/network/disease-import/verify` multipart 入口。客户端只提交 raw file、研究对象、证据策略与声明元数据；`records`、任何 hash、provenance/readiness、lineage/intersection 和人工 adjudication 字段由 `extra="forbid"` 拒绝为 `422`。
- 新增 stdlib Open Targets GraphQL `disease.associatedTargets` 静态 parser；从该 GraphQL response schema 的 `target.id`、`target.approvedSymbol`、`score` 字段派生 records。release/query/retrieved time/mapping/license 由服务器控制、按 raw-byte SHA-256 索引的 trusted manifest 封存，客户端不能提交 hash 或自证 envelope。这里的 trusted 只表示 manifest 位于服务器控制的配置边界，内容仍是 operator-recorded facts，不是 Open Targets 签名或官方真实性背书。manifest 未配置、hash 未登记、声明不符、损坏字节、低于阈值或空 artifact 失败关闭且不创建 task。
- 新增中间态 `server_verified_raw_artifact`。服务端从 raw bytes 派生 records，分别保存 raw-byte `source_artifact_sha256` 与 canonical `import_payload_sha256`，并保存 filename、media type、release、query/retrieved time 和 usage/license note。
- 原始字节按 SHA-256 content-addressed、临时文件完整写入后原子替换到 gitignored runtime `backend/data/runtime/network_raw_artifacts/`；可用 `NETWORK_RAW_ARTIFACT_DIR` 覆盖。上传上限为 5 MiB、记录上限为 500，raw response 未知字段失败关闭。
- JSON、SQLite 与 PostgreSQL JSONB 回读都接受 verified/unverified 联合 snapshot；task 创建后 owner、research protocol 与 disease snapshot 保持封存，后续 upsert/advance 不覆盖。
- disease、compound、intersection 三集合、source-row lineage、unique count、双侧 intersection refs 和默认 `pending/unreviewed` 语义保持不变。
- verified 路径移除“未验证客户端导入” blocker，改为“疾病来源已服务端核验；compound 来源保真、阈值与人工 adjudication 未完成”；`formal_network_ready` 仍硬性为 `false`。
- Markdown 报告与前端展示 `server_verified_raw_artifact`、两个 hash、release 与 usage/license note，并明确中间态边界。前端上传使用 `FormData`，不手写 `Content-Type`。
- 独立 stdlib validator 新增 `--source-artifact`，不 import 生产 service/parser；继续复算 payload hash、counts、row IDs、threshold、protocol 和 intersection refs，同时独立复算 raw-byte hash。不符退出 `2`。
- `docs/audits/2026-07-11-network-pharmacology-realignment/issues.csv` 将 NP-009 标为 closed/pass；这里关闭的是“客户端直接声明 records/provenance、服务端没有 raw artifact 锚点”的工程缺口，不是外部真实性或科学有效性问题。

## TDD 证据

A→H 依计划逐步执行。关键 RED 包括：verified schema 类缺失、parser/metadata 类缺失、verified snapshot builder 缺失、新 endpoint `404`、repository 仍只接受 `unverified_client_import`、validator 不识别 `--source-artifact`、报告缺 raw SHA、前端 multipart helper 缺失、runtime raw artifact 未保存、release 声明未绑定 trusted manifest、额外顶层 multipart 字段被忽略、超大/无 Content-Length 请求未提前拒绝。每项均在最小实现后 focused GREEN；相关后端聚焦回归最终为 `114 passed`，repository 额外覆盖 PostgreSQL JSONB row conversion。

## 收口验证

- 后端顺序门禁：`ruff format --check app tests`、`ruff check app tests`、`mypy app`、`pytest -q` 全绿；最终结果 `690 passed, 1 skipped`。
- 前端：`pnpm test` 为 `236 passed`；`pnpm typecheck` 通过；`pnpm build` 通过。
- `pnpm audit --prod`：`No known vulnerabilities found`。
- `./scripts/verify-local.ps1 -IncludeE2E`：通过；Playwright `4 passed`。
- protected smoke：token profile 与 reviewer owner isolation focused smoke `2 passed`；reviewer-b 读取 reviewer-a 的 result 与 report 均为 `404`，reviewer-a 可正常读取。
- validator focused test：原始 artifact 返回 `0`；同一路径字节追加后 hash 不符返回 `2`。
- `git diff --check`：退出 `0`，仅出现仓库既有 Windows LF→CRLF warning。
- 独立 adversarial 复审：首轮发现的自证 envelope、顶层 multipart fail-open、资源上限、非原子写入与 Markdown 注入问题均已整改；复审最终无 P0/P1。
- `frontend/next-env.d.ts` 已恢复为 `import "./.next/types/routes.d.ts";`。
- 未 stage、commit 或 push；未清理用户既有文件；未把 `.mcp.json`、`components.json`、runtime state、uploads、`.tmp` 或 secrets 纳入操作。

## 必须诚实保留的边界

`source_artifact_sha256` 只锚定处理的是哪一份原始文件字节，并允许独立 validator 检查该字节身份与完整性；`import_payload_sha256` 锚定持久化 canonical disease snapshot。raw-to-records 派生由生产 parser 与 parser 测试覆盖，当前独立 validator 不重演 GraphQL parser。因此这些一致性证据不证明：

- 所选 Open Targets release 正确；
- 上传 artifact 一定来自 Open Targets 官方渠道；
- AD 表型映射正确；
- identifier mapping 在科学上最适宜；
- 任一靶点具有生物学或临床意义；
- 自动抽取已经通过人工 adjudication。

状态名是 `server_verified_raw_artifact`，不是终态 `verified`。`formal_network_ready` 仍为 `false`；compound 来源保真、数据库版本/阈值和逐边人工 adjudication 仍未完成。独立 validator 只验证 artifact consistency，不替代外部数据库真实性核验或领域专家判断。默认 mock、无网络路径和冻结依赖边界均未改变；本切片没有引入任何 Open Targets 网络请求。

## 唯一推荐下一切片

补齐真实 compound-target lineage 的来源版本、阈值与可复核 provenance；完成前继续保持 `formal_network_ready=false`，不要提前进入人工 adjudication 终态或扩大基础设施依赖。
