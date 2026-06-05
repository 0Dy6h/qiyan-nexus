"""Unit tests for PDF quality helper functions."""

import pytest
from pypdf import PdfReader

from app.services.literature import (
    _calculate_cjk_ratio,
    _detect_low_text_density,
    _filter_header_footer_pages,
    detect_pdf_text_quality_warning,
)


class TestCalculateCjkRatio:
    """Test CJK character density calculation."""

    def test_empty_string(self):
        assert _calculate_cjk_ratio("") == 0.0

    def test_pure_chinese(self):
        text = "这是一段中文文本"
        assert _calculate_cjk_ratio(text) == 1.0

    def test_pure_english(self):
        text = "This is English text"
        assert _calculate_cjk_ratio(text) == 0.0

    def test_mixed_chinese_english(self):
        text = "特应性皮炎 atopic dermatitis"
        # 5 Chinese chars out of ~27 total chars (including spaces)
        ratio = _calculate_cjk_ratio(text)
        assert 0.1 < ratio < 0.3  # Approximately 18.5%

    def test_chinese_with_numbers_and_punctuation(self):
        text = "中国中医药信息杂志2024年第31卷第10期"
        # Should count only CJK characters, not digits
        ratio = _calculate_cjk_ratio(text)
        assert ratio > 0.5  # Majority is Chinese

    def test_japanese_kanji(self):
        # Japanese Kanji are also in CJK range
        text = "漢字テキスト"
        ratio = _calculate_cjk_ratio(text)
        assert ratio > 0.0  # Contains CJK characters


class TestDetectLowTextDensity:
    """Test low text density detection (tables/formulas)."""

    def test_empty_string(self):
        assert _detect_low_text_density("") is False

    def test_short_string(self):
        # Strings < 10 chars always return False
        assert _detect_low_text_density("abc") is False
        assert _detect_low_text_density("....") is False

    def test_normal_text_high_density(self):
        text = "This is normal text with good alphanumeric density."
        assert _detect_low_text_density(text) is False

    def test_chinese_text_high_density(self):
        text = "这是正常的中文文本，具有良好的字母数字密度。"
        # Chinese characters count as alphanumeric
        assert _detect_low_text_density(text) is False

    def test_mostly_punctuation_low_density(self):
        text = "... --- ... === ||| *** "
        # <20% alphanumeric
        assert _detect_low_text_density(text) is True

    def test_table_like_content(self):
        # Table with mostly separators
        text = "| --- | --- | --- | --- |"
        assert _detect_low_text_density(text) is True

    def test_formula_like_content(self):
        # Math symbols and spaces
        text = "∑ ∫ ∂ ≈ ≠ ± ∞ √ π "
        # Most characters are not alphanumeric
        assert _detect_low_text_density(text) is True

    def test_mixed_content_borderline(self):
        # 20% is the threshold
        text = "ab" + "." * 8  # 2 alphanumeric, 8 dots = 20%
        # Should be False (not strictly less than 20%)
        assert _detect_low_text_density(text) is False

        text = "a" + "." * 9  # 1 alphanumeric, 9 dots = 10%
        # Should be True (< 20%)
        assert _detect_low_text_density(text) is True


class TestDetectPdfTextQualityWarning:
    """Test PDF text quality warning detection."""

    def test_none_input(self):
        assert detect_pdf_text_quality_warning(None) is None

    def test_clean_text_no_nul_bytes(self):
        text = "This is clean text without any NUL bytes."
        assert detect_pdf_text_quality_warning(text) is None

    def test_one_nul_byte_below_threshold(self):
        # Use enough length so 1/len stays below the 5% ratio threshold
        text = "Clean text without issues " + "x" * 20 + "\x00"
        assert detect_pdf_text_quality_warning(text) is None

    def test_two_nul_bytes_below_threshold(self):
        # 2 NUL bytes with ratio below 5% and absolute count below 3
        text = "Some text without NUL problems " + "y" * 30 + "\x00mid\x00"
        assert detect_pdf_text_quality_warning(text) is None

    def test_three_nul_bytes_triggers_warning(self):
        text = "Text\x00with\x00three\x00NULs"
        # 3 NUL bytes triggers absolute minimum
        warning = detect_pdf_text_quality_warning(text)
        assert warning is not None
        assert "乱码" in warning

    def test_high_nul_ratio_triggers_warning(self):
        # 5% threshold: 1 NUL in 20 chars
        text = "a" * 19 + "\x00"
        # 1/20 = 5% exactly, should trigger
        warning = detect_pdf_text_quality_warning(text)
        assert warning is not None

    def test_below_5_percent_threshold(self):
        # 4% should not trigger
        text = "a" * 24 + "\x00"
        # 1/25 = 4%
        assert detect_pdf_text_quality_warning(text) is None

    def test_real_world_scenario_cn_ad_formula_002(self):
        # Simulating the cn-ad-formula-002 sample
        # After header filtering, expect <5% NUL ratio
        text = "特应性皮炎的中药治疗方案研究" + "\x00" * 2  # 2 NULs in ~30 chars = 6.7%
        warning = detect_pdf_text_quality_warning(text)
        assert warning is not None  # Should still trigger

        # After better filtering, expect cleaner
        text = "特应性皮炎的中药治疗方案研究分析" * 10  # ~150 chars
        text += "\x00" * 3  # 3 NULs in ~153 = 1.96%, but absolute count >=3
        warning = detect_pdf_text_quality_warning(text)
        assert warning is not None  # Triggered by absolute count

    def test_improved_tolerance_from_2_to_5_percent(self):
        # Old threshold was 2%, new is 5%
        # Test case: 3% NUL ratio should NOT trigger
        text = "a" * 97 + "\x00" * 3  # 3/100 = 3%
        warning = detect_pdf_text_quality_warning(text)
        assert warning is not None  # Still triggers due to >=3 absolute count

        # But with fewer than 3 NULs and <5%, should pass
        text = "a" * 98 + "\x00" * 2  # 2/100 = 2%
        warning = detect_pdf_text_quality_warning(text)
        assert warning is None  # Below both thresholds


class TestFilterHeaderFooterPages:
    """Test header/footer filtering from PDF pages.

    Note: These tests require mock PdfReader objects or real PDF files.
    For now, we test the logic indirectly through integration tests.
    """

    def test_basic_filtering_logic(self):
        # This is more of an integration test
        # We'll validate it with real PDFs in the next phase
        # For now, just ensure the function exists and has correct signature
        from inspect import signature

        sig = signature(_filter_header_footer_pages)
        params = list(sig.parameters.keys())
        assert "reader" in params
        assert "skip_top_ratio" in params
        assert "skip_bottom_ratio" in params

        # Verify default values
        assert sig.parameters["skip_top_ratio"].default == 0.15
        assert sig.parameters["skip_bottom_ratio"].default == 0.15
