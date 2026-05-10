# 架构约束 — Harness Engineering 支柱二

> 机械强制执行，非建议。Linter 报错即修复指令。

## 依赖方向分层

```
Types → Config → Repo → Service → Runtime → UI
   ↑                        ↑
   └── Providers ───────────┘
       (auth, connectors, telemetry, feature-flags)
```

**规则：**
- 代码只能「向前」依赖（从左到右）
- 跨领域关注点（认证、连接器、遥测）只能通过 `Providers` 入口进入
- 其他任何方式都不允许

## 前端架构约束

### 目录结构（Next.js 15 App Router）
```
src/
├── app/              ← 路由层（仅页面组合，不写业务逻辑）
│   ├── (marketing)/  ← 营销首页
│   └── (app)/        ← 认证后应用壳
├── components/       ← 通用 UI 组件（Ant Design 封装）
│   ├── ui/           ← 原子组件
│   └── features/     ← 功能组合组件
├── lib/              ← 工具函数、API 客户端
├── hooks/            ← 自定义 hooks
└── types/            ← TypeScript 类型定义
```

- 组件最大 300 行；超过时拆分
- `app/` 目录下文件只做路由组合，不写业务逻辑

### 命名规范
- 组件文件：`PascalCase.tsx`
- Hook 文件：`useCamelCase.ts`
- 类型文件：`camelCase.types.ts`
- API 端点：`kebab-case`

## 后端架构约束

### 目录结构（FastAPI）
```
backend/
├── app/
│   ├── api/          ← 路由层（薄层，参数校验 + 调用 service）
│   ├── services/     ← 业务逻辑层
│   ├── repositories/ ← 数据访问层
│   ├── models/       ← SQLAlchemy ORM 模型
│   ├── schemas/      ← Pydantic v2 schema
│   └── core/         ← 配置、依赖注入
├── tasks/            ← Celery 异步任务
└── tests/            ← pytest
```

- API 层不写业务逻辑，只做参数校验和调用 service
- Service 层不直接操作数据库，通过 Repository
- 所有外部 API 调用（DeepSeek/Claude）必须通过统一 Client 封装

## 工具链约束

| 层级 | 工具 | 执行命令 |
|------|------|---------|
| L1 格式 | Prettier + Ruff | `pnpm format` / `ruff format` |
| L2 类型 | tsc + Pyright | `pnpm typecheck` / `pyright` |
| L2 Lint | ESLint + Ruff | `pnpm lint` / `ruff check` |
| L3 架构 | 自定义 ESLint 规则 | `pnpm lint:arch` |
| L3 测试 | Vitest + pytest | `pnpm test` / `pytest` |
| L4 品味 | 命名/文件大小检查 | `pnpm lint:taste` |

## 不可做规则（机械强制）

- ❌ 前端组件直接调用 API（必须通过 `lib/api/` 客户端）
- ❌ 后端 API 层直接操作数据库（必须通过 Repository）
- ❌ 硬编码 API Key / Secret（必须在 `.env`）
- ❌ 同步调用 LLM（必须通过 Celery 异步任务或带超时封装）
- ❌ AI 输出不带免责声明
- ❌ 跳过类型检查提交代码

## 环境

| 环境 | 用途 |
|------|------|
| `dev` | 本地 Docker Compose 开发栈 |
| `staging` | 阿里云测试环境 |
| `prod` | 阿里云生产环境（内测 50 用户） |
