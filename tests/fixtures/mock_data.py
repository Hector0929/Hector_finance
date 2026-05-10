import pytest
import pandas as pd
import numpy as np


@pytest.fixture
def sample_ohlcv_120():
    np.random.seed(42)
    dates = pd.bdate_range(end="2026-05-02", periods=120)
    close = 100 + np.cumsum(np.random.randn(120) * 2)
    open_ = close * (1 + np.random.randn(120) * 0.005)
    high = np.maximum(close, open_) * (1 + np.abs(np.random.randn(120) * 0.003))
    low = np.minimum(close, open_) * (1 - np.abs(np.random.randn(120) * 0.003))
    volume = np.random.randint(1000, 10000, 120)
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=dates,
    )


@pytest.fixture
def sample_ohlcv_short():
    np.random.seed(0)
    dates = pd.bdate_range(end="2026-05-02", periods=15)
    close = 100 + np.cumsum(np.random.randn(15) * 2)
    open_ = close * (1 + np.random.randn(15) * 0.005)
    high = np.maximum(close, open_) * 1.01
    low = np.minimum(close, open_) * 0.99
    volume = np.random.randint(500, 3000, 15)
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=dates,
    )
