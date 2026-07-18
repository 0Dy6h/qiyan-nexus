# 执行准备报告：最小真实闭环里程碑

- 日期：2026-07-18
- 角色：副开发者 + 产品经理（调研与准备，未改任何业务代码）
- 服务目标：下一里程碑「最小真实闭环」——1 个方药端到端打通 真实数据源 → 人工 adjudication → source-bound 网络装配 → 可审计报告；以及并行的「用户-研究-任务容器」与「真实语料」两条线。
- 调研纪律：够用即停。外部事实均于 2026-07-18 经 GitHub API / PyPI JSON API / npm registry / 官方文档页实时核实，原始笔记存于 `.tmp/product-review/research-notes.md`。

---

## ① 依赖与环境

### 1.1 现状盘点（已核实）

| 层 | 技术 | 版本（声明 / 实测） | 备注 |
|---|---|---|---|
| 后端运行时 | Python | `requires-python >=3.11` / 实测 venv 为 **3.13.12** | README 写 `py -3.11` 建 venv，实际 3.13 全绿（794 passed）——**建议二选一钉死** |
| 后端框架 | FastAPI + Pydantic | `fastapi>=0.115`、`pydantic>=2.6,<3` | 分层 api→services→repositories→schemas |
| 后端关键库 | httpx / scipy / numpy / pypdf / slowapi / anthropic / faiss-cpu / python-multipart | 见 `backend/pyproject.toml` | dev extra 含 ruff、mypy、sentence-transformers、transformers、pytest-cov；postgresql extra 含 psycopg |
| 持久化 | JSON（默认）/ SQLite / PostgreSQL spike | `QIYAN_STATE_BACKEND` 切换 | 默认 json；pg 为 opt-in |
| 前端 | Next.js + React + Ant Design | `next ^16.2.6`、`react ^19.2.3`、`antd ^6.1.0` | TS 5.9、tsx 单测、Playwright 1.60 e2e |
| 前端工具链 | Node / pnpm | 实测 **Node 24.15.0 / pnpm 10.33.0** | PostCSS override 钉 8.5.10 |
| E2E | Playwright chromium | headless shell 已装；**完整 chromium 未装** | `pnpm e2e:install` 可补 |
| 环境变量 | `backend/.env.example`（98 行，已覆盖全部开关） | 含 access token / LLM / grounding / NLI / state backend / network provider / 双侧 manifest 路径 | 主开发者复制为 `backend/.env` 按需改；`.env` 已存在且 gitignored |
| 脚本 | `scripts/verify-local.ps1`、`run-internal-preview.ps1`、`smoke-internal-preview.ps1` | 一键门禁 / 起停 / smoke | Windows PowerShell 专用 |

已知小坑：`backend/` 下 `.venv` 与 `.uv-test-venv` 双 venv 并存，易混用，建议删一留一；README/AGENTS 均以 `.uv-test-venv` 为准。

### 1.2 安装 / 配置命令清单（仅列出，未执行安装）

```powershell
# 后端（首次）
cd backend
py -3.11 -m venv .uv-test-venv        # 或与实测 3.13 统一后改此处
& .\.uv-test-venv\Scripts\python.exe -m pip install -U pip
& .\.uv-test-venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env            # 按需改值；默认全离线可跑

# 前端（首次）
cd frontend
pnpm install
pnpm e2e:install                        # 仅需要跑 Playwright 时

# 统一门禁（开工前必过）
.\scripts\verify-local.ps1
```

### 1.3 下一里程碑拟新增依赖（待主开发者批准后引入，本次未安装）

| 依赖 | 版本（2026-07-18 核实） | 用在哪一步 | 引入时机 / 命令 |
|---|---|---|---|
| `chembl-webresource-client` | 0.10.9（ChEMBL 官方，2026-03 仍活跃） | 成分靶点采集，替代手写 requests；官方背书利于 provenance 审计 | 闭环切片开工时：`pip install chembl-webresource-client` |
| `statsmodels` | 0.14.6（11.5k★，活跃） | 富集分析真实 BH/FDR 校正（`multipletests`），替换 mock 字典 | 网络装配切片：`pip install statsmodels` |
| `goatools` | 1.6.5（900★，活跃） | 本地 GO 富集（无外部调用、无许可风险） | 富集切片可选：`pip install goatools` |
| `gseapy` | 1.3.0（705★，活跃） | Enrichr 在线富集封装（GO_2023 / Reactome / WikiPathways） | 与 goatools 二选一或并存：`pip install gseapy` |
| `cytoscape`（前端） | 3.34.0（周下载 1049 万，gzip 132 KB） | 网络图从内联 SVG 升级时 | 图升级切片再装：`pnpm add cytoscape` |
| RQ | 10.6k★，活跃 | 任务队列（仅当任务 >2 分钟 / 多用户并发 / 重启不丢任务任一触发） | 触发阈值再说，**默认不装** |

明确不引入：`gprofiler-official`（PyPI 停更 7 年）、`mygene`（客户端 4 年未发版）、AntV G6（390 KB，非必要）、Celery/Redis（维持冻结决策）。

---

## ② 同类项目调研

### 2.1 端到端参考实现（GitHub API 核实）

**MLi-lab-Bioinformatics-NJUCM/HerbiV**（56★，2025-05 仍更新）— github.com/MLi-lab-Bioinformatics-NJUCM/HerbiV
- 核心选择：**不自建爬虫，发布预整合本地数据库**（50 万+ 方剂/中药/成分/靶点记录，成分-蛋白边源自 STITCH combined_score，可设阈值）。支持正向与反向网络药理学，输出 Cytoscape 交换文件 + ECharts HTML。
- 借鉴：TCMSP 无官方 API 是社区共识痛点；三条路（自建本地库 / 抓非官方端点 / Selenium）里，**只有"预构建版本化本地数据集"与 Qiyan 的"离线 raw artifact + trusted manifest + SHA-256"治理模型兼容**。可评估直接整合 HerbiV 数据集作为 TCMSP 替代源（需先做 provenance 审查）。

**Hz-777/network-pharmacology**（1★，Streamlit，2026-05 仍更新）— github.com/Hz-777/network-pharmacology
- 模块划分与 Qiyan 高度同构：`tcmsp / disease_targets / string_db / swiss_target / pubchem / enrichment / report / visualization` + diskcache 缓存。疾病靶点四源并行合并（Open Targets GraphQL + Harmonizome/DisGeNET + UniProt + NCBI，ThreadPoolExecutor）；富集走 **Enrichr API 直接取 BH 校正后 p-value，不自算**。
- 其 TCMSP 抓取走非官方 Kendo-Grid JSON 端点（正则提取页面 token），自述"云端 IP 受限"——再次印证抓取路线不可持续。
- 借鉴：多源疾病靶点合并模式可作后续扩源参考；Enrichr 作为富集外包是务实选择。

**Shiqi-Wu/TCM-NetMiner**（7★，2024-11）— github.com/Shiqi-Wu/TCM-NetMiner
- Selenium + chromedriver 爬 TCMSP（OB>30 / DL>0.18 筛选），浏览器版本强耦合，是最脆弱的一条路。**反面教材，不采用。**

### 2.2 客户端库维护状态（PyPI / GitHub 核实）

| 库 | 最新版（发布日） | 维护判断 |
|---|---|---|
| chembl-webresource-client | 0.10.9（2024-02）/ repo 2026-03 活跃 | ✅ 引入 |
| statsmodels | 0.14.6（2025-12） | ✅ 引入（BH/FDR） |
| goatools | 1.6.5（2026-05） | ✅ 可选 |
| gseapy | 1.3.0（2026-06） | ✅ 可选 |
| pubchempy | 1.0.5（2025-09） | 可选；手写亦可 |
| unipressed | 1.4.0（2024-08） | 可选；UniProt 手写 requests 已够用 |
| bioservices | 1.16.0（2026-03） | 覆盖广但重，非必需 |
| mygene | 3.2.2（2021-04） | ❌ 客户端停更 |
| gprofiler-official | 1.0.0（2019-04） | ❌ 停更 7 年 |

### 2.3 外部服务使用约束（官方文档核实）

- **STRING**：每次调用带 `caller_identity`；调用间隔 ≥1 秒；生产钉版本化 URL（如 `version-12-0.string-db.org`）；>10 个蛋白必须指定 `species=9606`；推荐 POST；先 `get_string_ids` 映射再查 `network`。其 `/api/tsv/enrichment` 直接返回 BH 校正 FDR，但 **KEGG 注释因 KEGG 许可不可用**。
- **KEGG**：学术用户可免费浏览；**用 KEGG 数据对外提供服务需 academic service provider license，非学术使用需商业许可**（kegg.jp/kegg/legal.html，2024-10 更新）。Qiyan 面向医生/科研人员提供服务 → **KEGG 默认关闭、显式 opt-in 并注明边界**。
- **Open Targets**：数据 **CC0 1.0**（无限制），最自由，且已打通。
- **ChEMBL**：数据 **CC BY-SA 3.0** —— 报告与导出必须带署名；SA 传染性意味着再分发派生数据需同许可。

### 2.4 可视化与任务队列

- 网络图升级选 **Cytoscape.js**（gzip 132 KB、周下载 1049 万、社区交换格式天然兼容）；不选 G6（390 KB）或 react-force-graph（生态小）。当前内联 SVG 在 mock 规模继续够用。
- 单进程 uvicorn 内 5–30 秒多步外部调用，**维持现有进程内任务壳**（FastAPI BackgroundTasks 即社区主流）。必须上队列的阈值：任务 >2 分钟 / 多用户并发需排队取消 / 进程重启任务不丢 / 多 worker——届时选 **RQ**（最轻，契合冻结 Celery 的决策）。

### 2.5 可借鉴结论（8 条）

1. 成分靶点：维持"TCMSP 只读 cache + 离线 artifact"决策；评估 HerbiV 预整合数据集作为版本化替代源。
2. 疾病靶点：Open Targets（CC0）为主线已正确；多源合并（+DisGeNET/UniProt）留作扩源参考。
3. ID 标准化：UniProt REST 手写够用；不引入 mygene。
4. PPI：STRING 调用内置 1s 节流 + `caller_identity` + 版本钉扎，并把这三个字段写进 raw artifact provenance。
5. 富集：`statsmodels.multipletests` 做真实 BH/FDR；注释源走 goatools 本地 GO + Enrichr；KEGG 默认关。
6. 可视化：升级时选 Cytoscape.js，暂缓。
7. 队列：进程内壳维持到明确阈值触发，届时 RQ。
8. 合规：报告内置许可声明矩阵——Open Targets CC0 / ChEMBL CC BY-SA 3.0 署名 / STRING 引用要求 / KEGG opt-in 警示。

---

## ③ Skills / 工具搜集（按步骤落位）

| 闭环步骤 | 工具 / 库 / skill | 用途 |
|---|---|---|
| 成分靶点采集 | `chembl_webresource_client`（拟引入）+ 现有 `network_chembl.py` 离线 artifact 核验 | 官方客户端采集 → raw artifact → manifest 核验 |
| 疾病靶点 | 现有 `network_open_targets.py` connector | 已打通，沿用 |
| ID 标准化 | UniProt REST（手写 requests；unipressed 备选） | gene symbol ↔ UniProt 映射 |
| PPI | STRING API 手写 + 节流/版本钉扎 | 靶点互作边 |
| 富集 | goatools（本地 GO）/ gseapy（Enrichr）+ `statsmodels.multipletests` | 真实 FDR 校正富集表 |
| 网络图 | 现内联 SVG（够用到 mock 规模）；升级选 cytoscape | 结果可视化 |
| 报告导出 | 现有后端 Markdown / docx 生成；`md-to-pdf` skill | 可审计报告、PDF 版 |
| 富集图表 | `seaborn-visualization` skill | 富集气泡图 / 条形图（报告与面板用） |
| Adjudication 工作单 | `xlsx` skill | reviewer 判定工作表导入导出 |
| 文献证据扩充 | `scholar` 插件 + `backend/scripts/seed_pubmed_corpus.py` | 真实语料补充、边-证据绑定时的文献核查 |
| 项目容器 UI | `webapp-building` skill | "我的研究/任务历史"前端 |
| 走查与演示 | `kimi-webbridge` skill | 真实浏览器走查、reviewer 演示录制 |
| 定时语料刷新 / 面板 | `automation` / `canvas` / `widget` skills | 语料定时更新、研究进度看板（需要时） |
| 对抗性加固 | 仓库内 `.codex/skills/qiyan-adversarial-hardening` | 每个切片收尾的安全/边界复审 |
| 切片方法 | handoff 提及的 `project-grill`、`vertical-slice-planning`、`test-driven-development`、`requesting-code-review`（agent 工具链侧，不在仓库内） | 计划冻结 → RED 测试 → 实现 → 独立验收 |
| 最佳实践 | artifact manifest + SHA-256 provenance（沿用）；许可声明矩阵；`verify-local.ps1` 门禁；免责声明 load-bearing 纪律 | 全流程 |

---

## ④ 执行前置条件 Checklist（主开发者开工前）

### A. 工程基线
- [ ] **收口当前工作树**：`feat/pillar2-real-evidence-ranking` 分支有 **70 个未提交的修改文件**（Gate-2 compound provenance 工作，2026-07-15 验收通过但至今未 commit）——先提交/合并，再开任何新切片。
- [ ] 门禁基线全绿：`.\scripts\verify-local.ps1`（2026-07-18 实测 backend 794 passed / frontend 240 passed / build OK）。
- [ ] 钉死 Python 版本：README 说 3.11、实测 venv 3.13.12，二选一写进 README + pyproject。
- [ ] 处理 `.venv` / `.uv-test-venv` 双 venv 并存。
- [ ] （可选）`pnpm e2e:install` 补完整 chromium，供 reviewer 走查前 `-IncludeE2E`。

### B. 决策（需 owner 拍板，建议开工前一一次会议结清）
- [ ] 目标方药与表型：建议沿用协议示例「消风散 × 特应性皮炎伴 2 型炎症与皮肤屏障异常」。
- [ ] Adjudication 语义冻结：身份来源、状态机（pending→included/excluded/needs-review）、不可变 snapshot、只读 report、"不翻转 readiness"验收条件（按 2026-07-15 handoff 的既定方向）。
- [ ] 新依赖批准：最小集 `chembl-webresource-client` + `statsmodels`；可选项 goatools/gseapy。
- [ ] KEGG 策略确认：默认关、opt-in；批准报告中的许可声明矩阵文案。
- [ ] "研究项目"容器最小定义：字段（项目名/协议/task 列表/归档报告）、与现有 task owner 的关系、本地单用户是否够用。

### C. 数据资产（operator 侧准备）
- [ ] Open Targets AD 疾病关联 GraphQL 导出文件 + 在 `NETWORK_OPEN_TARGETS_MANIFEST_PATH` manifest 登记其 SHA-256 与元数据。
- [ ] 消风散成分 ChEMBL known-activities 导出 + `NETWORK_CHEMBL_MANIFEST_PATH` 登记。
- [ ] TCMSP 立场确认：维持只读 cache；如评估引入 HerbiV 数据集，先做一次来源/provenance 审查。
- [ ] 运行 `backend/scripts/seed_pubmed_corpus.py` 填充真实 PubMed runtime 语料。
- [ ] STRING 调用约定落实：`caller_identity`、版本钉扎 URL、1s 节流写进 connector 与 provenance。

### D. 人员 / 流程
- [ ] Adjudication reviewer 人选：1 名未参与 ranker 调参的领域 reviewer。
- [ ] Track A 150 个盲标 HITL 排期（与工程主线并行，不占主线）。
- [ ] 正式医生/科研 reviewer sign-off：进入任何外部试用前的人工决策点（自 2026-06-05 起空缺至今，建议本次里程碑收口前完成）。

### E. 明确不做（防范围蔓延）
- 不上 Celery/Redis/RQ（未触发阈值）；不翻 PostgreSQL 默认；不翻 L2 真实 LLM 默认；不引入 G6 / mygene / gprofiler-official；不碰 MVP-C 分子对接（仅 schema 预留）。

---

## 附：调研局限

- GitHub 搜索未认证限流下取样有限，端到端参考实现只核到 3 个；结论以"路线选择"为主，不以 star 数论优劣。
- HerbiV 数据集的许可与更新承诺未深入核实，引入前必须单独审查。
- STRING/KEGG/ChEMBL/Open Targets 许可条款以 2026-07-18 官方页面为准，正式对外提供服务前建议再复核一次。
