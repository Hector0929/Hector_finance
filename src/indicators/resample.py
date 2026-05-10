"""
resample.py — M8 多週期切換

將日K OHLCV DataFrame 重採樣為週K 或月K，供 Streamlit 儀表板圖表使用。
"""

import logging
import pandas as pd

logger = logging.getLogger(__name__)

# period 對應的 pandas resample rule
PERIOD_RESAMPLE_MAP: dict[str, str] = {
    "日K": "D",   # 不重採樣，直接回傳
    "週K": "W",
    "月K": "ME",  # pandas >= 2.2 用 "ME"，舊版用 "M"
}

# OHLCV 各欄位的重採樣聚合方式
_OHLCV_AGG = {
    "Open": "first",
    "High": "max",
    "Low": "min",
    "Close": "last",
    "Volume": "sum",
}


def resample_ohlcv(df: pd.DataFrame, period: str) -> pd.DataFrame:
    """
    將日K OHLCV DataFrame 重採樣為指定週期。

    Args:
        df: 日K OHLCV DataFrame，index 為 DatetimeIndex，
            欄位：Open, High, Low, Close, Volume。
        period: "日K" / "週K" / "月K"。

    Returns:
        重採樣後的 DataFrame（欄位相同）。
        "日K" 直接回傳 df（不重採樣）。
        不支援的 period 視為 "日K"，記錄 warning。

    重採樣規則：
        Open   → first
        High   → max
        Low    → min
        Close  → last
        Volume → sum

    結果 dropna()（移除無資料的週/月）。
    """
    if period not in PERIOD_RESAMPLE_MAP:
        logger.warning(
            "不支援的週期 %r，將視為 '日K' 直接回傳原始 DataFrame。", period
        )
        return df

    if period == "日K":
        return df

    rule = PERIOD_RESAMPLE_MAP[period]

    # 只對 DataFrame 中實際存在的欄位做聚合，避免 KeyError
    agg = {col: func for col, func in _OHLCV_AGG.items() if col in df.columns}

    # 嘗試以指定 rule 重採樣；若 pandas 版本較舊不支援 "ME"，改用 "M"
    try:
        resampled = df.resample(rule).agg(agg)
    except ValueError:
        if rule == "ME":
            logger.debug("pandas 版本不支援 'ME'，改用 'M' 重採樣。")
            resampled = df.resample("M").agg(agg)
        else:
            raise

    return resampled.dropna()


def get_period_label(period: str) -> str:
    """
    回傳週期對應的中文標籤，用於圖表標題。

    Args:
        period: "日K" / "週K" / "月K" 或其他字串。

    Returns:
        已知週期回傳對應標籤；未知週期回傳 "日K"。

    Examples:
        >>> get_period_label("週K")
        '週K'
        >>> get_period_label("季K")
        '日K'
    """
    known = {"日K", "週K", "月K"}
    return period if period in known else "日K"
