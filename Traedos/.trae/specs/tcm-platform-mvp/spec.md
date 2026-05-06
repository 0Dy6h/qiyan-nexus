# 中医药精准诊疗与科研一体化平台 - MVP 产品需求文档

## Overview
- **Summary**: 面向特应性皮炎领域的医生与科研人员，基于「肠-脑-皮肤轴」中西医结合路径，提供文献检索、网络药理学分析与精准诊疗辅助的一体化平台。
- **Purpose**: 解决临床医生快速查阅中英文证据、辨证与方剂思路辅助需求；满足科研人员批量文献分析、网络构建与图表生成需求；贯通「临床—科研—转化」全链条。
- **Target Users**: 皮肤科/中医皮肤科医师、研究生/科研助理、院所PI/方法学合作者

## Goals
- 构建 MVP 版本，支持中英文文献检索与 RAG 问答
- 实现网络药理学分析（异步长任务）
- 提供知识图谱可视化（中药-成分-靶点-疾病链）
- 建立用户认证与合规体系
- 支持 50 人内测规模

## Non-Goals (Out of Scope)
- 不做全病种泛化 — 现阶段只做特应性皮炎
- 不替代医生诊断 — 仅作为辅助决策工具
- 不做普通患者 C 端 — 先服务医生与科研人员
- 不自训大模型 — 使用成熟 API + 开源模型
- 不追求一次性完美 — MVP 上线后快速迭代

## Background & Context
- 垂直病种聚焦特应性皮炎，方法论采用「肠-脑-皮肤轴」中西医结合路径
- 技术架构：Next.js 15 + React + Ant Design 5 前端；FastAPI + Pydantic v2 后端；PostgreSQL 16 + pgvector 向量库；Neo4j Aura 知识图谱
- 双语 Embedding：text2vec-base-chinese（中文）+ PubMedBERT（英文）
- 主力 LLM：DeepSeek-chat（日常问答）+ Claude Sonnet（医学推理与报告）

## Functional Requirements
- **FR-1**: 中英文文献检索 — 支持双语切换、复合检索（疾病 + 中医证候/方药 + 通路关键词）
- **FR-2**: RAG 问答 — 对话线程 + 引用卡片（来源标题、页码/段落、置信度）
- **FR-3**: PDF 上传与解析 — 用户上传论文 PDF，系统自动解析内容
- **FR-4**: 网络药理学分析 — 提交分析任务、展示 task_id 与进度、完成后查看报告与图表
- **FR-5**: 知识图谱浏览 — 中药-成分-靶点-疾病链可视化、缩放筛选、导出图片
- **FR-6**: 用户认证 — 魔法链接登录、邀请白名单、用量与配额提示
- **FR-7**: 合规界面 — AI 输出免责声明、用户协议、隐私政策、算法说明

## Non-Functional Requirements
- **NFR-1**: 性能 — 检索响应时间 < 2s，长任务异步处理，提供进度反馈
- **NFR-2**: 可扩展性 — 支持后续添加辨证辅助、菌群分析、科研数据管理模块
- **NFR-3**: 安全性 — 临床数据脱敏、权限控制、符合 PIPL 要求
- **NFR-4**: 可访问性 — 全页可键盘操作、对比度满足 WCAG AA、图表有关联文本描述

## Constraints
- **Technical**: Next.js 15 + Ant Design 5 + FastAPI + PostgreSQL + Neo4j + Redis + Celery
- **Business**: 6 个月 MVP 预算约 ¥960，目标首月收入 ¥500–2000
- **Dependencies**: DeepSeek API、Claude API、Cloudflare R2、Neo4j Aura

## Assumptions
- 内测用户约 50 人，每人每日约 10 次复杂查询
- 中文文献约 1000 篇，英文文献约 500 篇
- 草药-成分-靶点数据约 1000 条

## Acceptance Criteria

### AC-1: 中英文文献检索
- **Given**: 用户在检索页面，语言切换为中文
- **When**: 输入特应性皮炎相关关键词并搜索
- **Then**: 返回中文文献列表，支持筛选与排序
- **Verification**: `programmatic`

### AC-2: RAG 问答功能
- **Given**: 用户在问答页面，已有检索上下文
- **When**: 用户提出关于文献的问题
- **Then**: 返回带引用来源的回答，包含置信度指标
- **Verification**: `programmatic`

### AC-3: PDF 上传解析
- **Given**: 用户上传一篇医学论文 PDF
- **When**: 系统完成解析
- **Then**: 可在检索结果中检索到该文档内容
- **Verification**: `programmatic`

### AC-4: 网络药理学异步分析
- **Given**: 用户填写分析参数表单
- **When**: 提交分析任务
- **Then**: 返回 task_id，展示进度，完成后显示报告与图表
- **Verification**: `programmatic`

### AC-5: 知识图谱可视化
- **Given**: 用户进入图谱页面
- **When**: 搜索中药节点并探索关系
- **Then**: 显示中药-成分-靶点-疾病链网络，支持缩放筛选
- **Verification**: `human-judgment`

### AC-6: 用户认证流程
- **Given**: 用户通过邀请链接访问登录页
- **When**: 输入邮箱并请求魔法链接
- **Then**: 收到邮件链接，点击后成功登录
- **Verification**: `programmatic`

### AC-7: 合规声明展示
- **Given**: 用户查看 AI 生成内容
- **When**: 浏览任意 AI 输出区块
- **Then**: 底部显示「非诊断结论、需结合临床」免责声明
- **Verification**: `human-judgment`

## Open Questions
- [ ] 具体的付费导出定价策略（¥99/次 vs ¥199/次）
- [ ] 是否需要移动端适配（当前优先桌面端）
- [ ] 具体的文献来源（知网/万方/PubMed 具体比例）