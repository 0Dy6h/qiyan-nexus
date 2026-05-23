# B4 — herb / compound / target / pathway sample 数据集（2026-05-22）

> 阶段 B 第四颗 slice。把 B3 留下的硬编码 3 行 mock chain 替换为可查询的 seed 实体图；literature 通过 `related_entity_ids` 跟 herb/formula/compound/target/pathway 互链，B5 跳转才有数据可挂。
> 前置 slice：B3（`docs/handoffs/2026-05-22-b3-network-task-shell.md`）。

## 落地点

- **seed 数据**：新增 `backend/data/network/` 目录，5 个 JSON 文件
  - `sample_herbs.json`（5 条：荆芥/防风/牛蒡子/白鲜皮/黄芪）
  - `sample_formulas.json`（2 条：消风散、当归饮子）含 `herb_ids[]`
  - `sample_compounds.json`（5 条：槲皮素、木犀草素、山奈酚、黄芪甲苷、白鲜碱）含 `herb_ids[]`
  - `sample_targets.json`（5 条：IL6/TNF/STAT3/TSLP/FLG）含 `disease_ids: ["disease-ad"]`
  - `sample_pathways.json`（4 条：PI3K-Akt、NF-kB、JAK-STAT、Skin barrier）含 `target_ids[]`
  - `sample_chains.json`（6 条 denormalized edges：compound→target→pathway + disease + score 0~1）
- **schema**：`app/schemas/network_entities.py` 新增 5 个实体 + `CompoundTargetPathway` edge + `EntityKind` literal；`app/schemas/network.py` `NetworkChain` 加可选 `formula: str | None`（formula 类查询时由 chain.formula 携带方剂名，chain.herb 则是真实成分药）。
- **repository**：`app/repositories/network_entities.py` 提供只读 `NetworkEntityRepository`（`list_*` + `find_formula_by_query` + `find_herb_by_query`）。匹配规则：精确 `name` 或大小写不敏感 `pinyin`。
- **literature 字段**：`LiteratureItem.related_entity_ids: list[str]`（default `[]`），3 条 seed literature 上挂实体 ID：
  - `cn-ad-formula-002` → formula-xiaofengsan / formula-danggui-yinzi / herb-jingjie / herb-fangfeng
  - `cn-ad-barrier-006` → target-flg / pathway-skin-barrier / compound-dictamnine
  - `cn-ad-network-007` → 3 通路 + 3 靶点
- **service 重写**：`app/services/network.py:_build_chains_from_seed(query, analysis_type)` 替代 B3 的 `_build_mock_chains`：
  - `formula` 查询：查 formula → 拿 `herb_ids` → 沿 `sample_chains.json` 展开，只保留来自 formula 成员药的 chain；chain.formula = formula 名
  - `herb` 查询：查 herb → 同样展开但限定单味药
  - 命中后按 `score` 降序，最多 `_MAX_CHAINS_PER_QUERY=5` 条
  - 未命中 query → 走 `_fallback_chains` echo（chain.herb / formula 都写 query 字面值），保证 UI 不空
- **测试**：
  - 后端：`test_network_entity_repository.py`（7 条：5 个 list_*、find_formula、find_herb）
  - 后端：`test_network_service.py`（4 条：formula 展开成分、herb 限定单味、unknown 走 fallback、≤5 条上限）
  - 后端：`test_literature_detail.py` 新增 1 条覆盖 `related_entity_ids` 流通；既有 deepEqual 断言同步补 `"related_entity_ids": []`
  - 后端：`test_network_api.py` 更新 `test_network_task_state_is_persisted_to_runtime_file` 末尾断言（formula 字段 + herb 在成分集合内）
- **前端**：`frontend/lib/api/literature.ts` `LiteratureItem` 加可选 `related_entity_ids?: string[]`（类型完整性，UI 暂不消费）；不改组件、不开新页面

## 行为契约（B4 后）

| 维度 | 行为 |
|---|---|
| `query="消风散", analysis_type="formula"` | 返回 ≥1 条 chain，每条 `formula="消风散"`，`herb ∈ {荆芥,防风,牛蒡子}`，按 score 降序 |
| `query="黄芪", analysis_type="herb"` | 返回 ≥1 条 chain，每条 `herb="黄芪"`，`formula is None` |
| `query="不存在的方剂", analysis_type="formula"` | 返回 ≥1 条 fallback chain，`herb=formula="不存在的方剂"`（echo），仍 ≤5 条 |
| chain 数量上限 | 5 |
| chain 字段 | `herb / formula?: str | None / compound / target / pathway / disease / score` |
| `LiteratureItem.related_entity_ids` | 默认 `[]`，挂的 3 条 seed 上有真实 ID |
| `POST /api/network/analyze` / `GET /api/network/result/{id}` | 路由形状不变；前端无需改 |
| `disclaimer` | 仍 `非诊断结论、需结合临床。` byte-identical |

## 调试痕迹

1. **fallback 路径错位**：第一版让 formula 没命中时仍走主循环（formula_label = query），但 `allowed_herb_ids=None` 等于「全实体扫描」，导致 fallback 测试断言 `chain.herb == query` 失败（chain.herb 是真实成分名）。修正：未命中时直接 `return _fallback_chains(...)`，主循环只跑命中路径。
2. **mypy `no-any-return`**：`json.loads(path.read_text()).` 返回值用作 `list[dict[str, Any]]` 时 mypy 拒绝 implicit Any，改成 `raw: list[...] = json.loads(...)` 显式标注。
3. **既有 `test_literature_detail_returns_item_by_id` deepEqual** 需要同步加 `"related_entity_ids": []`，否则 schema 加字段后整个 dict 断言会 mismatch。
4. **B3 的 persistence 断言**断言 `chains[0]["herb"] == "消风散"`，B4 把 chain.herb 改成真实成分药后必然失败 —— 在同 commit 内更新为校验 `chain.formula == "消风散"` 且 `chain.herb ∈ {荆芥/防风/牛蒡子}`。

## 不在 B4 范围

- 不开 `/api/network/entity/...` 路由（B5 才需要）
- 不在前端 `/network` 页加 entity 详情面板（B5）
- 不在 `/literature/[id]` 显示「相关网药实体」（B5）
- 不接 KEGG / STRING / TCMSP / TCM-IDmap 真实数据库
- 不引入 KEGG 富集分析（→ C4）
- 不引入 `formula_herb_proportion` / 君臣佐使 / 剂量 metadata（未来视需要再加）

## 验证

```bash
cd backend
.venv/bin/python -m ruff format --check app tests
.venv/bin/python -m ruff check app tests
.venv/bin/python -m mypy app
.venv/bin/python -m pytest -q
# 159 passed (+12 from B3)

cd frontend
pnpm test       # 87 passed (unchanged)
pnpm typecheck  # silent OK
pnpm build      # 8 routes prerender
```

**人工 smoke 路径**：

1. `fastapi dev` + `pnpm dev` 同启 → 访问 `http://localhost:3000/network`。
2. 输入 `消风散`、选「复方」→ 提交 → 看到 chain table（≤5 行），herb 列出现 `荆芥/防风/牛蒡子` 中至少一个；表头/分数列与 B3 一致。
3. 改输入 `黄芪`、选「单味中药」→ 看到 chain table 全部 herb=`黄芪`，compound 为 `山奈酚` / `黄芪甲苷`，pathway 含 `JAK-STAT`。
4. 改输入随便一个不存在词 `xxxx`、选「复方」→ 看到 5 行 fallback，herb 列就是 `xxxx`（确认前端不会因为字段变化崩）。
5. `curl -sS http://127.0.0.1:8000/api/literature/cn-ad-network-007 | jq .related_entity_ids` 应返回 6 个实体 id。

## 下一颗候选

按 roadmap §3.2 顺序：

- **B5**（roadmap 估 1.5d）：RAG citation ↔ network entity 双向跳转 —— 用 B4 落地的 `related_entity_ids` 做 anchor，给 citation 标签加链接 + `/network?focus=...` 反向「相关文献」。
- **B6**（roadmap 估 0.5d，独立小活）：数据来源切换面板（CNKI / PubMed / uploaded PDF 三类 banner 文案）。

推荐下一颗 **B5**，因为现在 entity 图已经齐备，趁热打铁把跳转闭环做掉。
