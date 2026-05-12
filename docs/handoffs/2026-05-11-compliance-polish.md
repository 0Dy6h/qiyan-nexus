# 2026-05-11 compliance polish handoff

## 背景

本轮没有继续扩展新业务能力，而是围绕 `frontend/app/compliance/page.tsx` 对 `/compliance` 页面做最小 UI 收口。目标是把该页面从“单独存在的一张说明页”收成与 `/rag`、`/literature`、`/literature/[id]` 同一语言体系下的合规/边界说明页。

## 本轮完成内容

### 第一轮：shared surface 对齐

- 顶部 intro 区块接入 `getSurfaceSectionStyle()`
- highlights 列表卡片接入 `getSurfaceCardStyle()`
- “当前阶段说明”保留为轻语义强调块，但基于 shared surface 做克制覆盖
- 说明正文复用 `CardBodyText`
- nav pills 保留原结构，只补 `minHeight: 44`

### 第二轮：细节收口

- 页面外边距从固定 `48` 改为 `clamp(20px, 4vw, 48px)`，让窄屏更稳
- nav pills 从偏 CTA 的按钮收成更低噪音的工作台导航标签
- 当前页高亮修正为 `/compliance`
- 补充 `nav aria-label="工作台导航"` 与 `aria-current="page"`
- 底部免责声明从单行文本提升为轻量“使用提醒” section

## 当前关键文件

- `frontend/app/compliance/page.tsx`
- `frontend/lib/ui/surfaces.ts`
- `frontend/components/CardMeta.tsx`

## 验证

已完成验证：

- `cd frontend && pnpm typecheck`
- `cd frontend && pnpm build`

两项均通过。

## 当前工作树状态

整理本 handoff 时观察到：

- `frontend/app/compliance/page.tsx` 已修改但尚未提交
- `AGENTS.md` 已修改但尚未提交
- `docs/handoffs/` 目录存在未跟踪内容

也就是说，本轮 `/compliance` polish 目前属于“已验证、未提交”的本地状态。

## 为什么先停在这里

这是一次体验收口，不是新功能推进。当前 `/compliance` 已经达到“够用且可信”的交付状态：

- 页面层级更接近医学证据工作台
- disclaimer 可见但不压屏
- 顶部、内容卡片、阶段说明、使用提醒的结构更统一

继续深挖这页容易走向过度设计，因此本轮停在“最小一致性 polish 完成”是合理边界。

## 若继续推进，建议顺序

1. 如需先收口事实源，优先确认是否提交当前 `/compliance` polish 与 handoff 文档。
2. 如果继续前端主路径，优先切到 `/rag` 做集中 UI 巡检：
   - citation cards 的视觉密度与层级
   - disclaimer 与 retrieval metadata 的摆放关系
   - source / top_k controls 的一致性
3. 若不做 `/rag`，再考虑 `/literature/[id]` 的最小视觉收口。

## 结论

本轮的核心成果不是新增功能，而是把 `/compliance` 明确纳入 Qiyan Nexus 当前工作台的统一产品语言，并保留其作为静态合规/边界说明页的克制表达。
