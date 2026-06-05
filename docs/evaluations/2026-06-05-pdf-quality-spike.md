# PDF 抽取质量改进 Spike — 2026-06-05

date: 2026-06-05  
status: in_progress  
time_box: 4-8 hours

---

## 目标

改善 pypdf 文本抽取质量，降低 `quality_warning` fallback 比例，提升用户体验。

## 背景

### 当前实现

**文件**：`backend/app/services/literature.py`

**抽取逻辑**：
```python
def extract_pdf_preview_text(storage_path: Path, max_chars: int = 300) -> str | None:
    try:
        reader = PdfReader(str(storage_path))
        text = "\n".join((page.extract_text() or "").strip() for page in reader.pages).strip()
    except Exception:
        return None
    if not text:
        return None
    return text[:max_chars]
```

**质量检测**：
```python
def detect_pdf_text_quality_warning(preview_text: str | None) -> str | None:
    if not preview_text:
        return None
    nul_count = preview_text.count("\x00")
    if nul_count >= 3 or (nul_count > 0 and nul_count / max(len(preview_text), 1) >= 0.02):
        return _PDF_TEXT_QUALITY_WARNING
    return None
```

### A5 验收结果（2026-06-04）

4 份真实中文 AD 文献 PDF：
- ✅ **3/4 干净抽取**（0 个 `\x00`，中文完整）
- ⚠️ **1/4 触发 quality_warning**（42 个 `\x00`，占比 14%，期刊数字字段乱码）

**问题分析**（样本 1：cn-ad-formula-002）：
```
中国 中医 药信 息 杂志 \x00\x00\x00\x00年 第 \x00卷 第 \x00\x00 期 ...
```
- 标题、作者可读
- 期刊年/卷/期字段被 PDF 嵌入字体表示为不可解码字符 → `\x00` 填充
- 这是 **PDF 制作方式问题**（嵌入字体子集缺失字符映射），不是 pypdf bug

---

## Spike 范围

### ✅ 包含（In Scope）

1. **质量启发式改进**
   - 检测并跳过表格区域（避免乱码混入正文）
   - 检测并过滤页眉页脚（期刊信息、页码）
   - 检测并过滤公式/数学符号区域（LaTeX 残留）
   - 改进 `\x00` 检测阈值（当前 2% 可能过于宽松）
   - 增加中文字符密度检测（preview 中 CJK 比例）

2. **备选库评估**（可选）
   - `pdfplumber`：更好的表格检测与文本布局分析
   - 对比 pypdf vs pdfplumber 在 A5 的 4 份样本上的抽取质量
   - **不评估** PyMuPDF (fitz)：AGPL 许可证，不适合商业项目

3. **测试数据验证**
   - 重新测试 A5 的 4 份样本
   - 记录改进前后的质量指标（`\x00` 数、CJK 密度、quality_warning 触发率）

### ❌ 不包含（Out of Scope）

- ❌ OCR（Tesseract/PaddleOCR）：扫描件 PDF，需要独立 spike
- ❌ 表格结构化解析：需要专门的表格理解模型
- ❌ 公式解析（LaTeX/MathML）：超出文本抽取范围
- ❌ 修改 PDF 上传/解析 API 契约
- ❌ 修改前端 UI（只优化后端质量检测）

---

## 问题诊断

### 问题 1：嵌入字体字符映射缺失（cn-ad-formula-002 根因）

**现象**：
- 期刊元信息（年/卷/期）显示为 `\x00`
- 正文标题、作者正常

**根因**：
- PDF 制作方使用嵌入字体子集，仅包含部分字符的映射表
- pypdf 无法将字体 glyph 反向映射为 Unicode 字符 → 返回 `\x00`

**可行性改进**：
- ✅ **跳过页眉区域**：期刊元信息通常在页面顶部 10-15% 区域
- ✅ **提高 `\x00` 容忍度**：将阈值从 2% 提高到 5%（允许少量元信息乱码）
- ❌ **修复字体映射**：需要解析 PDF 内部 CMap 表，pypdf 不支持，PyMuPDF 可以但许可证问题

### 问题 2：表格数据混入正文（潜在问题）

**现象**（A5 未出现，但已知风险）：
- 表格单元格按 PDF 内部顺序提取，可能打乱句子
- 数字列可能被误认为正文数字

**可行性改进**：
- ✅ **检测表格区域**：pdfplumber 提供 `extract_tables()` API
- ✅ **跳过低文本密度区域**：连续数字/短单词（<3 字符）占比 >80% 视为非正文

### 问题 3：页眉页脚混入 preview（已知风险）

**现象**：
- 每页顶部/底部的期刊名、页码混入 preview
- 影响前 300 字符的可读性

**可行性改进**：
- ✅ **检测重复文本**：相同字符串出现在多页 → 视为页眉页脚
- ✅ **位置启发式**：页面顶部 10% 或底部 10% → 跳过
- ✅ **数字模式**：单独的 `1`, `2`, `3` 等 → 页码，跳过

---

## 改进方案

### 方案 A：增强 pypdf 启发式（优先，低风险）

**改进点**：
1. **页眉页脚过滤**
   ```python
   def filter_header_footer(pages: list[PageObject]) -> str:
       # 只提取页面中部 20%-80% 区域的文本
       # 跳过顶部 20% 和底部 20%
   ```

2. **提高 `\x00` 容忍度**
   ```python
   # 从 2% 提高到 5%
   if nul_count >= 3 or (nul_count > 0 and nul_count / max(len(preview_text), 1) >= 0.05):
   ```

3. **低文本密度区域检测**
   ```python
   def detect_low_text_density(text: str) -> bool:
       # 连续数字/标点符号 >80% → 可能是表格
       alphanumeric = sum(c.isalnum() for c in text)
       if alphanumeric / max(len(text), 1) < 0.2:
           return True
   ```

4. **中文密度检测**
   ```python
   def calculate_cjk_ratio(text: str) -> float:
       cjk_count = sum('一' <= c <= '鿿' for c in text)
       return cjk_count / max(len(text), 1)
   
   # 如果 CJK 密度 < 10% 且文档标记为中文 → quality_warning
   ```

**预期效果**：
- cn-ad-formula-002 样本：`\x00` 占比从 14% 降到 ~5%（跳过页眉后）
- 其他 3 份样本：保持干净抽取

### 方案 B：评估 pdfplumber（可选，中风险）

**对比测试**：
```python
# pypdf baseline
reader = PdfReader(path)
text_pypdf = "\n".join(page.extract_text() or "" for page in reader.pages)

# pdfplumber
import pdfplumber
with pdfplumber.open(path) as pdf:
    text_pdfplumber = "\n".join(page.extract_text() or "" for page in pdf.pages)

# 对比指标
- \x00 数量
- CJK 密度
- 可读性主观评分（1-5 分）
```

**依赖添加**：
```toml
[project.optional-dependencies]
pdf_quality = [
    "pdfplumber>=0.10.0",
]
```

**风险**：
- pdfplumber 依赖 Pillow + pdfminer.six，包体积较大
- 可能引入新的边缘 case

---

## 实施计划

### Phase 1: 审计与设计（已完成）

- [x] 审计现有 PDF 解析逻辑
- [x] 分析 A5 验收结果
- [x] 设计改进方案

### Phase 2: 实现方案 A（预计 2 小时）

- [ ] 实现 `filter_header_footer()` 函数
- [ ] 调整 `\x00` 容忍度到 5%
- [ ] 实现 `calculate_cjk_ratio()` 函数
- [ ] 实现 `detect_low_text_density()` 函数
- [ ] 更新 `extract_pdf_preview_text()` 集成以上改进
- [ ] 单元测试（至少 3 个测试用例）

### Phase 3: 验证（预计 1 小时）

- [ ] 用 A5 的 4 份样本重新测试
- [ ] 记录改进前后的质量指标
- [ ] 确认没有引入新的 regression

### Phase 4: 可选 - pdfplumber 对比（预计 2 小时）

- [ ] 安装 pdfplumber
- [ ] 实现对比测试脚本
- [ ] 记录两种方案的优劣
- [ ] 推荐决策

### Phase 5: 结论（预计 30 分钟）

- [ ] 编写 spike 结论文档
- [ ] 推荐是否采纳改进
- [ ] 记录遗留问题

---

## 预期结果

### 成功标准

- ✅ cn-ad-formula-002 样本的 `\x00` 占比从 14% 降到 <5%
- ✅ 其他 3 份样本保持干净抽取（0 regression）
- ✅ 代码改动 <100 行（保持简单）
- ✅ 不引入新的外部依赖（方案 A）

### 决策标准

**采纳改进**如果：
- 方案 A 降低 quality_warning 触发率 >30%
- 没有引入新的 regression
- 代码复杂度可接受

**保持现状**如果：
- 改进效果不显著（<20% 改善）
- 引入新的 regression
- 复杂度过高（>200 行代码）

---

## 实际结果

（待填写）

---

**时间盒提醒**：如果 Phase 2 结束时已超过 3 小时，跳过 Phase 4（pdfplumber 对比），直接进入 Phase 5 记录结论。
