"""
claude_client.py — M6 AI 綜合評估核心模組（Gemini API）

使用 Google Gemini API 對台股個股技術指標進行 AI 分析，
回傳趨勢判斷、操作建議與風險評估。
"""

import logging
import os

from dotenv import load_dotenv

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:  # pragma: no cover
    genai = None  # type: ignore[assignment]
    genai_types = None  # type: ignore[assignment]

load_dotenv()
logger = logging.getLogger(__name__)

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = "gemini-2.0-flash"

# ---------------------------------------------------------------------------
# Prompt 建構
# ---------------------------------------------------------------------------


def build_analysis_prompt(
    stock_id: str,
    stock_name: str,
    close: float,
    change_pct: float,
    ma5: float,
    ma20: float,
    ma60: float,
    bb_upper: float,
    bb_lower: float,
    k_value: float,
    d_value: float,
    macd_dif: float,
    macd_signal: float,
    macd_osc: float,
    foreign_consecutive: int,
) -> str:
    """
    建立傳給 Claude 的分析 prompt。

    彙整股票基本資訊與技術指標，請 Claude 給出趨勢判斷、操作建議與風險等級。
    不呼叫 API，僅回傳格式化的 prompt 字串。

    Args:
        stock_id: 股票代號，例如 "2330"。
        stock_name: 股票名稱，例如 "台積電"。
        close: 最新收盤價。
        change_pct: 漲跌幅（%）。
        ma5: 5 日移動平均線。
        ma20: 20 日移動平均線。
        ma60: 60 日移動平均線。
        bb_upper: 布林通道上軌（BB Upper）。
        bb_lower: 布林通道下軌（BB Lower）。
        k_value: KD 指標 K 值。
        d_value: KD 指標 D 值。
        macd_dif: MACD DIF 線。
        macd_signal: MACD Signal（DEA）線。
        macd_osc: MACD 柱狀（OSC / Histogram）。
        foreign_consecutive: 外資連續買超天數（正值）或連續賣超天數（負值）。

    Returns:
        格式化的 prompt 字串，供 Claude API 使用。
    """
    foreign_desc: str
    if foreign_consecutive > 0:
        foreign_desc = f"連續買超 {foreign_consecutive} 天"
    elif foreign_consecutive < 0:
        foreign_desc = f"連續賣超 {abs(foreign_consecutive)} 天"
    else:
        foreign_desc = "今日無明確方向"

    prompt = f"""你是一位專業的台股技術分析師，請根據以下技術指標對個股進行分析，並給出簡潔的趨勢判斷與操作建議。

## 股票資訊
- 股票代號：{stock_id}
- 股票名稱：{stock_name}
- 收盤價：{close:.2f} 元（漲跌幅：{change_pct:+.2f}%）

## 技術指標摘要

### 均線（Moving Average）
- MA5：{ma5:.2f}
- MA20：{ma20:.2f}
- MA60：{ma60:.2f}

### 布林通道（Bollinger Bands / BB）
- BB 上軌：{bb_upper:.2f}
- BB 下軌：{bb_lower:.2f}
- 目前收盤價相對布林通道：{'接近上軌' if close >= bb_upper * 0.97 else ('接近下軌' if close <= bb_lower * 1.03 else '中間區域')}

### KD 指標
- K 值：{k_value:.2f}
- D 值：{d_value:.2f}
- KD 狀態：{'超買區（K>{k_value:.0f}）' if k_value > 80 else ('超賣區' if k_value < 20 else '中性區間')}

### MACD 指標
- DIF：{macd_dif:.4f}
- Signal（DEA）：{macd_signal:.4f}
- OSC（柱狀）：{macd_osc:.4f}
- MACD 狀態：{'多頭排列（DIF > Signal）' if macd_dif > macd_signal else '空頭排列（DIF < Signal）'}

### 三大法人籌碼
- 外資動向：{foreign_desc}

## 分析請求

請依據以上技術指標，提供：
1. **趨勢判斷**：請明確標示為「多頭」、「空頭」或「盤整」其中之一
2. **操作建議**：具體的買進、賣出或觀望建議（約 2-3 句）
3. **風險評估**：請明確標示風險等級為「低」、「中」或「高」其中之一

請以繁體中文回答，格式如下：
趨勢：[多頭/空頭/盤整]
操作建議：[具體建議]
風險：[低/中/高]
"""
    return prompt


# ---------------------------------------------------------------------------
# 回應解析
# ---------------------------------------------------------------------------


def parse_ai_response(raw_text: str) -> dict:
    """
    解析 Claude 回應文字，回傳結構化 dict。

    解析規則：
    - trend：從文字中尋找「多頭」、「空頭」、「盤整」關鍵字
    - suggestion：擷取操作建議段落
    - risk_level：從文字中尋找「低」、「中」、「高」風險關鍵字
    - raw：原始完整回應（原封不動保留）

    若解析失敗，trend / suggestion / risk_level 填 "N/A"，raw 填原始文字。

    Args:
        raw_text: Claude API 回傳的完整文字內容。

    Returns:
        dict with keys: trend (str), suggestion (str), risk_level (str), raw (str).
    """
    fallback = {
        "trend": "N/A",
        "suggestion": "N/A",
        "risk_level": "N/A",
        "raw": raw_text,
    }

    if not raw_text or not raw_text.strip():
        return fallback

    # --- 趨勢判斷 ---
    trend = "N/A"
    if "多頭" in raw_text:
        trend = "多頭"
    elif "空頭" in raw_text:
        trend = "空頭"
    elif "盤整" in raw_text:
        trend = "盤整"

    # --- 風險等級 ---
    # 優先比對「風險：X」格式，再退回全文搜尋
    risk_level = "N/A"
    lines = raw_text.splitlines()
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("風險") and ("：" in stripped or ":" in stripped):
            # 取冒號後內容
            after_colon = stripped.split("：", 1)[-1].split(":", 1)[-1].strip()
            if "低" in after_colon:
                risk_level = "低"
            elif "高" in after_colon:
                risk_level = "高"
            elif "中" in after_colon:
                risk_level = "中"
            break

    if risk_level == "N/A":
        # 退回全文模糊搜尋（「風險偏低」、「風險偏高」、「風險：低，...」等）
        if (
            "風險偏低" in raw_text
            or "低風險" in raw_text
            or "風險低" in raw_text
            or "風險：低" in raw_text
            or "風險:低" in raw_text
        ):
            risk_level = "低"
        elif (
            "風險偏高" in raw_text
            or "高風險" in raw_text
            or "風險高" in raw_text
            or "風險：高" in raw_text
            or "風險:高" in raw_text
        ):
            risk_level = "高"
        elif (
            "風險偏中" in raw_text
            or "中等風險" in raw_text
            or "風險中" in raw_text
            or "風險：中" in raw_text
            or "風險:中" in raw_text
        ):
            risk_level = "中"

    # --- 操作建議 ---
    suggestion = "N/A"
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("操作建議") and ("：" in stripped or ":" in stripped):
            after_colon = stripped.split("：", 1)[-1].split(":", 1)[-1].strip()
            if after_colon:
                suggestion = after_colon
            break

    if suggestion == "N/A":
        # 若無明確標籤，取全文作為建議
        cleaned = raw_text.strip()
        if cleaned:
            suggestion = cleaned[:200]  # 最多 200 字

    return {
        "trend": trend,
        "suggestion": suggestion,
        "risk_level": risk_level,
        "raw": raw_text,
    }


# ---------------------------------------------------------------------------
# 主要 API 呼叫函式
# ---------------------------------------------------------------------------


def get_ai_analysis(
    stock_id: str,
    stock_name: str,
    indicators: dict,
) -> dict:
    """
    呼叫 Gemini API 取得個股 AI 技術分析。

    indicators dict 應包含以下 key：
        close, change_pct, ma5, ma20, ma60,
        bb_upper, bb_lower, k, d, dif, signal, osc,
        foreign_consecutive

    使用 gemini-2.0-flash（速度快、成本低），max_output_tokens=512。

    套件未安裝或 API Key 未設定時直接回傳帶 error 的 fallback dict。
    API 呼叫失敗時記錄 error log 並回傳 fallback dict，不向上拋出例外。

    Args:
        stock_id: 股票代號，例如 "2330"。
        stock_name: 股票名稱，例如 "台積電"。
        indicators: 技術指標 dict，見上方說明。

    Returns:
        dict with keys: trend (str), suggestion (str), risk_level (str), raw (str).
        失敗時額外包含 error (str) key，說明失敗原因。
    """
    _unavailable = {
        "trend": "N/A",
        "suggestion": "AI 分析暫時無法使用",
        "risk_level": "N/A",
        "raw": "",
    }

    if genai is None:
        err = "google-generativeai 套件未安裝，請執行 pip install google-generativeai"
        logger.error(err)
        return {**_unavailable, "error": err}

    if not GEMINI_API_KEY:
        err = "GEMINI_API_KEY 未設定，請在 .env 檔案中加入 GEMINI_API_KEY=your_key"
        logger.error(err)
        return {**_unavailable, "error": err}

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = build_analysis_prompt(
            stock_id=stock_id,
            stock_name=stock_name,
            close=indicators["close"],
            change_pct=indicators["change_pct"],
            ma5=indicators["ma5"],
            ma20=indicators["ma20"],
            ma60=indicators["ma60"],
            bb_upper=indicators["bb_upper"],
            bb_lower=indicators["bb_lower"],
            k_value=indicators["k"],
            d_value=indicators["d"],
            macd_dif=indicators["dif"],
            macd_signal=indicators["signal"],
            macd_osc=indicators["osc"],
            foreign_consecutive=indicators["foreign_consecutive"],
        )
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                max_output_tokens=512,
                temperature=0.3,
            ),
        )
        raw_text: str = response.text
        return parse_ai_response(raw_text)
    except Exception as e:
        err = str(e)
        logger.error(f"get_ai_analysis 失敗 stock_id={stock_id}: {err}")
        return {**_unavailable, "error": err}
