"""Phase 3 整合測試：M8 多週期切換 + M12 Bot 查詢"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock


@pytest.fixture
def daily_ohlcv_252():
    np.random.seed(42)
    dates = pd.bdate_range(end="2026-05-02", periods=252)
    close = 100 + np.cumsum(np.random.randn(252) * 1.5)
    open_ = close * (1 + np.random.randn(252) * 0.003)
    high = np.maximum(close, open_) * 1.002
    low = np.minimum(close, open_) * 0.998
    volume = np.random.randint(2000, 9000, 252).astype(float)
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=dates
    )


@pytest.mark.integration
class TestResamplePipeline:
    def test_daily_to_weekly_then_chart(self, daily_ohlcv_252):
        """週K 重採樣後可直接送入 build_main_chart，不拋出例外"""
        from src.indicators.resample import resample_ohlcv
        from src.indicators.bollinger import build_main_chart
        weekly = resample_ohlcv(daily_ohlcv_252, "週K")
        fig = build_main_chart(weekly)
        assert fig.layout.height == 540

    def test_daily_to_monthly_then_chart(self, daily_ohlcv_252):
        """月K 重採樣後可直接送入 build_main_chart，不拋出例外"""
        from src.indicators.resample import resample_ohlcv
        from src.indicators.bollinger import build_main_chart
        monthly = resample_ohlcv(daily_ohlcv_252, "月K")
        fig = build_main_chart(monthly)
        assert fig.layout.height == 540

    def test_resample_then_indicator_chart(self, daily_ohlcv_252):
        """週K 重採樣後可送入 build_indicator_chart（KD+MACD），不拋出"""
        from src.indicators.resample import resample_ohlcv
        from src.indicators.macd_kd import build_indicator_chart
        weekly = resample_ohlcv(daily_ohlcv_252, "週K")
        fig = build_indicator_chart(weekly)
        assert fig.layout.height == 280

    def test_all_periods_produce_valid_figures(self, daily_ohlcv_252):
        """三種週期均可正常產出圖表"""
        from src.indicators.resample import resample_ohlcv
        from src.indicators.bollinger import build_main_chart
        import plotly.graph_objects as go
        for period in ["日K", "週K", "月K"]:
            df = resample_ohlcv(daily_ohlcv_252, period)
            fig = build_main_chart(df)
            assert isinstance(fig, go.Figure)


@pytest.mark.integration
class TestBotHandlerPipeline:
    def test_start_command_returns_welcome(self):
        from bot import handle_message
        reply = handle_message(123, "/start")
        assert len(reply) > 0

    def test_stock_query_returns_stock_id(self):
        from bot import handle_message
        reply = handle_message(123, "2330")
        assert "2330" in reply

    def test_watchlist_command_returns_string(self, tmp_path, monkeypatch):
        """/watchlist 指令不拋出例外，回傳字串"""
        import src.watchlist.manager as wm
        monkeypatch.setattr(wm, "WATCHLIST_PATH", tmp_path / "wl.json")
        from bot import handle_message
        reply = handle_message(123, "/watchlist")
        assert isinstance(reply, str)

    def test_bot_without_token_does_not_raise(self):
        """token 未設定時 run_bot 不拋出，直接 return"""
        with patch("bot.TELEGRAM_BOT_TOKEN", ""):
            from bot import run_bot
            run_bot()  # 不應拋出例外

    @patch("bot.requests.get")
    @patch("bot.requests.post")
    def test_full_bot_cycle(self, mock_post, mock_get):
        """模擬一次完整的 update → handle → reply 循環"""
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"ok": True, "result": [
                {"update_id": 1, "message": {"chat": {"id": 999}, "text": "2330"}}
            ]}
        )
        mock_post.return_value = MagicMock(
            status_code=200, json=lambda: {"ok": True, "result": {"message_id": 1}}
        )
        from bot import get_updates, send_reply, handle_message
        updates = get_updates(offset=0)
        assert len(updates) == 1
        msg = updates[0]["message"]
        reply = handle_message(msg["chat"]["id"], msg["text"])
        result = send_reply(msg["chat"]["id"], reply)
        assert result is True
