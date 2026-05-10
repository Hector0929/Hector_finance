"""
filter.py — 台股條件篩選模組（M10）

依成交量、漲跌幅等條件過濾全台股，供排程器與 Telegram Bot 使用。
"""

import logging
from typing import List

import pandas as pd

logger = logging.getLogger(__name__)


def run_screener(
    price_df: pd.DataFrame,
    volume_df: pd.DataFrame,
    min_volume: int = 3000,
    min_change_pct: float = 0.0,
    max_change_pct: float = 10.0,
) -> List[dict]:
    """
    依條件篩選全台股，回傳符合條件的股票清單。

    Parameters
    ----------
    price_df : pd.DataFrame
        全台股收盤價，index=date（DatetimeIndex），columns=stock_id。
    volume_df : pd.DataFrame
        全台股成交量（張），index=date（DatetimeIndex），columns=stock_id。
    min_volume : int, optional
        最小成交量（張），預設 3000。
    min_change_pct : float, optional
        最小漲跌幅（%），預設 0.0。
    max_change_pct : float, optional
        最大漲跌幅（%），避免抓到漲停鎖死，預設 10.0。

    Returns
    -------
    list[dict]
        符合條件的股票清單，每筆格式：
        {
            "stock_id": str,
            "close": float,
            "change_pct": float,
            "volume": int,
        }
        按 change_pct 由高到低排序。

    Notes
    -----
    篩選邏輯：
    1. 取最後一筆資料（最新交易日）
    2. 計算漲跌幅：(close - prev_close) / prev_close * 100
    3. 成交量 >= min_volume
    4. min_change_pct <= change_pct <= max_change_pct

    price_df 或 volume_df 為空時回傳 []，不拋出例外。
    """
    if price_df.empty or volume_df.empty:
        logger.warning("price_df 或 volume_df 為空，跳過篩選。")
        return []

    if len(price_df) < 2:
        logger.warning("price_df 資料不足兩筆，無法計算漲跌幅。")
        return []

    # 取最後兩筆（前日收盤、今日收盤）
    latest_close: pd.Series = price_df.iloc[-1]
    prev_close: pd.Series = price_df.iloc[-2]
    latest_volume: pd.Series = volume_df.iloc[-1]

    # 只處理三個 DataFrame 共有的股票
    common_stocks = latest_close.index.intersection(latest_volume.index).intersection(
        prev_close.index
    )

    results: List[dict] = []
    for stock_id in common_stocks:
        close_val = latest_close[stock_id]
        prev_val = prev_close[stock_id]
        vol_val = latest_volume[stock_id]

        # 跳過無效數值
        if pd.isna(close_val) or pd.isna(prev_val) or pd.isna(vol_val):
            continue
        if prev_val == 0:
            continue

        change_pct = (close_val - prev_val) / prev_val * 100.0
        volume_int = int(vol_val)

        # 套用篩選條件
        if volume_int < min_volume:
            continue
        if not (min_change_pct <= change_pct <= max_change_pct):
            continue

        results.append(
            {
                "stock_id": str(stock_id),
                "close": float(close_val),
                "change_pct": round(change_pct, 2),
                "volume": volume_int,
            }
        )

    # 按漲跌幅由高到低排序
    results.sort(key=lambda x: x["change_pct"], reverse=True)
    logger.info("條件篩選完成，共 %d 檔符合。", len(results))
    return results


def format_screener_message(results: List[dict], date: str = "") -> str:
    """
    將篩選結果格式化為 Telegram 訊息字串。

    Parameters
    ----------
    results : list[dict]
        run_screener() 回傳的股票清單。
    date : str, optional
        交易日期字串，例如 "2026-05-02"。

    Returns
    -------
    str
        格式化後的訊息，例如：

        📊 每日選股 2026-05-02
        共 2 檔符合條件：

        • 2330  +3.52%  量 5,234張
        • 2454  +4.11%  量 3,891張

        results 為空時回傳：「📊 每日選股 {date}\\n今日無符合條件股票」
    """
    header = f"📊 每日選股 {date}".strip()

    if not results:
        return f"{header}\n今日無符合條件股票"

    lines = [header, f"共 {len(results)} 檔符合條件：", ""]
    for item in results:
        stock_id = item["stock_id"]
        change_pct = item["change_pct"]
        volume = item["volume"]
        sign = "+" if change_pct >= 0 else ""
        lines.append(
            f"• {stock_id}  {sign}{change_pct:.2f}%  量 {volume:,}張"
        )

    return "\n".join(lines)
