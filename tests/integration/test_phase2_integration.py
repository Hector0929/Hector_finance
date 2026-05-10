"""
test_phase2_integration.py — Phase 2 整合測試（M5~M11）

BDD 格式：Given / When / Then
驗證各模組端到端串接行為，不發出真實 API 請求。
"""

import os
from unittest.mock import patch

import pandas as pd
import plotly.graph_objects as go
import pytest

from src.indicators.institutional import (
    build_institutional_chart,
    calc_consecutive_buy,
    calc_institutional_net,
)
from src.screener.filter import format_screener_message, run_screener
from src.notifier.telegram import send_message, send_screener_result
from src.ai.claude_client import build_analysis_prompt, get_ai_analysis, parse_ai_response
from src.watchlist.manager import (
    add_stock,
    is_in_watchlist,
    load_watchlist,
    remove_stock,
    save_watchlist,
    WATCHLIST_PATH,
)
from src.notes.notion import create_note, delete_note, get_notes


# ---------------------------------------------------------------------------
# M5 — 三大法人籌碼整合
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestInstitutionalPipeline:
    """calc_institutional_net 輸出可直接送入 build_institutional_chart"""

    def test_calc_and_build_chart(self, sample_inst_data):
        """
        Given 模擬三大法人籌碼 DataFrame
        When  calc_institutional_net 計算後送入 build_institutional_chart
        Then  回傳合法 go.Figure，barmode="group"，含 4 條 trace
        """
        df = sample_inst_data

        # calc_institutional_net 使用 Series 輸入
        df_result = calc_institutional_net(
            foreign=pd.Series(df["foreign"].values, index=df["date"]),
            trust=pd.Series(df["trust"].values, index=df["date"]),
            dealer=pd.Series(df["dealer"].values, index=df["date"]),
            days=20,
        )

        assert set(["date", "foreign", "trust", "dealer", "total"]).issubset(df_result.columns)
        assert len(df_result) == 20

        # 輸出直接送入圖表建構
        fig = build_institutional_chart(df_result)
        assert isinstance(fig, go.Figure), "應回傳 go.Figure"
        assert fig.layout.barmode == "group", "barmode 應為 group"
        assert len(fig.data) == 4, "應有 4 條 trace（外資、投信、自營商、合計）"

    def test_consecutive_buy_with_real_data(self, sample_inst_data):
        """
        Given sample_inst_data 的 foreign 欄位
        When  calc_consecutive_buy 執行
        Then  回傳 int，不拋出例外
        """
        foreign_series = pd.Series(
            sample_inst_data["foreign"].values,
            index=sample_inst_data["date"],
        )
        result = calc_consecutive_buy(foreign_series)
        assert isinstance(result, int), "應回傳 int"
        assert result >= 0, "連續買超天數不應為負值"


# ---------------------------------------------------------------------------
# M10 — 條件篩選整合
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestScreenerPipeline:
    """run_screener / format_screener_message 端到端串接"""

    def test_screener_with_mock_data(self, sample_price_volume):
        """
        Given 模擬 price_df / volume_df（5 檔 × 30 日）
        When  run_screener 執行（放寬條件確保有結果）
        Then  回傳 list[dict]，每筆含必要欄位
        """
        price_df, volume_df = sample_price_volume
        results = run_screener(
            price_df,
            volume_df,
            min_volume=0,
            min_change_pct=-100.0,
            max_change_pct=100.0,
        )
        assert isinstance(results, list), "應回傳 list"
        for item in results:
            assert "stock_id" in item
            assert "close" in item
            assert "change_pct" in item
            assert "volume" in item

    def test_screener_to_message_format(self, sample_price_volume):
        """
        Given run_screener 的結果
        When  format_screener_message 格式化
        Then  輸出非空字串
        """
        price_df, volume_df = sample_price_volume
        results = run_screener(
            price_df,
            volume_df,
            min_volume=0,
            min_change_pct=-100.0,
            max_change_pct=100.0,
        )
        msg = format_screener_message(results, date="2026-05-02")
        assert isinstance(msg, str), "應回傳字串"
        assert len(msg) > 0, "訊息不應為空字串"

    def test_empty_screener_message_contains_no_stock(self):
        """
        Given run_screener 空結果（[]）
        When  format_screener_message 格式化
        Then  訊息含「今日無符合條件」字樣
        """
        msg = format_screener_message([], date="2026-05-02")
        assert "今日無符合條件" in msg, f"空結果訊息應含「今日無符合條件」，got: {msg}"


# ---------------------------------------------------------------------------
# M11 — Telegram 推播整合
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestNotifierPipeline:
    """send_message / send_screener_result Telegram 推播整合"""

    def test_send_screener_result_calls_api(self, mock_requests_post_success):
        """
        Given mock requests.post 回傳成功
        When  send_screener_result 推播含一筆股票的結果
        Then  requests.post 被呼叫一次
        """
        results = [{"stock_id": "2330", "close": 850.0, "change_pct": 2.5, "volume": 5000}]
        # TELEGRAM_BOT_TOKEN 在模組載入時已讀取，需同時 patch 模組層級變數
        with patch("src.notifier.telegram.TELEGRAM_BOT_TOKEN", "fake-token"):
            with patch("src.notifier.telegram.TELEGRAM_CHAT_ID", "123"):
                send_screener_result(results, date="2026-05-02")
        mock_requests_post_success.assert_called_once()

    def test_empty_results_sends_message(self, mock_requests_post_success):
        """
        Given results=[]
        When  send_screener_result 推播空結果
        Then  requests.post 仍被呼叫一次（推播「今日無符合條件」）
        """
        with patch("src.notifier.telegram.TELEGRAM_BOT_TOKEN", "fake-token"):
            with patch("src.notifier.telegram.TELEGRAM_CHAT_ID", "123"):
                send_screener_result([], date="2026-05-02")
        mock_requests_post_success.assert_called_once()

    def test_telegram_api_failure_does_not_raise(self):
        """
        Given requests.post 拋出 ConnectionError
        When  send_message 被呼叫
        Then  不向上拋出例外，回傳 {"success": False, ...}
        """
        with patch("src.notifier.telegram.requests.post", side_effect=ConnectionError("timeout")):
            with patch("src.notifier.telegram.TELEGRAM_BOT_TOKEN", "fake-token"):
                result = send_message("測試訊息")
        assert result["success"] is False, "失敗時 success 應為 False"
        assert "error" in result, "失敗時應含 error 欄位"


# ---------------------------------------------------------------------------
# M6 — AI 綜合評估整合
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestAIPipeline:
    """build_analysis_prompt / parse_ai_response / get_ai_analysis 整合"""

    def test_get_ai_analysis_with_mock(self, mock_anthropic):
        """
        Given mock Anthropic client 回傳「趨勢：多頭\\n操作建議：可買進\\n風險：低」
        When  get_ai_analysis 呼叫
        Then  回傳 dict 含 trend/suggestion/risk_level/raw 四個 key
        """
        indicators = {
            "close": 850.0,
            "change_pct": 2.5,
            "ma5": 845.0,
            "ma20": 830.0,
            "ma60": 800.0,
            "bb_upper": 870.0,
            "bb_lower": 810.0,
            "k": 65.0,
            "d": 60.0,
            "dif": 5.2,
            "signal": 4.8,
            "osc": 0.4,
            "foreign_consecutive": 3,
        }
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "fake-key"}):
            result = get_ai_analysis("2330", "台積電", indicators)

        for key in ("trend", "suggestion", "risk_level", "raw"):
            assert key in result, f"回傳 dict 應含 '{key}' key"

        assert result["trend"] == "多頭", f"trend 應解析為多頭，got: {result['trend']}"
        assert result["risk_level"] == "低", f"risk_level 應解析為低，got: {result['risk_level']}"

    def test_parse_response_from_prompt_output(self):
        """
        Given build_analysis_prompt 產出的 prompt 格式（模擬 Claude 回應）
        When  parse_ai_response 解析標準格式回應
        Then  trend / risk_level 均正確解析，不為 N/A
        """
        # 模擬 Claude 依照 prompt 格式回答
        mock_response = "趨勢：空頭\n操作建議：建議觀望，等待趨勢確認。\n風險：高"
        result = parse_ai_response(mock_response)

        assert result["trend"] == "空頭", f"trend 解析錯誤，got: {result['trend']}"
        assert result["risk_level"] == "高", f"risk_level 解析錯誤，got: {result['risk_level']}"
        assert result["suggestion"] != "N/A", "suggestion 不應為 N/A"
        assert result["raw"] == mock_response, "raw 應保留原始回應"


# ---------------------------------------------------------------------------
# M9 — 自選清單整合
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestWatchlistPipeline:
    """add_stock / remove_stock / is_in_watchlist / load / save 整合"""

    def test_add_remove_round_trip(self, tmp_path, monkeypatch):
        """
        Given 空白的暫時 watchlist 檔案路徑
        When  add_stock → is_in_watchlist=True → remove_stock
        Then  is_in_watchlist 最終為 False
        """
        fake_path = tmp_path / "watchlist.json"
        monkeypatch.setattr("src.watchlist.manager.WATCHLIST_PATH", fake_path)

        add_result = add_stock("2330", "台積電")
        assert add_result["success"] is True, "add_stock 應成功"

        assert is_in_watchlist("2330") is True, "加入後 is_in_watchlist 應為 True"

        remove_result = remove_stock("2330")
        assert remove_result["success"] is True, "remove_stock 應成功"

        assert is_in_watchlist("2330") is False, "移除後 is_in_watchlist 應為 False"

    def test_load_save_consistency(self, tmp_path, monkeypatch):
        """
        Given 自定義 watchlist 資料
        When  save_watchlist 後 load_watchlist
        Then  回傳相同資料（stock_id 一致）
        """
        fake_path = tmp_path / "watchlist.json"
        monkeypatch.setattr("src.watchlist.manager.WATCHLIST_PATH", fake_path)

        watchlist_data = [
            {"stock_id": "2330", "name": "台積電", "added_at": "2026-05-02T00:00:00"},
            {"stock_id": "2454", "name": "聯發科", "added_at": "2026-05-02T00:01:00"},
        ]
        save_result = save_watchlist(watchlist_data)
        assert save_result is True, "save_watchlist 應回傳 True"

        loaded = load_watchlist()
        loaded_ids = [item["stock_id"] for item in loaded]
        assert loaded_ids == ["2330", "2454"], f"load 回傳 stock_id 應一致，got: {loaded_ids}"


# ---------------------------------------------------------------------------
# M7 — 個人筆記（Notion）整合
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestNotesPipeline:
    """create_note / get_notes / delete_note Notion 整合（mock Client）"""

    def test_create_note_success(self, mock_notion):
        """
        Given mock Notion Client，pages.create 回傳 {"id": "test-page-id-001"}
        When  create_note 呼叫
        Then  回傳 {"success": True, "page_id": "test-page-id-001", ...}
        """
        with patch.dict(os.environ, {"NOTION_TOKEN": "fake", "NOTION_DATABASE_ID": "fake-db"}):
            result = create_note(
                stock_id="2330",
                note_type="買入",
                price=850.0,
                shares=1,
                content="布林通道突破",
                date="2026-05-02",
            )
        assert result["success"] is True, f"create_note 應成功，got: {result}"
        assert result["page_id"] == "test-page-id-001", f"page_id 應為 test-page-id-001，got: {result['page_id']}"

    def test_get_notes_empty(self, mock_notion):
        """
        Given mock Notion Client，databases.query 回傳 {"results": []}
        When  get_notes("2330") 呼叫
        Then  回傳空 list []
        """
        with patch.dict(os.environ, {"NOTION_TOKEN": "fake", "NOTION_DATABASE_ID": "fake-db"}):
            result = get_notes("2330")
        assert result == [], f"空資料庫應回傳 []，got: {result}"

    def test_delete_note_success(self, mock_notion):
        """
        Given mock Notion Client，pages.update 回傳 {}（成功）
        When  delete_note("test-page-id-001") 呼叫
        Then  回傳 {"success": True, ...}
        """
        with patch.dict(os.environ, {"NOTION_TOKEN": "fake", "NOTION_DATABASE_ID": "fake-db"}):
            result = delete_note("test-page-id-001")
        assert result["success"] is True, f"delete_note 應成功，got: {result}"
