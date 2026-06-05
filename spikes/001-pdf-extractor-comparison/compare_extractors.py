from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

QUALITY_WARNING_TEXT = "检测到抽取文本可能存在数字或表格乱码，请对照原始 PDF 核对关键数值。"

TERMS = [
    "特应性皮炎",
    "异位性皮炎",
    "瘙痒",
    "皮肤屏障",
    "临床",
    "中医",
    "治疗",
    "SCORAD",
    "EASI",
]


@dataclass(frozen=True)
class Sample:
    sample_id: str
    names: tuple[str, ...]
    expectation: str


SAMPLES = [
    Sample(
        sample_id="cn-ad-formula-002",
        names=(
            "中医辨证治疗异位性皮炎临床观察_周海啸.pdf",
            "pdf-cn-ad-formula-002-pdf-5ffc0e56.pdf",
        ),
        expectation="known embedded-font numeric garbling; current path should warn",
    ),
    Sample(
        sample_id="cn-ad-pruritus-005",
        names=(
            "中药健脾止痒颗粒合铍宝消炎癣湿药膏治疗特应性皮炎疗效分析_杨瑛 - 副本.pdf",
            "pdf-cn-ad-pruritus-005-pdf-99512ec5.pdf",
        ),
        expectation="clean text-layer sample",
    ),
    Sample(
        sample_id="cn-ad-barrier-006",
        names=(
            "健脾养血祛风法治疗特应性皮炎临床疗效及对皮肤屏障功能的影响_杨雪松.pdf",
            "pdf-cn-ad-barrier-006-pdf-2c576156.pdf",
        ),
        expectation="clean text-layer sample",
    ),
    Sample(
        sample_id="cn-ad-external-008",
        names=(
            "除湿糊剂治疗特应性皮炎的实验与临床观察_王琼 - 副本.pdf",
            "pdf-cn-ad-external-008-pdf-d28de853.pdf",
        ),
        expectation="clean text-layer sample",
    ),
]


def _configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def discover_sample_paths(sample_roots: list[Path]) -> dict[str, Path]:
    found: dict[str, Path] = {}
    for sample in SAMPLES:
        for root in sample_roots:
            for name in sample.names:
                candidate = root / name
                if candidate.exists():
                    found[sample.sample_id] = candidate
                    break
            if sample.sample_id in found:
                break
    return found


def serialize_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def current_nul_warning(text: str | None) -> str | None:
    if not text:
        return None
    nul_count = text.count("\x00")
    if nul_count >= 3 or (nul_count > 0 and nul_count / max(len(text), 1) >= 0.05):
        return QUALITY_WARNING_TEXT
    return None


def calculate_cjk_ratio(text: str) -> float:
    if not text:
        return 0.0
    cjk_count = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
    return cjk_count / len(text)


def condense_preview(text: str, max_chars: int = 36) -> str:
    normalized = re.sub(r"\s+", " ", text.replace("\x00", "[NUL]")).strip()
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 1] + "…"


def detect_spike_flags(text: str) -> list[str]:
    if not text:
        return ["empty_text"]
    flags: list[str] = []
    cid_count = len(re.findall(r"\(cid:\d+\)", text))
    replacement_count = text.count("\ufffd")
    if current_nul_warning(text):
        flags.append("nul_warning")
    if cid_count:
        flags.append("cid_tokens")
    if replacement_count:
        flags.append("replacement_chars")
    if len(text.strip()) < 120:
        flags.append("short_text")
    if calculate_cjk_ratio(text) < 0.15:
        flags.append("low_cjk_ratio")
    return flags


def extract_pypdf_full(path: Path) -> tuple[str, dict[str, Any]]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    return "\n".join(page for page in pages if page).strip(), {"pages": len(reader.pages)}


def extract_pypdf_middle_lines(path: Path) -> tuple[str, dict[str, Any]]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if not page_text:
            continue
        lines = page_text.split("\n")
        if len(lines) <= 3:
            parts.append(page_text.strip())
            continue
        skip_top_lines = max(1, int(len(lines) * 0.15))
        skip_bottom_lines = max(1, int(len(lines) * 0.15))
        filtered = "\n".join(lines[skip_top_lines : len(lines) - skip_bottom_lines]).strip()
        if filtered:
            parts.append(filtered)
    return "\n".join(parts).strip(), {"pages": len(reader.pages)}


def extract_pdfplumber_default(path: Path) -> tuple[str, dict[str, Any]]:
    import pdfplumber

    parts: list[str] = []
    table_count = 0
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            parts.append((page.extract_text() or "").strip())
            try:
                table_count += len(page.extract_tables() or [])
            except Exception:
                pass
        pages = len(pdf.pages)
    return "\n".join(part for part in parts if part).strip(), {
        "pages": pages,
        "tables_detected": table_count,
    }


def extract_pdfplumber_layout(path: Path) -> tuple[str, dict[str, Any]]:
    import pdfplumber

    parts: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            parts.append((page.extract_text(layout=True) or "").strip())
        pages = len(pdf.pages)
    return "\n".join(part for part in parts if part).strip(), {"pages": pages}


EXTRACTORS = {
    "pypdf_full": extract_pypdf_full,
    "pypdf_current_middle_lines": extract_pypdf_middle_lines,
    "pdfplumber_default": extract_pdfplumber_default,
    "pdfplumber_layout": extract_pdfplumber_layout,
}


def analyze_text(
    sample_id: str, extractor_name: str, text: str, meta: dict[str, Any]
) -> dict[str, Any]:
    nul_count = text.count("\x00")
    cid_count = len(re.findall(r"\(cid:\d+\)", text))
    replacement_count = text.count("\ufffd")
    term_hits = sorted(term for term in TERMS if term.lower() in text.lower())
    digest = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:12]
    return {
        "sample_id": sample_id,
        "extractor": extractor_name,
        "status": "ok",
        "chars": len(text),
        "nul_count": nul_count,
        "nul_ratio": round(nul_count / max(len(text), 1), 6),
        "cjk_ratio": round(calculate_cjk_ratio(text), 6),
        "cid_token_count": cid_count,
        "replacement_char_count": replacement_count,
        "term_hits": term_hits,
        "term_hit_count": len(term_hits),
        "current_quality_warning": current_nul_warning(text),
        "spike_flags": detect_spike_flags(text),
        "preview_digest": digest,
        "preview_sample": condense_preview(text),
        **meta,
    }


def analyze_sample(path: Path, sample_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for extractor_name, extractor in EXTRACTORS.items():
        started = time.perf_counter()
        try:
            text, meta = extractor(path)
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            rows.append(
                {
                    **analyze_text(sample_id, extractor_name, text, meta),
                    "elapsed_ms": elapsed_ms,
                }
            )
        except ModuleNotFoundError as exc:
            rows.append(
                {
                    "sample_id": sample_id,
                    "extractor": extractor_name,
                    "status": "missing_dependency",
                    "error": str(exc),
                }
            )
        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            rows.append(
                {
                    "sample_id": sample_id,
                    "extractor": extractor_name,
                    "status": "error",
                    "error": f"{type(exc).__name__}: {exc}",
                    "elapsed_ms": elapsed_ms,
                }
            )
    return rows


def package_versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for package in ["pypdf", "pdfplumber", "pdfminer.six"]:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return versions


def write_markdown(payload: dict[str, Any], output_path: Path) -> None:
    rows = payload["rows"]
    lines = [
        "# PDF Extractor Comparison Results",
        "",
        f"Generated: {payload['generated_at']}",
        "",
        "## Environment",
        "",
        "| Package | Version |",
        "|---|---|",
    ]
    for package, version in payload["package_versions"].items():
        lines.append(f"| {package} | {version or 'not installed'} |")
    lines.extend(
        [
            "",
            "## Samples",
            "",
            "| Sample | Source File | Expectation |",
            "|---|---|---|",
        ]
    )
    for sample in SAMPLES:
        path = payload["sample_paths"].get(sample.sample_id)
        lines.append(
            f"| {sample.sample_id} | {Path(path).name if path else 'missing'} | {sample.expectation} |"
        )
    lines.extend(
        [
            "",
            "## Metrics",
            "",
            "| Sample | Extractor | Chars | NUL | NUL % | CJK % | CID | Terms | Current warning | Flags | ms |",
            "|---|---|---:|---:|---:|---:|---:|---:|---|---|---:|",
        ]
    )
    for row in rows:
        if row["status"] != "ok":
            lines.append(
                f"| {row['sample_id']} | {row['extractor']} | - | - | - | - | - | - | {row['status']} | {row.get('error', '')} | {row.get('elapsed_ms', '-')} |"
            )
            continue
        warning = "yes" if row["current_quality_warning"] else "no"
        flags = ", ".join(row["spike_flags"]) if row["spike_flags"] else "none"
        lines.append(
            f"| {row['sample_id']} | {row['extractor']} | {row['chars']} | {row['nul_count']} | {row['nul_ratio'] * 100:.2f} | {row['cjk_ratio'] * 100:.2f} | {row['cid_token_count']} | {row['term_hit_count']} | {warning} | {flags} | {row.get('elapsed_ms', 0):.2f} |"
        )
    lines.extend(
        [
            "",
            "## Short Preview Samples",
            "",
            "Short preview samples are intentionally capped to avoid committing article-scale extracted text.",
            "",
            "| Sample | Extractor | Preview sample | Digest |",
            "|---|---|---|---|",
        ]
    )
    for row in rows:
        if row["status"] == "ok":
            preview = row["preview_sample"].replace("|", "\\|")
            lines.append(
                f"| {row['sample_id']} | {row['extractor']} | {preview} | {row['preview_digest']} |"
            )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare pypdf and pdfplumber extraction on A5 PDFs."
    )
    parser.add_argument(
        "--sample-root",
        action="append",
        type=Path,
        help="Directory containing A5 PDFs. May be passed multiple times.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "results",
        help="Directory for JSON and Markdown results.",
    )
    return parser.parse_args()


def main() -> int:
    _configure_stdout()
    args = parse_args()
    root = repo_root()
    sample_roots = args.sample_root or [
        root / "local-review-pdfs",
        root / "backend" / "uploads",
    ]
    sample_roots = [path.resolve() for path in sample_roots]
    sample_paths = discover_sample_paths(sample_roots)
    rows: list[dict[str, Any]] = []
    for sample in SAMPLES:
        path = sample_paths.get(sample.sample_id)
        if path is None:
            rows.append(
                {
                    "sample_id": sample.sample_id,
                    "extractor": "all",
                    "status": "missing_sample",
                    "error": "sample PDF not found",
                }
            )
            continue
        rows.extend(analyze_sample(path, sample.sample_id))

    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "sample_roots": [serialize_path(path, root) for path in sample_roots],
        "sample_paths": {key: serialize_path(value, root) for key, value in sample_paths.items()},
        "package_versions": package_versions(),
        "rows": rows,
    }

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "pdf_extractor_comparison.json"
    md_path = output_dir / "pdf_extractor_comparison.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(payload, md_path)

    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    ok_rows = [row for row in rows if row["status"] == "ok"]
    warning_rows = [row for row in ok_rows if row["current_quality_warning"]]
    print(
        f"Analyzed {len(ok_rows)} extractor/sample rows; current warning rows: {len(warning_rows)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
