# 中医药精准诊疗与科研一体化平台 - MVP 实现计划

## [ ] Task 1: 基础设施环境搭建
- **Priority**: P0
- **Depends On**: None
- **Description**: 
  - 配置 Docker Compose 环境（PostgreSQL+pgvector、PgBouncer、Redis、Nginx）
  - 安装双 Embedding 模型（text2vec-base-chinese、PubMedBERT）
  - 配置 Celery + Flower 异步任务监控
- **Acceptance Criteria Addressed**: AC-1, AC-2, AC-4
- **Test Requirements**:
  - `programmatic` TR-1.1: Docker Compose 启动所有服务无报错
  - `programmatic` TR-1.2: pgvector 写入验证通过
  - `human-judgment` TR-1.3: Flower 监控界面可访问，显示任务状态

## [ ] Task 2: 后端 API 开发
- **Priority**: P0
- **Depends On**: Task 1
- **Description**: 
  - FastAPI 工程搭建，配置依赖与 .env
  - 实现文献检索 API（中英文分流）
  - 实现 RAG 问答 API
  - 实现网络药理学分析异步 API（/analyze、/result/{id}）
  - 实现 PDF 解析管道（PyMuPDF + unstructured）
- **Acceptance Criteria Addressed**: AC-1, AC-2, AC-3, AC-4
- **Test Requirements**:
  - `programmatic` TR-2.1: 检索 API 返回正确格式（含中英文标记）
  - `programmatic` TR-2.2: RAG 问答返回带引用卡片的结果
  - `programmatic` TR-2.3: 异步分析返回 task_id，轮询可获取进度与结果
  - `programmatic` TR-2.4: PDF 上传解析后可被检索

## [ ] Task 3: 知识图谱配置
- **Priority**: P0
- **Depends On**: Task 1
- **Description**: 
  - 配置 Neo4j Aura 连接
  - 导入 TCM 数据（HERB、SymMap 2.0）
  - 实现图谱查询 API
- **Acceptance Criteria Addressed**: AC-5
- **Test Requirements**:
  - `programmatic` TR-3.1: Neo4j 查询返回中药-成分-靶点-疾病链数据
  - `human-judgment` TR-3.2: 数据导入完整，无缺失关联

## [ ] Task 4: 用户认证模块
- **Priority**: P0
- **Depends On**: Task 1
- **Description**: 
  - 集成 NextAuth.js 认证
  - 实现魔法链接登录流程
  - 实现邀请白名单机制
  - 实现用量与配额提示
- **Acceptance Criteria Addressed**: AC-6
- **Test Requirements**:
  - `programmatic` TR-4.1: 魔法链接流程完整（发送→点击→登录）
  - `programmatic` TR-4.2: 白名单外用户无法注册
  - `programmatic` TR-4.3: 配额超限提示正确显示

## [ ] Task 5: 前端页面开发
- **Priority**: P0
- **Depends On**: Task 2, Task 3, Task 4
- **Description**: 
  - Next.js + Ant Design 5 应用壳搭建
  - 营销首页（病种聚焦、三联价值展示）
  - 登录/邀请页面
  - 文献检索页（搜索框、中英切换、筛选侧栏、结果列表）
  - RAG 对话页（对话线程 + 引用卡片）
  - 网络药理学分析页（表单→进度→报告）
  - 图谱可视化页（AntV G6）
  - 设置/合规页（隐私政策、用户协议）
- **Acceptance Criteria Addressed**: AC-1, AC-2, AC-4, AC-5, AC-7
- **Test Requirements**:
  - `human-judgment` TR-5.1: 页面布局符合设计规范，主色青黛绿 (#0d9488)
  - `programmatic` TR-5.2: 中英文切换功能正常
  - `programmatic` TR-5.3: 分页、筛选、排序功能正常
  - `human-judgment` TR-5.4: AI 输出区块显示免责声明

## [ ] Task 6: 对象存储集成
- **Priority**: P1
- **Depends On**: Task 1
- **Description**: 
  - 配置 Cloudflare R2（或 MinIO）
  - 实现 PDF 文件上传存储
  - 实现文件下载/预览接口
- **Acceptance Criteria Addressed**: AC-3
- **Test Requirements**:
  - `programmatic` TR-6.1: PDF 上传成功后可从 R2 下载
  - `programmatic` TR-6.2: 文件预览接口返回正确内容

## [ ] Task 7: 监控与限流配置
- **Priority**: P1
- **Depends On**: Task 1, Task 2
- **Description**: 
  - 配置 Nginx 速率限制
  - 配置 Sentry 错误监控
  - 配置语义缓存（Redis）
  - 配置 Claude 配额控制
- **Acceptance Criteria Addressed**: AC-2, AC-4
- **Test Requirements**:
  - `programmatic` TR-7.1: 超限请求返回 429 状态码
  - `programmatic` TR-7.2: 相同语义查询命中缓存
  - `human-judgment` TR-7.3: Sentry 可接收错误日志

## [ ] Task 8: 部署与内测准备
- **Priority**: P1
- **Depends On**: All previous tasks
- **Description**: 
  - 配置阿里云服务器
  - Nginx SSL 配置
  - 部署 Docker Compose 到云端
  - 准备 50 人内测邀请列表
- **Acceptance Criteria Addressed**: 整体
- **Test Requirements**:
  - `human-judgment` TR-8.1: 云端部署完成，所有页面可正常访问
  - `programmatic` TR-8.2: 邀请链接发送功能正常