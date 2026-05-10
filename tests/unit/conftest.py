"""
conftest.py — 單元測試共用 fixtures

提供 M2 及後續模組測試所需的 sample_close 與 sample_ohlcv fixtures。
"""

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def sample_close() -> pd.Series:
    """
    100 筆模擬收盤價 Series，index 為連續交易日期。

    使用固定亂數種子以確保測試可重現。
    """
    rng = np.random.default_rng(42)
    dates = pd.date_range("2024-01-02", periods=100, freq="B")
    prices = 100.0 + np.cumsum(rng.normal(0, 1, 100))
    return pd.Series(prices, index=dates, name="Close")


@pytest.fixture
def sample_ohlcv() -> pd.DataFrame:
    """
    100 筆模擬 OHLCV DataFrame，index 為連續交易日期。

    欄位：Open, High, Low, Close, Volume
    保證 High >= max(Open, Close) 且 Low <= min(Open, Close)。
    """
    rng = np.random.default_rng(42)
    dates = pd.date_range("2024-01-02", periods=100, freq="B")

    close = 100.0 + np.cumsum(rng.normal(0, 1, 100))
    open_ = close + rng.normal(0, 0.5, 100)
    high = np.maximum(close, open_) + rng.uniform(0.1, 1.0, 100)
    low = np.minimum(close, open_) - rng.uniform(0.1, 1.0, 100)
    volume = rng.integers(1000, 50000, 100).astype(float)

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume,
        },
        index=dates,
    )


@pytest.fixture
def sample_inst_df():
    """
    20 筆模擬三大法人籌碼 DataFrame。

    columns: date, foreign, trust, dealer, total
    """
    import numpy as np

    dates = pd.bdate_range(end="2026-05-02", periods=20)
    rng = np.random.default_rng(42)
    foreign = rng.integers(-500, 2000, 20)
    trust = rng.integers(-200, 500, 20)
    dealer = rng.integers(-100, 300, 20)
    return pd.DataFrame(
        {
            "date": dates,
            "foreign": foreign,
            "trust": trust,
            "dealer": dealer,
            "total": foreign + trust + dealer,
        }
    )


@pytest.fixture
def sample_price_volume():
    """回傳 (price_df, volume_df) tuple，5 支股票 × 30 日"""
    import numpy as np

    np.random.seed(123)
    dates = pd.bdate_range(end="2026-05-02", periods=30)
    stocks = ["2330", "2454", "3661", "6669", "2382"]
    price_data = {s: 100 + np.cumsum(np.random.randn(30) * 2) for s in stocks}
    volume_data = {s: np.random.randint(2000, 8000, 30).astype(float) for s in stocks}
    price_df = pd.DataFrame(price_data, index=dates)
    volume_df = pd.DataFrame(volume_data, index=dates)
    return price_df, volume_df


@pytest.fixture
def daily_ohlcv():
    """252 個交易日的 OHLCV DataFrame（約 1 年）"""
    import numpy as np

    np.random.seed(99)
    dates = pd.bdate_range(end="2026-05-02", periods=252)
    close = 100 + np.cumsum(np.random.randn(252) * 1.5)
    open_ = close * (1 + np.random.randn(252) * 0.003)
    high = np.maximum(close, open_) * (1 + np.abs(np.random.randn(252) * 0.002))
    low = np.minimum(close, open_) * (1 - np.abs(np.random.randn(252) * 0.002))
    volume = np.random.randint(2000, 9000, 252).astype(float)
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=dates,
    )
