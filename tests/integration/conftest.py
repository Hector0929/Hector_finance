import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "fixtures"))
from mock_data import sample_ohlcv_120, sample_ohlcv_short

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock


@pytest.fixture
def sample_price_volume():
    """回傳 (price_df, volume_df) tuple，5 支股票 × 30 日"""
    np.random.seed(123)
    dates = pd.bdate_range(end="2026-05-02", periods=30)
    stocks = ["2330", "2454", "3661", "6669", "2382"]
    price_data = {s: 100 + np.cumsum(np.random.randn(30) * 2) for s in stocks}
    volume_data = {s: np.random.randint(2000, 8000, 30).astype(float) for s in stocks}
    price_df = pd.DataFrame(price_data, index=dates)
    volume_df = pd.DataFrame(volume_data, index=dates)
    return price_df, volume_df


@pytest.fixture
def sample_inst_data():
    dates = pd.bdate_range(end="2026-05-02", periods=20)
    np.random.seed(42)
    return pd.DataFrame({
        "date": dates,
        "foreign": np.random.randint(-500, 2000, 20),
        "trust": np.random.randint(-200, 500, 20),
        "dealer": np.random.randint(-100, 300, 20),
        "total": np.random.randint(-800, 2800, 20),
    })


@pytest.fixture
def mock_requests_post_success():
    with patch("src.notifier.telegram.requests.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"ok": True, "result": {"message_id": 99}}
        )
        yield mock_post


@pytest.fixture
def mock_anthropic():
    with patch("src.ai.claude_client.Anthropic") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        mock_instance.messages.create.return_value = MagicMock(
            content=[MagicMock(text="趨勢：多頭\n操作建議：可買進\n風險：低")]
        )
        yield mock_instance


@pytest.fixture
def mock_notion():
    with patch("src.notes.notion.Client") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        mock_instance.pages.create.return_value = {"id": "test-page-id-001"}
        mock_instance.databases.query.return_value = {"results": []}
        mock_instance.pages.update.return_value = {}
        yield mock_instance
