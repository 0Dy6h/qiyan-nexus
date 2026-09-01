# ADR-0009: 前端实际版本基线与 Ant Design 使用策略

日期：2026-05-06

## 状态

Accepted

## 背景

早期规划文档冻结的前端方案是 Next.js 15 + React + Ant Design 5。

当前 `frontend/package.json` 的实际安装基线是：
- Next.js 16.2.6
- React 19.2.3
- Ant Design 6.1.0

当前 `pnpm test` 与 `pnpm build` 已通过，因此实际工程基线应以 package.json 和 lockfile 为准。

## 决策

1. 前端实际版本基线采用当前已验证组合：Next.js 16 + React 19 + Ant Design 6。
2. 后续文档提到前端版本时，应写实际基线，而不是继续写 Next.js 15 / Ant Design 5。
3. 在第一阶段纵向切片中，优先保证页面可构建与交互可验证，不强制所有 UI 立即迁移到 Ant Design 组件。
4. Ant Design 用于稳定组件和设计系统沉淀；若某个 AntD 组件影响静态构建，应先用原生 markup 完成交付切片，再单独引入并测试。

## 后果

正面：
- 文档与实际依赖保持一致。
- 避免开发者按旧版本排错。
- 保留当前已通过构建的工程基线。

代价：
- 早期规划文档中的 Next.js 15 / AntD 5 表述需要逐步更新。
- Ant Design 6 的行为与 AntD 5 可能不同，组件引入需要配套 build 验证。

## 验证

当前验证命令：

```bash
cd frontend && pnpm test && pnpm build
```

当前结果：3 tests passed，Next.js production build passed。
