# 08: 演示数据横幅声称「未对接 PubMed 真实库」，与同页来源说明及实时同步行为矛盾

状态: Agent可接
优先级: P2
发现轮次: 第 3 轮（筛选/同步/导出走查）

## 现象

`/literature` 与 `/rag` 顶部 DemoDataBanner 写「文献条目为小型合成样本集……未对接知网/PubMed 真实库」，但同页下方「数据来源说明」写「已汇总中文/英文演示 seed、PubMed 实时同步与上传 PDF 三类记录」。实测点击「同步 PubMed」当场拉回 5 条 `pubmed_live` 记录——横幅被产品自身行为证伪。研究者刚同步完真实记录，抬头看到「未对接真实库」，对边界标注的可信度是损害。

## 根因

`frontend/components/DemoDataBanner.tsx` 文案是 PubMed live sync 落地（2026-06 PubMed 同步入口上线）之前的旧话术，未随能力更新。

## 整改方案

横幅改为按来源分述的准确边界：中文文献为合成 seed 未对接知网/万方；PubMed 为 NCBI E-utilities 实时同步（遵守条款与限速）；上传 PDF 仅本地 runtime 演示；演示 seed 不可当真实文献引用。headline 改为「数据边界提示：演示 seed 与实时记录分开标注……」；compact 与完整变体同步。测试断言更新并显式禁止旧短语回归。

## 验证

- UI：/literature、/rag 横幅新文案；同步后不再出现自相矛盾表述
- `demo-data-banner.test.ts` 全绿

## 评论

- 已整改并随第 3 轮提交验证：verify-local 全绿（82.1s），/literature 与 /rag 横幅复查通过。
