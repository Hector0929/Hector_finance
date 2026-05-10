"""
Unit tests for M2 K線+布林通道 — TDD Red 階段

測試對象：
  src/indicators/bollinger.py
    - calc_bollinger(close, window, std) -> (mid, upper, lower)
    - calc_ma(close, window) -> pd.Series
    - build_main_chart(df) -> go.Figure

設計規格參考：docs/design_spec.md M2/M4 章節
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

from src.indicators.bollinger import build_main_chart, calc_bollinger, calc_ma


# ---------------------------------------------------------------------------
# TestCalcBollinger
# ---------------------------------------------------------------------------


class TestCalcBollinger:
    """測試 calc_bollinger(close, window=20, std=2.0)"""

    def test_upper_greater_than_mid(self, sample_close: pd.Series) -> None:
        """上軌應大於中軌（在有效計算區間內）。"""
        mid, upper, lower = calc_bollinger(sample_close)
        valid = ~upper.isna() & ~mid.isna()
        assert valid.sum() > 0, "應有足夠資料產生有效值"
        assert (upper[valid] > mid[valid]).all(), "所有有效點：upper > mid"

    def test_mid_greater_than_lower(self, sample_close: pd.Series) -> None:
        """中軌應大於下軌（在有效計算區間內）。"""
        mid, upper, lower = calc_bollinger(sample_close)
        valid = ~mid.isna() & ~lower.isna()
        assert valid.sum() > 0, "應有足夠資料產生有效值"
        assert (mid[valid] > lower[valid]).all(), "所有有效點：mid > lower"

    def test_mid_equals_sma(self, sample_close: pd.Series) -> None:
        """中軌應等於 20 日 SMA。"""
        mid, _, _ = calc_bollinger(sample_close, window=20)
        expected_mid = sample_close.rolling(20).mean()
        pd.testing.assert_series_equal(
            mid,
            expected_mid,
            check_names=False,
            rtol=1e-6,
        )

    def test_insufficient_data_returns_nan(self) -> None:
        """資料少於 window 時，前 window-1 筆應為 NaN。"""
        close = pd.Series(range(1, 16), dtype=float)  # 15 筆
        mid, upper, lower = calc_bollinger(close, window=20)
        # 15 < 20，所有值均為 NaN
        assert mid.isna().all(), "15 筆資料 window=20，mid 全部應為 NaN"
        assert upper.isna().all(), "15 筆資料 window=20，upper 全部應為 NaN"
        assert lower.isna().all(), "15 筆資料 window=20，lower 全部應為 NaN"

    def test_bollinger_width_proportional_to_std(self, sample_close: pd.Series) -> None:
        """std=4 的通道寬度應為 std=2 的 2 倍。"""
        mid2, upper2, lower2 = calc_bollinger(sample_close, window=20, std=2.0)
        mid4, upper4, lower4 = calc_bollinger(sample_close, window=20, std=4.0)

        # 有效區間
        valid = ~upper2.isna() & ~upper4.isna()
        assert valid.sum() > 0

        width2 = (upper2 - lower2)[valid]
        width4 = (upper4 - lower4)[valid]

        np.testing.assert_allclose(
            width4.values,
            (width2 * 2).values,
            rtol=1e-6,
            err_msg="std=4 的寬度應為 std=2 的 2 倍",
        )


# ---------------------------------------------------------------------------
# TestCalcMa
# ---------------------------------------------------------------------------


class TestCalcMa:
    """測試 calc_ma(close, window)"""

    def test_ma5(self, sample_close: pd.Series) -> None:
        """MA5 應等於 5 日 rolling mean。"""
        result = calc_ma(sample_close, window=5)
        expected = sample_close.rolling(5).mean()
        pd.testing.assert_series_equal(result, expected, check_names=False, rtol=1e-6)

    def test_insufficient_data_returns_nan(self) -> None:
        """資料筆數小於 window 時，所有值應為 NaN。"""
        close = pd.Series([1.0, 2.0, 3.0])
        result = calc_ma(close, window=5)
        assert result.isna().all(), "3 筆資料 window=5，全部應為 NaN"

    def test_returns_series_same_length(self, sample_close: pd.Series) -> None:
        """回傳 Series 的長度應與輸入相同。"""
        result = calc_ma(sample_close, window=10)
        assert len(result) == len(sample_close), "回傳長度應與輸入一致"


# ---------------------------------------------------------------------------
# TestBuildMainChart
# ---------------------------------------------------------------------------


class TestBuildMainChart:
    """測試 build_main_chart(df) -> go.Figure"""

    def test_returns_figure(self, sample_ohlcv: pd.DataFrame) -> None:
        """應回傳 go.Figure 型別。"""
        fig = build_main_chart(sample_ohlcv)
        assert isinstance(fig, go.Figure), "回傳值應為 go.Figure"

    def test_has_two_rows(self, sample_ohlcv: pd.DataFrame) -> None:
        """Figure 應包含兩個子圖（row 1：K線；row 2：成交量）。"""
        fig = build_main_chart(sample_ohlcv)
        # make_subplots 會建立 xaxis 與 xaxis2
        layout_dict = fig.layout.to_plotly_json()
        assert "xaxis2" in layout_dict, "應存在 xaxis2（row 2）"
        assert "yaxis2" in layout_dict, "應存在 yaxis2（row 2）"

    def test_candlestick_trace_exists(self, sample_ohlcv: pd.DataFrame) -> None:
        """圖表中應包含一個 Candlestick trace。"""
        fig = build_main_chart(sample_ohlcv)
        candlestick_traces = [
            t for t in fig.data if isinstance(t, go.Candlestick)
        ]
        assert len(candlestick_traces) >= 1, "應至少有一個 Candlestick trace"

    def test_volume_trace_exists(self, sample_ohlcv: pd.DataFrame) -> None:
        """圖表中應包含一個名為「成交量」的 Bar trace。"""
        fig = build_main_chart(sample_ohlcv)
        volume_traces = [
            t for t in fig.data
            if isinstance(t, go.Bar) and t.name == "成交量"
        ]
        assert len(volume_traces) >= 1, "應至少有一個名為「成交量」的 Bar trace"

    def test_figure_height(self, sample_ohlcv: pd.DataFrame) -> None:
        """Figure 高度應為 540px。"""
        fig = build_main_chart(sample_ohlcv)
        assert fig.layout.height == 540, f"Figure 高度應為 540，實際為 {fig.layout.height}"
