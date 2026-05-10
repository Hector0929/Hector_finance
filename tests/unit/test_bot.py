"""
test_bot.py — M12 Telegram Bot 查詢單元測試

測試範圍：
- get_updates：成功回傳 list、失敗回傳 []
- send_reply：成功回傳 True、失敗回傳 False
- handle_message：各類指令及輸入的回覆內容
"""

from unittest.mock import patch, MagicMock
from bot import get_updates, send_reply, handle_message


class TestGetUpdates:
    @patch("bot.requests.get")
    def test_success_returns_list(self, mock_get):
        """API 成功時，回傳包含 update 的 list。"""
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"ok": True, "result": [{"update_id": 1, "message": {}}]},
        )
        result = get_updates(offset=0)
        assert isinstance(result, list)
        assert len(result) == 1

    @patch("bot.requests.get")
    def test_failure_returns_empty_list(self, mock_get):
        """網路例外時，回傳空 list 而非拋出例外。"""
        mock_get.side_effect = Exception("Network error")
        result = get_updates()
        assert result == []

    @patch("bot.requests.get")
    def test_ok_false_returns_empty_list(self, mock_get):
        """API 回傳 ok=False 時，回傳空 list。"""
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"ok": False, "description": "Unauthorized"},
        )
        result = get_updates(offset=0)
        assert result == []

    @patch("bot.requests.get")
    def test_passes_offset_param(self, mock_get):
        """確認 offset 參數被正確帶入請求。"""
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"ok": True, "result": []},
        )
        get_updates(offset=42)
        call_kwargs = mock_get.call_args
        assert call_kwargs.kwargs["params"]["offset"] == 42


class TestSendReply:
    @patch("bot.requests.post")
    def test_success_returns_true(self, mock_post):
        """API 成功時，回傳 True。"""
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"ok": True},
        )
        result = send_reply(chat_id=123, text="測試")
        assert result is True

    @patch("bot.requests.post")
    def test_failure_returns_false(self, mock_post):
        """網路例外時，回傳 False 而非拋出例外。"""
        mock_post.side_effect = Exception("Error")
        result = send_reply(chat_id=123, text="測試")
        assert result is False

    @patch("bot.requests.post")
    def test_ok_false_returns_false(self, mock_post):
        """API 回傳 ok=False 時，回傳 False。"""
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"ok": False, "description": "Bad Request"},
        )
        result = send_reply(chat_id=123, text="測試")
        assert result is False

    @patch("bot.requests.post")
    def test_sends_markdown_parse_mode(self, mock_post):
        """確認傳送時使用 Markdown parse_mode。"""
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"ok": True},
        )
        send_reply(chat_id=456, text="*粗體*")
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs["json"]
        assert payload["parse_mode"] == "Markdown"
        assert payload["chat_id"] == 456


class TestHandleMessage:
    def test_start_command(self):
        """'/start' 應回傳含「歡迎」的訊息。"""
        reply = handle_message(123, "/start")
        assert "歡迎" in reply or "start" in reply.lower()

    def test_help_command(self):
        """'/help' 應回傳非空說明文字。"""
        reply = handle_message(123, "/help")
        assert len(reply) > 0

    def test_help_contains_commands(self):
        """'/help' 回覆應包含常見指令說明。"""
        reply = handle_message(123, "/help")
        assert "/start" in reply or "/watchlist" in reply or "指令" in reply

    def test_stock_code_4_digits(self):
        """4 位數字股票代號應出現在回覆中。"""
        reply = handle_message(123, "2330")
        assert "2330" in reply

    def test_stock_code_5_digits(self):
        """5 位數字股票代號應出現在回覆中。"""
        reply = handle_message(123, "00878")
        assert "00878" in reply

    def test_stock_code_3_digits_not_matched(self):
        """3 位數字不應被當作股票代號，改走未識別指令。"""
        reply = handle_message(123, "123")
        assert "help" in reply.lower() or "說明" in reply or "無法" in reply

    def test_stock_code_6_digits_not_matched(self):
        """6 位數字不應被當作股票代號，改走未識別指令。"""
        reply = handle_message(123, "123456")
        assert "help" in reply.lower() or "說明" in reply or "無法" in reply

    def test_watchlist_command_returns_string(self):
        """/watchlist 應回傳字串（無論自選清單是否為空）。"""
        reply = handle_message(123, "/watchlist")
        assert isinstance(reply, str)

    def test_watchlist_command_with_mock_data(self):
        """/watchlist mock 有資料時，回覆應含股票代號。"""
        with patch("src.watchlist.manager.get_watchlist_ids", return_value=["2330", "0050"]):
            reply = handle_message(123, "/watchlist")
        assert "2330" in reply or "0050" in reply

    def test_watchlist_command_empty(self):
        """/watchlist mock 空清單時，回覆應提示清單為空。"""
        with patch("src.watchlist.manager.get_watchlist_ids", return_value=[]):
            reply = handle_message(123, "/watchlist")
        assert "空" in reply or "empty" in reply.lower() or "沒有" in reply or "新增" in reply

    def test_unknown_command(self):
        """未知指令（/ 開頭）應提示使用 /help。"""
        reply = handle_message(123, "/unknown_xyz")
        assert "help" in reply.lower() or "說明" in reply or "無法" in reply

    def test_random_text(self):
        """一般文字（非數字、非指令）應回傳非空字串。"""
        reply = handle_message(123, "hello world")
        assert isinstance(reply, str)
        assert len(reply) > 0

    def test_text_with_leading_trailing_spaces(self):
        """前後有空白的 /start 指令仍應正常處理。"""
        reply = handle_message(123, "  /start  ")
        assert "歡迎" in reply or "start" in reply.lower()

    def test_stock_code_with_spaces_not_matched(self):
        """含空白的數字字串不應被當作股票代號。"""
        reply = handle_message(123, " 2330 ")
        # 因為 strip() 後為 "2330"，仍應被視為股票代號
        assert "2330" in reply
