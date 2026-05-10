"""
test_phase1_integration.py — Phase 1 整合測試（M1~M4）

BDD 格式：Given / When / Then
驗證各模組端到端串接行為，不發出真實 API 請求。
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

from src.data.finlab_client import (
    format_change,
    format_volume,
    validate_stock_id,
)
from src.indicators.bollinger import build_main_chart, calc_bollinger
from src.indicators.macd_kd import build_indicator_chart, calc_kd, calc_macd


# ---------------------------------------------------------------------------
# TestIndicatorPipeline
# ---------------------------------------------------------------------------


class TestIndicatorPipeline:
    """端到端技術指標與圖表建構整合測試"""

    @pytest.mark.integration
    def test_bollinger_full_pipeline(self, sample_ohlcv_120):
        """
        Given 120 筆 OHLCV
        When  calc_bollinger 計算布林通道
        Then  上軌 >= 中軌 >= 下軌（dropna 後），中軌等於 rolling(20).mean()
        """
        close = sample_ohlcv_120["Close"]
        mid, upper, lower = calc_bollinger(close, window=20, std=2.0)

        # dropna 後比較
        valid_idx = mid.dropna().index
        assert len(valid_idx) > 0, "dropna 後應有有效數據"

        assert (upper[valid_idx] >= mid[valid_idx]).all(), "上軌應 >= 中軌"
        assert (mid[valid_idx] >= lower[valid_idx]).all(), "中軌應 >= 下軌"

        # 中軌應等於 rolling(20).mean()
        expected_mid = close.rolling(20).mean()
        pd.testing.assert_series_equal(mid, expected_mid, check_names=False)

    @pytest.mark.integration
    def test_kd_full_pipeline(self, sample_ohlcv_120):
        """
        Given 120 筆 OHLCV
        When  calc_kd 計算 KD 指標
        Then  K 和 D 都在 0~100 之間，且無 NaN
        """
        k, d = calc_kd(
            sample_ohlcv_120["High"],
            sample_ohlcv_120["Low"],
            sample_ohlcv_120["Close"],
        )

        assert not k.isna().any(), "K 值不應有 NaN"
        assert not d.isna().any(), "D 值不應有 NaN"
        assert (k >= 0).all() and (k <= 100).all(), "K 值應在 0~100"
        assert (d >= 0).all() and (d <= 100).all(), "D 值應在 0~100"

    @pytest.mark.integration
    def test_macd_full_pipeline(self, sample_ohlcv_120):
        """
        Given 120 筆 OHLCV
        When  calc_macd 計算 MACD
        Then  OSC = DIF - Signal（誤差 < 1e-10），三 Series 長度等於輸入
        """
        close = sample_ohlcv_120["Close"]
        dif, signal, osc = calc_macd(close)

        assert len(dif) == len(close), "DIF 長度應等於輸入"
        assert len(signal) == len(close), "Signal 長度應等於輸入"
        assert len(osc) == len(close), "OSC 長度應等於輸入"

        expected_osc = dif - signal
        diff = (osc - expected_osc).abs()
        assert (diff < 1e-10).all(), "OSC 應等於 DIF - Signal（誤差 < 1e-10）"

    @pytest.mark.integration
    def test_build_main_chart_structure(self, sample_ohlcv_120):
        """
        Given 120 筆 OHLCV
        When  build_main_chart 建立圖表
        Then  回傳 go.Figure，height==540，含 Candlestick trace，含 Bar trace（成交量）
        """
        fig = build_main_chart(sample_ohlcv_120)

        assert isinstance(fig, go.Figure), "應回傳 go.Figure"
        assert fig.layout.height == 540, "圖表高度應為 540"

        trace_types = [type(t).__name__ for t in fig.data]
        assert "Candlestick" in trace_types, "應含 Candlestick trace"
        assert "Bar" in trace_types, "應含 Bar trace（成交量）"

    @pytest.mark.integration
    def test_build_indicator_chart_structure(self, sample_ohlcv_120):
        """
        Given 120 筆 OHLCV
        When  build_indicator_chart 建立圖表
        Then  go.Figure，height==280，含K/D Scatter，含DIF/Signal Scatter，含 Bar trace
        """
        fig = build_indicator_chart(sample_ohlcv_120)

        assert isinstance(fig, go.Figure), "應回傳 go.Figure"
        assert fig.layout.height == 280, "圖表高度應為 280"

        scatter_names = [t.name for t in fig.data if isinstance(t, go.Scatter)]
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]

        assert "K" in scatter_names, "應含名稱為 K 的 Scatter"
        assert "D" in scatter_names, "應含名稱為 D 的 Scatter"

        dif_names = [n for n in scatter_names if "DIF" in n]
        signal_names = [n for n in scatter_names if "Signal" in n]
        assert len(dif_names) > 0, "應含名稱含 DIF 的 Scatter"
        assert len(signal_names) > 0, "應含名稱含 Signal 的 Scatter"

        assert len(bar_traces) > 0, "應含 Bar trace（OSC）"

    @pytest.mark.integration
    def test_short_data_does_not_raise(self, sample_ohlcv_short):
        """
        Given 僅 15 筆 OHLCV（短資料）
        When  build_main_chart 與 build_indicator_chart 均被呼叫
        Then  均不拋出例外
        """
        try:
            build_main_chart(sample_ohlcv_short)
        except Exception as exc:
            pytest.fail(f"build_main_chart 不應拋出例外：{exc}")

        try:
            build_indicator_chart(sample_ohlcv_short)
        except Exception as exc:
            pytest.fail(f"build_indicator_chart 不應拋出例外：{exc}")

    @pytest.mark.integration
    def test_chart_bgcolor(self, sample_ohlcv_120):
        """
        Given 120 筆 OHLCV
        When  build_main_chart 建立圖表
        Then  layout.plot_bgcolor == "#0D1117"
        """
        fig = build_main_chart(sample_ohlcv_120)
        assert fig.layout.plot_bgcolor == "#0D1117", "背景色應為 #0D1117"

    @pytest.mark.integration
    def test_volume_color_up_down(self):
        """
        Given 明確包含漲跌兩種情境的 DataFrame
        When  build_main_chart 建立圖表
        Then  Volume Bar 的 marker.color 含有 #F85149（上漲）和 #3FB950（下跌）
        """
        # 建立確定漲（close > open）和跌（close < open）的數據
        dates = pd.bdate_range(end="2026-05-02", periods=10)
        close = np.array([101, 99, 101, 99, 101, 99, 101, 99, 101, 99], dtype=float)
        open_ = np.array([100, 100, 100, 100, 100, 100, 100, 100, 100, 100], dtype=float)
        high = close + 1
        low = open_ - 1
        volume = np.ones(10) * 1000

        df = pd.DataFrame(
            {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
            index=dates,
        )

        fig = build_main_chart(df)

        # 找到 Bar trace（成交量）
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        assert len(bar_traces) > 0, "應有 Bar trace"
        vol_bar = bar_traces[0]

        colors = list(vol_bar.marker.color)
        assert "#F85149" in colors, "應含上漲紅色 #F85149"
        assert "#3FB950" in colors, "應含下跌綠色 #3FB950"


# ---------------------------------------------------------------------------
# TestHelperFunctions
# ---------------------------------------------------------------------------


class TestHelperFunctions:
    """M1 輔助函式邊界值整合測試"""

    @pytest.mark.integration
    def test_format_volume_boundary(self):
        """
        Given 邊界值 9999 與 10000
        When  format_volume 被呼叫
        Then  9999 → "9,999 張"，10000 → "1.0 萬張"
        """
        assert format_volume(9999) == "9,999 張", "9999 應顯示千分位整數"
        assert format_volume(10000) == "1.0 萬張", "10000 應換算為 1.0 萬張"

    @pytest.mark.integration
    def test_validate_stock_id_formats(self):
        """
        Given 各種股票代號格式
        When  validate_stock_id 被呼叫
        Then  4碼True，5碼True，6碼False，含空格False
        """
        assert validate_stock_id("2330") is True, "4碼數字應為合法"
        assert validate_stock_id("00878") is True, "5碼數字應為合法"
        assert validate_stock_id("123456") is False, "6碼數字應為不合法"
        assert validate_stock_id("23 0") is False, "含空格應為不合法"

    @pytest.mark.integration
    def test_format_change_precision(self):
        """
        Given 正值、負值、零
        When  format_change 被呼叫
        Then  保留2位小數，正值帶"+"，0.0不帶符號
        """
        result_positive = format_change(1.5)
        assert result_positive == "+1.50", f"正值應帶+號，保留2位小數，got: {result_positive}"
        assert result_positive.startswith("+"), "正值應以+開頭"

        result_negative = format_change(-2.3)
        assert result_negative == "-2.30", f"負值應自動帶-號，got: {result_negative}"

        result_zero = format_change(0.0)
        assert result_zero == "0.00", f"0.0 應顯示 0.00，got: {result_zero}"
        assert not result_zero.startswith("+"), "0.0 不應帶+號"
        assert not result_zero.startswith("-"), "0.0 不應帶-號"
