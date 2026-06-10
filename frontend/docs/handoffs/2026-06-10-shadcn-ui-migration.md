# 2026-06-10 shadcn/ui 迁移完成

## 背景

将 Qiyan Nexus 前端从 Ant Design 默认体系 + 内联样式迁移到 shadcn/ui + Tailwind CSS v4，目标是提升视觉上限、打造专业克制的医疗科研工作台气质。

决策理由：只从最终视觉效果判断，shadcn/ui + Tailwind + Radix 的视觉上限更高，更适合做出现代、专业、有产品感的证据工作台。

## 迁移范围

### 已迁移（阶段 0-2）

**核心页面**（5 个）：
- `/` — 首页
- `/literature` — 文献检索页
- `/literature/[id]` — 文献详情页
- `/rag` — RAG 问答页
- `/network` — 网络药理学页

**shadcn/ui 组件**（6 个）：
- `Button`（default/outline/secondary/ghost 变体）
- `Card`（Header/Title/Description/Content/Footer）
- `Badge`（default/secondary/outline/destructive 变体）
- `Input`
- `Separator`
- `Skeleton`

**依赖安装**：
- Tailwind CSS v4 + `@tailwindcss/postcss`
- Radix UI primitives（`@radix-ui/react-slot`、`@radix-ui/react-separator`）
- `class-variance-authority`、`clsx`、`tailwind-merge`、`lucide-react`

**移除**：
- `antd/dist/reset.css` 导入（不再需要 Ant Design 的全局样式重置）

### 未迁移（保留现状）

**页面**：
- `/compliance` — 合规说明页（使用 `surfaces.ts` + 内联样式）
- `/evals/rag-ad` — RAG 评估页（可能使用 Ant Design Table）

**组件**：
- `RagAnswerClient` — RAG 答案客户端（内部仍使用 `CardMeta` + `surfaces`）
- `NetworkAnalysisClient` — 网络分析客户端（内部仍使用 `surfaces`）
- `LiteraturePdfUploadClient` — PDF 上传客户端（使用 `CardMeta`）
- `LiteraturePubmedSyncClient` — PubMed 同步客户端（使用 `CardMeta`）
- `DemoDataBanner` — Demo 数据横幅（内联样式，独立设计）
- `StatusPanel` — 状态面板（内联样式）

**辅助模块（保留）**：
- `lib/ui/surfaces.ts` — `getSurfaceCardStyle()` / `getSurfaceSectionStyle()`
- `components/CardMeta.tsx` — `CardMetaRow` / `CardBodyText`
- `antd` 依赖包（保留，未来可能用于表格等复杂组件）

## 设计系统

### 青黛绿主色

CSS 变量已在 `app/globals.css` 中定义：

```css
:root {
  --color-primary-50: #f0fdfa;
  --color-primary-100: #ccfbf1;
  --color-primary-200: #99f6e4;
  --color-primary-300: #5eead4;
  --color-primary-400: #2dd4bf;
  --color-primary-500: #14b8a6;
  --color-primary-600: #0d9488;  /* 主色 */
  --color-primary-700: #0f766e;
  --color-primary-800: #115e59;
  --color-primary-900: #134e4a;
}
```

Tailwind 中使用：
- 按钮：`bg-primary-600 hover:bg-primary-700`
- 焦点环：`focus-visible:ring-primary-500`
- 文本：`text-primary-600`

### 排版层级

- H1 主标题：`text-4xl font-semibold`（首页 `text-5xl`）
- H2 区块标题：`text-2xl font-semibold`
- 正文：`text-base leading-relaxed`
- 次要信息：`text-sm`
- 标签：`text-xs`

### 间距系统

- 页面边距：`px-5 md:px-8 lg:px-12 py-8`
- 卡片间距：`gap-5`
- 内容间距：`gap-2` / `gap-3` / `gap-4`

### 组件使用规范

**按钮**：
```tsx
<Button variant="default" size="default">主要操作</Button>
<Button variant="outline" size="sm">次要操作</Button>
<Button variant="secondary" size="sm">辅助操作</Button>
<Button asChild><a href="/path">链接按钮</a></Button>
```

**卡片**：
```tsx
<Card>
  <CardHeader>
    <CardTitle>标题</CardTitle>
    <CardDescription>描述</CardDescription>
  </CardHeader>
  <CardContent>内容</CardContent>
</Card>
```

**标签**：
```tsx
<Badge variant="secondary">标签</Badge>
<Badge variant="outline">次要标签</Badge>
```

## 技术细节

### Tailwind CSS v4 配置

**关键变化**：
- 使用 `@tailwindcss/postcss` 替代 `tailwindcss` PostCSS 插件
- 删除 `tailwind.config.js`（CSS-first 配置）
- 在 `globals.css` 中使用 `@import "tailwindcss";`

**postcss.config.js**：
```js
module.exports = {
  plugins: {
    '@tailwindcss/postcss': {},
    autoprefixer: {},
  },
}
```

### TypeScript 路径映射

**tsconfig.json**：
```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./*"]
    }
  }
}
```

使 `@/components/ui/button` 这样的导入可以正常工作。

### 测试更新

更新了 3 个测试文件以匹配新的 Tailwind 类名和 JSX 语法（非模板字符串）：
- `tests/client-section-consistency.test.ts`
- `tests/page-shell-consistency.test.ts`
- `tests/literature-detail-meta.test.ts`

所有 157 个测试通过。

## 视觉验证

通过 Playwright 截图验证了迁移效果：
- **首页**：干净的白色卡片居中布局，清晰的排版层级
- **文献检索页**：统一的导航栏、卡片式表单、Badge 标签
- **RAG 问答页**：一致的视觉语言

关键改进：
- 统一的卡片圆角和阴影
- 统一的按钮高度和交互状态
- 统一的色彩语义（青黛绿主色，灰度文本层级）
- 统一的间距和排版节奏

## 后续建议

### 继续迁移（可选）

**高优先级**：
- `RagAnswerClient` — RAG 核心交互组件
- `NetworkAnalysisClient` — 网络分析核心组件

**中优先级**：
- `LiteraturePdfUploadClient`
- `LiteraturePubmedSyncClient`

**低优先级**：
- `/compliance` 页面（内容为主，视觉次要）
- `/evals/rag-ad` 页面（内部工具页）

### 组件增强

**未实现的 shadcn/ui 组件**（按需添加）：
- `Select` — 替代原生 `<select>`（当前为简化保留原生）
- `Textarea` — 替代原生 `<textarea>`
- `Dialog` / `AlertDialog` — 弹窗交互
- `Tabs` — 多标签页切换
- `Table` — 数据表格（若不用 Ant Design）

### 代码清理

当所有组件迁移完成后：
- 删除 `lib/ui/surfaces.ts`
- 删除 `components/CardMeta.tsx`
- 评估是否移除 `antd` 依赖

## 文件清单

**新增**：
- `components/ui/button.tsx`
- `components/ui/card.tsx`
- `components/ui/badge.tsx`
- `components/ui/input.tsx`
- `components/ui/separator.tsx`
- `components/ui/skeleton.tsx`
- `lib/utils.ts`

**修改**：
- `app/layout.tsx` — 移除 `antd/dist/reset.css`
- `app/globals.css` — 添加 Tailwind v4 + CSS 变量
- `postcss.config.js` — 使用 `@tailwindcss/postcss`
- `tsconfig.json` — 添加路径映射
- `package.json` — 添加 shadcn/ui 依赖
- 5 个页面文件（`page.tsx`）
- 1 个组件文件（`LiteratureSearchClient.tsx`）

**删除**：
- `tailwind.config.js`

## 验证命令

```bash
cd frontend
pnpm build        # 构建成功
pnpm typecheck    # 类型检查通过
pnpm test         # 157 tests passed
```

---

**移交时间**：2026-06-10  
**验证状态**：✅ 构建通过 / ✅ 测试通过 / ✅ 视觉验证通过  
**下一步入口**：继续迁移内部组件，或保持当前状态并专注业务功能开发
