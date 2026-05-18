# CONTEXT.md — TCM 平台领域共享语言

> Harness Engineering 支柱一 · 上下文工程
> 每次 Agent 会话必加载此文件。用精确术语替代冗长描述。
> 更新规则：`grill-with-docs` 每次对齐后自动增量更新。

## 核心领域术语

| 术语 | 简称 | 定义 |
|------|------|------|
| 特应性皮炎 | AD | Atopic Dermatitis，本平台唯一聚焦病种 |
| 肠-脑-皮肤轴 | GBS-Axis | Gut-Brain-Skin Axis，中西医结合核心方法论 |
| 网络药理学 | NetPharm | 从草药→成分→靶点→通路的计算分析方法论 |
| 辨证辅助 | Syndrome-Dx | 中医辨证论治的 AI 辅助（非替代） |
| 方剂 | Formula | 中药复方组合 |
| 证据链 | Evidence-Chain | AI 输出的可追溯性保障。MVP 中即为 RAG 回答附带的引用卡片集合（来源→片段→置信度），后台不维护独立证据链对象 |
| 引用卡片 | Citation-Card | 证据链的前端展示单元：来源文献标题、页码/段落片段、置信度指标（必展示，非可选） |
| 魔法链接 | Magic-Link | 无密码登录方式，通过邮件发送一次性链接 |

## 系统组件简称

| 简称 | 组件 | 用途 |
|------|------|------|
| 文献引擎 | LitEngine | 中英文文献检索管道：中文预建本地 pgvector 索引 + 英文 PubMed API 实时检索（见 ADR-0001） |
| RAG | 检索增强生成 | 文献检索 + 问答流水线 |
| Celery | 异步任务队列 | 网络药理学分析后台处理 |
| Flower | Celery 监控面板 | 端口 5555 的任务监控 UI |
| G6 | AntV G6 | 前端图谱可视化引擎 |
| R2 / MinIO | MinIO 对象存储 | 本地 Docker Compose S3 兼容存储，PDF 文件仓库（见 ADR-0007）。阶段 2 可无缝迁移至 Cloudflare R2 |
| PgBouncer | 数据库连接池 | PostgreSQL 连接管理 |

## 流程中的术语

| 术语 | 含义 |
|------|------|
| 中英分流 | 根据 `language` 字段选择 text2vec-chinese 或 PubMedBERT 做 Embedding |
| 异步长任务 | 网络药理学分析等耗时操作，通过 task_id 轮询状态 |
| 语义缓存 | Redis 中对同用户同会话内精确匹配文本的 LLM 响应缓存，减少重复 API 调用。仅精确文本匹配，不做向量相似度 |
| 模型路由 | Model-Route | 按 API endpoint 决定 LLM：文献/RAG→DeepSeek V4 Flash，报告/辨证→Claude Sonnet 4.6（见 ADR-0004） |
| 红-绿-重构 | TDD 循环：先写失败测试→实现→重构 |

## 角色术语

| 角色 | 权限层级 |
|------|---------|
| 皮肤科医师 | 标准用户（受邀） |
| 科研助理/研究生 | 标准用户 + 批量分析 |
| PI/方法学合作者 | 标准用户 + 数据导出 |
| 管理员 | 全权限（账户管理、监控面板） |

## 已记录的 ADR（架构决策）

详见 `docs/adr/` 目录。ADR 记录长期架构决策与阶段边界；当前开发事实源仍以 `docs/current-state.md`、代码、测试和最新 handoff 为准。

| 编号 | 决策 |
|------|------|
| 0001 | 中英文文献分源索引：中文预建本地索引 + 英文 PubMed API |
| 0002 | MVP 仅桌面端，不做移动端适配 |
| 0003 | MVP 不集成付费，全部导出免费 |
| 0004 | 双模型路由：DeepSeek V4 Flash（日常）+ Claude Sonnet 4.6（医学推理） |
| 0005 | 双 Embedding 模型分流：text2vec-base-chinese + PubMedBERT |
| 0006 | NextAuth.js 魔法链接 + 邀请白名单认证 |
| 0007 | 本地 MinIO 对象存储（S3 兼容，阶段 2 可迁 Cloudflare R2） |
| 0008 | Celery + Redis 异步任务架构 |
| 0009 | 前端实际版本基线与 Ant Design 使用策略 |
| 0010 | 研究工作台模块路线图：MVP-A 证据工作台，MVP-B 网络药理学，MVP-C 分子对接/MD |
