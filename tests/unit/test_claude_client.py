"""
test_claude_client.py — M6 AI 綜合評估單元測試

TDD：測試先行，驗證 build_analysis_prompt、parse_ai_response、get_ai_analysis。
"""

from unittest.mock import patch, MagicMock

import pytest

from src.ai.claude_client import build_analysis_prompt, parse_ai_response, get_ai_analysis

# ---------------------------------------------------------------------------
# 共用 fixtures
# ---------------------------------------------------------------------------

SAMPLE_INDICATORS = {
    "close": 100.0,
    "change_pct": 1.5,
    "ma5": 98.0,
    "ma20": 95.0,
    "ma60": 90.0,
    "bb_upper": 110.0,
    "bb_lower": 80.0,
    "k": 70.0,
    "d": 65.0,
    "dif": 0.5,
    "signal": 0.3,
    "osc": 0.2,
    "foreign_consecutive": 3,
}


def _make_prompt() -> str:
    """輔助函式：建立標準測試用 prompt。"""
    return build_analysis_prompt(
        stock_id="2330",
        stock_name="台積電",
        close=100.0,
        change_pct=1.5,
        ma5=98.0,
        ma20=95.0,
        ma60=90.0,
        bb_upper=110.0,
        bb_lower=80.0,
        k_value=70.0,
        d_value=65.0,
        macd_dif=0.5,
        macd_signal=0.3,
        macd_osc=0.2,
        foreign_consecutive=3,
    )


# ---------------------------------------------------------------------------
# TestBuildAnalysisPrompt
# ---------------------------------------------------------------------------


class TestBuildAnalysisPrompt:
    """驗證 build_analysis_prompt 產出合法 prompt 字串。"""

    def test_returns_string(self):
        """回傳型別必須是 str。"""
        result = _make_prompt()
        assert isinstance(result, str)

    def test_not_empty(self):
        """prompt 不可為空字串。"""
        result = _make_prompt()
        assert len(result.strip()) > 0

    def test_contains_stock_id(self):
        """prompt 中應包含股票代號。"""
        result = _make_prompt()
        assert "2330" in result

    def test_contains_stock_name(self):
        """prompt 中應包含股票名稱。"""
        result = _make_prompt()
        assert "台積電" in result

    def test_contains_key_indicators(self):
        """prompt 必須包含主要技術指標名稱關鍵字（大小寫均可）。"""
        result = _make_prompt().upper()
        # MA 系列
        assert "MA5" in result or "MA 5" in result
        # KD 指標
        assert "KD" in result or "K值" in result or "K " in result
        # MACD
        assert "MACD" in result

    def test_contains_close_price(self):
        """prompt 應包含收盤價數值。"""
        result = _make_prompt()
        assert "100" in result  # close=100.0

    def test_contains_foreign_consecutive(self):
        """prompt 應包含外資連續買賣超資訊。"""
        result = _make_prompt()
        # foreign_consecutive=3，數字應出現
        assert "3" in result

    def test_contains_bollinger_bands(self):
        """prompt 應包含布林通道相關資訊。"""
        result = _make_prompt().upper()
        assert "BB" in result or "布林" in result or "BOLLINGER" in result

    def test_different_stock_ids_produce_different_prompts(self):
        """不同股票代號應產出不同 prompt。"""
        prompt_2330 = build_analysis_prompt(
            stock_id="2330", stock_name="台積電",
            close=100.0, change_pct=1.5,
            ma5=98.0, ma20=95.0, ma60=90.0,
            bb_upper=110.0, bb_lower=80.0,
            k_value=70.0, d_value=65.0,
            macd_dif=0.5, macd_signal=0.3, macd_osc=0.2,
            foreign_consecutive=3,
        )
        prompt_2317 = build_analysis_prompt(
            stock_id="2317", stock_name="鴻海",
            close=100.0, change_pct=1.5,
            ma5=98.0, ma20=95.0, ma60=90.0,
            bb_upper=110.0, bb_lower=80.0,
            k_value=70.0, d_value=65.0,
            macd_dif=0.5, macd_signal=0.3, macd_osc=0.2,
            foreign_consecutive=3,
        )
        assert prompt_2330 != prompt_2317


# ---------------------------------------------------------------------------
# TestParseAiResponse
# ---------------------------------------------------------------------------


class TestParseAiResponse:
    """驗證 parse_ai_response 能正確解析 Gemini 回應。"""

    def test_all_keys_present(self):
        """回傳 dict 必須包含 trend, suggestion, risk_level, raw 四個 key。"""
        result = parse_ai_response("趨勢：多頭\n操作建議：可買進\n風險：低")
        for key in ("trend", "suggestion", "risk_level", "raw"):
            assert key in result, f"缺少 key: {key}"

    def test_normal_bullish_response(self):
        """含「多頭」關鍵字時，trend 應為 '多頭'。"""
        result = parse_ai_response("目前呈現多頭趨勢，建議買進，風險偏低。")
        assert result["trend"] == "多頭"

    def test_normal_bearish_response(self):
        """含「空頭」關鍵字時，trend 應為 '空頭'。"""
        result = parse_ai_response("目前空頭走勢明顯，建議觀望，風險偏高。")
        assert result["trend"] == "空頭"

    def test_consolidation_response(self):
        """含「盤整」關鍵字時，trend 應為 '盤整'。"""
        result = parse_ai_response("目前處於盤整階段，短期無明確方向。")
        assert result["trend"] == "盤整"

    def test_unknown_trend_returns_na_or_consolidation(self):
        """不含趨勢關鍵字時，trend 應為 'N/A' 或 '盤整'（實作可選擇預設值）。"""
        result = parse_ai_response("這是一段沒有明確趨勢關鍵字的回應。")
        assert result["trend"] in ("N/A", "盤整")

    def test_raw_always_preserved(self):
        """raw 欄位必須等於輸入的原始文字。"""
        raw_text = "趨勢：多頭\n操作建議：可買進\n風險：低風險"
        result = parse_ai_response(raw_text)
        assert result["raw"] == raw_text

    def test_empty_string_returns_na(self):
        """空字串輸入時，trend 應為 'N/A' 或 '盤整'，raw 為空字串。"""
        result = parse_ai_response("")
        assert result["trend"] in ("N/A", "盤整")
        assert result["raw"] == ""

    def test_risk_low_detected(self):
        """含「低」風險關鍵字時，risk_level 應反映低風險。"""
        result = parse_ai_response("多頭趨勢，風險：低，建議買進。")
        assert result["risk_level"] in ("低", "low", "Low")

    def test_risk_high_detected(self):
        """含「高」風險關鍵字時，risk_level 應反映高風險。"""
        result = parse_ai_response("空頭趨勢，風險偏高，建議停損。")
        assert result["risk_level"] in ("高", "high", "High")

    def test_suggestion_not_empty_for_valid_response(self):
        """有效回應的 suggestion 不應為空字串。"""
        result = parse_ai_response("多頭趨勢，建議分批買進，注意回檔風險。")
        assert isinstance(result["suggestion"], str)
        assert len(result["suggestion"]) > 0


# ---------------------------------------------------------------------------
# TestGetAiAnalysis
# ---------------------------------------------------------------------------


class TestGetAiAnalysis:
    """驗證 get_ai_analysis 的 API 呼叫流程與錯誤處理。"""

    @patch("src.ai.claude_client.GEMINI_API_KEY", "fake-key")
    @patch("src.ai.claude_client.genai")
    def test_api_success_returns_dict(self, mock_genai):
        """API 呼叫成功時，回傳 dict 含必要 key。"""
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model
        mock_model.generate_content.return_value = MagicMock(
            text="趨勢：多頭趨勢\n操作建議：可買進\n風險：低"
        )

        result = get_ai_analysis("2330", "台積電", SAMPLE_INDICATORS)

        assert isinstance(result, dict)
        for key in ("trend", "suggestion", "risk_level", "raw"):
            assert key in result, f"缺少 key: {key}"

    @patch("src.ai.claude_client.GEMINI_API_KEY", "fake-key")
    @patch("src.ai.claude_client.genai")
    def test_api_success_trend_is_bullish(self, mock_genai):
        """API 回應含「多頭」時，trend 應為 '多頭'。"""
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model
        mock_model.generate_content.return_value = MagicMock(
            text="多頭走勢，建議買進，風險低。"
        )

        result = get_ai_analysis("2330", "台積電", SAMPLE_INDICATORS)
        assert result["trend"] == "多頭"

    @patch("src.ai.claude_client.GEMINI_API_KEY", "fake-key")
    @patch("src.ai.claude_client.genai")
    def test_api_failure_returns_fallback(self, mock_genai):
        """API 拋出 Exception 時，回傳 fallback dict，不拋出例外。"""
        mock_genai.GenerativeModel.side_effect = Exception("API connection error")

        result = get_ai_analysis("2330", "台積電", SAMPLE_INDICATORS)

        assert isinstance(result, dict)
        assert result["trend"] == "N/A"
        assert result["risk_level"] == "N/A"
        assert "暫時無法使用" in result["suggestion"] or result["suggestion"] != ""
        assert result["raw"] == ""

    @patch("src.ai.claude_client.GEMINI_API_KEY", "fake-key")
    @patch("src.ai.claude_client.genai")
    def test_api_create_failure_returns_fallback(self, mock_genai):
        """generate_content 拋出例外時，回傳 fallback dict。"""
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model
        mock_model.generate_content.side_effect = RuntimeError("rate limit exceeded")

        result = get_ai_analysis("9999", "測試股票", SAMPLE_INDICATORS)

        assert result["trend"] == "N/A"
        assert result["raw"] == ""

    @patch("src.ai.claude_client.GEMINI_API_KEY", "fake-key")
    @patch("src.ai.claude_client.genai")
    def test_api_called_with_correct_model(self, mock_genai):
        """確認呼叫 API 時使用指定的 Gemini model。"""
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model
        mock_model.generate_content.return_value = MagicMock(
            text="多頭，低風險，建議買進。"
        )

        get_ai_analysis("2330", "台積電", SAMPLE_INDICATORS)

        mock_genai.GenerativeModel.assert_called_once_with("gemini-2.0-flash")

    @patch("src.ai.claude_client.GEMINI_API_KEY", "fake-key")
    @patch("src.ai.claude_client.genai")
    def test_api_called_with_max_tokens(self, mock_genai):
        """確認呼叫 API 時 max_output_tokens=512。"""
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model
        mock_model.generate_content.return_value = MagicMock(
            text="多頭，低風險，建議買進。"
        )

        get_ai_analysis("2330", "台積電", SAMPLE_INDICATORS)

        call_kwargs = mock_model.generate_content.call_args.kwargs
        generation_config = call_kwargs.get("generation_config", {})
        assert generation_config.get("max_output_tokens") == 512

    def test_api_key_not_hardcoded(self):
        """確認模組可正常 import，GEMINI_API_KEY 透過 os.getenv 取得。"""
        import src.ai.claude_client as module
        import os
        expected = os.getenv("GEMINI_API_KEY", "")
        assert module.GEMINI_API_KEY == expected

    def test_missing_api_key_returns_error(self):
        """GEMINI_API_KEY 未設定時，回傳含 error key 的 fallback dict。"""
        with patch("src.ai.claude_client.GEMINI_API_KEY", ""):
            result = get_ai_analysis("2330", "台積電", SAMPLE_INDICATORS)

        assert result["trend"] == "N/A"
        assert result["raw"] == ""
        assert "error" in result
        assert "GEMINI_API_KEY" in result["error"]

    @patch("src.ai.claude_client.GEMINI_API_KEY", "fake-key")
    @patch("src.ai.claude_client.genai")
    def test_indicators_passed_to_prompt(self, mock_genai):
        """確認 indicators 中的數值有傳遞進 prompt（透過 generate_content 內容驗證）。"""
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model
        mock_model.generate_content.return_value = MagicMock(
            text="多頭，低風險，建議買進。"
        )

        indicators = dict(SAMPLE_INDICATORS)
        indicators["close"] = 999.99

        get_ai_analysis("2330", "台積電", indicators)

        call_args = mock_model.generate_content.call_args
        prompt_content = call_args.args[0] if call_args.args else call_args.kwargs.get("contents", "")
        assert "999" in prompt_content  # close=999.99 應出現在 prompt
