"""batch_pdf_ocr.py — 批量OCR扫描版PDF（PaddleOCR GPU）

为 backend/uploads/ 下扫描版PDF提取文本，输出到 data/runtime/ocr_results/。
当前 MVP-A 用 pypdf 文本抽取，扫描版回退占位符；此脚本为未来RAG语料扩充。

依赖安装（注意：脚本用 PaddleOCR 2.x API，3.x 改了参数名和返回结构，务必钉版本）：
  pip install "paddleocr>=2.7,<3" "paddlepaddle-gpu" pymupdf  # GPU版
  # 或 pip install "paddleocr>=2.7,<3" paddlepaddle pymupdf  # CPU版

Usage（GPU）：
  cd backend
  python scripts/batch_pdf_ocr.py --input-dir uploads --use-gpu

Usage（CPU）：
  cd backend
  python scripts/batch_pdf_ocr.py --input-dir uploads

输出：
  data/runtime/ocr_results/{pdf_filename}_ocr.json  — 每页OCR文本+置信度
  data/runtime/ocr_results/summary.json             — 汇总统计
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import fitz  # PyMuPDF
from paddleocr import PaddleOCR

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

OUTPUT_DIR = BACKEND_ROOT / "data" / "runtime" / "ocr_results"


def pdf_to_images(pdf_path: Path, dpi: int = 200):
    """将PDF每页转PIL Image"""
    doc = fitz.open(pdf_path)
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=matrix)
        img_data = pix.tobytes("png")
        yield page_num, img_data


def ocr_pdf(pdf_path: Path, ocr_engine, lang: str = "ch") -> dict:
    """OCR单个PDF，返回结果字典"""
    print(f"  [{pdf_path.name}] ", end="", flush=True)
    pages_result = []
    total_chars = 0

    for page_num, img_data in pdf_to_images(pdf_path):
        result = ocr_engine.ocr(img_data, cls=True)
        if not result or not result[0]:
            pages_result.append({"page": page_num + 1, "text": "", "lines": []})
            continue

        lines = []
        page_text = []
        for line in result[0]:
            text = line[1][0]
            conf = line[1][1]
            lines.append({"text": text, "confidence": conf})
            page_text.append(text)
            total_chars += len(text)

        pages_result.append(
            {
                "page": page_num + 1,
                "text": "\n".join(page_text),
                "lines": lines,
            }
        )

    print(f"{len(pages_result)}页, {total_chars}字符")

    return {
        "pdf_path": str(pdf_path.name),
        "page_count": len(pages_result),
        "total_chars": total_chars,
        "ocr_at": datetime.now(timezone.utc).isoformat(),  # noqa: UP017 (Python 3.10 compat)
        "pages": pages_result,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="uploads", help="PDF目录")
    parser.add_argument("--use-gpu", action="store_true", help="启用GPU")
    parser.add_argument("--lang", default="ch", help="ch/en/chinese_cht")
    parser.add_argument("--dpi", type=int, default=200, help="PDF转图DPI")
    args = parser.parse_args()

    input_dir = BACKEND_ROOT / args.input_dir
    if not input_dir.exists():
        print(f"❌ 目录不存在: {input_dir}")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[1/3] 初始化PaddleOCR (GPU={args.use_gpu}, lang={args.lang})...")
    ocr = PaddleOCR(use_angle_cls=True, lang=args.lang, use_gpu=args.use_gpu, show_log=False)

    print(f"[2/3] 扫描PDF: {input_dir}")
    pdfs = list(input_dir.glob("*.pdf"))
    if not pdfs:
        print("  未找到PDF文件")
        return
    print(f"  找到 {len(pdfs)} 个PDF")

    print("[3/3] 批量OCR...")
    results = []
    for pdf_path in pdfs:
        try:
            ocr_result = ocr_pdf(pdf_path, ocr, args.lang)
            out_file = OUTPUT_DIR / f"{pdf_path.stem}_ocr.json"
            out_file.write_text(
                json.dumps(ocr_result, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            results.append(
                {
                    "pdf": pdf_path.name,
                    "page_count": ocr_result["page_count"],
                    "total_chars": ocr_result["total_chars"],
                    "output_file": out_file.name,
                }
            )
        except Exception as e:
            print(f"  ❌ 失败: {e}")
            results.append({"pdf": pdf_path.name, "error": str(e)})

    summary_path = OUTPUT_DIR / "summary.json"
    summary = {
        "total_pdfs": len(pdfs),
        "success_count": sum(1 for r in results if "error" not in r),
        "processed_at": datetime.now(timezone.utc).isoformat(),  # noqa: UP017 (Python 3.10 compat)
        "results": results,
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n✅ 完成！{summary['success_count']}/{len(pdfs)} 成功")
    print(f"   输出: {OUTPUT_DIR}")
    print(f"   汇总: {summary_path.name}")


if __name__ == "__main__":
    main()
