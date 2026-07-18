# 收工交接：raw-artifact 切片知识同步与经验固化

date: 2026-07-12  
branch: `feat/pillar2-real-evidence-ranking`  
status: development complete locally; closeout complete; not staged/committed/pushed

## 本轮目标与当前状态

本轮不再扩展产品代码，而是按第一性原则完成收工：核对实现与当前事实源的一致性，把可复用的不变量写入项目记忆和 hardening Skill，并留下可直接续接的工作记录。

Open Targets 离线 raw-artifact 纵向切片已经完成并通过全套开发门禁。当前工作树仍未提交；没有 stage、commit 或 push，也没有清理用户既有文件。`server_verified_raw_artifact` 仍是中间态，`formal_network_ready` 仍为 `false`。

## 已同步的事实源

- `docs/current-state.md`：把 raw-artifact connector、trusted manifest、raw/canonical 双 hash、三类 repository snapshot 与 validator 的真实边界写入当前状态，并把唯一主线推进到 compound-target provenance。
- `AGENTS.md`、`CLAUDE.md`、`CONTEXT.md`：区分旧客户端 `unverified_client_import` 与服务端 `server_verified_raw_artifact`，固化 multipart 双层 allowlist、客户端不可自证和 readiness 不翻转规则。
- `README.md`、疾病导入 guide、cloud trial runbook、质量评分与已完成计划：同步 endpoint、环境变量、部署信任边界、使用示例和完成状态。
- 审计 `STATUS.md` / `WORKLOG.md`：保留历史记录，追加 NP-009 的窄工程关闭语义、最终门禁和下一检查点。
- `.codex/skills/qiyan-adversarial-hardening/SKILL.md`：把 raw-artifact provenance 的通用对抗检查加入项目 Skill。

## 从本次任务提炼的第一性原则

1. 同一客户端控制的两份输入不形成独立证据。上传文件、客户端 hash、客户端 release 声明和客户端 records 都属于同一信任域；可信升级必须引入服务端计算与服务器控制的事实锚。
2. `extra="forbid"` 只保护实际送入该模型验证的对象。严格 metadata 不会自动约束 multipart 的兄弟字段、headers、filename、media type 或 framing，外层 envelope 必须另设 allowlist。
3. 资源门禁必须早于昂贵处理。请求 framing、字节上限和行数上限应在 multipart spool、domain parser 和 repository write 前失败关闭。
4. content-addressed 文件名不等于原子安全。可靠 CAS 需要同目录临时文件、完整写入、flush/fsync、服务端复算 hash 与 atomic replace。
5. provenance 既是审计数据，也是输出注入面。即使字节 hash 正确，filename、release、query 和 license note 仍必须在 Markdown/HTML/export 边界安全编码。
6. artifact consistency 与 scientific readiness 必须永远分开。`source_artifact_sha256` 锚定 raw bytes，`import_payload_sha256` 锚定 canonical snapshot；它们不证明 release 选对、来源官方、表型映射正确或靶点有生物学意义。
7. 独立 validator 的独立性必须精确描述。当前脚本不 import producer，可复算 raw-byte hash、canonical payload 与 lineage 不变量，但不独立重演 GraphQL raw-to-records parser。

## 仍未完成

- compound-target lineage 仍缺真实来源版本、阈值与可复核 provenance。
- 自动抽取尚未进入 owner-scoped 的真实人工 adjudication。
- 尚无真实领域 reviewer 对 release 选择、表型映射或靶点生物学意义签字。
- 因此 `formal_network_ready=false`；不得把 `server_verified_raw_artifact` 简写成 `verified`。

## 下一会话唯一建议

只规划并实施真实 compound-target provenance 纵向切片：先建立来源版本、查询/阈值、原始或等价可复核 artifact 锚点和 source-row lineage，再讨论人工 adjudication。不要并行扩展网络、富集或基础设施。

推荐阅读顺序：

1. `docs/current-state.md`
2. `docs/handoffs/2026-07-12-open-targets-raw-artifact-connector.md`
3. `docs/adr/0017-network-pharmacology-first-product-contract.md`
4. `docs/guides/network-disease-target-import.md`
5. 下一会话新建的 compound-target provenance 计划

推荐使用的 Skill：`qiyan-adversarial-hardening`、`test-driven-development`、`codegraph`；在正式写下一切片计划前，可用 `project-grill` 压测信任边界与完成定义。
