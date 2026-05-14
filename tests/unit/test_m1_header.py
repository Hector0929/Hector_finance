"""
Unit tests for M1 個股搜尋標頭 — 純邏輯函式
TDD Red 階段：先撰寫測試，再實作
"""

import pytest
from src.data.finlab_client import (
    format_volume,
    format_change,
    validate_stock_id,
    get_change_color,
)


class TestFormatVolume:
    """測試 format_volume(volume: int) -> str"""

    def test_zero(self):
        assert format_volume(0) == "0 張"

    def test_below_thousand(self):
        assert format_volume(999) == "999 張"

    def test_four_digits_with_comma(self):
        assert format_volume(1234) == "1,234 張"

    def test_exact_ten_thousand(self):
        assert format_volume(10000) == "1.0 萬張"

    def test_large_value(self):
        assert format_volume(123456) == "12.3 萬張"

    def test_boundary_9999(self):
        """9999 張仍以千分位顯示，不換算萬"""
        assert format_volume(9999) == "9,999 張"

    def test_boundary_10000_exact(self):
        """剛好 10000 張換算為 1.0 萬張"""
        assert format_volume(10000) == "1.0 萬張"

    def test_large_round(self):
        assert format_volume(50000) == "5.0 萬張"


class TestFormatChange:
    """測試 format_change(value: float, is_pct: bool = False) -> str"""

    def test_positive_value(self):
        assert format_change(1.5) == "+1.50"

    def test_positive_value_with_pct(self):
        assert format_change(1.5, is_pct=True) == "+1.50%"

    def test_negative_value(self):
        assert format_change(-2.3) == "-2.30"

    def test_negative_value_with_pct(self):
        assert format_change(-2.3, is_pct=True) == "-2.30%"

    def test_zero(self):
        assert format_change(0.0) == "0.00"

    def test_zero_with_pct(self):
        assert format_change(0.0, is_pct=True) == "0.00%"

    def test_positive_small(self):
        assert format_change(0.01) == "+0.01"

    def test_negative_small(self):
        assert format_change(-0.01) == "-0.01"

    def test_large_positive(self):
        assert format_change(100.0) == "+100.00"

    def test_large_negative(self):
        assert format_change(-10.55) == "-10.55"


class TestValidateStockId:
    """測試 validate_stock_id(stock_id: str) -> bool"""

    def test_valid_four_digits(self):
        assert validate_stock_id("2330") is True

    def test_valid_five_digits(self):
        assert validate_stock_id("00878") is True

    def test_empty_string(self):
        assert validate_stock_id("") is False

    def test_alpha_chars(self):
        assert validate_stock_id("abc") is False

    def test_mixed_alpha_digit(self):
        assert validate_stock_id("23A3") is False

    def test_three_digits(self):
        """3 位純數字也不合法（台股代號最少 4 碼）"""
        assert validate_stock_id("233") is False

    def test_six_digits_invalid(self):
        """6 位數字不合法"""
        assert validate_stock_id("123456") is False

    def test_spaces(self):
        """含空白不合法"""
        assert validate_stock_id("2330 ") is False

    def test_special_chars(self):
        assert validate_stock_id("23.3") is False

    def test_valid_four_zeros(self):
        assert validate_stock_id("0050") is True


class TestGetChangeColor:
    """測試 get_change_color(value: float) -> str（v2 Light Theme 色彩）"""

    def test_positive_value(self):
        assert get_change_color(1.0) == "#D92B2B"

    def test_negative_value(self):
        assert get_change_color(-1.0) == "#1A7F4B"

    def test_zero(self):
        assert get_change_color(0.0) == "#0A1628"

    def test_large_positive(self):
        assert get_change_color(100.0) == "#D92B2B"

    def test_large_negative(self):
        assert get_change_color(-100.0) == "#1A7F4B"

    def test_small_positive(self):
        assert get_change_color(0.001) == "#D92B2B"

    def test_small_negative(self):
        assert get_change_color(-0.001) == "#1A7F4B"
