# ADR-0012: 真实 LLM 启用决策与不变量

日期：2026-05-31

## 状态

Accepted

## 背景

C 阶段路线图（`docs/plans/2026-05-21-roadmap.md`）的最后一项是「MVP-A LLM 化」：让真实 LLM provider 从仅本地显式 smoke，推进到一条有治理、可回滚的内部预览启用路径。前置工作已完成：

- C1 真实 provider（`opencode_go` 优先，`anthropic` 后置）已接入并可回退 deterministic；
- 结构化 + 证据 ID + BGE 语义 grounding gate 已落地并验证（`docs/evaluations/2026-05-31-bge-semantic-evaluation.md`）；
- 2026-05-31 真实 live smoke 完成（`docs/evaluations/2026-05-31-opencode-go-bge-smoke.md`）；
- 成本/延迟 SLI 已暴露到 API/前端/日志；
- 外部数据流向与 PIPL 措辞已记录（ADR-0011）。

live smoke 暴露了两个必须写入启用决策的事实：
1. `deepseek-v4-flash`（thinking mode）拒绝强制 `tool_choice`（HTTP 400），真实路径只能走 structured claims v3，而非 provider-native tool use；
2. 默认 `max_tokens=1200` 会被 reasoning 吃光导致空 content → deterministic fallback，需 ≥4000 才能让真实路径生效。

同时，0.78 阈值（在 20 对标注集上校准）对真实、较长、含改写的 LLM claim 偏严，会把若干可能忠实的 claim 拦截（`semantic_low_support`）。这意味着「打开真实模型」与「让真实模型答案默认对用户可见」是两个不同的成熟度。

## 决策

1. **保留 deterministic 为默认**：真实 provider 始终是显式 opt-in（`QIYAN_LLM_PROVIDER`），默认用户路径不外发、不依赖 key。

2. **真实 provider 启用的强制不变量**（任何启用场景都必须满足，否则不得启用）：
   - **免责声明**：`非诊断结论、需结合临床。` 在每个回答 byte-identical 存在（由后端 `DISCLAIMER` 与前后端测试锁定，不得改写）。
   - **grounding gate 常开**：外部 provider 的回答必须经过 grounding gate（结构化 claims + 证据 ID 白名单 + BGE 语义阈值）；未通过即替换为 hard-block 文案、`grounding.status="blocked"`，绝不展示未校验草稿。
   - **安全回退**：缺 key、HTTP 错误、网关失败、空 content、响应结构异常都必须回退 deterministic，`/api/rag/answer` 不对用户硬失败。
   - **secret 仅 env**：key 只从 `QIYAN_OPENCODE_GO_API_KEY` 读取，不入仓库/README/handoff/测试/日志。

3. **模型相关配置约束**（基于 live smoke）：
   - `deepseek-v4-flash` 不支持强制 tool_choice；启用时按 structured claims v3 路径预期，不假设 provider-native tool grounding。
   - `QIYAN_OPENCODE_GO_MAX_TOKENS` 必须 ≥4000（thinking 模型需在 reasoning 之后留出 content 余量）；过低会静默退化为 deterministic。

4. **分两级启用成熟度**：
   - **L1 — 受控 smoke / 演示（当前可启用）**：本地或受控环境用真实 provider 演示，grounding gate 常开。允许出现 `semantic_low_support` 拦截，并向观众解释这是反幻觉护栏在工作。无需阈值重校准。
   - **L2 — 默认预览路径（暂不启用，需补前置）**：把真实 provider 作为内部预览默认 RAG 路径，前置条件：
     a. 扩充 `backend/data/evals/grounding_semantic_pairs.json` 至包含真实 LLM 风格 claim，并用 `run_grounding_semantic_separation` 重新校准阈值（候选区间 0.55–0.72），使忠实改写不被过度拦截；
     b. 用真实合同单价配置 `QIYAN_OPENCODE_GO_PRICE_*`，并记录成本/延迟 SLI 基线；
     c. 完成一次真人内部 reviewer 走查（`docs/checklists/internal-preview-smoke.md`）。

5. **回滚开关**：设 `QIYAN_LLM_PROVIDER=deterministic`（或清空）即时关闭真实 provider，无需改代码。这是唯一且充分的回滚动作。

## 后果

正面：
- 真实模型可在 L1 受控场景启用，路线图「MVP-A LLM 化」的工程底座收口。
- 不变量写明后，启用/回滚动作可被任何运维或下一会话安全执行。
- L1/L2 分级避免把「能调真实模型」误当成「真实答案默认可见」。

代价：
- L2（默认预览）仍被阈值重校准与真人走查阻塞，不在本轮交付范围。
- thinking 模型的 token 余量与 tool 限制属于模型相关约束，换模型需重跑 smoke 复核。

## 验证

- 启用与回滚步骤见 `docs/guides/real-llm-enablement-runbook.md`。
- 不变量回归由现有后端/前端 grounding、disclaimer、fallback 测试覆盖（`tests/test_rag_service.py`、`tests/test_grounding_semantic.py`、前端 `rag-export` / `client-section-consistency`）。
- live 行为证据见 `docs/evaluations/2026-05-31-opencode-go-bge-smoke.md`。
