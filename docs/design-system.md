# Qiyan Nexus 设计系统规范

shadcn/ui + Tailwind CSS + Radix UI 实施指南

---

## 核心原则

**定位**：面向医生/科研人员的特应性皮炎证据工作台。

**气质关键词**：
- 专业、可信、浅色、低噪音
- 中高信息密度、证据优先
- 克制、现代、细腻信息层级

**反面清单**（避免）：
- 花哨 AI 风格（大渐变、霓虹色、过度动效）
- 玻璃拟态（frosted glass / glassmorphism）
- 营销页式 hero（大标题+插图+CTA）
- 通用企业后台气质（过于中性、缺乏品牌感）

---

## 颜色系统

### 主色（青黛绿）

```css
/* Primary - 用于品牌识别、关键操作、链接 */
--primary-600: #0d9488;  /* 标准青黛绿 */
--primary-500: #14b8a6;  /* 浅青黛绿 */
--primary-700: #0f766e;  /* 深色变体 */
--primary-100: #ccfbf1;  /* 极浅背景 */
```

Tailwind 映射：`bg-teal-600` / `text-teal-600` / `border-teal-500` 等（teal 系列与青黛绿接近）。

### 中性色

```css
/* Neutral - 用于文本、边框、背景 */
--gray-50:  #f9fafb;  /* 页面背景 */
--gray-100: #f3f4f6;  /* 卡片背景 */
--gray-200: #e5e7eb;  /* 边框 */
--gray-400: #9ca3af;  /* 次要文本 */
--gray-700: #374151;  /* 主要文本 */
--gray-900: #111827;  /* 强调文本 */
```

Tailwind 映射：直接使用 `gray-*` 系列。

### 语义色

```css
/* Success - 成功/正面反馈 */
--success: #10b981;  /* green-500 */

/* Warning - 警告/注意 */
--warning: #f59e0b;  /* amber-500 */

/* Error - 错误/危险操作 */
--error: #ef4444;   /* red-500 */

/* Info - 信息提示 */
--info: #3b82f6;    /* blue-500 */
```

---

## 排版

### 字体栈

```css
font-family: 'Noto Sans SC', -apple-system, BlinkMacSystemFont, 'Segoe UI', 
             'Helvetica Neue', Arial, sans-serif;
```

**中文**：Noto Sans SC（思源黑体简体），清晰、现代、医疗场景适用。  
**英文/数字**：系统默认 sans-serif 栈。

### 字阶

```css
/* 标题 */
--text-3xl: 1.875rem;  /* 30px - 页面主标题 */
--text-2xl: 1.5rem;    /* 24px - 区块标题 */
--text-xl:  1.25rem;   /* 20px - 卡片标题 */
--text-lg:  1.125rem;  /* 18px - 小标题 */

/* 正文 */
--text-base: 1rem;     /* 16px - 正文 */
--text-sm:   0.875rem; /* 14px - 次要信息 */
--text-xs:   0.75rem;  /* 12px - 辅助信息、标签 */
```

Tailwind 映射：`text-3xl` / `text-base` / `text-sm` 等。

### 行高

```css
--leading-tight:  1.25;   /* 标题 */
--leading-normal: 1.5;    /* 正文 */
--leading-relaxed: 1.625; /* 长文本 */
```

---

## 间距

采用 Tailwind 默认 spacing scale（`1` = 0.25rem = 4px）：

| Token | 值 | 用途 |
|-------|---|------|
| `space-1` | 4px | 紧凑间距（图标与文字） |
| `space-2` | 8px | 小间距（标签内边距） |
| `space-3` | 12px | 标准间距（按钮内边距） |
| `space-4` | 16px | 卡片内边距 |
| `space-6` | 24px | 区块间距 |
| `space-8` | 32px | 大区块间距 |
| `space-12` | 48px | 页面级间距 |

**容器内边距**：`px-6 py-4`（卡片）、`px-8 py-6`（页面主容器）。  
**响应式页面边距**：使用现有 `clamp(20px, 4vw, 48px)` 或 Tailwind `px-5 md:px-8 lg:px-12`。

---

## 组件规范

### 按钮

**主按钮**（Primary）：
```tsx
<Button className="bg-teal-600 hover:bg-teal-700 text-white">
  确认提交
</Button>
```

**次按钮**（Secondary）：
```tsx
<Button variant="outline" className="border-gray-300 text-gray-700 hover:bg-gray-50">
  取消
</Button>
```

**文本按钮**（Ghost）：
```tsx
<Button variant="ghost" className="text-teal-600 hover:bg-teal-50">
  查看详情
</Button>
```

### 卡片

**标准卡片**：
```tsx
<Card className="bg-white border border-gray-200 rounded-lg shadow-sm">
  <CardHeader className="border-b border-gray-100 px-6 py-4">
    <CardTitle className="text-xl font-semibold text-gray-900">
      文献标题
    </CardTitle>
  </CardHeader>
  <CardContent className="px-6 py-4">
    {/* 内容 */}
  </CardContent>
</Card>
```

**悬浮效果**（可交互卡片）：
```css
hover:shadow-md transition-shadow duration-200
```

### 输入框

```tsx
<Input 
  className="border-gray-300 focus:border-teal-500 focus:ring-teal-500"
  placeholder="搜索文献..."
/>
```

### 标签（Tag）

**类别标签**：
```tsx
<Badge variant="secondary" className="bg-gray-100 text-gray-700 text-xs">
  中医药
</Badge>
```

**状态标签**：
```tsx
<Badge className="bg-teal-100 text-teal-700 text-xs">
  已解析
</Badge>
```

### 分隔线

```tsx
<Separator className="bg-gray-200" />
```

---

## 布局模式

### 页面容器

```tsx
<main className="min-h-screen bg-gray-50">
  <div className="max-w-7xl mx-auto px-5 md:px-8 lg:px-12 py-8">
    {/* 页面内容 */}
  </div>
</main>
```

### 栅格布局

**文献列表**（2列）：
```tsx
<div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
  {items.map(item => <LiteratureCard key={item.id} {...item} />)}
</div>
```

**详情页**（侧边栏 + 主内容）：
```tsx
<div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
  <aside className="lg:col-span-1">{/* 元数据 */}</aside>
  <article className="lg:col-span-3">{/* 正文 */}</article>
</div>
```

---

## 交互规范

### 状态反馈

- **加载**：使用 `Skeleton` 占位（灰色矩形闪烁），不用 spinner。
- **成功**：toast 提示，绿色图标 + 文字，3 秒自动消失。
- **错误**：toast 提示，红色图标 + 文字，需手动关闭。
- **空状态**：居中展示"暂无数据"+ 插图（可选）+ 引导操作。

### 焦点与键盘

- 所有可交互元素支持键盘 Tab 导航。
- 焦点环使用 `focus:ring-2 focus:ring-teal-500 focus:ring-offset-2`。
- 模态框打开时焦点锁定在对话框内，Esc 关闭。

### 动效

**原则**：克制、快速、功能性。

```css
/* 标准过渡 */
transition-colors duration-200
transition-shadow duration-200

/* 弹窗/下拉进入 */
animate-in fade-in-0 zoom-in-95 duration-200

/* 避免 */
- 超过 300ms 的过渡
- 弹跳/弹性动效（spring easing）
- 装饰性动画（粒子、波纹、流星）
```

---

## shadcn/ui 组件安装清单

按需安装到 `frontend/components/ui/`：

**第一批（试点页面必需）**：
- `button`
- `card`
- `input`
- `badge`
- `separator`
- `skeleton`

**第二批（交互增强）**：
- `dialog`
- `dropdown-menu`
- `tabs`
- `tooltip`
- `toast`

**第三批（复杂场景）**：
- `table`（如需替换 Ant Design Table）
- `form`（如需替换 Ant Design Form）
- `select`
- `checkbox` / `radio-group`

---

## 迁移检查清单

每个页面迁移完成后需验证：

- [ ] `pnpm build` 通过
- [ ] `pnpm typecheck` 通过
- [ ] 页面在 Chrome / Safari / Firefox 显示一致
- [ ] 键盘导航可用（Tab / Enter / Esc）
- [ ] 焦点环清晰可见
- [ ] 颜色对比度符合 WCAG AA（文本至少 4.5:1）
- [ ] 没有硬编码颜色（应使用 Tailwind token）
- [ ] 视觉效果符合"专业、可信、低噪音"定位

---

## 试点页面建议

**优先级 1**：`/literature`（文献列表页）
- 核心功能页面，信息密度高，适合验证卡片/标签/分页组件。
- 当前使用 Ant Design List，迁移后用自定义卡片 + shadcn/ui Badge。

**优先级 2**：`/rag`（RAG 问答页）
- 用户高频使用，需验证输入框/答案展示/引用卡片。
- 当前已有自定义样式，迁移后统一用 shadcn/ui Card + Badge。

**优先级 3**：`/literature/[id]`（文献详情页）
- 长文本排版，需验证 Typography / Tabs / Separator。

---

## 参考资源

- [shadcn/ui 文档](https://ui.shadcn.com/)
- [Tailwind CSS 文档](https://tailwindcss.com/docs)
- [Radix UI 文档](https://www.radix-ui.com/)
- [Tailwind 配色工具](https://uicolors.app/create)（生成 teal 系列完整色阶）
