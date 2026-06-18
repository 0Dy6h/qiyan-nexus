# Qiyan Nexus 正式 Reviewer 走查任务单

用途：给医生 / 科研 reviewer 用 30-45 分钟完成正式 sign-off 走查。正式展开 S1-S4 前，先跑 10-15 分钟“核心证据整理任务”，验证真实用户是否愿意用 Qiyan Nexus 完成一次 AD 中医药证据整理，并认可引用可追溯性。详细步骤不在本任务单重抄；需要展开操作时，按 `docs/checklists/internal-preview-reviewer-walkthrough.md` 的对应小节执行。

## 本轮产品验证目标

不扩功能，先验证：

> 真实医生 / 科研用户是否愿意用 Qiyan Nexus 完成一次 AD 中医药证据整理任务，并认可其证据可追溯性。

判定信号：

- reviewer 能在少量提示下完成“文献或 PDF → RAG 提问 → citation 追溯 → Markdown 导出”。
- reviewer 没有把 seed / sample / uploaded PDF / network mock 数据误解为外部真实数据库结论。
- reviewer 认为 citation cards 和文献详情跳转足以支持后续人工核查。
- 所有 AI/RAG/network 输出都保留 `非诊断结论、需结合临床。`。
- 若出现 P0/P1，先修复并复测，不进入更大范围试用。

配套执行计划见 `docs/plans/2026-06-18-core-evidence-workflow-validation.md`。

## 走查前固定边界

| 项 | 本轮固定值 |
|---|---|
| 运行 profile | `deterministic` provider + `keyword` retrieval + 离线 + isolated runtime |
| Runtime root | `.tmp\reviewer-card-open` |
| 禁止开启 | 真实 LLM key、真实 embedding、pgvector、Neo4j、`QIYAN_GROUNDING_SEMANTIC_THRESHOLD=0` |
| 免责声明字节串 | `非诊断结论、需结合临床。` |
| 主 PDF 样本 | `local-review-pdfs/健脾养血祛风法治疗特应性皮炎临床疗效及对皮肤屏障功能的影响_杨雪松.pdf` |
| 可选质量警告样本 | `local-review-pdfs/中医辨证治疗异位性皮炎临床观察_周海啸.pdf` |
| 反馈记录 | `docs/evaluations/2026-06-05-reviewer-feedback.md`，临床写 Reviewer A，科研写 Reviewer B，问题分级用 P0-P3 |
| Request ID | 优先用 smoke 输出的 `request_ids` 表；浏览器手工复现时取 DevTools Network 响应头 `X-Request-ID` |

技术团队应先跑并留存 smoke 结果：

```powershell
.\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\reviewer-card-open
.\scripts\smoke-internal-preview.ps1
.\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\reviewer-card-open -Stop
```

## 10-15 分钟核心证据整理任务

先让 reviewer 独立完成这个短流程，再进入 S1-S4 完整走查：

1. 访问 `/literature`，检索 `特应性皮炎` 或 reviewer 自己关心的 AD 中医药关键词。
2. 打开一篇文献详情；如果要验证本地 PDF，使用主 PDF 样本完成上传和解析。
3. 访问 `/rag`，提出一个真实证据问题，例如：`健脾养血祛风法治疗特应性皮炎的证据主要支持哪些观察指标？`
4. 检查回答里的免责声明、引用卡片、记录来源和文献详情跳转。
5. 导出 Markdown，并确认导出内容包含问题、答案、引用和免责声明。
6. 回答三件事：
   - 我是否愿意再次用它整理 AD 中医药证据？
   - citation 是否足够可追溯，让我愿意把它当作科研/临床参考辅助？
   - 是否有任何 seed、mock、uploaded PDF 或 AI 输出边界让我误解？

记录位置：正式 reviewer 写入 `docs/evaluations/2026-06-05-reviewer-feedback.md`；小范围试用参与者写入 `docs/evaluations/2026-06-06-small-scale-trial-feedback.md`。

## 自动化覆盖对照表

| 场景 | 已自动验证的客观锚 | 只能人工判断 |
|---|---|---|
| S1 文献四来源检索 | smoke `literature_all` / `literature_pubmed` / `literature_cnki` / `literature_uploaded_filter`：对应 `/api/literature/search` 返回 200 且有 `items` 字段；pytest `test_literature_search.py`：关键词结果、PubMed source filter、`has_pdf_upload=true/false`；Playwright `literature-data-source.spec.ts`：四来源选择器发送正确查询参数并更新数据来源 banner。 | reviewer 是否真正理解 seed / sample / uploaded PDF 边界；检索结果对临床或科研任务是否有用；TCM / AD 术语是否准确。 |
| S2 PDF 上传 → 解析 → RAG 引用 | smoke `pdf_upload`：201 + `pending`；smoke `pdf_auto_parse`：200 + `parsed` + `pdf_parse_result`；pytest `test_upload_api.py`：upload 不自动解析、auto-parse parsed/failed、preview / quality warning / placeholder 回退、runtime chunk 写入 `source_type=uploaded_pdf`；pytest `test_rag_service.py`：uploaded PDF citation metadata；frontend `rag-uploaded-pdf-citation.test.ts`：上传 PDF badge 与预览链接；Playwright `internal-preview.spec.ts`：上传后显示解析成功、解析方式和 PDF 预览入口。 | 抽取文本、数字和表格乱码是否影响信任；citation 的上传 PDF 来源说明是否清楚；解析失败或回退说明是否诚实。smoke 当前未断言“本次上传 PDF 必定进入 RAG citation”，该项需人工看或未来补断言。 |
| S3 RAG 答案 + 免责声明 | smoke `rag_answer`：200、免责声明字节一致、`citations.Count > 0`；smoke `rag_export`：Markdown export 200 且包含免责声明；pytest `test_rag_api.py`：默认 `deterministic` + `keyword`、免责声明、citation / source / top_k 元数据；pytest `test_rag_literature_contract.py`：每个 `citations[*].literature_id` 都能被 `/api/literature/{id}` resolve；Playwright `main-path.spec.ts`：RAG 页面显示免责声明、引用卡片、文献详情链接、Markdown 导出按钮。 | 答案医学准确性；是否过度承诺疗效；免责声明是否足够显著；引用是否真的支撑答案中的论断。 |
| S4 网络药理学 mock 边界 | smoke `network_analyze`：202 且 `data_mode=mock`；smoke `network_result`：200、completed、`data_mode=mock`、免责声明字节一致、`chains > 0`、`enrichment.terms > 0`；smoke `network_report`：report 200 且包含免责声明；pytest `test_network_api.py`：mock task 状态机、chains、report；pytest `test_network_enrichment_integration.py`：消风散 mock 分析返回非空 enrichment terms；pytest `test_network_report_service.py`：报告含 mock 边界说明、免责声明和富集参数；Playwright `internal-preview.spec.ts`：链 #1、报告导出、免责声明；Playwright `network-graph-keyboard.spec.ts`：键盘 focus / Enter / Space / Escape / arrow 导航。 | reviewer 是否清楚理解这是“非真实科研结果”；富集 p-value 是否会被误读为真实统计；作用链证据、边界提示和科研可信度是否足够。 |

## S1 文献四来源检索

- 目标：确认 reviewer 能理解并使用“全部来源 / PubMed 记录 / CNKI sample / 上传 PDF”的边界。
- 操作路径：访问 `/literature`，分别切换四来源并检索；需要细节时看 `internal-preview-reviewer-walkthrough.md` 的 S1 小节。
- ✅ 已自动验证：见对照表中的 smoke literature flows、`test_literature_search.py`、`literature-data-source.spec.ts`。
- 🧠 只看你的专业判断：数据来源 banner 是否让你真正理解“演示 seed != 真实可检索文献”；检索结果是否对临床 / 科研问题有用；标题、证候、疾病、数据源术语是否准确。
- 📝 在哪记录：临床意见写 Reviewer A，科研意见写 Reviewer B；问题 `flow` 填 `S1 文献四来源检索`，按 P0-P3 分级，附 request_id / 截图。

## S2 PDF 上传 → 解析 → RAG 引用

- 目标：确认上传 PDF 的解析结果和引用来源标记是否足以建立信任。
- 操作路径：在文献详情页上传主 PDF 样本，等待解析，查看解析方式 / preview，再到 `/rag` 提一个与上传 PDF 相关的问题；需要细节时看 walkthrough 的 S2 小节。
- ✅ 已自动验证：见对照表中的 smoke `pdf_upload` / `pdf_auto_parse`、`test_upload_api.py`、`test_rag_service.py`、`rag-uploaded-pdf-citation.test.ts`、`internal-preview.spec.ts`。
- 🧠 只看你的专业判断：抽取文本是否可读；数字、表格、页眉页脚或乱码是否影响你信任；“来源：上传 PDF / 来自上传 PDF”是否清楚；解析失败或 placeholder 回退是否诚实。
- 📝 在哪记录：临床意见写 Reviewer A，科研意见写 Reviewer B；问题 `flow` 填 `S2 PDF 上传 → 解析 → RAG 引用`，按 P0-P3 分级，附 request_id / 截图。

## S3 RAG 答案 + 免责声明

- 目标：确认 RAG 答案在医学安全、引用支撑和免责声明显著性上可被正式 reviewer 接受。
- 操作路径：访问 `/rag`，用 AD / 中医治疗 / 皮肤屏障 / 肠皮轴相关问题提问，检查答案、引用卡片、文献详情跳转和 Markdown 导出；需要细节时看 walkthrough 的 S3 小节。
- ✅ 已自动验证：见对照表中的 smoke `rag_answer` / `rag_export`、`test_rag_api.py`、`test_rag_literature_contract.py`、`main-path.spec.ts`。
- 🧠 只看你的专业判断：答案医学准确性；是否把样本证据说成确定疗效；是否出现诊断或治疗建议越界；免责声明是否足够显著；引用是否真正支撑论断。
- 📝 在哪记录：临床意见写 Reviewer A，科研意见写 Reviewer B；问题 `flow` 填 `S3 RAG 答案 + 免责声明`，按 P0-P3 分级，附 request_id / 截图。

## S4 网络药理学 mock 边界

- 目标：确认 reviewer 明确知道网络药理学当前是 mock / sample 数据链路，不是真实科研计算结果。
- 操作路径：访问 `/network`，运行默认 mock 分析，查看作用链、网络图、富集分析、报告导出和边界说明；需要细节时看 walkthrough 的 S4 小节。
- ✅ 已自动验证：见对照表中的 smoke `network_analyze` / `network_result` / `network_report`、`test_network_api.py`、`test_network_enrichment_integration.py`、`test_network_report_service.py`、`internal-preview.spec.ts`、`network-graph-keyboard.spec.ts`。
- 🧠 只看你的专业判断：mock 数据边界是否被清楚理解为“非真实科研结果”；富集 p-value 是否会被误读为真实统计；作用链证据是否可信；边界说明是否足以避免科研发表或临床决策误用。
- 📝 在哪记录：科研意见写 Reviewer B；若发现医学安全或临床误用风险，也写 Reviewer A；问题 `flow` 填 `S4 网络药理学 mock 边界`，按 P0-P3 分级，附 request_id / 截图。

## Sign-off 声明

自动化锚、内部代走、AI 技术预审和证据包都不能替代本任务单的人工 sign-off。只有真实医生 / 科研 reviewer 完成上述 S1-S4 并在 `docs/evaluations/2026-06-05-reviewer-feedback.md` 留下结论后，才算通过这道 gate。
