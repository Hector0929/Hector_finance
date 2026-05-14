"""
finlab_client.py — 台股資料抓取與格式化輔助模組

資料來源：
- finlab：OHLCV 歷史資料、三大法人籌碼、全市場篩選
- TWSE OpenAPI：股票名稱（openapi.twse.com.tw）

設計規格參考：docs/design_spec.md M1 章節
"""

import os
import re
import logging
from typing import Optional

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 純邏輯輔助函式（無外部依賴）
# ---------------------------------------------------------------------------


def format_volume(volume: int) -> str:
    """
    將成交量（張）格式化為易讀字串。

    規則：
    - 0 ~ 9,999 張：顯示千分位整數 + 「 張」
    - >= 10,000 張：換算為萬張，保留 1 位小數 + 「 萬張」

    Args:
        volume: 成交量，單位張，非負整數。

    Returns:
        格式化後的字串，例如 "1,234 張" 或 "12.3 萬張"。
    """
    if volume < 10_000:
        return f"{volume:,} 張"
    else:
        wan = volume / 10_000
        return f"{wan:.1f} 萬張"


def format_change(value: float, is_pct: bool = False) -> str:
    """
    將漲跌金額或漲跌幅格式化為帶正負號的字串。

    Args:
        value:  漲跌數值（金額或百分比數字）。
        is_pct: 是否為百分比，預設 False。

    Returns:
        格式化字串，例如 "+1.50"、"-2.30%"、"0.00"。
    """
    suffix = "%" if is_pct else ""
    if value > 0:
        return f"+{value:.2f}{suffix}"
    elif value < 0:
        return f"{value:.2f}{suffix}"
    else:
        return f"0.00{suffix}"


def validate_stock_id(stock_id: str) -> bool:
    """
    驗證台股股票代號是否合法（4 或 5 碼純數字）。

    Args:
        stock_id: 使用者輸入的股票代號字串。

    Returns:
        True 若合法，False 若不合法。
    """
    return bool(re.fullmatch(r"\d{4,5}", stock_id))


def get_change_color(value: float) -> str:
    """
    依漲跌值回傳對應的色碼字串（台股慣例：漲紅跌綠）。

    Args:
        value: 漲跌數值。

    Returns:
        色碼字串（含 # 前綴）。
    """
    if value > 0:
        return "#D92B2B"
    elif value < 0:
        return "#1A7F4B"
    else:
        return "#0A1628"


# ---------------------------------------------------------------------------
# FinLab 初始化（單次登入）
# ---------------------------------------------------------------------------

_finlab_logged_in = False


def _ensure_finlab_login() -> bool:
    """確保 finlab 已登入，回傳是否成功。"""
    global _finlab_logged_in
    if _finlab_logged_in:
        return True
    try:
        import finlab
        api_token = os.getenv("FINLAB_API_TOKEN", "")
        if not api_token:
            logger.error("FINLAB_API_TOKEN 未設定")
            return False
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            finlab.login(api_token)
        _finlab_logged_in = True
        return True
    except Exception as exc:
        logger.error("finlab 登入失敗：%s", exc)
        return False


# ---------------------------------------------------------------------------
# TWSE OpenAPI：股票名稱（免 API key）
# ---------------------------------------------------------------------------

_twse_name_cache: dict[str, str] = {}


def fetch_stock_name(stock_id: str) -> str:
    """
    從 TWSE OpenAPI 取得股票中文名稱。
    結果快取於模組層級 dict，避免重複請求。

    Args:
        stock_id: 台股代號。

    Returns:
        股票中文名稱字串，找不到時回傳空字串。
    """
    if stock_id in _twse_name_cache:
        return _twse_name_cache[stock_id]
    try:
        resp = requests.get(
            "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL",
            timeout=10,
        )
        if resp.ok:
            for item in resp.json():
                _twse_name_cache[item["Code"]] = item["Name"]
        # 補上上市前市場（OTC）
        resp_otc = requests.get(
            "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes",
            timeout=10,
        )
        if resp_otc.ok:
            for item in resp_otc.json():
                code = item.get("SecuritiesCompanyCode", "")
                name = item.get("CompanyName", "")
                if code and name:
                    _twse_name_cache[code] = name
    except Exception as exc:
        logger.warning("fetch_stock_name 失敗：%s", exc)

    return _twse_name_cache.get(stock_id, "")


# ---------------------------------------------------------------------------
# 個股基本資訊（M1 標頭）
# ---------------------------------------------------------------------------


def fetch_stock_info(stock_id: str) -> dict:
    """
    取得個股基本資訊（收盤、漲跌、成交量、52週高低、名稱）。

    資料來源：
    - 名稱：TWSE OpenAPI
    - 收盤/成交量：finlab price 資料表
    - 52週高低：finlab 近 252 筆收盤價

    Args:
        stock_id: 合法的台股代號（4 或 5 碼數字字串）。

    Returns:
        含以下 key 的 dict，失敗時回傳 {}：
        stock_id, name, close, change, change_pct, volume, high_52w, low_52w
    """
    if not _ensure_finlab_login():
        return {}
    try:
        from finlab import data as finlab_data

        close_df: pd.DataFrame = finlab_data.get("price:收盤價")
        if stock_id not in close_df.columns:
            logger.error("fetch_stock_info: 找不到股票 %s", stock_id)
            return {}

        close_series = close_df[stock_id].dropna()
        if len(close_series) < 2:
            logger.error("fetch_stock_info: 股票 %s 資料不足", stock_id)
            return {}

        close_today = float(close_series.iloc[-1])
        close_prev = float(close_series.iloc[-2])
        change = round(close_today - close_prev, 2)
        change_pct = round((change / close_prev) * 100, 2) if close_prev != 0 else 0.0

        recent_252 = close_series.tail(252)
        high_52w = float(recent_252.max())
        low_52w = float(recent_252.min())

        # 成交量：股數 / 1000 = 張
        volume = 0
        try:
            vol_df: pd.DataFrame = finlab_data.get("price:成交股數")
            if stock_id in vol_df.columns:
                vol_series = vol_df[stock_id].dropna()
                if len(vol_series) > 0:
                    volume = int(float(vol_series.iloc[-1]) / 1000)
        except Exception as exc:
            logger.warning("成交量取得失敗：%s", exc)

        name = fetch_stock_name(stock_id)

        return {
            "stock_id": stock_id,
            "name": name,
            "close": close_today,
            "change": change,
            "change_pct": change_pct,
            "volume": volume,
            "high_52w": high_52w,
            "low_52w": low_52w,
        }

    except Exception as exc:
        logger.error("fetch_stock_info 失敗 stock_id=%s：%s", stock_id, exc)
        return {}


# ---------------------------------------------------------------------------
# 個股 OHLCV 歷史資料（M2/M3/M4 圖表）
# ---------------------------------------------------------------------------


def fetch_ohlcv(stock_id: str, days: int = 300) -> pd.DataFrame:
    """
    取得個股 OHLCV 歷史資料（供 K 線圖使用）。

    Args:
        stock_id: 台股代號。
        days:     取最近幾個交易日，預設 300（約 1.2 年）。

    Returns:
        DataFrame，index 為 DatetimeIndex，欄位：Open, High, Low, Close, Volume（張）。
        失敗時回傳空 DataFrame。
    """
    if not _ensure_finlab_login():
        return pd.DataFrame()
    try:
        from finlab import data as finlab_data

        open_df = finlab_data.get("price:開盤價")
        high_df = finlab_data.get("price:最高價")
        low_df = finlab_data.get("price:最低價")
        close_df = finlab_data.get("price:收盤價")
        vol_df = finlab_data.get("price:成交股數")

        for name, df in [("open", open_df), ("high", high_df), ("low", low_df),
                         ("close", close_df), ("vol", vol_df)]:
            if stock_id not in df.columns:
                logger.error("fetch_ohlcv: %s 找不到股票 %s", name, stock_id)
                return pd.DataFrame()

        ohlcv = pd.DataFrame({
            "Open":   open_df[stock_id],
            "High":   high_df[stock_id],
            "Low":    low_df[stock_id],
            "Close":  close_df[stock_id],
            "Volume": (vol_df[stock_id] / 1000).round(0),
        }).dropna().tail(days)

        ohlcv.index = pd.to_datetime(ohlcv.index)
        return ohlcv

    except Exception as exc:
        logger.error("fetch_ohlcv 失敗 stock_id=%s：%s", stock_id, exc)
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# 三大法人籌碼（M5）
# ---------------------------------------------------------------------------


def fetch_institutional(stock_id: str, days: int = 60) -> pd.DataFrame:
    """
    取得個股三大法人買賣超資料。

    Args:
        stock_id: 台股代號。
        days:     取最近幾個交易日，預設 60。

    Returns:
        DataFrame，欄位：date, foreign, trust, dealer, total（單位：張）。
        失敗時回傳空 DataFrame。
    """
    if not _ensure_finlab_login():
        return pd.DataFrame()
    try:
        from finlab import data as finlab_data

        foreign_df = finlab_data.get(
            "institutional_investors_trading_summary:外陸資買賣超股數(不含外資自營商)"
        )
        trust_df = finlab_data.get(
            "institutional_investors_trading_summary:投信買賣超股數"
        )
        dealer_df = finlab_data.get(
            "institutional_investors_trading_summary:自營商買賣超股數(自行買賣)"
        )

        def _get_series(df: pd.DataFrame, sid: str) -> pd.Series:
            if sid not in df.columns:
                return pd.Series(dtype=float)
            return df[sid].dropna()

        foreign_s = _get_series(foreign_df, stock_id)
        trust_s = _get_series(trust_df, stock_id)
        dealer_s = _get_series(dealer_df, stock_id)

        # 對齊 index，三表取交集
        idx = foreign_s.index.intersection(trust_s.index).intersection(dealer_s.index)
        if len(idx) == 0:
            return pd.DataFrame()

        result = pd.DataFrame({
            "date":    idx,
            "foreign": (foreign_s.reindex(idx) / 1000).round(0).astype(int),
            "trust":   (trust_s.reindex(idx) / 1000).round(0).astype(int),
            "dealer":  (dealer_s.reindex(idx) / 1000).round(0).astype(int),
        }).reset_index(drop=True)
        result["total"] = result["foreign"] + result["trust"] + result["dealer"]

        return result.tail(days).reset_index(drop=True)

    except Exception as exc:
        logger.error("fetch_institutional 失敗 stock_id=%s：%s", stock_id, exc)
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# 全市場資料（M10 條件篩選用）
# ---------------------------------------------------------------------------


def get_price_df() -> pd.DataFrame:
    """
    取得全台股收盤價 DataFrame（index=date, columns=stock_id）。
    失敗時回傳空 DataFrame。
    """
    if not _ensure_finlab_login():
        return pd.DataFrame()
    try:
        from finlab import data as finlab_data
        return finlab_data.get("price:收盤價")
    except Exception as exc:
        logger.error("get_price_df 失敗：%s", exc)
        return pd.DataFrame()


def get_volume_df() -> pd.DataFrame:
    """
    取得全台股成交量 DataFrame（單位：張，index=date, columns=stock_id）。
    失敗時回傳空 DataFrame。
    """
    if not _ensure_finlab_login():
        return pd.DataFrame()
    try:
        from finlab import data as finlab_data
        vol = finlab_data.get("price:成交股數")
        return (vol / 1000).round(0)
    except Exception as exc:
        logger.error("get_volume_df 失敗：%s", exc)
        return pd.DataFrame()
