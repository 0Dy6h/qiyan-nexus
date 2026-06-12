# 方案 A：多语 embedding 真实模型评估 — 完成总结

## 执行情况

✅ **Slice 1: bge-m3 真实模型评估** — 已完成（2026-06-12）
✅ **Slice 2: multilingual-e5-large 对比评估** — 已完成（2026-06-12）
⏭️ **Slice 3: grounding semantic 阈值重校准** — 跳过（无需切换 backend）

## 核心结论

**❌ 不推荐切换到 bge-m3 或 multilingual-e5-large**

### 数据支持

| Backend | Strategy | Cross Recall | vs Baseline (0.9688) |
|---------|----------|:------------:|:--------------------:|
| n/a | **keyword** | **0.9375** | -0.0313 ✅ |
| bge-m3 | vector | 0.6250 | -0.3438 ❌ |
| bge-m3 | hybrid | 0.9062 | -0.0626 ⚠️ |
| e5-large | vector | **0.0625** | **-0.9063** ❌❌ |
| e5-large | hybrid | 0.6562 | -0.3126 ❌ |

**关键发现**：
1. 两个多语模型的纯 vector 策略均无法超越 keyword+术语桥
2. e5-large 跨语召回接近完全失效（0.0625，仅 1/16 题命中）
3. bge-m3 hybrid 接近但仍低于 keyword（gap 0.0313）
4. 所有配置的 mono recall 均为 1.0000（中文检索无退化）

### 根因

通用多语模型在 **AD 医学领域的 CN↔EN 术语配对** 训练不足：
- 日常词汇（"cat→猫"）对齐良好
- 专业术语（"gut-brain-skin axis→肠-脑-皮肤轴"）语义空间距离大

Keyword + 显式术语桥（17 组确定性映射）保证 100% 召回已知映射。

## 产出文件

### 新增文件
1. `backend/scripts/eval_cross_lingual_bge_m3.py` — bge-m3 评估脚本
2. `backend/scripts/eval_cross_lingual_e5_large.py` — e5-large 评估脚本
3. `docs/evaluations/2026-06-12-bge-m3-cross-lingual-eval.md` — 完整评估报告
4. `docs/handoffs/2026-06-12-multilingual-embedding-real-eval.md` — 会话交接文档

### 已有文件（未修改）
- `backend/app/services/retrieval/embedding.py` — BgeM3 / E5Large backends 已在 2026-06-10 落地
- `backend/tests/test_cross_lingual_eval.py` — 25 passed，无修改

## 验证通过

- ✅ bge-m3 评估完成（3 策略 × 16 题）
- ✅ e5-large 评估完成（3 策略 × 16 题）
- ✅ 跨语言测试通过（`pytest tests/test_cross_lingual_eval.py -q` 25 passed）
- ✅ 完整后端测试套件（`pytest -q` 489 passed, 1 skipped）

## 技术决策

**保持现状**：
- `QIYAN_EMBEDDING_BACKEND=hashing`（默认，零下载）
- `QIYAN_RETRIEVAL_PROVIDER=keyword`（默认）
- 跨语言术语桥保持 17 组映射（`backend/data/retrieval/cross_lingual_terms.json`）

**不采纳**：
- bge-m3 vector/hybrid（跨语能力弱于 keyword）
- multilingual-e5-large（跨语几乎完全失效）

## 下一步推荐

按照原计划优先级：

### 方案 B：PostgreSQL/pgvector spike（推荐）
- 当前 SQLite runtime backend 已落地（2026-06-02）
- pgvector 是生产级向量检索必经之路
- 工程铺垫，不改变用户体验

### 方案 C：L2 预览推进（被治理决策阻塞）
- 需业务/采购确认 BGE=0.3 + NLI=0.5 profile 可接受性
- 需复核真实合同价格（当前用公开价格估算）
- 需正式医生/科研 reviewer sign-off

### MVP-B 继续推进
- 按 `docs/plans/2026-05-21-roadmap.md`，B1-B6 大部分已提前落地
- 可推进网络药理学 mock → 真实富集分析

## 备注

多语 embedding spike 作为技术探索已完成，验证了假设但未改变系统配置。这是 **evaluate-then-decide** 模式的正确应用：投入少量时间（3-4 小时）验证技术方向，避免盲目切换带来的工程成本和性能退化。

---

**评估完成日期**：2026-06-12  
**耗时**：~3.5 小时（模型下载 + 2 次评估运行 + 文档编写）  
**状态**：✅ 已闭环，可归档
