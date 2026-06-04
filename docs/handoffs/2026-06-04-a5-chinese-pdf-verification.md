# A5 真实中文 PDF 人工验收 closure — 2026-06-04

> roadmap §3.1 A5 验收：上传 2-3 个真实中文文本型 PDF，确认 `pypdf-text-preview` 返回中文不乱码；不通过则回退到 fallback 文案。
>
> 闭合先前 `docs/current-state.md:78` 提及"4 份本地中文 PDF 样本最小验收探测"但缺正式 handoff 记录的状态。

## 验收方法

走 FastAPI 后端真实 API 端到端路径（不绕过 service / 不 mock pypdf）：

1. `POST /api/uploads/pdf` — multipart 上传文件至 `backend/uploads/`，初始 `pdf_parse_status=pending`
2. `POST /api/uploads/pdf/auto-parse` — 触发 `auto_parse_uploaded_pdf` → `update_pdf_parse_status` → `build_pdf_parse_result` → `extract_pdf_preview_text` (真实 pypdf 5.x)
3. `GET /api/literature/{id}` — 核对 detail 视图返回的 `pdf_parse_status` / `pdf_upload_id` 持久化一致

通过 `fastapi.testclient.TestClient(app)` 直接驱动，但 **不启用 pytest conftest 隔离 fixture**——即运行在真实 `backend/data/runtime/literature_state.json` + `backend/uploads/` 上下文中（uploads-staging 副本拷出，原 PDF 仍在 `local-review-pdfs/`，gitignored 不入仓）。

启发式判定准则（来自 `app/services/literature.py:detect_pdf_text_quality_warning`）：
- `\x00` 数 ≥ 3 或占比 ≥ 2% → `quality_warning` 触发
- 自定义 CJK 密度阈值：preview 中 U+4E00–U+9FFF 字符 ≥ 30 视为含可读中文

## 样本元信息

| literature_id | 文件名（不入仓） | 文件大小 | 主题 |
|---|---|---|---|
| cn-ad-formula-002 | 中医辨证治疗异位性皮炎临床观察_周海啸.pdf | 306 KB | 中医辨证治疗（综述/临床观察） |
| cn-ad-pruritus-005 | 中药健脾止痒颗粒合铍宝消炎癣湿药膏治疗特应性皮炎疗效分析_杨瑛 - 副本.pdf | 96 KB | 中药复方止痒（疗效分析） |
| cn-ad-barrier-006 | 健脾养血祛风法治疗特应性皮炎临床疗效及对皮肤屏障功能的影响_杨雪松.pdf | 306 KB | 健脾养血祛风法（皮肤屏障） |
| cn-ad-external-008 | 除湿糊剂治疗特应性皮炎的实验与临床观察_王琼 - 副本.pdf | 70 KB | 外用除湿糊剂（实验+临床观察） |

源 PDF 存放于 `local-review-pdfs/`（gitignored），不入仓。`backend/uploads/` 下的副本同样 gitignored。

## 实测结果

### 样本 1 — cn-ad-formula-002（**case A：quality_warning 正确触发**）

| 字段 | 值 |
|---|---|
| upload_status_code | `201` ✅ |
| pdf_upload_id | `pdf-cn-ad-formula-002-pdf-5ffc0e56` |
| parse_status_code | `200` ✅ |
| pdf_parse_status | `parsed` |
| extraction_method | `pypdf-text-preview` |
| preview_len | 300 |
| CJK 字符数 | **137** |
| `\x00` 数 | **42**（占比 **14.0%**，远超 2% 阈值） |
| quality_warning | **触发** ✅：`检测到抽取文本可能存在数字或表格乱码，请对照原始 PDF 核对关键数值。` |
| preview 前 80 | `中国 中医 药信 息 杂志 \x00\x00\x00\x00年 第 \x00卷 第 \x00\x00 期 中医辨证治疗异位性皮炎临床观察 周 海啸 …` |
| GET 详情核对 | `pdf_parse_status=parsed`、`pdf_upload_id` 一致 ✅ |

**判定**：text-layer 提取出可读中文标题与作者，**但** 期刊年/卷/期等数字字段被 PDF 嵌入字体表示为不可解码字符 → `\x00` 填充。`detect_pdf_text_quality_warning` 按设计契约正确触发警告文案，前端 UI 会显示该警告提醒人工核对数值。**符合 case A 既有 fallback 路径**，算 A5 通过项。

### 样本 2 — cn-ad-pruritus-005（**干净中文**）

| 字段 | 值 |
|---|---|
| upload_status_code | `201` ✅ |
| parse_status_code | `200` ✅ |
| pdf_parse_status | `parsed` |
| extraction_method | `pypdf-text-preview` |
| CJK 字符数 | **130** |
| `\x00` 数 | **0** |
| quality_warning | 未触发 |
| preview 前 80 | `中 国 中 西 医 结 合 皮 肤 性 病 学 杂 志 2007 年 第 6 卷 第 3 期 细 胞 凋 亡 在 致 敏 的 T 淋 巴 细 胞 的 清 除 起…` |

**判定**：✅ 干净中文。

### 样本 3 — cn-ad-barrier-006（**干净中文**）

| 字段 | 值 |
|---|---|
| upload_status_code | `201` ✅ |
| parse_status_code | `200` ✅ |
| pdf_parse_status | `parsed` |
| extraction_method | `pypdf-text-preview` |
| CJK 字符数 | **159** |
| `\x00` 数 | **0** |
| quality_warning | 未触发 |
| preview 前 80 | `第 32卷第 3期 2009年 6月 云南中医学院学报 ＪｏｕｒｎａｌｏｆＹｕｎｎａｎＵｎｉｖｅｒｓｉｔｙｏｆＴｒａｄｉｔｉｏｎａｌＣｈｉｎｅｓｅＭｅｄｉｃｉｎ…` |

**判定**：✅ 干净中文（含全角拉丁，正常）。

### 样本 4 — cn-ad-external-008（**干净中文**）

| 字段 | 值 |
|---|---|
| upload_status_code | `201` ✅ |
| parse_status_code | `200` ✅ |
| pdf_parse_status | `parsed` |
| extraction_method | `pypdf-text-preview` |
| CJK 字符数 | **200** |
| `\x00` 数 | **0** |
| quality_warning | 未触发 |
| preview 前 80 | `特应性皮炎 (AD) 是一种与遗传过敏素质有关的皮肤炎症性 疾病。表现为多形性皮疹 , 剧烈瘙痒。常伴有哮喘和过敏性鼻炎 , 反复发作 , 易于扩散。皮疹在不同…` |

**判定**：✅ 干净中文，整句可读，临床/中医术语完整。

## checklist 状态

- [x] `POST /api/uploads/pdf` 201（4/4）；`pdf_upload_id` 稳定（同 literature_id + 同 file_name 幂等）
- [x] `POST /api/uploads/pdf/auto-parse` 200（4/4）；`pdf_parse_status` 全部 `pending → parsed`
- [x] text-layer 样本 ≥ 1 份返回干净中文（实测 3/4 干净；plan 阈值"至少 1 份"通过）
- [x] case A 触发样本（cn-ad-formula-002）：`extraction_method == "pypdf-text-preview"` + `quality_warning` 正确触发
- [x] runtime state 写入：`backend/data/runtime/literature_state.json` 含 4 个 literature 的 `pdf_parse_*` 字段
- [x] `GET /api/literature/{id}` 返回的 `pdf_parse_status` / `pdf_upload_id` 与 auto-parse 返回一致

## 决策

**A5 closure：✅ PASSED**

- 3/4 真实中文 AD PDF 走通 `pypdf-text-preview` 路径并返回干净可读中文（CJK 130-200，零 `\x00`），覆盖 plan 的"至少 1 份 text-layer 干净中文"通过标准；
- 1/4（cn-ad-formula-002）触发 `quality_warning` fallback 路径，行为符合既有 `detect_pdf_text_quality_warning` 契约（仍返回部分可读 preview + 警告文案，前端会渲染提示）；
- 未观察到 case B（pypdf 抛异常 / preview 为空 → `file-metadata-placeholder`）—— 4 份样本均为文本层 PDF。该路径仍由 `app/services/literature.py:204-238` 的 try/except + `or _PDF_PARSE_RESULT_FALLBACK_PREVIEW` 兜底，行为契约不变。

## 已知 caveat（不阻 A5 收尾）

- **case A 的根因**：cn-ad-formula-002 的期刊年/卷/期数字字段在 PDF 中用嵌入子集字体表示，无 CMap → `\x00`。这是中文学术 PDF 的常见品质问题，不是 pypdf bug。当前 `quality_warning` 提示是合适的处理方式。
- **case C 未覆盖**：preview 看似正常但实际乱码（同形字 / CMap 错误映射）。当前缺 CJK density 启发式之外的检测；后续若上 PDF 质量 spike，建议加入 unigram 词频比对（与中文常用字表对照）。
- **case B（扫描件 / 图片型 PDF）未实测**：本批 4 份样本均为 text-layer。fallback 路径靠现有自动化测试（`backend/tests/test_upload_api.py`）覆盖；无新增风险。
- **CN density 阈值**：本次验收用 ≥ 30 作为"含可读中文"启发式，仅本 handoff 内的判定标准，未写入代码。

## 下一步（不在 A5 范围）

- PDF 质量启发式升级 spike（case C 检测）：归 B/C 阶段独立 slice，按需排
- OCR / 扫描件支持（case B 增强）：仍为深柜项，handoff-2026-06-03 已标注

## 复现说明

本验收用一次性脚本驱动：

```python
# 文件位置：backend/a5_verify.py（已删除，不入仓）
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
# upload → auto-parse → GET literature/{id} 三接口逐份跑
```

复现：

```bash
cd backend
.\.uv-test-venv\Scripts\python.exe a5_verify.py
# 结果写入 backend/a5_results.json（已删除，不入仓）
```

如需再复现，将 4 份 PDF 放回 `local-review-pdfs/`（gitignored），重建脚本，跑后清理。
