# Work Log

## 2026-07-11 — 初始化

- 输入：仓库代码、测试、`AGENTS.md`、`docs/current-state.md`、`README.md`、`CONTEXT.md`、ADR-0010/0015、最新 hardening 与 retrieval handoff。
- 操作：建立隔离整改工作区；声明受保护路径、失败关闭边界和科研 readiness 分离规则。
- 初步判断：工程质量投入真实存在，但产品价值主轴发生倒置；网络药理学缺少最小科研协议，RAG/LLM/retrieval 获得了远高于主研究链路的建设深度。
- 下一步：冻结整改前关键证据哈希，随后用 TDD 落地 Gate 1。

## 2026-07-11 — Gate 1 完成

- 冻结：初始化 `evidence_manifest.csv`，覆盖 35 个方向事实源、核心网络代码、前端入口和全部 tracked network seed；基线未被重写。
- RED：服务测试先证明 `research_protocol` 无法传入；API 测试先证明缺少协议仍可创建；报告测试先证明协议/readiness 未导出；前端 client 与 UI/source tests 先证明 payload、表单和主轴文案缺失。
- GREEN：新增 `NetworkResearchProtocol`、`NetworkResearchReadiness`、repository 持久化、API 必填验证、readiness 评估、Markdown 协议章节、前端研究协议表单与科研门禁块。
- 产品纠偏：首页、侧栏与 `/network` 改为网络药理学主轴；新增 ADR-0017；README、AGENTS、current-state 与 quality score 同步。
- 独立验证范围：后端格式/lint/mypy/pytest，前端 test/typecheck/build，Playwright E2E，依赖审计，PowerShell parse，两个 reviewer protected smoke 与跨 owner 404。
- 验证结果：backend 643 passed / 1 skipped；frontend 230 tests；E2E 4 passed；0 production vulnerabilities。
- Manifest 复核：11 个 mismatch 全部是本次预期修改/新增；`backend/data/network/*.json` 全部 MATCH，原始 seed 未改。
- 未完成：没有真实领域 reviewer 或独立工程 reviewer 对本次方向决策签字；没有真实外部数据库版本、逐边人工判定或网络/富集独立复算。
- 唯一下一步：Gate 2 row-level target lineage。

## 2026-07-11 — Gate 2 结构基础

- 第一性原则不变量：疾病靶点必须来自独立采集，不能用成分靶点集合自身制造交集；自动提取与专家判定是两个不同事实层。
- RED/GREEN：API 测试先证明 result 没有 `target_lineage`；报告测试先证明集合与 lineage 未导出；service 对抗测试先暴露相同 canonical symbol 的不同 source record 被折叠；前端 source test 先证明审计表缺失；独立 validator 测试先证明脚本缺失，再证明伪造交集未被拒绝。
- 实现：新增 disease/compound/intersection 三集合、source-record 级 lineage、unique count 与 row count、自动抽取/人工判定状态；当前 disease/intersection 诚实保持空集。结果 UI 使用高密度审计表，报告给出空集原因和禁止自造交集声明。
- 独立验证：新增 stdlib-only `validate_network_target_lineage.py`，不 import 业务 service；复算集合计数、真实 symbol intersection、lineage row count 和 protocol query date/species，一致退出 0，不一致退出 2。
- 科研降级：Gate 2 仅标记 partial foundation；NP-004 从 open 降为 mitigated，不关闭。没有独立疾病靶点输入、真实版本/阈值和人工 adjudication 时，`formal_network_ready` 保持 false。
- 验证：focused backend 47 passed；backend 全量 648 passed / 1 skipped；frontend 231 passed，typecheck/build 通过；unified verify 与 IncludeE2E 通过，Playwright 4/4；production audit 0 vulnerabilities；protected reviewer-a/reviewer-b smoke 通过，跨 owner result/report 均为 404。
- Manifest 收口：未覆盖基线 `evidence_manifest.csv`；同步项目记忆后再次更新 `evidence_manifest_check.csv`，当前 39 行 hash 全部与工作树一致，其中 24 MATCH、11 个预期基线修改、4 个预期新增文件；全部 tracked `backend/data/network/*.json` 保持 MATCH。
- 唯一下一步：实现独立疾病靶点导入契约；交集仅由导入疾病行与现有成分行复算生成。

## 2026-07-11 — 收工与经验固化

- 文档洁癖检查：根规则文件均低于软上限；README/current-state 已包含 Gate 2 当前事实，未向 `AGENTS.md` 追加会话流水账。
- 项目记忆：在 `AGENTS.md` 固化“疾病/成分/交集分离、无独立疾病来源则空集、source-record 行不折叠、自动抽取不等于人工判定”的硬约束；在 `CONTEXT.md` 补齐 Research-Protocol、Target-Lineage、Disease/Compound/Intersection Targets、Adjudication、Artifact-Consistency、Scientific-Readiness 等共享语言，并补齐 ADR-0011 至 ADR-0017 索引。
- Skill 迭代：扩展项目级 `qiyan-adversarial-hardening`，把本轮科研完整性经验转为可复用流程和对抗性反例；更新 UI metadata，并通过 Skill validator。
- 评分同步：`docs/quality-score.md` 调整为 Gate 2 结构基础已经落地、独立疾病靶点和真实人工判定仍缺失的保守口径。
- 交接增强：本 handoff 新增工作树边界、下次阅读顺序、推荐 Skill 和唯一下一切片；会话状态为主动暂停，不是 blocked。

## 2026-07-12 — Gate 2 独立疾病靶点导入 snapshot

- 第一性原则不变量：疾病 artifact 是 task 创建时的不可变输入；浏览器声明的 source/version 不是已验证 provenance；intersection 是双侧 lineage 的派生关系，不是 disease row 副本。
- RED/GREEN：API tracer 先证明未知 `disease_target_import` 被静默丢弃；service RED 证明绕过 router 可写入协议不一致 artifact；repository RED 证明 JSON/SQLite update 会覆盖 task 原始导入；validator RED 证明 symbol/count 正确但 refs 伪造的 intersection 会误判通过；report/frontend RED 证明非空 disease/intersection 无逐行审计出口。
- 实现：新增严格 `open_targets_association_v1` 请求模型、服务端 `unverified_client_import` snapshot 与 canonical payload SHA-256；JSON/SQLite/PostgreSQL 持久化输入且 existing task update 不覆盖原 snapshot；零命中 `records=[]` 合法。
- Lineage：disease/compound source row 使用 provenance-bound SHA-256 ID；intersection 一条/unique symbol，`canonical_symbol_exact_match_v1`，完整引用两侧所有匹配 row IDs；三类记录均保持 pending/unreviewed。
- 独立复算：validator 现可拒绝错误 count、row ID、payload hash、threshold、protocol、缺失/悬空/跨 symbol/不完整 refs 以及伪造人工状态；合法非空 artifact 退出 0。
- 输出：Markdown 与 `/network` 展示导入来源、版本、查询、阈值、mapping、payload hash、disease/compound 行和双侧 intersection refs；前端 JSON parser 拒绝服务端/人工字段并在提交前核对协议。
- 当前验证：backend focused 87 passed、full 662 passed / 1 skipped；frontend 235 tests、typecheck、production build；统一门禁与 IncludeE2E 均通过，Playwright 4/4；production audit 0 vulnerabilities；`git diff --check` 通过。
- 科研降级：Gate 2 仍为 partial；payload hash 只证明封存内容，不能证明 Open Targets 原始来源；compound 仍有 mock/版本/阈值缺口，人工 adjudication 尚未实现。
- 唯一下一步：服务端 Open Targets 原始快照核验/connector，为一个明确 AD 表型保存真实 release、结构化 query、retrieved time、usage note 与 source artifact hash。

## 2026-07-12 — Gate 2 Open Targets 离线 raw-artifact 核验

- 第一性原则不变量：客户端上传的文件与同一客户端提交的 release/hash/records 属于同一信任域，不能互相作证；可信升级必须来自服务端原始字节哈希、服务端 parser 与 operator-controlled manifest 的联合约束。
- TDD A→H：逐步覆盖严格 verified schema、GraphQL parser、snapshot builder、multipart API、三类 repository 回读、独立 validator、报告/前端展示和 raw artifact 持久化；关键 fail-closed RED 还覆盖 release 声明不符、低于阈值、额外顶层 multipart 字段、无效 framing、超限 artifact 与篡改字节。
- 实现：新增 `POST /api/network/disease-import/verify`，固定中间态 `server_verified_raw_artifact`；保存 server-computed `source_artifact_sha256`、canonical `import_payload_sha256`、release/version、结构化 query、retrieved time 与 usage/license note。没有引入任何 Open Targets 网络请求。
- 信任与资源边界：raw-byte hash 必须命中 `NETWORK_OPEN_TARGETS_MANIFEST_PATH`；multipart 外层与 metadata 内层都使用 allowlist；请求 framing、5 MiB artifact 上限和 500 rows 上限在昂贵处理前失败关闭。
- 持久化与独立复算：原始字节以临时文件完整写入、flush/fsync、复算 hash 后原子替换到 content-addressed runtime；JSON、SQLite、PostgreSQL snapshot 均可回读。stdlib-only validator 不 import service/parser，可独立复算 raw-byte hash 与 persisted canonical payload 一致性，篡改退出 2，但不重演 GraphQL raw-to-records 派生。
- 输出与科研降级：前端和 Markdown 显示中间态、双 hash、release 与 license note；provenance 文本经过安全输出处理。`formal_network_ready` 仍为 false，blocker 聚焦 compound 来源保真、阈值与人工 adjudication。
- 收口：backend 690 passed / 1 skipped；frontend 236 passed、typecheck/build；Playwright 4/4；production audit 0 vulnerabilities；reviewer-a/reviewer-b owner 隔离 smoke 通过；`git diff --check` 通过。NP-009 只按“服务端具备 raw artifact 锚点且客户端不能自证 records/provenance”的窄工程语义关闭。
- 唯一下一步：真实 compound-target provenance，包括来源版本、阈值和可独立复核的 lineage；不要提前进入人工终态或翻转 readiness。

## 2026-07-15 — Gate 2 ChEMBL provenance 与 session closeout

- 第一性原则不变量：compound artifact 必须绑定同 owner 的已核验 disease parent；parent link 是独立授权与 provenance 边界。raw/canonical hash 只证明工程一致性，不授权网络或科学结论。
- 实现收口：新增离线 `chembl_known_activity_v1` parser、operator-controlled manifest、strict multipart、content-addressed raw artifact、immutable compound child 与 JSON/SQLite/PostgreSQL `source_task_id` 持久化；拒绝 self-link、child-of-child、foreign parent 与 legacy unlinked child。
- 科研边界：compound child 固定为 snapshot-only，只输出冻结双侧 lineage 与服务端派生交集，`chains=[]`、`enrichment=null`，不调用 provider，不生成 PPI、通路或 enrichment；validator/report/UI 同步执行该边界。
- 对抗性补强：raw/manifest duplicate JSON key、bool/NaN/Infinity/out-of-range 数值、重复 source record、错误 protocol、篡改 hash/refs、额外或重复 multipart 字段均失败关闭。
- owner 回归：新增受保护模式 HTTP 集成测试，reviewer B 使用 reviewer A 的 `source_task_id` 返回通用 `404`，task 数量与 raw artifact 目录均不变。
- 最终验证：network-focused backend `219 passed`；backend 全量 `794 passed, 1 skipped`；frontend `240 passed`、typecheck/build；Playwright `4 passed`；`git diff --check` 无 whitespace error。两轮独立复审均无 P0-P3 findings。
- 工具边界：`pnpm audit --prod` 因 npm quick/fallback audit endpoint HTTP 410 retired 未形成 advisory 结果；不得解释为 0 vulnerabilities，也不得复用旧 audit 结果冒充当前结论。
- 经验回灌：项目规则与 `qiyan-adversarial-hardening` skill 新增 derived-parent、legacy read-only failure、snapshot-only projection 和 audit-tool failure 的长期约束。
- 当前判断：本切片已完成且主动收工，不是 blocked。下一且仅下一工程切片为 owner-scoped 人工 adjudication；其后仍需独立 source-bound network-assembly gate。
