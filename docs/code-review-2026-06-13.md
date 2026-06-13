# Qiyan Nexus 代码审查总结与优化计划

**审查日期**: 2026-06-13  
**审查范围**: Backend (59 Python 文件) + Frontend (43 TypeScript/TSX 文件)  
**当前状态**: 所有门禁绿色 ✅ (ruff + mypy + pytest)

---

## 执行摘要

### 总体评价
✅ **良好** — 代码质量整体优秀，架构分层清晰，类型安全完整。

### 关键指标
- **CRITICAL**: 3 个问题（安全风险）
- **HIGH**: 5 个问题（生产风险）
- **MEDIUM**: 11 个问题（代码质量）
- **LOW**: 9 个问题（最佳实践）

### 优先级建议
1. **立即修复** (CRITICAL + HIGH): 8 个问题，预计 4-6 小时
2. **短期优化** (MEDIUM): 11 个问题，预计 8-12 小时
3. **长期改进** (LOW): 9 个问题，技术债务管理

---

## CRITICAL 级别问题（必须立即修复）

### 🔴 1. Frontend: 外部链接缺少 `rel="noopener noreferrer"`
**风险**: Tabnabbing 安全漏洞  
**位置**: `frontend/components/LiteraturePdfUploadClient.tsx` 及其他使用 `target="_blank"` 的地方  
**修复时间**: 15 分钟

```bash
# 查找所有问题
grep -r 'target="_blank"' frontend/components frontend/app --include="*.tsx" | grep -v "rel="
```

### 🔴 2. Backend: SQL 字符串拼接反模式
**风险**: 未来可能引入 SQL 注入  
**位置**: `sqlite_literature.py:163`, `sqlite_chunk.py:101`, `sqlite_network_tasks.py:104`  
**修复时间**: 30 分钟

添加列名白名单校验：
```python
ALLOWED_COLUMNS = frozenset(["id", "title", "language", ...])

def _validate_column_names(columns: list[str]) -> None:
    for col in columns:
        if col not in ALLOWED_COLUMNS:
            raise ValueError(f"Invalid column name: {col}")
```

### 🔴 3. Backend: 全局异常处理器不记录日志
**风险**: 生产环境无法排查问题  
**位置**: `backend/app/main.py:15-21`  
**修复时间**: 20 分钟

```python
import logging
logger = logging.getLogger(__name__)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s %s", request.method, request.url.path, exc_info=exc)
    # 开发环境返回详细错误，生产环境返回通用消息
    ...
```

---

## HIGH 级别问题（生产风险）

### 🟠 4. Backend: 缺少请求体大小限制
**风险**: DoS 攻击（上传超大文件耗尽资源）  
**位置**: `backend/app/main.py`, `backend/app/api/upload.py`  
**修复时间**: 45 分钟

添加中间件限制请求体大小（50MB），PDF 上传限制 20MB。

### 🟠 5. Backend: PDF 路径遍历风险
**风险**: 理论上可访问系统文件  
**位置**: `backend/app/services/pdf_storage.py:13-23`  
**修复时间**: 10 分钟

收紧 `_PDF_UPLOAD_ID_PATTERN`，禁止 `.` 字符：
```python
_PDF_UPLOAD_ID_PATTERN = re.compile(r"^pdf-[a-zA-Z0-9_-]{1,100}$")
```

### 🟠 6. Backend: SQLite `check_same_thread=False` 并发风险
**风险**: 高并发下数据损坏  
**位置**: `backend/app/repositories/sqlite_literature.py:87`  
**修复时间**: 2 小时

使用连接池或全局写锁保证线程安全。

### 🟠 7. Backend: 环境变量未验证必需值
**风险**: 配置错误运行时才发现  
**位置**: `backend/app/core/config.py`  
**修复时间**: 30 分钟

在 `__post_init__` 中验证生产环境必需配置。

### 🟠 8. Frontend: ErrorBoundary 缺少生产错误上报
**风险**: 用户错误无法追踪  
**位置**: `frontend/components/ErrorBoundary.tsx:29-35`  
**修复时间**: 1 小时（需集成 Sentry）

---

## MEDIUM 级别问题（代码质量）

### 🟡 9. Backend: Repository 层缺少统一错误处理
定义 `RepositoryError` 基类，统一转换存储层异常。

### 🟡 10. Backend: `answer_question` 函数过长（143 行）
拆分成 5-6 个独立函数，提升可测试性。

### 🟡 11. Backend: 缺少速率限制
使用 `slowapi` 限制 `/api/rag/answer` (10/min), `/api/uploads/pdf` (5/min)。

### 🟡 12. Frontend: `RagAnswerClient` 组件过大（408 行）
拆分成 `RagAnswerForm`, `RagAnswerResult`, `RagCitations` 子组件。

### 🟡 13. Frontend: Loading 状态缺少可访问性标签
添加 `aria-busy`, `aria-live`, `role="status"` 提升屏幕阅读器支持。

### 🟡 14. Backend: PubMed 同步缺少幂等性保证
添加事务性保证或 sync_batch_id 避免重复处理。

### 其他 MEDIUM 问题
- 类型注解不完整（TypedDict）
- 硬编码样式值分散
- 魔法数字未提取常量
- 日志级别使用不一致
- 缺少键盘快捷键

---

## LOW 级别问题（最佳实践）

### 技术债务
- 测试覆盖率未测量
- Repository 行为不一致
- `list_items()` 无分页
- 大组件未使用 React.memo
- 重复的格式化函数
- 过多模块级全局变量

---

## 优化计划

### Phase 1: 安全加固（立即，1 天）
**优先级**: CRITICAL + HIGH  
**目标**: 修复所有安全漏洞和生产风险

- [ ] 修复外部链接 `rel` 属性
- [ ] 添加 SQL 列名白名单校验
- [ ] 全局异常处理器记录日志
- [ ] 添加请求体大小限制
- [ ] 收紧 PDF upload ID pattern
- [ ] 修复 SQLite 并发问题或迁移到 Postgres
- [ ] 验证环境变量必需值
- [ ] 集成错误监控服务（Sentry）

**验收标准**:
```bash
# 安全扫描
bandit -r backend/app/

# 依赖漏洞扫描
pip-audit

# 手动测试
- [ ] 上传 50MB+ 文件被拒绝
- [ ] 异常被记录到日志
- [ ] 生产环境缺少 API key 启动失败
```

---

### Phase 2: 代码质量提升（1-2 周）
**优先级**: MEDIUM  
**目标**: 提升可维护性和可测试性

- [ ] 定义 Repository 异常体系
- [ ] 重构 `answer_question` 函数（拆分成 5 个子函数）
- [ ] 添加速率限制（`slowapi`）
- [ ] 重构 `RagAnswerClient` 组件（拆分成 3 个子组件）
- [ ] 添加可访问性标签（ARIA）
- [ ] PubMed 同步添加事务性
- [ ] 提取格式化函数到独立模块
- [ ] 提取常量和 CSS 变量

**验收标准**:
```bash
# 代码复杂度检查
radon cc backend/app/services/rag.py --min B  # 确保无 B 级以上复杂度

# 前端组件大小
wc -l frontend/components/*.tsx | awk '$1 > 300 {print}'  # 应无超过 300 行的组件

# 速率限制测试
for i in {1..20}; do curl -X POST http://127.0.0.1:8000/api/rag/answer -d '{}'; done
# 应在第 11 次返回 429
```

---

### Phase 3: 性能与架构优化（持续）
**优先级**: LOW  
**目标**: 长期改进

- [ ] 添加测试覆盖率报告（pytest-cov, 80% 门槛）
- [ ] 实现 Repository 契约测试
- [ ] `list_items()` 添加分页
- [ ] 前端大组件使用 React.memo
- [ ] 统一前后端格式化逻辑
- [ ] 重构模块级全局变量为依赖注入
- [ ] 添加键盘快捷键
- [ ] 添加性能监控（Lighthouse CI）

---

## 建议执行顺序

### 本周（紧急）
1. ✅ 修复所有 CRITICAL 问题（2 小时）
2. ✅ 修复 HIGH 优先级的 4-5-7 问题（2 小时）
3. ⏭️ 其余 HIGH 问题可推迟到 PostgreSQL backend 全面迁移后

### 下周（重要）
1. 添加速率限制（防止滥用）
2. 重构过长函数和组件（提升可维护性）
3. 完善可访问性（WCAG 合规）

### 后续（改进）
1. 测试覆盖率报告
2. 性能优化
3. 架构重构

---

## 不需要修复的

以下模式虽然可以改进，但当前不影响功能：
- ✅ 短连接 PostgreSQL（已有 TODO，连接池是后续优化）
- ✅ 缺少真实 embedding 模型（已评估，keyword 更优）
- ✅ 缺少 L2 预览治理（已推迟，ADR-0012）
- ✅ Next.js 使用 Pages Router（稳定，迁移 App Router 非必需）

---

## 总结

Qiyan Nexus 代码库质量整体优秀：
- ✅ 架构分层清晰（API → Service → Repository）
- ✅ 类型安全完整（mypy strict mode 通过）
- ✅ 测试覆盖良好（489 passed）
- ✅ 三个 runtime backend 可切换

**关键改进点**:
1. **安全加固** — 8 个 CRITICAL/HIGH 问题需要优先修复
2. **代码拆分** — 几个过长函数/组件影响可维护性
3. **生产就绪** — 缺少速率限制、错误监控、日志完善

**推荐路径**:
- 先修复 CRITICAL 安全问题（2 小时）
- 再逐步改进 MEDIUM 代码质量（1-2 周）
- 最后持续优化 LOW 架构问题

---

**审查人**: Claude Opus 4.8  
**审查工具**: code-reviewer agent (Sonnet 4.6, 112736 tokens)  
**完整报告**: 见上方详细问题列表
