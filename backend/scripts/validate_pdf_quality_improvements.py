"""Validate PDF quality improvements on A5 samples.

This script tests the PDF quality improvements on real Chinese AD literature PDFs
and compares before/after metrics.

Usage:
    python -m scripts.validate_pdf_quality_improvements
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.literature import (
    _calculate_cjk_ratio,
    _detect_low_text_density,
    detect_pdf_text_quality_warning,
    extract_pdf_preview_text,
)


def analyze_pdf_quality(pdf_path: Path) -> dict:
    """Analyze PDF extraction quality metrics.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Dictionary with quality metrics
    """
    preview_text = extract_pdf_preview_text(pdf_path, max_chars=500)

    if preview_text is None:
        return {
            "file": pdf_path.name,
            "status": "extraction_failed",
            "preview_length": 0,
            "nul_count": 0,
            "nul_ratio": 0.0,
            "cjk_ratio": 0.0,
            "low_text_density": False,
            "quality_warning": None,
        }

    nul_count = preview_text.count("\x00")
    nul_ratio = nul_count / max(len(preview_text), 1)
    cjk_ratio = _calculate_cjk_ratio(preview_text)
    low_text_density = _detect_low_text_density(preview_text)
    quality_warning = detect_pdf_text_quality_warning(preview_text)

    return {
        "file": pdf_path.name,
        "status": "success",
        "preview_length": len(preview_text),
        "nul_count": nul_count,
        "nul_ratio": nul_ratio,
        "nul_ratio_percent": f"{nul_ratio * 100:.2f}%",
        "cjk_ratio": cjk_ratio,
        "cjk_ratio_percent": f"{cjk_ratio * 100:.2f}%",
        "low_text_density": low_text_density,
        "quality_warning": quality_warning,
        "preview_snippet": preview_text[:100].replace("\x00", "[NUL]"),
    }


def _configure_stdout() -> None:
    """Use UTF-8 on Windows consoles so preview snippets with NUL/garbled bytes print safely."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    """Run validation on A5 PDF samples."""
    _configure_stdout()

    # A5 samples (4 real Chinese AD PDFs from 2026-06-04 verification)
    upload_dir = Path(__file__).parent.parent / "uploads"

    # Canonical A5 samples from docs/handoffs/2026-06-04-a5-chinese-pdf-verification.md
    a5_samples = [
        "pdf-cn-ad-formula-002-pdf-5ffc0e56.pdf",  # Known problem: ~14% NUL ratio (embedded font)
        "pdf-cn-ad-pruritus-005-pdf-99512ec5.pdf",  # Expected clean
        "pdf-cn-ad-barrier-006-pdf-2c576156.pdf",  # Expected clean
        "pdf-cn-ad-external-008-pdf-d28de853.pdf",  # Expected clean
    ]

    print("=" * 80)
    print("PDF Quality Validation - A5 Chinese AD Literature Samples")
    print("=" * 80)
    print()

    results = []
    for sample_name in a5_samples:
        pdf_path = upload_dir / sample_name
        if not pdf_path.exists():
            print(f"⊘ SKIP: {sample_name} (not found)")
            continue

        print(f"Analyzing: {sample_name}")
        result = analyze_pdf_quality(pdf_path)
        results.append(result)

        # Print summary
        print(f"  Status: {result['status']}")
        if result["status"] == "success":
            print(f"  Preview length: {result['preview_length']} chars")
            print(f"  NUL bytes: {result['nul_count']} ({result['nul_ratio_percent']})")
            print(f"  CJK ratio: {result['cjk_ratio_percent']}")
            print(f"  Low text density: {result['low_text_density']}")
            print(f"  Quality warning: {'YES' if result['quality_warning'] else 'NO'}")
            print(f"  Preview snippet: {result['preview_snippet']}")
        print()

    # Summary statistics
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    success_results = [r for r in results if r["status"] == "success"]
    if not success_results:
        print("No successful extractions.")
        return

    print(f"Total samples: {len(results)}")
    print(f"Successful extractions: {len(success_results)}")
    print()

    # Calculate aggregate metrics
    avg_nul_ratio = sum(r["nul_ratio"] for r in success_results) / len(success_results)
    avg_cjk_ratio = sum(r["cjk_ratio"] for r in success_results) / len(success_results)
    quality_warning_count = sum(1 for r in success_results if r["quality_warning"])

    print(f"Average NUL ratio: {avg_nul_ratio * 100:.2f}%")
    print(f"Average CJK ratio: {avg_cjk_ratio * 100:.2f}%")
    print(f"Quality warnings triggered: {quality_warning_count}/{len(success_results)}")
    print()

    # Expected results (from spike document)
    print("=" * 80)
    print("EXPECTED RESULTS (from spike)")
    print("=" * 80)
    print("✅ cn-ad-formula-002: NUL ratio from 14% → <5% (after header filtering)")
    print("✅ Other 3 samples: maintain clean extraction (0 regression)")
    print()

    # Check if expectations are met
    print("=" * 80)
    print("VALIDATION")
    print("=" * 80)

    formula_002_result = next(
        (r for r in success_results if "formula-002" in r["file"]), None
    )
    if formula_002_result:
        nul_ratio = formula_002_result["nul_ratio"]
        if nul_ratio < 0.05:
            print(f"✅ PASS: cn-ad-formula-002 NUL ratio is {nul_ratio * 100:.2f}% (<5%)")
        else:
            print(
                f"⚠️ FAIL: cn-ad-formula-002 NUL ratio is {nul_ratio * 100:.2f}% (≥5%)"
            )
    else:
        print("⊘ SKIP: cn-ad-formula-002 not found")

    # Check other samples for regression
    other_samples = [r for r in success_results if "formula-002" not in r["file"]]
    regression_count = sum(1 for r in other_samples if r["quality_warning"])
    if regression_count == 0:
        print(f"✅ PASS: No regressions in other {len(other_samples)} samples")
    else:
        print(
            f"⚠️ FAIL: {regression_count} regressions detected in other samples"
        )

    print()
    print("=" * 80)
    print("Validation complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
