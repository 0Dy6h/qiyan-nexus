# 04: CardMetaRow 全空项仍渲染空 `<p>` 节点

状态: Agent可接
优先级: P3
发现轮次: 第 1 轮（UI 走查）

## 现象

文献详情页无 PDF 时，可访问性树出现两个空 `paragraph`（上传 ID/文件名行、解析元数据行全部为 null）。

## 根因

`frontend/components/CardMeta.tsx` `CardMetaRow` 无条件渲染 `<p>{joinMetaItems(items)}</p>`，全空项时产出空段落。

## 整改方案

`joinMetaItems(items)` 为空串时返回 `null`。

## 验证

- `frontend/tests/card-meta.test.ts` 增加 `createElement(CardMetaRow, { items: [null] })` 渲染断言（react-dom/server renderToStaticMarkup，无 JSX 依赖）
- 文献详情页空段落消失

## 评论

- 已整改并随第 1 轮提交验证：前端门禁 288 tests + typecheck + build 全绿，UI 复查通过（见 docs/reports/2026-09-04-ux-review-cycles.md 第 1 轮）。
