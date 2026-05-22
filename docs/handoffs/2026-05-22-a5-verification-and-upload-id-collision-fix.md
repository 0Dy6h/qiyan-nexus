# A5 验收 + 两个 data-hygiene 修（2026-05-22）

## A5 主结论：PASS

3 个真实中文文本型 PDF 全部走通 `pypdf-text-preview` 路径，中文字符无乱码（无 `???` / `���`），RAG 链路可引用。Phase A 验收口径成立。

### 验收样本

| PDF | extraction_method | 中文可读性 | 备注 |
|---|---|---|---|
| 除湿糊剂治疗特应性皮炎...王琼.pdf | `pypdf-text-preview` ✓ | 流畅 ✓ | 标准单栏排版 |
| 滋阴除湿方治疗异位性皮炎43例...孙剑虹.pdf | `pypdf-text-preview` ✓ | **字序错乱** ⚠ | 双栏 PDF，pypdf 抽取顺序限制；字符本身未乱码 |
| 中医内外合治特应性皮炎...刘汉长.pdf | `pypdf-text-preview` ✓ | 可读（字间多余空格） ✓ | 字符位置布局型 PDF |

### 已知 limitation（不在本 slice 修）

- **双栏 PDF 抽取错乱**：pypdf 默认按 PDF 字符位置顺序输出，复杂排版可能丢失阅读顺序。这是 pypdf 限制，不是项目 bug。C 阶段引入 embedding 后影响减弱（向量检索对局部 token 不敏感）。

## 验收过程发现的两个真 bug（本 slice 一并修）

### Fix #1：纯中文文件名导致 upload ID 碰撞

**症状**：`build_pdf_upload_id` 的 slug 用 `re.sub(r"[^a-z0-9]+", "-", file_name.lower())` 过滤，把所有 CJK 字符替换成 `-`，剥掉后只剩 `pdf` 后缀。`除湿糊剂...王琼.pdf` 和 `中医内外合治...刘汉长.pdf` 挂到同一个 `literature_id` 上时生成完全相同的 `pdf-cn-ad-gbs-001-pdf`，磁盘文件 + runtime state 都被后者覆盖，前者数据丢失。

**修复**：当 slug 退化为空或仅 `pdf` 时，附加 `sha1(file_name)[:8]` 做去碰撞。ASCII 文件名行为不变（slug 不退化时不附加 hash），所有现有测试 fixture 不受影响。

**测试**：`tests/test_literature_service.py` 加 5 条
- ASCII slug 保持原形
- 纯中文 → ID 以 `pdf-{lit}-pdf-` 起头且后缀 8 位十六进制
- 两个不同中文文件名 → 不同 ID
- 同名重传 → ID 幂等
- 文件名无后缀 → 同样附 hash

### Fix #2：chunk 仓库写 seed file

**症状**：`InMemoryChunkRepository.upsert_uploaded_pdf_chunk` 直接写 `data/literature/sample_ad_chunks.json`——这是 git-tracked 的 seed 文件。每次上传 PDF 都 mutate 仓库追踪的固化数据。A5 三次上传把 seed 加了 4 条 `uploaded_pdf` chunk + 整文件重格式化。

**Root cause**：commit `c04d8de` 把 literature 仓库的 seed/runtime 切开了，但 chunk 仓库当时没有同步处理。

**修复**：在 `app/repositories/runtime_storage.py` 镜像加 `resolve_chunk_storage_path()`：env 覆盖 `CHUNK_RUNTIME_STATE_PATH`，默认落 `backend/data/runtime/chunk_state.json`，首次访问从 seed 二进制 bootstrap。`app/services/rag.py` 和 `app/services/fake_parser.py` 都改用 runtime 路径。

**测试**：`tests/test_runtime_storage.py` 加 3 条（mirror 既有 literature 路径测试）；`tests/test_upload_api.py` 5 处 `monkeypatch.setattr(fake_parser_service, "_CHUNK_DATA_PATH", ...)` 改为直接 monkeypatch `_CHUNK_REPOSITORY` 实例。

## 不在本 slice 范围

- chunk runtime state 的 GC / 清理策略（runtime 副本会随上传增长，没有自动回收）
- PDF 上传时按内容哈希查重（同一份 PDF 多次上传不同文件名仍会产生独立 chunk）
- 双栏 PDF 抽取顺序优化

## 验证

```bash
cd backend
.venv/bin/python -m ruff format --check app tests
.venv/bin/python -m ruff check app tests
.venv/bin/python -m mypy app
.venv/bin/python -m pytest -q
# 142 passed
```

Phase A 收尾的所有 6 颗 slice（A1 / A1.5 / A2 / A2.1 / A3 / A4 / A5 / A6）全部 done。A5 是最后一颗。

## 操作痕迹清理

- `git checkout backend/data/literature/sample_ad_chunks.json` 还原 seed（A5 上传污染）
- `rm -f backend/data/runtime/literature_state.json` 让 runtime 重新从 seed bootstrap
- `backend/uploads/*.pdf`（4 个 A5 实测 PDF）保留在磁盘（gitignored，不入仓）
