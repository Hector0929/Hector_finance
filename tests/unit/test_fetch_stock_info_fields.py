"""
test_fetch_stock_info_fields.py — fetch_stock_info 新欄位的單元測試

測試 pe_ratio 和 market_cap 欄位在各種情境下的行為（使用 mock 隔離 FinLab）。
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from typing import Optional
import pandas as pd
import pytest


def _build_finlab_mock(stock_id: str, close: float,
                        pe: Optional[float] = None,
                        market_cap: Optional[float] = None) -> MagicMock:
    """
    建立模擬 finlab.data.get 回傳值。
    close_df, vol_df 預設包含合法資料；pe_df / mc_df 依參數決定是否含該股票。
    """
    def _series(val, length=5):
        dates = pd.date_range("2024-01-01", periods=length, freq="B")
        return pd.Series([val] * length, index=dates)

    close_series = _series(close)
    prev_series  = pd.concat([_series(close - 1, 4), _series(close)])

    close_df = pd.DataFrame({stock_id: prev_series})
    vol_df   = pd.DataFrame({stock_id: _series(1_000_000)})
    pe_df    = pd.DataFrame({stock_id: _series(pe)}   if pe is not None   else {})
    mc_df    = pd.DataFrame({stock_id: _series(market_cap)} if market_cap is not None else {})

    def _get(key: str):
        mapping = {
            "price:收盤價":   close_df,
            "price:成交股數":  vol_df,
            "fundamental_features:本益比": pe_df,
            "fundamental_features:市值":   mc_df,
        }
        return mapping.get(key, pd.DataFrame())

    mock = MagicMock()
    mock.get.side_effect = _get
    return mock


@pytest.fixture(autouse=True)
def _reset_finlab_login():
    """每個測試前重置登入狀態，確保 mock 生效。"""
    import src.data.finlab_client as m
    m._finlab_logged_in = False
    yield
    m._finlab_logged_in = False


class TestFetchStockInfoPeAndMarketCap:
    def _run(self, stock_id, close, pe=None, market_cap=None):
        finlab_mock = _build_finlab_mock(stock_id, close, pe, market_cap)
        with (
            patch("src.data.finlab_client._ensure_finlab_login", return_value=True),
            patch("src.data.finlab_client.fetch_stock_name", return_value="測試股票"),
            patch("src.data.finlab_client.finlab_data", finlab_mock, create=True),
            patch.dict("sys.modules", {"finlab": MagicMock(), "finlab.data": finlab_mock}),
        ):
            # 直接 import 並 patch data 物件
            import src.data.finlab_client as fc
            import importlib

            # 注入 finlab_data mock
            original = getattr(fc, "_finlab_logged_in", False)
            fc._finlab_logged_in = True

            # patch finlab.data inside the function
            import finlab
            finlab.data = finlab_mock

            result = fc.fetch_stock_info(stock_id)
            fc._finlab_logged_in = False
            return result

    def test_result_contains_pe_ratio_key(self):
        """回傳 dict 必須包含 pe_ratio key。"""
        import src.data.finlab_client as fc

        close_series = pd.Series([99.0, 100.0], index=pd.date_range("2024-01-01", periods=2, freq="B"))
        close_df  = pd.DataFrame({"2330": close_series})
        vol_df    = pd.DataFrame({"2330": pd.Series([1_000_000, 1_000_000],
                                   index=pd.date_range("2024-01-01", periods=2, freq="B"))})
        pe_df     = pd.DataFrame({"2330": pd.Series([20.5, 20.5],
                                   index=pd.date_range("2024-01-01", periods=2, freq="B"))})
        mc_df     = pd.DataFrame({"2330": pd.Series([5e12, 5e12],
                                   index=pd.date_range("2024-01-01", periods=2, freq="B"))})

        def _get(key):
            return {
                "price:收盤價": close_df,
                "price:成交股數": vol_df,
                "fundamental_features:本益比": pe_df,
                "fundamental_features:市值": mc_df,
            }.get(key, pd.DataFrame())

        import sys
        finlab_mock_module = MagicMock()
        finlab_mock_module.data = MagicMock()
        finlab_mock_module.data.get.side_effect = _get

        with (
            patch("src.data.finlab_client._ensure_finlab_login", return_value=True),
            patch("src.data.finlab_client.fetch_stock_name", return_value="台積電"),
            patch.dict(sys.modules, {"finlab": finlab_mock_module}),
        ):
            fc._finlab_logged_in = True
            result = fc.fetch_stock_info("2330")
            fc._finlab_logged_in = False

        assert "pe_ratio" in result
        assert "market_cap" in result

    def test_pe_ratio_none_when_table_missing(self):
        """fundamental_features:本益比 不含該股票時，pe_ratio 應為 None。"""
        import src.data.finlab_client as fc
        import sys

        close_series = pd.Series([99.0, 100.0], index=pd.date_range("2024-01-01", periods=2, freq="B"))
        close_df = pd.DataFrame({"2330": close_series})
        vol_df   = pd.DataFrame({"2330": pd.Series([1_000_000, 1_000_000],
                                  index=pd.date_range("2024-01-01", periods=2, freq="B"))})

        def _get(key):
            return {
                "price:收盤價": close_df,
                "price:成交股數": vol_df,
            }.get(key, pd.DataFrame())

        finlab_mock_module = MagicMock()
        finlab_mock_module.data = MagicMock()
        finlab_mock_module.data.get.side_effect = _get

        with (
            patch("src.data.finlab_client._ensure_finlab_login", return_value=True),
            patch("src.data.finlab_client.fetch_stock_name", return_value="台積電"),
            patch.dict(sys.modules, {"finlab": finlab_mock_module}),
        ):
            fc._finlab_logged_in = True
            result = fc.fetch_stock_info("2330")
            fc._finlab_logged_in = False

        assert result.get("pe_ratio") is None
        assert result.get("market_cap") is None

    def test_market_cap_converted_to_yi(self):
        """market_cap 應轉換為億元（原始值 / 1e8）。"""
        import src.data.finlab_client as fc
        import sys

        close_series = pd.Series([99.0, 100.0], index=pd.date_range("2024-01-01", periods=2, freq="B"))
        close_df = pd.DataFrame({"2330": close_series})
        vol_df   = pd.DataFrame({"2330": pd.Series([1_000_000, 1_000_000],
                                  index=pd.date_range("2024-01-01", periods=2, freq="B"))})
        # 5 兆元 = 50,000 億元
        mc_series = pd.Series([5e12, 5e12], index=pd.date_range("2024-01-01", periods=2, freq="B"))
        mc_df = pd.DataFrame({"2330": mc_series})

        def _get(key):
            return {
                "price:收盤價": close_df,
                "price:成交股數": vol_df,
                "fundamental_features:市值": mc_df,
            }.get(key, pd.DataFrame())

        finlab_mock_module = MagicMock()
        finlab_mock_module.data = MagicMock()
        finlab_mock_module.data.get.side_effect = _get

        with (
            patch("src.data.finlab_client._ensure_finlab_login", return_value=True),
            patch("src.data.finlab_client.fetch_stock_name", return_value="台積電"),
            patch.dict(sys.modules, {"finlab": finlab_mock_module}),
        ):
            fc._finlab_logged_in = True
            result = fc.fetch_stock_info("2330")
            fc._finlab_logged_in = False

        assert result.get("market_cap") == pytest.approx(50000.0)
