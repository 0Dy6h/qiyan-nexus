# shadcn/ui 迁移实施路径

基于 ADR-0015 和 `design-system.md` 的具体迁移步骤。

---

## 阶段 0：准备工作（预计 1-2 小时）

### 0.1 安装 Tailwind CSS + shadcn/ui

```bash
cd frontend

# 安装 Tailwind CSS
pnpm add -D tailwindcss postcss autoprefixer
pnpm exec tailwindcss init -p

# 安装 shadcn/ui CLI 依赖
pnpm add -D @types/node
pnpm add class-variance-authority clsx tailwind-merge lucide-react

# 初始化 shadcn/ui（会生成 components/ui/ 和 lib/utils.ts）
pnpm dlx shadcn@latest init
```

**shadcn init 配置选项**：
- TypeScript: Yes
- Style: New York (更现代、克制)
- Base color: Slate (中性灰，与设计系统对齐)
- CSS variables: Yes (便于主题定制)
- Components path: `@/components`
- Utils path: `@/lib/utils`
- React Server Components: Yes
- tailwind.config.js: Yes

### 0.2 配置 Tailwind 主题

编辑 `frontend/tailwind.config.js`，添加青黛绿主色和 Noto Sans SC 字体：

```js
module.exports = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0fdfa',
          100: '#ccfbf1',
          200: '#99f6e4',
          300: '#5eead4',
          400: '#2dd4bf',
          500: '#14b8a6',  // 浅青黛绿
          600: '#0d9488',  // 标准青黛绿
          700: '#0f766e',
          800: '#115e59',
          900: '#134e4a',
        },
      },
      fontFamily: {
        sans: ['Noto Sans SC', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
```

### 0.3 引入 Tailwind CSS

编辑 `frontend/app/globals.css`（如不存在则创建）：

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  body {
    @apply font-sans text-gray-900 bg-gray-50;
  }
}
```

在 `frontend/app/layout.tsx` 中引入：

```tsx
import './globals.css';
```

### 0.4 安装第一批组件

```bash
cd frontend
pnpm dlx shadcn@latest add button card badge separator skeleton input
```

### 0.5 验证

```bash
cd frontend
pnpm build    # 确保 Tailwind 编译通过
pnpm typecheck
```

---

## 阶段 1：试点页面迁移（预计 4-6 小时）

### 试点选择：`/literature`（文献列表页）

**理由**：
- 核心功能页面，用户高频访问
- 包含导航、搜索表单、卡片列表、分页，覆盖多数组件类型
- 当前使用内联样式 + 少量 Ant Design，迁移复杂度适中

### 1.1 迁移导航栏

**现状**（`page.tsx:16-43`）：
- 硬编码的 `<a>` 标签 + 内联样式
- 当前页高亮逻辑用 `background` 和 `border` 实现

**目标**：
```tsx
import { Button } from '@/components/ui/button';

<nav className="flex gap-3 flex-wrap">
  {navigationLinks.map((link) => {
    const isCurrent = link.href === '/literature';
    return (
      <Button
        key={link.href}
        asChild
        variant={isCurrent ? 'default' : 'outline'}
        className={isCurrent ? 'bg-primary-600 hover:bg-primary-700' : ''}
      >
        <a href={link.href} aria-current={isCurrent ? 'page' : undefined}>
          {link.label}
        </a>
      </Button>
    );
  })}
</nav>
```

### 1.2 迁移页面标题区块

**现状**（`page.tsx:47-55`）：
- `<article style={getSurfaceSectionStyle()}>` + 内联样式

**目标**：
```tsx
import { Card, CardContent } from '@/components/ui/card';

<Card>
  <CardContent className="pt-6">
    <p className="text-primary-600 font-bold text-sm mb-2">Evidence workbench</p>
    <h1 className="text-gray-900 text-3xl font-semibold mb-2">文献检索</h1>
    <p className="text-gray-600 text-base leading-relaxed">
      当前页面调用后端 <code className="bg-gray-100 px-1 rounded">/api/literature/search</code>...
    </p>
  </CardContent>
</Card>
```

### 1.3 迁移搜索表单

**现状**（`LiteratureSearchClient.tsx:177-242`）：
- 原生 `<input>` / `<select>` / `<button>` + 内联样式

**目标**：
```tsx
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

<form onSubmit={onSubmit} className="grid gap-4">
  <div className="grid gap-2">
    <label htmlFor="search-query" className="text-gray-900 font-semibold">
      检索关键词
    </label>
    <Input
      id="search-query"
      name="q"
      value={state.query}
      onChange={(e) => setState((current) => ({ ...current, query: e.target.value }))}
      className="border-gray-300 focus:border-primary-500 focus:ring-primary-500"
    />
  </div>

  <div className="flex gap-3 items-end flex-wrap">
    <div className="grid gap-2">
      <label className="text-gray-900 font-semibold">文献来源</label>
      <Select name="view" defaultValue={state.view}>
        <SelectTrigger className="w-[180px]">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">全部来源</SelectItem>
          <SelectItem value="pubmed_live">PubMed 实时</SelectItem>
          <SelectItem value="cnki_sample">CNKI sample</SelectItem>
          <SelectItem value="uploaded_pdf">上传 PDF</SelectItem>
        </SelectContent>
      </Select>
    </div>
    
    {/* 排序、每页数量同理 */}
    
    <Button
      type="submit"
      disabled={state.isLoading}
      className="bg-primary-600 hover:bg-primary-700"
    >
      {state.isLoading ? statusCopy.loadingLabel : statusCopy.submitLabel}
    </Button>
  </div>
</form>
```

### 1.4 迁移文献卡片列表

**现状**（`LiteratureSearchClient.tsx:305-322`）：
- `<article style={getSurfaceCardStyle()}>` + 自定义 `CardMetaRow` / `CardBodyText`

**目标**：
```tsx
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

<div className="grid gap-4">
  {state.items.map((item) => (
    <Card key={item.id} className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex gap-2 flex-wrap mb-2">
          <Badge variant="secondary" className="text-xs">
            {item.language === 'zh' ? '中文' : '英文'}
          </Badge>
          <Badge variant="outline" className="text-xs">
            {getLiteratureSourceLabel(item.source_type)}
          </Badge>
          <Badge variant="outline" className="text-xs">
            {item.year}
          </Badge>
          <Badge 
            variant={item.pdf_parse_status === 'parsed' ? 'default' : 'secondary'}
            className="text-xs"
          >
            {getPdfParseStatusLabel(item.pdf_parse_status ?? null)}
          </Badge>
        </div>
        <CardTitle className="text-xl">{item.title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-gray-600 text-sm leading-relaxed mb-4">
          {item.snippet}
        </p>
        <a 
          href={`/literature/${encodeURIComponent(item.id)}`}
          className="text-primary-600 font-semibold hover:underline"
        >
          查看详情 →
        </a>
      </CardContent>
    </Card>
  ))}
</div>
```

### 1.5 迁移分页按钮

**现状**（`LiteratureSearchClient.tsx:267-301`）：
- 原生 `<button>` + 内联样式

**目标**：
```tsx
<div className="flex gap-2">
  <Button
    variant="outline"
    disabled={state.isLoading || state.page <= 1}
    onClick={() => runSearch(state.query, state.view, state.page - 1, state.pageSize, state.sort)}
  >
    上一页
  </Button>
  <Button
    disabled={state.isLoading || state.page >= state.totalPages}
    className="bg-primary-600 hover:bg-primary-700"
    onClick={() => runSearch(state.query, state.view, state.page + 1, state.pageSize, state.sort)}
  >
    下一页
  </Button>
</div>
```

### 1.6 验证试点页面

```bash
cd frontend
pnpm build
pnpm typecheck
pnpm test  # 确保 literature-sync-api.test.ts 等测试通过

# 启动开发服务器，目视检查
pnpm dev
# 访问 http://localhost:3000/literature
```

**检查清单**：
- [ ] 页面无报错，布局正常
- [ ] 青黛绿主色正确应用（按钮、链接、标签）
- [ ] 卡片悬浮效果流畅
- [ ] 搜索表单可正常提交
- [ ] 分页按钮交互正常
- [ ] 键盘 Tab 导航可用
- [ ] 焦点环清晰可见

---

## 阶段 2：扩展到其他核心页面（预计 6-8 小时）

### 2.1 `/rag`（RAG 问答页）

**优先级**：高（用户高频使用）

**迁移重点**：
- 输入框 + 提交按钮（已有 Input / Button）
- 答案展示卡片（Card）
- 引用文献标签（Badge）
- 免责声明横幅（Alert 组件，需安装：`pnpm dlx shadcn@latest add alert`）

### 2.2 `/literature/[id]`（文献详情页）

**优先级**：高（从列表页点击进入）

**迁移重点**：
- 元数据区块（Card）
- 长文本排版（Typography，可用 Tailwind `prose` 类）
- Tab 切换（需安装：`pnpm dlx shadcn@latest add tabs`）
- 分隔线（Separator）

### 2.3 `/`（首页）

**优先级**：中（当前可能较简单）

**迁移重点**：
- Hero 区块（避免营销页式设计，保持专业克制）
- 快速入口卡片（Card）

### 2.4 `/evals/rag-ad`（RAG 评估页）

**优先级**：中（内部验证工具）

**迁移重点**：
- 表格展示（考虑是否需要 `pnpm dlx shadcn@latest add table`，或继续用 Ant Design Table）

---

## 阶段 3：清理与优化（预计 2-4 小时）

### 3.1 移除 Ant Design 依赖（谨慎）

**前提**：所有页面迁移完成，Ant Design 无引用。

```bash
cd frontend
pnpm remove antd
```

**注意**：如表格、表单等复杂组件仍依赖 Ant Design，保留依赖，仅在新页面中不引入。

### 3.2 统一组件导入路径

确保所有页面使用 `@/components/ui/*` 导入 shadcn/ui 组件。

### 3.3 清理旧样式工具

**评估以下工具是否仍需要**：
- `lib/ui/surfaces.ts`（`getSurfaceCardStyle` / `getSurfaceSectionStyle`）
- `lib/ui/states.ts`
- `components/CardMeta.tsx`

**决策**：
- 如已完全由 shadcn/ui Card 替代，删除并更新引用。
- 如仍有特殊场景需要，保留并注释"遗留工具，新代码不应使用"。

### 3.4 更新测试

**受影响测试**：
- `frontend/tests/client-section-consistency.test.mjs`（检查组件引用）
- `frontend/tests/page-shell-consistency.test.mjs`（检查页面结构）

**更新策略**：
- 将硬编码的 inline style 检查改为 Tailwind 类名检查。
- 示例：`/style={{.*background.*}}/` → `/className=".*bg-gray-50.*"/`

---

## 阶段 4：文档与移交（预计 1 小时）

### 4.1 更新 CLAUDE.md

在"前端 test setup"段落后添加：

```markdown
### shadcn/ui 组件使用

新页面和重构页面优先使用 shadcn/ui + Tailwind CSS（详见 ADR-0015 和 `docs/design-system.md`）。

组件安装：
```bash
cd frontend
pnpm dlx shadcn@latest add <component-name>
```

已安装组件：button, card, badge, separator, skeleton, input, select, alert, tabs, table。

样式定制：编辑 `frontend/tailwind.config.js` 和 `frontend/app/globals.css`。
```

### 4.2 创建迁移总结文档

`docs/handoffs/2026-06-10-shadcn-ui-migration.md`，记录：
- 迁移的页面清单
- 遇到的问题与解决方案
- 未迁移的页面及原因
- 后续维护建议

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 试点页面迁移后视觉不符合预期 | 高 | 在 `/literature` 试点阶段充分调整，确认设计系统可行后再扩展 |
| Ant Design 和 shadcn/ui 样式冲突 | 中 | Tailwind 使用 CSS layers，优先级高于 Ant Design；必要时用 `!important` |
| 表格/表单组件迁移成本高 | 中 | 保留 Ant Design Table/Form，仅迁移简单组件；或按需引入 shadcn/ui table |
| 测试失败（regex 断言不匹配） | 中 | 迁移时同步更新测试文件的正则表达式 |
| pnpm build 失败 | 高 | 每完成一个页面立即运行 `pnpm build` + `pnpm typecheck`，不累积问题 |

---

## 时间预估总计

- 阶段 0：1-2 小时
- 阶段 1：4-6 小时
- 阶段 2：6-8 小时
- 阶段 3：2-4 小时
- 阶段 4：1 小时

**总计**：14-21 小时（约 2-3 个工作日，单人全职）

---

## 下一步行动

1. **立即执行**：阶段 0（准备工作），验证 Tailwind + shadcn/ui 可正常构建。
2. **确认设计**：用设计工具（Figma / 草图）绘制 `/literature` 页面的目标视觉，与设计系统对齐。
3. **试点迁移**：阶段 1，完整迁移 `/literature` 并验证。
4. **评审决策**：试点完成后，召集评审确认视觉效果，决定是否全面推进。

需要我立即开始阶段 0 的安装配置吗？
