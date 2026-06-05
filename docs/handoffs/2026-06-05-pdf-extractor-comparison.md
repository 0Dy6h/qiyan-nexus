# PDF 抽取器对比 handoff — 2026-06-05

## 背景

承接 `docs/evaluations/2026-06-05-pdf-quality-spike.md`：前一阶段已完成 pypdf 启发式增强、A5 四份中文 PDF 复测与结论，但 Phase 4 的 `pdfplumber` 对照当时因时间盒跳过。本 handoff 记录补跑结果，避免后续再次重复同一个 spike。

## 本轮新增

- 新增独立 spike 目录：`spikes/001-pdf-extractor-comparison/`
- 新增对比脚本：`spikes/001-pdf-extractor-comparison/compare_extractors.py`
- 新增结果文件：
  - `spikes/001-pdf-extractor-comparison/results/pdf_extractor_comparison.json`
  - `spikes/001-pdf-extractor-comparison/results/pdf_extractor_comparison.md`
- 更新评估文档：`docs/evaluations/2026-06-05-pdf-quality-spike.md`

脚本只读取 gitignored 的 `local-review-pdfs/` / `backend/uploads/` 样本，只输出指标、短 preview 与 hash，不提交原始 PDF 或大段正文。

## 运行命令

```powershell
uv run --with pypdf==6.12.2 --with pdfplumber python .\spikes\001-pdf-extractor-comparison\compare_extractors.py
```

该命令用 `uv` 临时依赖环境安装 `pdfplumber`，没有把 `pdfplumber` 写入 `backend/pyproject.toml`，也没有改默认后端依赖。

## 核心结果

| 样本 | 抽取器 | 字符数 | NUL 数 | NUL 比例 | CJK 比例 | 当前 warning |
|---|---|---:|---:|---:|---:|---|
| cn-ad-formula-002 | pypdf_full | 6249 | 805 | 12.88% | 42.87% | yes |
| cn-ad-formula-002 | pypdf_current_middle_lines | 4084 | 596 | 14.59% | 40.52% | yes |
| cn-ad-formula-002 | pdfplumber_default | 4431 | 805 | 18.17% | 60.46% | yes |
| cn-ad-formula-002 | pdfplumber_layout | 9858 | 805 | 8.17% | 27.18% | yes |
| cn-ad-pruritus-005 | pdfplumber_default | 7359 | 0 | 0.00% | 41.79% | no |
| cn-ad-barrier-006 | pdfplumber_default | 10242 | 0 | 0.00% | 30.83% | no |
| cn-ad-external-008 | pdfplumber_default | 5312 | 0 | 0.00% | 59.05% | no |

## 判定

**Verdict: PARTIAL**

- `pdfplumber` 能抽取 4/4 样本，3 份干净样本没有新增 warning。
- `pdfplumber` 没有解决 `cn-ad-formula-002` 的嵌入字体 NUL 问题；`pdfplumber_default` NUL 比例反而更高，`pdfplumber_layout` 只是靠文本膨胀稀释比例，原始 NUL 数仍为 805。
- `pdfplumber_layout` 会显著膨胀文本并稀释 CJK 比例，对默认 preview/RAG chunk 路径不是净收益。

## 决策

不把 `pdfplumber` 引入默认后端依赖，不替换当前 `pypdf` 路径。

当前推荐保持：

- 文本型 PDF：`pypdf` text-layer preview
- 可疑嵌入字体/数字乱码：保留 `quality_warning`
- 扫描件/OCR：仍不进入默认内部预览路径，未来按独立 spike 评估

后续如果继续小步改善 PDF 体验，优先考虑 **preview-window 选择**，例如优先摘要/标题/正文样式行，避免 preview 起始落到参考文献、材料方法碎片或页眉页脚；这比替换解码器更贴近当前问题。

## 验证

已跑：

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m pytest tests\test_pdf_quality_helpers.py tests\test_upload_api.py -q
```

结果：`39 passed in 2.39s`。
