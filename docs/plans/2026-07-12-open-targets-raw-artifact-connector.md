# 执行计划：Open Targets 原始快照服务端核验 connector（Gate 2 → provenance 升级）

date: 2026-07-12
branch: `feat/pillar2-real-evidence-ranking`
owner-agent: codex
status: completed
scientific_readiness_after_slice: **仍为 false**（本切片不翻转）

---

## 0. 一句话目标（Goal）

> 让疾病靶点 snapshot 由**服务端从一份真实的 Open Targets 原始导出文件（raw artifact）派生**，
> 保存真实 release/version、结构化查询参数、retrieved time、license/usage note 与对**原始字节**的
> `source_artifact_sha256`，并把 provenance 从 `unverified_client_import` 升级为新的中间态
> `server_verified_raw_artifact`。

这是 `docs/current-state.md` 第 101 行、audit issue **NP-009**、以及两份最新 handoff
（2026-07-11 / 2026-07-12）共同指向的**唯一工程主线下一切片**。

### 成功标准（可验证，逐条对应验收）

1. 存在服务端入口，输入一份 Open Targets 原始导出文件 + 元数据，输出一个 disease import snapshot，
   其 `provenance_verification_status == "server_verified_raw_artifact"` 且带 `source_artifact_sha256`
   （= 对**原始文件字节**的 SHA-256，**不是** canonical payload hash）。
2. 服务端**自己解析** raw artifact 得到 `records`；浏览器/客户端不能再直接提交 records 冒充已验证来源。
3. 篡改原始文件字节 / 声明的 release 与文件内容不符 / 记录不满足声明阈值 → **失败关闭**（拒绝，不产出 verified snapshot）。
4. `formal_network_ready` 在本切片仍恒为 `false`；readiness blocker 文案从"未经服务端核验"更新为
   "疾病来源已服务端核验，但 compound 来源保真 / 人工 adjudication 未完成"。
5. 独立 validator（`validate_network_target_lineage.py`）识别并复算新的 verified 状态与
   `source_artifact_sha256`；伪造字节 hash 退出 2。
6. 全量本地门禁 + E2E 绿；`git diff --check` 干净。

### 明确的 Non-Goals（不要做，越界即失败）

- **不引入任何网络请求 / httpx 调用 Open Targets。** 本切片是 **offline raw-artifact only**。
  live GraphQL 拉取留作后续独立 slice（复用本切片的 static parser）。
- 不翻转 `formal_network_ready`，不把状态叫 `verified`（那是后续全链人工 adjudication 后的终态）。
- 不改 compound 侧 mock/live 边界，不动 RAG/PDF/检索默认路径。
- 不提交 raw artifact 样本为 git fixture，除非明确作为**测试夹具**放在 `backend/tests/data/` 且体积可控。
- 不改默认依赖边界（无 Neo4j/Celery/真实 LLM/pgvector）。

---

## 1. 第一性原理拆解（为什么是这个切片）

三个集合语义（Gate 2 已建立）：疾病靶点、成分靶点、二者交集。当前疾病靶点虽已能被冻结成严格
task snapshot，但**来源是客户端声明的**：`import_payload_sha256` 只证明"服务端封存了浏览器发来的
payload"，**不证明这份 payload 真的来自 Open Targets**。这正是 issue NP-009 的 close_condition。

要打破这个循环，信任边界必须从"客户端声明"移到"服务端对一份不可变原始产物的字节级核验 + 服务端解析"。
参照仓库已有 connector 模式（`TcmspConnector`）：**注入式 fetch + `@staticmethod parse_*` + cache_repo**，
其中 `parse_*` 是纯函数信任边界、可完全离线单测。本切片对 Open Targets 复用同一模式，但 fetch 退化为
"读取用户提供的原始文件字节"，因此零网络、完全可测。

---

## 2. 现状锚点（真实符号，勿凭记忆）

- schema：`backend/app/schemas/network.py`
  - `NetworkDiseaseTargetImport`（L54）、`NetworkDiseaseTargetImportSnapshot`（L101，
    `provenance_verification_status: Literal["unverified_client_import"]`、`import_payload_sha256`）、
    `NetworkDiseaseTargetImportProvenance`（L106）、`NetworkDiseaseTargetRecord`（L41）。
  - `NetworkResearchReadiness`（L125）、`NetworkTargetLineageRow`（L131）、`NetworkTargetIntersectionRow`（L157）。
- service：`backend/app/services/network.py`
  - `_canonical_sha256`（L111）、`_build_import_snapshot`（L121）、`_build_lineage_row_id`（L134）、
    readiness 组装（L195–232，含 L212 的 `unverified_client_import` blocker 文案）、
    `build_target_lineage`（L236，参数 `disease_target_import`）、analyze 入口（L382 起）。
- connector 模式参考：`backend/app/services/network_connectors.py` → `TcmspConnector`
  （注入 `fetch_html` + `@staticmethod parse_compounds_from_html`）；外部 IO 封装
  `network_external_client.py`（本切片**不使用**其网络能力）。
- API：`backend/app/api/network.py`（`/api/network/analyze` 已接受可选 `disease_target_import`）。
- validator：`backend/scripts/validate_network_target_lineage.py`（stdlib-only，不 import service）。
- 前端：`frontend/lib/api/network.ts`、`frontend/lib/network-disease-import.ts`、
  `frontend/components/NetworkAnalysisClient.tsx`。
- 操作说明：`docs/guides/network-disease-target-import.md`。
- CORS：`app/main.py` 仅 `GET, POST`（本切片新增端点必须是 POST）。

---

## 3. TDD 纵向切片（RED → GREEN → REFACTOR，小步提交）

> 每步先写失败测试。后端门禁四件套 + pytest 必须逐步保持可绿。

### 步骤 A — schema：新增 verified 状态与字节 hash（RED 先行）

1. 新增 `NetworkDiseaseTargetVerifiedSnapshot`（或在现有 snapshot 上扩展一个可辨识变体）：
   - `provenance_verification_status: Literal["server_verified_raw_artifact"]`
   - `source_artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")`  ← 原始**文件字节** hash
   - 保留 `import_payload_sha256`（服务端解析后 canonical payload 的完整性锚，语义不同，两者并存）
   - `source_artifact_filename` / `source_artifact_media_type` / `usage_license_note`（真实 usage/license 说明）
   - `provenance_verification_status` 的**联合类型**：`Literal["unverified_client_import", "server_verified_raw_artifact"]`
     在 `NetworkDiseaseTargetImportProvenance` 与 task 持久化模型上放开为二选一。
   - **验证**：`test_network_service.py` 新增 RED —— verified snapshot 必须带 `source_artifact_sha256`，
     缺失或非 64-hex 时 `ValidationError`。

### 步骤 B — parser（纯函数信任边界，完全离线可测）

2. 新增 `backend/app/services/network_open_targets.py`：
   - `@staticmethod parse_open_targets_associations(raw_bytes: bytes, *, expected: <声明的 release/query/threshold/mapping>) -> list[NetworkDiseaseTargetRecord]`
     - 解析离线保存的 Open Targets GraphQL `data.disease.associatedTargets` JSON response；release/query/mapping/license 等 response 外事实由 raw-byte SHA-256 索引的 server-controlled manifest 封存。
     - 抽取 `approvedSymbol` → `canonical_symbol`、target id → `raw_identifier`、`associationScore`(=score_name) → `source_score`、
       稳定 `source_record_id`。
     - **失败关闭校验**（任一不满足 → raise）：release/version 与文件内声明不一致；记录 `source_score < applied_threshold`；
       identifier mapping 与声明不符；records 为空且声明非零。
   - **验证**：新增 `test_network_open_targets.py`，用 `backend/tests/data/` 下一份**小型**真实结构样本，
     覆盖：正常解析、字节篡改（hash 不符）、阈值不满足、release 声明不一致、空文件。

### 步骤 C — service：字节 hash + 服务端派生 verified snapshot

3. 新增 `_build_verified_import_snapshot(raw_bytes, declared_meta) -> NetworkDiseaseTargetVerifiedSnapshot`：
   - `source_artifact_sha256 = hashlib.sha256(raw_bytes).hexdigest()`（**原始字节**）。
   - 调 parser 得 `records`，再复用现有 `_build_import_snapshot` 逻辑生成 `import_payload_sha256`
     （对服务端解析出的 canonical payload）。
   - 组装 `NetworkDiseaseTargetImportProvenance`，`provenance_verification_status="server_verified_raw_artifact"`。
   - **验证**：`test_network_service.py` —— 相同 raw bytes ⇒ 相同两个 hash（确定性）；篡改一个字节 ⇒
     `source_artifact_sha256` 改变；records 仍走既有 lineage_row_id 稳定性不变量。

4. readiness（L195–232）：
   - 当疾病来源为 `server_verified_raw_artifact` 时，**移除**"未验证客户端导入"blocker，
     **改写**为"疾病来源已服务端核验；compound 来源保真 / 阈值 / 人工 adjudication 未完成，
     不能进入正式研究状态"。
   - `formal_network_ready` 仍 `False`。
   - **验证**：verified 路径与 unverified 路径分别断言 blocking_reasons 文案与 `formal_network_ready=False`。

### 步骤 D — API 入口（POST，multipart 原始文件）

5. 新增 `POST /api/network/disease-import/verify`（或在 analyze 增开 multipart 变体，二选一，倾向独立端点）：
   - 接收 `file`（raw artifact，multipart）+ 声明元数据（release/version、query id/label、
     structured query params、query_date、retrieved_at、applied_threshold、identifier_mapping_version、
     usage_license_note）。
   - schema `extra="forbid"`：客户端**不能**提交 records、row ID、intersection、readiness、
     provenance_verification_status、任何 hash 或人工判定字段。
   - 服务端读字节 → 派生 verified snapshot → 落 task（JSON/SQLite/PostgreSQL 三路 repo 均需带新字段）。
   - owner scope 与原子推进不变；后续 upsert 不覆盖原始 verified snapshot。
   - **验证**：`test_network_api.py` —— 合法文件 ⇒ verified snapshot 落库；提交 records/hash 字段 ⇒ 422；
     字节篡改后声明不符 ⇒ 拒绝；owner 隔离（reviewer-b 读 reviewer-a 任务 404）保持。

### 步骤 E — repositories 持久化三路一致

6. `network_tasks.py` / `sqlite_network_tasks.py` / `postgres_network_tasks.py` + `postgres_schema.sql`
   + `protocols.py`：持久化并回读新字段（`source_artifact_sha256`、`provenance_verification_status`
   联合值、license note 等）。
   - **验证**：`test_network_task_repository_backends.py` 对三 backend 断言 round-trip 保真。

### 步骤 F — Markdown 报告 + 独立 validator

7. `build_network_report_markdown`（network.py 内报告段）：新增/更新 provenance 段，展示
   `server_verified_raw_artifact`、`source_artifact_sha256`、release/version、usage/license note，
   并保留"疾病来源已核验但整体未达 readiness"的边界提示。
8. `backend/scripts/validate_network_target_lineage.py`：
   - 识别 `provenance_verification_status ∈ {unverified_client_import, server_verified_raw_artifact}`。
   - 若为 verified，要求存在 `source_artifact_sha256`（64-hex）；对给定 raw artifact 路径（可选参数）
     复算字节 hash 并比对，不符退出 2。
   - 保留原有计数 / row IDs / payload hash / 阈值 / protocol / 双侧 refs 复算。
   - **验证**：`test_validate_network_target_lineage.py` 新增 verified-good（退 0）与
     tampered-artifact-hash（退 2）用例。

### 步骤 G — 前端最小对齐（不扩范围）

9. `frontend/lib/api/network.ts` types + `NetworkAnalysisClient.tsx`：
   - 展示 `server_verified_raw_artifact` 徽标与 `source_artifact_sha256`、release、usage note；
   - 与 `unverified_client_import` 视觉区分；
   - 上传原始文件走 multipart（**不手写 `Content-Type`**，符合既有约定）。
   - **验证**：`network-api.test.ts` / `network-report-ui.test.ts` / 源码 regex 一致性测试保持绿；
     必要时更新断言文案。

### 步骤 H — guide 更新

10. `docs/guides/network-disease-target-import.md`：新增"服务端原始快照核验"章节：支持的原始文件格式、
    如何从 Open Targets 导出、声明字段含义、`server_verified_raw_artifact` 的**准确含义与边界**
    （字节完整性 + 服务端解析 ≠ 生物学正确 ≠ release 选择正确 ≠ 人工判定通过）。

---

## 4. 验收门禁（收口前必须全绿）

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m ruff format --check app tests
& .\.uv-test-venv\Scripts\python.exe -m ruff check app tests
& .\.uv-test-venv\Scripts\python.exe -m mypy app
& .\.uv-test-venv\Scripts\python.exe -m pytest -q
```
```bash
cd frontend && pnpm test && pnpm typecheck && pnpm build
```
```powershell
.\scripts\verify-local.ps1
.\scripts\verify-local.ps1 -IncludeE2E   # Playwright 4/4
```
- `pnpm audit --prod` = 0 vulnerabilities。
- `git diff --check` 干净（仅允许既有 Windows line-ending warning）。
- protected token smoke：reviewer-a / reviewer-b 均通过；reviewer-b 读 reviewer-a result/report = 404。
- 独立 validator 对一份 verified artifact 退 0、对篡改字节退 2。

---

## 5. 收口时必须诚实声明的边界（写进 handoff）

- `source_artifact_sha256` 只锚定**原始文件字节身份与完整性**，`import_payload_sha256` 只锚定
  **持久化 canonical snapshot**；raw-to-records 派生由生产 parser 与 parser 测试覆盖，当前独立 validator
  不重演 GraphQL parser。它们都**不证明** Open Targets release 选择正确、表型映射正确或靶点有生物学意义。
- 本切片**不翻转** `formal_network_ready`；compound 来源保真、数据库版本/阈值、逐边人工 adjudication
  仍是其后独立门禁。
- verified 状态名为 `server_verified_raw_artifact`，**不是** `verified`（终态需全链人工判定）。
- 默认 mock 与无网络路径不变；未引入任何 Open Targets 网络请求。
- 自动化 validator 只证明 artifact/字节一致性，不替代外部数据库真实性核验或领域专家判断。

---

## 6. 工作树边界（交给 codex 的硬约束）

- 分支保持 `feat/pillar2-real-evidence-ranking`；与用户既有 Track A / Gate 1 / Gate 2 改动共存。
- **不要** stage/commit/push（除非用户明确要求）；**不要**清理用户既有文件。
- **不要**提交 `.mcp.json`、`components.json`、runtime state、`backend/uploads/`、`.tmp`、secrets。
- `frontend/next-env.d.ts`：若 E2E 后变成 `.next/dev/types/routes.d.ts`，收口前恢复为
  tracked 的 `./.next/types/routes.d.ts`。
- 遵守 CodeGraph 优先、结构查询不用 grep 的项目规则。

---

## 7. 建议 codex skill 与执行顺序

1. `qiyan-adversarial-hardening`：先定义受保护科研资产（raw artifact 字节完整性、服务端解析信任边界）
   与失败关闭行为。
2. `test-driven-development`：从"字节篡改必须拒绝""客户端不能提交 records/hash 冒充 verified"
   两条 RED 测试起步。
3. 若原始文件支持格式仍有歧义，先用 `project-grill` 收紧 parser 契约，再写单一纵向切片实现。
