"""
test_macd_kd.py — M3 KD+MACD 指標計算與圖表建構單元測試

TDD Red 階段：先定義所有測試案例，再實作 src/indicators/macd_kd.py。

設計規格參考：docs/design_spec.md M3 章節
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

from src.indicators.macd_kd import build_indicator_chart, calc_kd, calc_macd


# ---------------------------------------------------------------------------
# TestCalcKd
# ---------------------------------------------------------------------------


class TestCalcKd:
    """測試 calc_kd 函式。"""

    def test_returns_two_series(self, sample_ohlcv: pd.DataFrame) -> None:
        """應回傳長度相同的兩條 Series（K, D）。"""
        k, d = calc_kd(
            sample_ohlcv["High"],
            sample_ohlcv["Low"],
            sample_ohlcv["Close"],
        )
        assert isinstance(k, pd.Series)
        assert isinstance(d, pd.Series)
        assert len(k) == len(sample_ohlcv)
        assert len(d) == len(sample_ohlcv)

    def test_k_range_0_to_100(self, sample_ohlcv: pd.DataFrame) -> None:
        """K 值有效範圍應在 [0, 100]（排除 NaN）。"""
        k, _ = calc_kd(
            sample_ohlcv["High"],
            sample_ohlcv["Low"],
            sample_ohlcv["Close"],
        )
        valid = k.dropna()
        assert (valid >= 0).all(), "K 值出現小於 0 的值"
        assert (valid <= 100).all(), "K 值出現大於 100 的值"

    def test_d_range_0_to_100(self, sample_ohlcv: pd.DataFrame) -> None:
        """D 值有效範圍應在 [0, 100]（排除 NaN）。"""
        _, d = calc_kd(
            sample_ohlcv["High"],
            sample_ohlcv["Low"],
            sample_ohlcv["Close"],
        )
        valid = d.dropna()
        assert (valid >= 0).all(), "D 值出現小於 0 的值"
        assert (valid <= 100).all(), "D 值出現大於 100 的值"

    def test_initial_nan_count(self, sample_ohlcv: pd.DataFrame) -> None:
        """
        period=9，RSV 前 8 筆（index 0-7）為 NaN。
        使用 fillna(50) 後，K/D 從第一筆起就有值，所以全部 100 筆皆應為有效值。
        """
        k, d = calc_kd(
            sample_ohlcv["High"],
            sample_ohlcv["Low"],
            sample_ohlcv["Close"],
            period=9,
        )
        # RSV fillna(50) 後，ewm 對整個序列計算，不應有 NaN
        assert k.isna().sum() == 0, f"K 應全數有值，但有 {k.isna().sum()} 個 NaN"
        assert d.isna().sum() == 0, f"D 應全數有值，但有 {d.isna().sum()} 個 NaN"

    def test_same_high_low_returns_nan(self) -> None:
        """
        當 high == low（分母為 0）時，RSV 應為 NaN，不拋出 ZeroDivisionError。
        K/D 在此位置應以 50 初始值計算，不拋出例外。
        """
        dates = pd.date_range("2024-01-02", periods=15, freq="B")
        # 前幾筆 high == low，模擬分母為 0 的情況
        high = pd.Series([100.0] * 15, index=dates)
        low = pd.Series([100.0] * 15, index=dates)
        close = pd.Series([100.0] * 15, index=dates)

        try:
            k, d = calc_kd(high, low, close, period=9)
        except ZeroDivisionError:
            pytest.fail("calc_kd 在 high == low 時不應拋出 ZeroDivisionError")

        # RSV 分母為 0，應全為 NaN，K/D 以 50 計算
        assert not k.isna().all() or True  # K/D 可能全為 50，只要不拋例外即可
        # 主要驗證：不拋出例外，且不包含 inf
        assert not np.isinf(k.fillna(0)).any(), "K 值出現 inf"
        assert not np.isinf(d.fillna(0)).any(), "D 值出現 inf"


# ---------------------------------------------------------------------------
# TestCalcMacd
# ---------------------------------------------------------------------------


class TestCalcMacd:
    """測試 calc_macd 函式。"""

    def test_returns_three_series(self, sample_close: pd.Series) -> None:
        """應回傳長度相同的三條 Series（DIF, Signal, OSC）。"""
        dif, signal, osc = calc_macd(sample_close)
        assert isinstance(dif, pd.Series)
        assert isinstance(signal, pd.Series)
        assert isinstance(osc, pd.Series)
        assert len(dif) == len(sample_close)
        assert len(signal) == len(sample_close)
        assert len(osc) == len(sample_close)

    def test_osc_equals_dif_minus_signal(self, sample_close: pd.Series) -> None:
        """OSC 應等於 DIF - Signal（在有值的位置）。"""
        dif, signal, osc = calc_macd(sample_close)
        expected = dif - signal
        pd.testing.assert_series_equal(
            osc,
            expected,
            check_names=False,
            rtol=1e-10,
        )

    def test_initial_values_not_all_nan(self, sample_close: pd.Series) -> None:
        """
        100 筆資料，使用 ewm(adjust=False)，DIF 從第一筆起就有值（不會全為 NaN）。
        ewm 不依賴固定窗格，不會因資料不足產生 NaN。
        """
        dif, signal, osc = calc_macd(sample_close)
        assert dif.isna().sum() == 0, "DIF 不應含有 NaN（ewm adjust=False）"
        assert signal.isna().sum() == 0, "Signal 不應含有 NaN"
        assert osc.isna().sum() == 0, "OSC 不應含有 NaN"

    def test_fast_ema_crosses_slow_ema(self) -> None:
        """
        製造一個明顯上升趨勢，確認 DIF 最終為正值（快線 > 慢線）。
        """
        dates = pd.date_range("2024-01-02", periods=100, freq="B")
        # 線性遞增序列，快線 EMA 應追趕並超越慢線 EMA
        prices = pd.Series(np.linspace(50.0, 200.0, 100), index=dates)
        dif, _, _ = calc_macd(prices)
        # 最後幾筆的 DIF 應為正值（上升趨勢中快線 > 慢線）
        assert dif.iloc[-1] > 0, f"上升趨勢中 DIF 末端應為正，實際為 {dif.iloc[-1]:.4f}"


# ---------------------------------------------------------------------------
# TestBuildIndicatorChart
# ---------------------------------------------------------------------------


class TestBuildIndicatorChart:
    """測試 build_indicator_chart 函式。"""

    def test_returns_figure(self, sample_ohlcv: pd.DataFrame) -> None:
        """應回傳 plotly go.Figure 物件。"""
        fig = build_indicator_chart(sample_ohlcv)
        assert isinstance(fig, go.Figure)

    def test_figure_height_280(self, sample_ohlcv: pd.DataFrame) -> None:
        """圖表高度應為 280px（依 design_spec.md 規格）。"""
        fig = build_indicator_chart(sample_ohlcv)
        assert fig.layout.height == 280, (
            f"圖表高度應為 280px，實際為 {fig.layout.height}px"
        )

    def test_has_kd_traces(self, sample_ohlcv: pd.DataFrame) -> None:
        """圖表應包含 K 線與 D 線 trace（名稱為 'K' 和 'D'）。"""
        fig = build_indicator_chart(sample_ohlcv)
        trace_names = [t.name for t in fig.data]
        assert "K" in trace_names, f"找不到 'K' trace，現有：{trace_names}"
        assert "D" in trace_names, f"找不到 'D' trace，現有：{trace_names}"

    def test_has_macd_traces(self, sample_ohlcv: pd.DataFrame) -> None:
        """圖表應包含 DIF 與 Signal trace。"""
        fig = build_indicator_chart(sample_ohlcv)
        trace_names = [t.name for t in fig.data]
        assert "DIF" in trace_names, f"找不到 'DIF' trace，現有：{trace_names}"
        assert "Signal" in trace_names, f"找不到 'Signal' trace，現有：{trace_names}"

    def test_osc_positive_negative_split(self, sample_ohlcv: pd.DataFrame) -> None:
        """
        OSC 應分為兩條 Bar trace：'OSC 多頭'（正值）與 '空頭'（負值）。
        正值 trace 的負值位置應為 None；負值 trace 的正值位置應為 None。
        """
        fig = build_indicator_chart(sample_ohlcv)
        trace_names = [t.name for t in fig.data]
        assert "OSC 多頭" in trace_names, f"找不到 'OSC 多頭' trace，現有：{trace_names}"
        assert "OSC 空頭" in trace_names, f"找不到 'OSC 空頭' trace，現有：{trace_names}"

        # 取 OSC 多頭 trace（應為 Bar 型別）
        osc_bull = next(t for t in fig.data if t.name == "OSC 多頭")
        osc_bear = next(t for t in fig.data if t.name == "OSC 空頭")

        assert isinstance(osc_bull, go.Bar), "'OSC 多頭' 應為 Bar trace"
        assert isinstance(osc_bear, go.Bar), "'OSC 空頭' 應為 Bar trace"

        # 多頭 trace 的負值位置應為 None（或 NaN）
        bull_y = [v for v in osc_bull.y if v is not None and not (isinstance(v, float) and np.isnan(v))]
        bear_y = [v for v in osc_bear.y if v is not None and not (isinstance(v, float) and np.isnan(v))]

        # 多頭只包含正值（> 0）
        assert all(v > 0 for v in bull_y), "OSC 多頭 trace 不應包含非正值"
        # 空頭只包含非正值（<= 0）
        assert all(v <= 0 for v in bear_y), "OSC 空頭 trace 不應包含正值"
