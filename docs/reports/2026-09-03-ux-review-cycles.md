# 2026-09-03 UX 评审循环记录（三轮：使用体验 → 问题清单 → 整改方案 → 实施验证）

> 环境：内部预览 isolated runtime（backend 8010 / frontend 3000，open dev mode）。
> 背景约束：本机 8000 被另一项目（简历撰写工具 uvicorn）常驻占用，全程不可触碰。

## 第 1 轮：启动与工具链体验

**走查**：`run-internal-preview.ps1` 启动、`verify-local.ps1 -IncludeE2E`、smoke 首次运行。

**问题清单（6 项，全部 P1）与整改**：

| # | 问题 | 根因 | 整改 | 验证 |
|---|---|---|---|---|
| 1 | E2E 静默跑在错误服务上 | `playwright.config.ts` 硬编码 3000/8000，与 start 脚本的 `QIYAN_E2E_*_PORT` 约定断裂 | config 读取同名 env（默认不变） | 隔离端口 E2E 4/4 绿 |
| 2 | `verify-local -IncludeE2E` 无法换端口 | 脚本不透传 env | 新增 `-E2eBackendPort/-E2eFrontendPort` | 同上 |
| 3 | preview 端口被占静默挂起 | 无占用预检 | `Assert-PortAvailable` fail fast + 指引 | 8000 被占场景立即报错 |
| 4 | 启动失败无反馈（Next 16 同目录单 dev server 锁等） | 启动后无健康检查 | 前后端健康轮询 + 失败日志指引 | 启动日志出现 passed 检查 |
| 5 | smoke 在干净运行时崩溃（StrictMode 属性访问） | 空任务列表 `[0].owner_id` | 显式属性存在性检查 | smoke 全绿 |
| 6 | smoke 对 mock 任务数组越界 + 中文断言恒假 | 无 lineage 时 `[0]` 越界；`.ps1` 无 BOM 中文乱码 + `Out-String` 重排 | 判空跳过 + 补 UTF-8 BOM + 直断言 | smoke 14 流程全绿 |

**插曲（诊断记录）**：孤儿 next dev（曾占 3000）触发 Next 16「同目录单 dev server 锁」，导致 E2E `reuseExistingServer` 复用了指向错误后端的孤儿前端——是第 1 次 E2E 全红的直接原因。清理后以 `-FrontendPort 3000 -BackendPort 8010` 重启。

## 第 2 轮：研究者真实任务全流程走查

**走查路径**：文献搜索（消风散 6 条，seed 来源标注）→ 文献详情 → RAG 问答（answer + 2 citations + 免责声明逐字节正确 + deterministic provider）→ 网络 mock 分析（5 链恒 `mock_inferred`、富集 14 条、`formal_network_ready=false`）→ 报告（人工判定/证据分级/**组学验证(0)** 各段齐全）→ **omics 新能力真实端到端**：6MB 真实 GSE32924 + GPL570 经 HTTP 导入（201 封存→200 幂等）、opt-in DEG 投影（200，21,755 基因/1,178 通过，与离线验收一致）、HITL 门禁真实拒绝（IL6 非候选 → 422 fail closed）。

**问题清单（1 项 P2）与整改**：
- P2-1：preview 后端 env 固定，`NETWORK_OPEN_TARGETS_MANIFEST_PATH` 无法注入 → verified 流程在预览环境必 422。**整改**：`run-internal-preview.ps1` 新增 `-OpenTargetsManifestPath`（存在性校验 + 绝对路径注入）。已用该参数完成 verified disease task 的 HTTP 创建与 omics 走查。

**非问题记录**：Git Bash 内联中文经命令行传递会损坏编码（RAG body、metadata 字段两次踩中）——应用行为正确，操作侧改用 `--data-binary @file` / `-F "k=<file"`。

## 第 3 轮：错误与边界体验

| 探测 | 期望 | 实测 |
|---|---|---|
| RAG 离题查询（高血压降压药） | 0 citations + 免责声明 | ✓ 诚实 0 citations |
| 不存在的 network task | 404 fail closed | ✓ |
| omics manifest 缺字段 | 422 结构化报错 | ✓ 13 条 pydantic 明细 |
| 客户端提交 provenance 封存字段 | 422 extra_forbidden | ✓ |
| omics manifest 声明注解但未上传 | 422 明确信息 | ✓ |
| PDF 两步流（upload 不自动解析） | upload pending → 单独 auto-parse | ✓（smoke 覆盖） |

**结论**：负路径无新代码缺陷；本轮落地文档同步（AGENTS.md 命令段补新参数用法）。

## 遗留候选（不在本次范围）

- 前端 `/network` 尚无 omics opt-in 的 UI 入口（能力仅 API 层）——产品决策项，需研究者拍板形态
- CORS 仍固定 3000 origin（硬约束）；如需多端口前端，须先过约束修订
- IL6/STAT3/TNF 未获 `omics_validated` 候选（真实数据不支持）；AL vs ANL 对比需新 snapshot 决策
