"""
test_institutional.py — M5 三大法人籌碼 單元測試

TDD Red → Green 流程：先定義測試，再實作。
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

from src.indicators.institutional import (
    build_institutional_chart,
    calc_consecutive_buy,
    calc_institutional_net,
)


# ---------------------------------------------------------------------------
# TestCalcInstitutionalNet
# ---------------------------------------------------------------------------


class TestCalcInstitutionalNet:
    """測試 calc_institutional_net 函式。"""

    def _make_series(self, n: int, seed: int = 0) -> tuple:
        """產生長度為 n 的三個隨機 Series。"""
        rng = np.random.default_rng(seed)
        dates = pd.bdate_range(end="2026-05-02", periods=n)
        foreign = pd.Series(rng.integers(-500, 2000, n), index=dates)
        trust = pd.Series(rng.integers(-200, 500, n), index=dates)
        dealer = pd.Series(rng.integers(-100, 300, n), index=dates)
        return foreign, trust, dealer

    def test_returns_dataframe_with_correct_columns(self):
        """回傳 DataFrame 必須包含 date, foreign, trust, dealer, total 欄位。"""
        foreign, trust, dealer = self._make_series(30)
        result = calc_institutional_net(foreign, trust, dealer)
        expected_cols = {"date", "foreign", "trust", "dealer", "total"}
        assert isinstance(result, pd.DataFrame)
        assert expected_cols == set(result.columns)

    def test_total_equals_sum(self):
        """total 欄位必須等於 foreign + trust + dealer。"""
        foreign, trust, dealer = self._make_series(30)
        result = calc_institutional_net(foreign, trust, dealer)
        expected_total = result["foreign"] + result["trust"] + result["dealer"]
        pd.testing.assert_series_equal(
            result["total"].reset_index(drop=True),
            expected_total.reset_index(drop=True),
            check_names=False,
        )

    def test_days_limit(self):
        """輸入 50 筆，days=20，輸出恰好 20 筆。"""
        foreign, trust, dealer = self._make_series(50)
        result = calc_institutional_net(foreign, trust, dealer, days=20)
        assert len(result) == 20

    def test_short_input_returns_all(self):
        """輸入 10 筆，days=20，輸出 10 筆（不報錯）。"""
        foreign, trust, dealer = self._make_series(10)
        result = calc_institutional_net(foreign, trust, dealer, days=20)
        assert len(result) == 10

    def test_all_zeros_input(self):
        """全零輸入時，total 應為 0，且回傳正確欄位。"""
        dates = pd.bdate_range(end="2026-05-02", periods=10)
        foreign = pd.Series([0] * 10, index=dates)
        trust = pd.Series([0] * 10, index=dates)
        dealer = pd.Series([0] * 10, index=dates)
        result = calc_institutional_net(foreign, trust, dealer)
        assert (result["total"] == 0).all()
        assert list(result.columns) == ["date", "foreign", "trust", "dealer", "total"]


# ---------------------------------------------------------------------------
# TestCalcConsecutiveBuy
# ---------------------------------------------------------------------------


class TestCalcConsecutiveBuy:
    """測試 calc_consecutive_buy 函式。"""

    def test_all_positive(self):
        """[1,2,3,4,5] → 5（全為正值）。"""
        s = pd.Series([1, 2, 3, 4, 5])
        assert calc_consecutive_buy(s) == 5

    def test_ends_negative(self):
        """[1,2,-1] → 0（最後一筆為負值）。"""
        s = pd.Series([1, 2, -1])
        assert calc_consecutive_buy(s) == 0

    def test_mixed_ends_positive(self):
        """[-1,2,3] → 2（最後連續 2 筆正值）。"""
        s = pd.Series([-1, 2, 3])
        assert calc_consecutive_buy(s) == 2

    def test_empty_series(self):
        """空 Series → 0。"""
        s = pd.Series([], dtype=float)
        assert calc_consecutive_buy(s) == 0

    def test_single_zero(self):
        """[0] → 0（threshold=0，> 0 才算）。"""
        s = pd.Series([0])
        assert calc_consecutive_buy(s, threshold=0) == 0


# ---------------------------------------------------------------------------
# TestBuildInstitutionalChart
# ---------------------------------------------------------------------------


class TestBuildInstitutionalChart:
    """測試 build_institutional_chart 函式。"""

    def test_returns_figure(self, sample_inst_df):
        """回傳值必須是 go.Figure 實例。"""
        fig = build_institutional_chart(sample_inst_df)
        assert isinstance(fig, go.Figure)

    def test_height_300(self, sample_inst_df):
        """圖表高度必須為 300。"""
        fig = build_institutional_chart(sample_inst_df)
        assert fig.layout.height == 300

    def test_has_three_bar_traces(self, sample_inst_df):
        """必須有三條 Bar trace（外資、投信、自營商）。"""
        fig = build_institutional_chart(sample_inst_df)
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        assert len(bar_traces) == 3

    def test_has_total_scatter(self, sample_inst_df):
        """必須有一條 Scatter trace（合計線）。"""
        fig = build_institutional_chart(sample_inst_df)
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        assert len(scatter_traces) == 1

    def test_bgcolor(self, sample_inst_df):
        """plot_bgcolor 與 paper_bgcolor 必須為白色（v2 light theme）。"""
        fig = build_institutional_chart(sample_inst_df)
        assert fig.layout.plot_bgcolor == "#FFFFFF"
        assert fig.layout.paper_bgcolor == "#FFFFFF"
