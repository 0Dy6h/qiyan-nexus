# ADR-0011: 外部 LLM 数据流向与 PIPL 处理原则

日期：2026-05-31

## 状态

Accepted

## 背景

默认 RAG 路径是离线 deterministic provider，不向任何外部服务发送数据。C 阶段引入了可选的真实 LLM provider（当前优先 `opencode_go`，后置可选 `anthropic`）。一旦启用真实 provider，RAG 回答的生成会把请求发送到外部 OpenAI 兼容网关。

2026-05-31 的真实 live smoke（见 `docs/evaluations/2026-05-31-opencode-go-bge-smoke.md`）确认：启用 `opencode_go` 后，后端会把「问题文本 + 本次命中的引用片段（chunk quote/snippet）」组装进 system/user message 发送给外部网关。检索、引用卡片、免责声明与 grounding gate 仍由本地后端控制，但生成步骤的输入确实离开了本地进程。

平台面向医生与科研人员（非患者 C 端），合规底线要求所有 AI 输出带 `非诊断结论、需结合临床。`，并且不替代诊断。在启用真实模型前，必须明确对外发送了什么、不发送什么，以满足 PIPL 的最小必要与告知原则，并让 `/compliance` 页对用户透明。

## 决策

1. **默认不外发**：`QIYAN_LLM_PROVIDER=deterministic`（默认）与 `mock_claude` 完全离线，问题与引用片段不发送给任何外部服务。这是默认用户路径。

2. **启用真实 provider 时的外发边界**：当 `QIYAN_LLM_PROVIDER=opencode_go`（或后置可选 `anthropic`）时，仅以下内容会发送至外部 OpenAI 兼容网关：
   - 当前问题文本；
   - 本次检索命中的引用片段文本（chunk 的 `quote`，缺失时回退 `snippet`）与其证据 ID；
   - 固定的 grounding system prompt 与（在支持的模型上）工具 schema。

3. **明确不外发清单**：
   - 患者身份信息、就诊记录、姓名、联系方式等任何可识别个人信息（平台本就不要求上传此类数据）；
   - 完整 PDF 原文、runtime state 文件、上传文件本体；
   - API key 不会出现在任何日志、README、handoff、测试或本 ADR；secret 只从 env 读取。

4. **PIPL 原则落地**：
   - 最小必要：只发送生成回答所需的问题与引用片段，不发送多余上下文；
   - 告知：`/compliance` 页「隐私与数据处理」段明示默认离线、启用真实模型后的外发内容与外发边界（见 `frontend/lib/compliance-page.ts`，由 `compliance-page.test.ts` 断言）；
   - 可控：是否启用真实 provider 完全由本地 env 控制，运维可随时切回 deterministic 关闭外发。

5. **观测但不外发敏感内容**：SLI 结构化日志（`rag_sli`，见 ADR/Slice 2）只记录 provider 名、grounding 状态、延迟、token 数与成本，不记录问题正文、引用正文或 key。

## 后果

正面：
- 启用真实模型前后的数据流向有书面、可核对的边界，便于合规审查与内部 sign-off。
- `/compliance` 对用户透明，符合 PIPL 告知原则。
- 默认路径仍然零外发，真实 provider 是显式 opt-in。

代价：
- 启用真实 provider 即意味着问题与引用片段离开本地；在处理任何含敏感信息的真实查询前，需要由使用方确保查询本身不含个人可识别信息。
- 本 ADR 描述的是数据流向原则，不替代与具体外部网关供应商之间的数据处理协议（DPA）；正式生产部署仍需单独评估供应商条款。

## 验证

- `frontend/tests/compliance-page.test.ts::getComplianceHighlights privacy section discloses external LLM egress and PIPL handling` 锁定 `/compliance` 隐私段措辞。
- `docs/evaluations/2026-05-31-opencode-go-bge-smoke.md` 记录真实外发行为的观测证据。
- 启用决策与运维开关见后续 ADR-0012（真实 LLM 启用决策）。
