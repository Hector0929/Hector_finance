"""
test_telegram_notifier.py — M11 Telegram 推播模組單元測試

TDD：使用 unittest.mock.patch mock requests.post，確保不發送真實 HTTP 請求。
"""

from unittest.mock import MagicMock, patch

import pytest

from src.notifier.telegram import send_message, send_screener_result


class TestSendMessage:
    @patch("src.notifier.telegram.requests.post")
    def test_success_returns_message_id(self, mock_post):
        """成功發送時應回傳 success=True 及 message_id。"""
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"ok": True, "result": {"message_id": 42}},
        )
        with patch("src.notifier.telegram.TELEGRAM_BOT_TOKEN", "fake_token"):
            result = send_message("測試訊息", chat_id="123456")
        assert result["success"] is True
        assert result["message_id"] == 42

    @patch("src.notifier.telegram.requests.post")
    def test_api_error_returns_failure(self, mock_post):
        """Telegram API 回傳非 200 或 ok=False 時，應回傳 success=False。"""
        mock_post.return_value = MagicMock(
            status_code=400,
            json=lambda: {"ok": False, "description": "Bad Request"},
        )
        with patch("src.notifier.telegram.TELEGRAM_BOT_TOKEN", "fake_token"):
            result = send_message("測試", chat_id="123")
        assert result["success"] is False

    @patch("src.notifier.telegram.requests.post")
    def test_network_exception_returns_failure(self, mock_post):
        """網路例外發生時，應回傳 success=False，不拋出例外。"""
        mock_post.side_effect = Exception("網路錯誤")
        with patch("src.notifier.telegram.TELEGRAM_BOT_TOKEN", "fake_token"):
            result = send_message("測試", chat_id="123")
        assert result["success"] is False

    @patch("src.notifier.telegram.requests.post")
    def test_uses_env_chat_id_when_not_provided(self, mock_post):
        """未傳入 chat_id 時，應使用環境變數 TELEGRAM_CHAT_ID。"""
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"ok": True, "result": {"message_id": 1}},
        )
        with patch("src.notifier.telegram.TELEGRAM_BOT_TOKEN", "fake_token"):
            with patch("src.notifier.telegram.TELEGRAM_CHAT_ID", "env_chat_id"):
                send_message("測試")
        call_kwargs = mock_post.call_args[1]["json"]
        assert call_kwargs["chat_id"] == "env_chat_id"

    @patch("src.notifier.telegram.requests.post")
    def test_missing_token_returns_failure_without_request(self, mock_post):
        """TELEGRAM_BOT_TOKEN 未設定時，不發出 HTTP 請求，直接回傳 success=False。"""
        with patch("src.notifier.telegram.TELEGRAM_BOT_TOKEN", ""):
            result = send_message("測試", chat_id="123")
        mock_post.assert_not_called()
        assert result["success"] is False

    @patch("src.notifier.telegram.requests.post")
    def test_correct_url_is_called(self, mock_post):
        """requests.post 應以正確的 Telegram API URL 呼叫。"""
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"ok": True, "result": {"message_id": 10}},
        )
        with patch("src.notifier.telegram.TELEGRAM_BOT_TOKEN", "my_token"):
            send_message("測試", chat_id="999")
        called_url = mock_post.call_args[0][0]
        assert called_url == "https://api.telegram.org/botmy_token/sendMessage"

    @patch("src.notifier.telegram.requests.post")
    def test_error_field_present_on_failure(self, mock_post):
        """失敗時回傳 dict 應包含 error 欄位。"""
        mock_post.return_value = MagicMock(
            status_code=401,
            json=lambda: {"ok": False, "description": "Unauthorized"},
        )
        with patch("src.notifier.telegram.TELEGRAM_BOT_TOKEN", "bad_token"):
            result = send_message("測試", chat_id="123")
        assert "error" in result


class TestSendScreenerResult:
    @patch("src.notifier.telegram.send_message")
    def test_empty_results_still_sends(self, mock_send):
        """results 為空時，仍應呼叫 send_message 一次，且訊息含「今日無符合條件」。"""
        mock_send.return_value = {"success": True, "message_id": 1}
        send_screener_result([], date="2026-05-02")
        mock_send.assert_called_once()
        call_text = mock_send.call_args[0][0]
        assert "今日無符合條件" in call_text

    @patch("src.notifier.telegram.send_message")
    def test_sends_formatted_results(self, mock_send):
        """有篩選結果時，應呼叫 send_message，且訊息含股票代碼。"""
        mock_send.return_value = {"success": True, "message_id": 2}
        results = [
            {"stock_id": "2330", "close": 850.0, "change_pct": 3.5, "volume": 5000}
        ]
        send_screener_result(results, date="2026-05-02")
        mock_send.assert_called_once()
        call_text = mock_send.call_args[0][0]
        assert "2330" in call_text

    @patch("src.notifier.telegram.send_message")
    def test_returns_send_message_result(self, mock_send):
        """應回傳 send_message 的結果。"""
        expected = {"success": True, "message_id": 99}
        mock_send.return_value = expected
        result = send_screener_result([], date="2026-05-02")
        assert result == expected

    @patch("src.notifier.telegram.send_message")
    def test_date_included_in_message(self, mock_send):
        """訊息應包含傳入的日期字串。"""
        mock_send.return_value = {"success": True, "message_id": 3}
        send_screener_result([], date="2026-05-02")
        call_text = mock_send.call_args[0][0]
        assert "2026-05-02" in call_text

    @patch("src.notifier.telegram.send_message")
    def test_chat_id_passed_through(self, mock_send):
        """傳入的 chat_id 應正確傳遞給 send_message。"""
        mock_send.return_value = {"success": True, "message_id": 4}
        send_screener_result([], date="2026-05-02", chat_id="custom_id")
        call_kwargs = mock_send.call_args[1]
        assert call_kwargs.get("chat_id") == "custom_id"
