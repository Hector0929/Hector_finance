"""
test_screener.py — M10 條件篩選單元測試

TDD：測試先行，覆蓋 run_screener 與 format_screener_message 的核心行為。
"""

import numpy as np
import pandas as pd
import pytest

from src.screener.filter import format_screener_message, run_screener


class TestRunScreener:
    """run_screener() 的單元測試。"""

    def test_returns_list(self, sample_price_volume):
        """基本呼叫應回傳 list。"""
        price_df, volume_df = sample_price_volume
        result = run_screener(price_df, volume_df)
        assert isinstance(result, list)

    def test_volume_filter(self, sample_price_volume):
        """min_volume 設極大值，應回傳空列表。"""
        price_df, volume_df = sample_price_volume
        result = run_screener(price_df, volume_df, min_volume=9_999_999)
        assert result == []

    def test_change_pct_filter(self, sample_price_volume):
        """
        強制所有股票最新一日為下跌（change_pct < 0），
        min_change_pct=0 → 不符合 >= 0，應回傳空列表。
        """
        price_df, volume_df = sample_price_volume
        # 壓低最後一列，使所有漲跌幅為負
        price_df = price_df.copy()
        price_df.iloc[-1] = price_df.iloc[-2] * 0.80  # 跌 20%
        result = run_screener(
            price_df, volume_df, min_change_pct=0.0, max_change_pct=10.0
        )
        assert result == []

    def test_result_fields(self, sample_price_volume):
        """結果每筆必須包含 stock_id, close, change_pct, volume 四個欄位。"""
        price_df, volume_df = sample_price_volume
        # 放寬條件確保有結果
        result = run_screener(
            price_df, volume_df, min_volume=0, min_change_pct=-100.0, max_change_pct=100.0
        )
        assert len(result) > 0, "放寬條件後應有結果"
        for item in result:
            assert "stock_id" in item
            assert "close" in item
            assert "change_pct" in item
            assert "volume" in item

    def test_result_field_types(self, sample_price_volume):
        """結果欄位型別正確：stock_id=str, close=float, change_pct=float, volume=int。"""
        price_df, volume_df = sample_price_volume
        result = run_screener(
            price_df, volume_df, min_volume=0, min_change_pct=-100.0, max_change_pct=100.0
        )
        assert len(result) > 0
        for item in result:
            assert isinstance(item["stock_id"], str)
            assert isinstance(item["close"], float)
            assert isinstance(item["change_pct"], float)
            assert isinstance(item["volume"], int)

    def test_empty_price_df_returns_empty(self):
        """price_df 為空 DataFrame → 回傳 []，不拋出例外。"""
        price_df = pd.DataFrame()
        volume_df = pd.DataFrame({"2330": [1000, 2000]})
        result = run_screener(price_df, volume_df)
        assert result == []

    def test_empty_volume_df_returns_empty(self):
        """volume_df 為空 DataFrame → 回傳 []，不拋出例外。"""
        dates = pd.bdate_range(end="2026-05-02", periods=2)
        price_df = pd.DataFrame({"2330": [100.0, 102.0]}, index=dates)
        volume_df = pd.DataFrame()
        result = run_screener(price_df, volume_df)
        assert result == []

    def test_single_row_df_returns_empty(self):
        """
        price_df 只有 1 筆資料（無前日），無法計算漲跌幅 → 回傳 []。
        """
        dates = pd.bdate_range(end="2026-05-02", periods=1)
        price_df = pd.DataFrame({"2330": [100.0]}, index=dates)
        volume_df = pd.DataFrame({"2330": [5000.0]}, index=dates)
        result = run_screener(price_df, volume_df)
        assert result == []

    def test_max_change_pct_filter(self, sample_price_volume):
        """
        強制所有股票漲幅 > 1.0%，max_change_pct=0.5 → 不符合 <= 0.5 → []。
        """
        price_df, volume_df = sample_price_volume
        price_df = price_df.copy()
        # 最後一日拉高 5%，確保所有漲幅 > 1.0
        price_df.iloc[-1] = price_df.iloc[-2] * 1.05
        result = run_screener(
            price_df, volume_df, min_volume=0, min_change_pct=0.0, max_change_pct=0.5
        )
        assert result == []

    def test_results_sorted_by_change_pct_desc(self, sample_price_volume):
        """結果應按 change_pct 由高到低排序。"""
        price_df, volume_df = sample_price_volume
        result = run_screener(
            price_df, volume_df, min_volume=0, min_change_pct=-100.0, max_change_pct=100.0
        )
        if len(result) >= 2:
            for i in range(len(result) - 1):
                assert result[i]["change_pct"] >= result[i + 1]["change_pct"]

    def test_volume_threshold_boundary(self, sample_price_volume):
        """
        volume_df 中最後一日全設為 min_volume（邊界值），應全部通過成交量篩選。
        """
        price_df, volume_df = sample_price_volume
        threshold = 3000
        volume_df = volume_df.copy()
        volume_df.iloc[-1] = float(threshold)
        result = run_screener(
            price_df, volume_df,
            min_volume=threshold,
            min_change_pct=-100.0,
            max_change_pct=100.0,
        )
        # 所有結果的 volume 應 >= threshold
        for item in result:
            assert item["volume"] >= threshold


class TestFormatScreenerMessage:
    """format_screener_message() 的單元測試。"""

    def test_empty_results_returns_no_stock_message(self):
        """results 為空時，回傳包含「今日無符合條件股票」的訊息。"""
        msg = format_screener_message([], date="2026-05-02")
        assert "今日無符合條件" in msg
        assert "2026-05-02" in msg

    def test_normal_results_format(self):
        """正常結果應包含 stock_id 與 change_pct。"""
        results = [
            {"stock_id": "2330", "close": 850.0, "change_pct": 3.52, "volume": 5234},
        ]
        msg = format_screener_message(results, date="2026-05-02")
        assert "2330" in msg
        assert "3.52" in msg

    def test_date_in_message(self):
        """日期字串應出現在訊息中。"""
        msg = format_screener_message([], date="2026-05-02")
        assert "2026-05-02" in msg

    def test_multiple_results_all_present(self):
        """多筆結果，每筆 stock_id 都應出現在訊息中。"""
        results = [
            {"stock_id": "2330", "close": 850.0, "change_pct": 3.52, "volume": 5234},
            {"stock_id": "2454", "close": 1200.0, "change_pct": 4.11, "volume": 3891},
            {"stock_id": "3661", "close": 400.0, "change_pct": 1.20, "volume": 4000},
        ]
        msg = format_screener_message(results, date="2026-05-02")
        for r in results:
            assert r["stock_id"] in msg

    def test_stock_count_in_message(self):
        """訊息中應顯示符合條件的股票數量。"""
        results = [
            {"stock_id": "2330", "close": 850.0, "change_pct": 3.52, "volume": 5234},
            {"stock_id": "2454", "close": 1200.0, "change_pct": 4.11, "volume": 3891},
        ]
        msg = format_screener_message(results, date="2026-05-02")
        assert "2" in msg  # 共 2 檔

    def test_negative_change_pct_format(self):
        """負漲跌幅應顯示負號（不加 +）。"""
        results = [
            {"stock_id": "2330", "close": 850.0, "change_pct": -2.50, "volume": 5000},
        ]
        msg = format_screener_message(results, date="2026-05-02")
        assert "-2.50" in msg

    def test_positive_change_pct_has_plus_sign(self):
        """正漲跌幅應顯示 + 號。"""
        results = [
            {"stock_id": "2330", "close": 850.0, "change_pct": 3.52, "volume": 5234},
        ]
        msg = format_screener_message(results, date="2026-05-02")
        assert "+3.52" in msg

    def test_no_date_still_works(self):
        """不傳 date 時不應拋出例外，訊息仍可正常產生。"""
        msg = format_screener_message([], date="")
        assert "今日無符合條件" in msg

    def test_emoji_in_message(self):
        """訊息應包含 📊 emoji。"""
        msg = format_screener_message([], date="2026-05-02")
        assert "📊" in msg
