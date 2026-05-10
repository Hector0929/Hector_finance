"""
test_resample.py — M8 多週期切換單元測試

TDD Red-Green：測試涵蓋 resample_ohlcv 與 get_period_label 的主要邏輯。
"""

import pandas as pd
import pytest

from src.indicators.resample import get_period_label, resample_ohlcv


class TestResampleOhlcv:
    def test_daily_returns_same_df(self, daily_ohlcv):
        """period="日K" 應回傳相同 DataFrame（不做重採樣）"""
        result = resample_ohlcv(daily_ohlcv, "日K")
        pd.testing.assert_frame_equal(result, daily_ohlcv)

    def test_weekly_reduces_rows(self, daily_ohlcv):
        """週K 的資料筆數應少於日K"""
        result = resample_ohlcv(daily_ohlcv, "週K")
        assert len(result) < len(daily_ohlcv)

    def test_monthly_fewer_than_weekly(self, daily_ohlcv):
        """月K 筆數應少於週K"""
        weekly = resample_ohlcv(daily_ohlcv, "週K")
        monthly = resample_ohlcv(daily_ohlcv, "月K")
        assert len(monthly) < len(weekly)

    def test_weekly_open_is_first(self, daily_ohlcv):
        """週K 的 Open 應為該週第一個交易日的 Open"""
        result = resample_ohlcv(daily_ohlcv, "週K")
        assert result["Open"].notna().all()

        # 驗證第一週的 Open 確實等於該週第一筆日K 的 Open
        first_week_end = result.index[0]
        # 取出屬於該週（index <= first_week_end）的日K 資料
        week_daily = daily_ohlcv[daily_ohlcv.index <= first_week_end]
        expected_open = week_daily["Open"].iloc[0]
        assert abs(result["Open"].iloc[0] - expected_open) < 1e-9

    def test_weekly_high_is_max(self, daily_ohlcv):
        """週K 的 High 應 >= 該週所有日 High"""
        result = resample_ohlcv(daily_ohlcv, "週K")

        # 取第一週，驗證 High >= max(daily High in that week)
        first_week_end = result.index[0]
        week_daily = daily_ohlcv[daily_ohlcv.index <= first_week_end]
        expected_high = week_daily["High"].max()
        assert abs(result["High"].iloc[0] - expected_high) < 1e-9

    def test_weekly_low_is_min(self, daily_ohlcv):
        """週K 的 Low 應為該週最低價"""
        result = resample_ohlcv(daily_ohlcv, "週K")

        first_week_end = result.index[0]
        week_daily = daily_ohlcv[daily_ohlcv.index <= first_week_end]
        expected_low = week_daily["Low"].min()
        assert abs(result["Low"].iloc[0] - expected_low) < 1e-9

    def test_weekly_close_is_last(self, daily_ohlcv):
        """週K 的 Close 應為該週最後一個交易日的 Close"""
        result = resample_ohlcv(daily_ohlcv, "週K")

        first_week_end = result.index[0]
        week_daily = daily_ohlcv[daily_ohlcv.index <= first_week_end]
        expected_close = week_daily["Close"].iloc[-1]
        assert abs(result["Close"].iloc[0] - expected_close) < 1e-9

    def test_volume_is_sum(self, daily_ohlcv):
        """週K 的 Volume 應等於該週每日 Volume 之和"""
        result = resample_ohlcv(daily_ohlcv, "週K")

        first_week_end = result.index[0]
        week_daily = daily_ohlcv[daily_ohlcv.index <= first_week_end]
        expected_volume = week_daily["Volume"].sum()
        assert abs(result["Volume"].iloc[0] - expected_volume) < 1e-9

    def test_unknown_period_returns_daily(self, daily_ohlcv):
        """未知 period 應視為日K，回傳原始 DataFrame"""
        result = resample_ohlcv(daily_ohlcv, "季K")
        pd.testing.assert_frame_equal(result, daily_ohlcv)

    def test_required_columns_preserved(self, daily_ohlcv):
        """重採樣後應保留 Open/High/Low/Close/Volume 欄位"""
        required = {"Open", "High", "Low", "Close", "Volume"}
        for period in ["日K", "週K", "月K"]:
            result = resample_ohlcv(daily_ohlcv, period)
            assert required.issubset(result.columns), (
                f"period={period} 缺少欄位：{required - set(result.columns)}"
            )

    def test_monthly_open_is_first(self, daily_ohlcv):
        """月K 的 Open 應為該月第一個交易日的 Open"""
        result = resample_ohlcv(daily_ohlcv, "月K")
        assert result["Open"].notna().all()

    def test_result_index_is_datetimeindex(self, daily_ohlcv):
        """重採樣結果的 index 應為 DatetimeIndex"""
        for period in ["週K", "月K"]:
            result = resample_ohlcv(daily_ohlcv, period)
            assert isinstance(result.index, pd.DatetimeIndex), (
                f"period={period} 的 index 不是 DatetimeIndex"
            )

    def test_no_nan_after_resample(self, daily_ohlcv):
        """重採樣後不應有 NaN（dropna 應已移除）"""
        for period in ["週K", "月K"]:
            result = resample_ohlcv(daily_ohlcv, period)
            assert not result.isnull().any().any(), (
                f"period={period} 仍有 NaN 值"
            )


class TestGetPeriodLabel:
    def test_known_periods(self):
        assert get_period_label("日K") == "日K"
        assert get_period_label("週K") == "週K"
        assert get_period_label("月K") == "月K"

    def test_unknown_returns_daily(self):
        assert get_period_label("季K") == "日K"

    def test_empty_string_returns_daily(self):
        assert get_period_label("") == "日K"
