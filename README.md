# Qiyan Nexus

面向特应性皮炎（AD）医生与科研人员的中医药证据与科研工作台。

当前状态：MVP-A 证据工作台基本可内部走查；MVP-B 网络药理学 mock 起步链路已落地；C 阶段 provider / retrieval / grounding 底座部分提前完成。文献检索使用本地 JSON seed + repository/service 层；运行时 PDF metadata、parse 状态、PubMed sync 结果与 network task 写入 `backend/data/runtime/`，不再污染 seed fixture。RAG endpoint 默认采用 deterministic provider + keyword retrieval，返回 answer、citation cards、retrieval metadata、provider name、token usage、grounding metadata 字段与“非诊断结论、需结合临床”免责声明；后端可通过本地 env 显式切换到 `mock_claude`、`opencode_go` 或后置可选的 `anthropic` provider 做 wiring/live smoke，其中 `opencode_go` 是当前优先 live-provider 路径：优先尝试 OpenAI-compatible tool/function calling，若网关拒绝 tools 则回退到 structured claim grounding v3；`anthropic` 路径保留为后续有订阅时的可选 smoke。PDF upload 支持本地文件存储、稳定 upload id 下载/预览；文本型 PDF 可通过 `pypdf` 生成预览文本，扫描件或无法抽取文本时诚实回退到文件级占位说明。当前默认仍不接真实 LLM、真实 embedding 模型、pgvector、Neo4j、Celery、Redis、MinIO、NextAuth 或外部生产服务；外部服务只作为本地显式 smoke，不进入默认用户路径。

当前事实源索引见 `docs/current-state.md`。正式命名建议见 `docs/evaluations/2026-05-06-project-evaluation-and-optimization.md`。当前本地工作区为 `D:\Projects\Tcm_tech`。

## 目录

- `frontend/` — Next.js 前端应用
- `backend/` — FastAPI 后端应用
- `infra/` — 本地基础设施说明与后续 Docker Compose 入口
- `docs/` — 当前状态、ADR、计划、交接与历史归档
- `docs/archive/pre-dev-planning/` — 早期 AI 工具链规划、Word 文档与 HTML 原型，仅作历史参考

## 后端

首次安装（Windows PowerShell）：

```powershell
cd backend
py -3.11 -m venv .uv-test-venv
& .\.uv-test-venv\Scripts\python.exe -m pip install -U pip
& .\.uv-test-venv\Scripts\python.exe -m pip install -e ".[dev]"
```

运行测试：

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m pytest -q
```

启动开发服务：

```powershell
cd backend
& .\.uv-test-venv\Scripts\fastapi.exe dev app/main.py
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

访问控制（可选，A2）：

- 默认 `QIYAN_ACCESS_TOKENS` 未设置时全部接口开放（dev 模式）。
- 设置后所有非 `/health` 与非 OPTIONS preflight 请求必须带 `X-Access-Token` 请求头匹配白名单，否则返回 401。
- 示例：`$env:QIYAN_ACCESS_TOKENS="dev-token-1,internal-reviewer-2"; & .\.uv-test-venv\Scripts\fastapi.exe dev app/main.py`，调用方需 `curl -H "X-Access-Token: dev-token-1" http://127.0.0.1:8000/api/literature/search?q=AD`。
- CORS 配置不变；前端如需带 token 调用，需要后续在 fetch wrapper 里加 header（A2 不动前端）。

文献检索 API 数据来源：

- seed 文献 JSON：`backend/data/literature/sample_ad_literature.json`
- seed chunk JSON：`backend/data/literature/sample_ad_chunks.json`
- runtime 文献状态：`backend/data/runtime/literature_state.json`（gitignored，可从 seed bootstrap）
- repository 层：`backend/app/repositories/literature.py`
- service 层：`backend/app/services/literature.py`
- 当前 PDF metadata 字段：`pdf_upload_id`、`pdf_file_name`、`pdf_parse_status`、`pdf_parse_message`、`pdf_parse_started_at`、`pdf_parse_finished_at`、`last_parse_trigger`、`parse_attempt_count`、`pdf_parse_result`
- 当前支持本地 PDF 上传存储：`POST /api/uploads/pdf`（multipart `file`），默认写入 `backend/uploads/`，可通过 `UPLOAD_STORAGE_DIR` 覆盖
- 当前支持本地 PDF 下载/预览：`GET /api/uploads/pdf/{pdf_upload_id}`，按稳定 upload id 读取 `UPLOAD_STORAGE_DIR` 下的 PDF 文件
- 当前支持文本型 PDF 预览：parse result 可返回 `extraction_method="pypdf-text-preview"` 与 `preview_text`；无法抽取文本时返回 `file-metadata-placeholder`

文献检索 API：

```bash
curl "http://127.0.0.1:8000/api/literature/search?q=特应性皮炎"
```

支持参数：

- `q`：必填检索关键词，后端会 trim。
- `source`：`all` / `cn_literature` / `pubmed`，默认 `all`。
- `page`：页码，默认 `1`。
- `page_size`：每页数量，默认 `10`，最大 `50`。
- `sort`：`relevance` / `year_desc` / `year_asc`，默认 `relevance`。

示例：

```bash
curl "http://127.0.0.1:8000/api/literature/search?q=瘙痒&source=cn_literature&page=1&page_size=5&sort=relevance"
```

返回字段保留 `query`、`total`、`items`，并新增 `source`、`page`、`page_size`、`total_pages`、`sort`，用于前端分页和排序展示。

文献详情 API：

```bash
curl "http://127.0.0.1:8000/api/literature/cn-ad-gbs-001"
```

PDF upload API（本地文件存储 + 自动关联 literature metadata；默认返回 pending）：

```bash
curl -X POST "http://127.0.0.1:8000/api/uploads/pdf" \
  -F "literature_id=cn-ad-gbs-001" \
  -F "file=@/absolute/path/to/ad-evidence.pdf;type=application/pdf"
```

PDF download/preview API（本地对象存储 mock）：

```bash
curl -L "http://127.0.0.1:8000/api/uploads/pdf/pdf-cn-ad-gbs-001-ad-evidence-pdf" \
  -o ad-evidence.pdf
```

说明：upload endpoint 负责落盘与写入 `pending`；独立 auto-parse endpoint 负责推进 parse 状态，并补充 `pdf_parse_message`、`pdf_parse_started_at`、`pdf_parse_finished_at`、`last_parse_trigger`、`parse_attempt_count` 与 `pdf_parse_result`。解析成功后会向 runtime chunk 状态补充 `source_type=uploaded_pdf` 的 chunk，使上传 PDF 的解析片段可进入 RAG 检索与 citation cards。

Auto-parse API：

```bash
curl -X POST "http://127.0.0.1:8000/api/uploads/pdf/auto-parse" \
  -H "Content-Type: application/json" \
  -d '{"literature_id":"cn-ad-gbs-001","file_name":"ad-evidence.pdf"}'
```

PDF metadata attach API（backend-only）：

```bash
curl -X POST "http://127.0.0.1:8000/api/literature/pdf-metadata" \
  -H "Content-Type: application/json" \
  -d '{"literature_id":"cn-ad-gbs-001","file_name":"ad-evidence.pdf","source_type":"uploaded_pdf"}'
```

PDF parse status API（backend-only）：

```bash
curl -X POST "http://127.0.0.1:8000/api/literature/pdf-parse-status" \
  -H "Content-Type: application/json" \
  -d '{"literature_id":"cn-ad-gbs-001","pdf_parse_status":"parsed"}'
```

RAG API：

```bash
curl -X POST "http://127.0.0.1:8000/api/rag/answer" \
  -H "Content-Type: application/json" \
  -d '{"question":"特应性皮炎和肠-脑-皮肤轴有什么关系？","source":"all","top_k":2}'
```

当前 RAG endpoint 默认采用 `deterministic` provider + `keyword` retrieval：基于 literature + chunk 样本，对 title/snippet/abstract/keywords/evidence_tags/chunk text 做关键词命中计分，并返回 answer + citation cards + “非诊断结论、需结合临床”免责声明。后端契约测试保证每个 `citations[*].literature_id` 都能通过 `/api/literature/{item_id}` 解析到文献详情。RAG 请求支持 `source`（`all` / `cn_literature` / `pubmed`）和 `top_k`（>= 1）控制 citation card，并返回 `retrieval` 元数据（`applied_source`、`applied_top_k`、`available_citation_count`、`strategy`）供前端展示当前检索条件；response 顶层同时返回 `provider_name`、`input_tokens`、`output_tokens` 与 `grounding` metadata，其中 deterministic / fallback 路径 token 为 `null`、grounding 为 `skipped`。

Grounding：

- `opencode_go` 是当前优先 live-provider grounding 路径：后端优先发送 OpenAI-compatible `record_grounded_claims` function tool，工具参数只允许 `claims[].text` 与 `claims[].evidence_refs`；后端只展示由工具输入重新组装且通过本次 citation 证据 ID 白名单的 answer。
- 若 OpenCode Go 网关或模型拒绝 tool/function calling，provider 会重试不带 tools 的 structured claims JSON 路径，后续仍由 structured claim grounding v3 校验：`{"claims":[{"text":"...","evidence_refs":["chunk-..."]}]}`。
- `anthropic` 成功路径保留 provider-native strict tool use，但当前后置为可选 smoke，不作为优先路径。
- 若 provider 未调用预期工具、工具参数不合法、claims 为空，或任一外部 provider 引用了本次 citations 未提供的证据 ID，`answer` 会被替换为拦截提示，`grounding.status="blocked"`，但 citations、provider name、token usage、`claim_count`、`cited_claim_count`、`structured_claims`、native grounding 与 tool metadata 会保留，便于排查。
- 语义级 grounding（hallucination reject）：结构与证据 ID 校验通过后，外部 provider 的每条 claim 还会与其引用 chunk 文本（`quote`，缺失时回退 `snippet`）计算 cosine 相似度；任一 claim 低于阈值则 `grounding.status="blocked"`、`blocked_reason="semantic_low_support"`，`grounding.structured_claims[].semantic_score`、`min_semantic_score`、`semantic_threshold` 一并返回。阈值由 `QIYAN_GROUNDING_SEMANTIC_THRESHOLD` 控制（默认 `0.40`，`<=0` 关闭）。**默认 `hashing` embedding backend 下该分数是逐字符的词汇重叠代理（lexical proxy），不是真正的语义判定；`QIYAN_EMBEDDING_BACKEND="bge"` 可原地升级为真实语义。** 标注语料 `backend/data/evals/grounding_semantic_pairs.json` 上，默认阈值对忠实 claim 零误拦、配对分离 10/10；可通过 `run_grounding_semantic_separation` 复核混淆矩阵。
- `deterministic` 与外部 provider fallback 到 deterministic 的路径不做后验拦截，`grounding.status="skipped"`（语义 gate 同样只作用于 `anthropic` / `opencode_go`）。
- 当前 grounding 约束引用声明、工具调用、越界证据 ID 与上述语义支持度阈值；语义层为 lexical proxy（除非启用 `bge`），仍不等同于完整事实核验，也不代表真实 LLM 默认开放（隐私措辞、延迟/成本 SLI 为独立后续 slice）。

可选 LLM providers（本地 smoke 用，默认不启用）：

- `QIYAN_LLM_PROVIDER=deterministic` 或未设置：默认离线 deterministic provider。
- `QIYAN_LLM_PROVIDER=mock_claude`：离线 mock provider，用于前后端 wiring 与 UI 展示。
- `QIYAN_LLM_PROVIDER=opencode_go`：当前优先 live-provider；调用 OpenCode Go OpenAI-compatible Chat Completions API；优先尝试 function tool grounding，必要时回退 structured claims v3。
- `QIYAN_LLM_PROVIDER=anthropic`：后置可选；调用 Anthropic SDK；key 从 `ANTHROPIC_API_KEY` 读取；模型与 token 上限可用 `QIYAN_ANTHROPIC_MODEL`、`QIYAN_ANTHROPIC_MAX_TOKENS` 覆盖；成功路径必须经过 `record_grounded_claims` strict tool-use grounding。
- provider 出错或缺 key 时应回退 deterministic，不应让 `/api/rag/answer` 对用户硬失败。

- `QIYAN_LLM_PROVIDER=opencode_go` 时，RAG answer 文本会调用 OpenCode Go OpenAI-compatible Chat Completions API；检索、citation cards 与 disclaimer 仍由本地后端控制。
- API key 只从 `QIYAN_OPENCODE_GO_API_KEY` 读取，不能写入仓库、README、handoff 或测试。
- 默认 endpoint 与模型：`QIYAN_OPENCODE_GO_BASE_URL="https://opencode.ai/zen/go/v1"`，`QIYAN_OPENCODE_GO_MODEL="deepseek-v4-flash"`。
- 建议 smoke 时使用 `QIYAN_OPENCODE_GO_MAX_TOKENS="1200"`；实测部分 reasoning 模型在过低上限下只返回 `reasoning_content` 而 `content` 为空，会触发 deterministic fallback。
- 未设置 key、HTTP 错误、网关失败或响应结构异常时，provider 会记录不含 secret 的 warning，并回退到 deterministic answer。

可选 retrieval providers（默认不启用 vector/hybrid）：

- `QIYAN_RETRIEVAL_PROVIDER=keyword` 或未设置：默认 keyword + alias ranker。
- `QIYAN_RETRIEVAL_PROVIDER=vector`：使用本地 chunk vector index；默认 hashing embedding backend 可离线运行。
- `QIYAN_RETRIEVAL_PROVIDER=hybrid`：用 Reciprocal Rank Fusion 融合 keyword + vector。
- 当前默认不启用真实 embedding 模型；`vector` / `hybrid` 仅用于 opt-in ablation 与 smoke。

PowerShell 本地 smoke 示例：

```powershell
cd backend
$env:QIYAN_LLM_PROVIDER="opencode_go"
$env:QIYAN_OPENCODE_GO_API_KEY="<local-secret>"
$env:QIYAN_OPENCODE_GO_MODEL="deepseek-v4-flash"
$env:QIYAN_OPENCODE_GO_MAX_TOKENS="1200"
& .\.uv-test-venv\Scripts\fastapi.exe dev app/main.py
```

另开终端调用：

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/rag/answer" `
  -ContentType "application/json" `
  -Body '{"question":"特应性皮炎和肠-脑-皮肤轴有什么关系？","source":"all","top_k":1}'
```

RAG eval API：

```bash
curl "http://127.0.0.1:8000/api/evals/rag-ad/report"
```

当前评估报告基于 `backend/data/evals/rag_ad_eval_questions.json` 的 50 个特应性皮炎问题，调用 deterministic RAG 后返回 summary + item results。当前基线目标：50 题通过率保持内部基线，citation/chunk 命中、disclaimer coverage 与 must_not violations 以本地测试输出与最新 handoff 为准。

Network pharmacology API（mock）：

```bash
curl -X POST "http://127.0.0.1:8000/api/network/analyze" \
  -H "Content-Type: application/json" \
  -d '{"query":"消风散","analysis_type":"formula"}'
```

随后轮询：

```bash
curl "http://127.0.0.1:8000/api/network/result/<task_id>"
curl "http://127.0.0.1:8000/api/network/entities"
```

当前网络药理学仍是 seed graph + runtime task 壳，用于验证「复方/草药 - 成分 - 靶点 - 通路 - 疾病」产品路径、citation/entity 双向跳转与前端 Markdown 报告导出，不代表科研级 TCMSP / STRING / KEGG / GO 富集分析。

标准后端验证：

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m ruff format --check app tests
& .\.uv-test-venv\Scripts\python.exe -m ruff check app tests
& .\.uv-test-venv\Scripts\python.exe -m mypy app
& .\.uv-test-venv\Scripts\python.exe -m pytest -q
```

## 前端

首次安装：

```bash
cd frontend
pnpm install
```

构建验证：

```bash
cd frontend
pnpm build
```

启动开发服务：

```bash
cd frontend
pnpm dev
```

前端 API 地址默认是 `http://127.0.0.1:8000`。如需覆盖：

```bash
cd frontend
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 pnpm dev
```

前端测试：

```bash
cd frontend
pnpm test
pnpm typecheck
pnpm build
```

页面：

- 首页：`/`
- 文献检索页：`/literature`
- RAG 问答页：`/rag`
- 文献详情页：`/literature/[id]`
- RAG 评估页：`/evals/rag-ad`
- 合规说明页：`/compliance`
- 网络药理学页：`/network`

当前前端能力：

- `/literature`：支持 query 输入、来源筛选、加载/错误/空结果状态、结果卡片跳转详情页，并展示演示数据提示。
- `/rag`：支持 question、source、top_k 输入，展示 answer、provider、retrieval strategy、token usage、grounding status、native grounding、tool metadata、句级引用覆盖、结构化声明数、citation cards 与免责声明；当外部 provider 草稿未通过 grounding 时展示拦截提示；支持 Markdown 导出。
- `/literature/[id]`：服务端读取文献详情，展示统一 meta/body 样式，并提供 PDF 上传入口、PDF 预览链接、parse status、parse message、时间戳、触发来源、尝试次数、解析方式与解析结果预览。
- `/evals/rag-ad`：客户端触发 `/api/evals/rag-ad/report`，展示 50 题 RAG 评估的通过率、引用命中、chunk 命中、免责声明覆盖、禁用语检查与 grounding 拦截计数。
- `/network`：提交 mock 网络药理学分析任务，展示 seed chain、entity chips、相关文献与 RAG/network 互链，并可把当前完成结果导出为 Markdown 报告。
- `/rag` 与 `/literature` 的状态文案、状态面板、meta 行和正文密度已做最小统一。
- 当 RAG 成功返回 0 citations 时，会展示明确空状态提示，而不是空白引用区。

## 合规底线

所有 AI 输出必须带：

非诊断结论、需结合临床。

本平台不替代医生诊断，不面向普通患者 C 端。
