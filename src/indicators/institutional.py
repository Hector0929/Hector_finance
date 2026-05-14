"""
institutional.py — M5 三大法人籌碼計算與圖表建構

提供：
  - calc_institutional_net：取最近 N 日三大法人買賣超彙總
  - calc_consecutive_buy：計算連續買超天數
  - build_institutional_chart：建立 grouped bar chart + 合計線
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


# ---------------------------------------------------------------------------
# 色彩常數（來自設計系統）
# ---------------------------------------------------------------------------

_COLOR_FOREIGN = "#0057B8"   # 外資
_COLOR_TRUST = "#B85C00"     # 投信
_COLOR_DEALER = "#6B3DD1"    # 自營商
_COLOR_TOTAL = "#0A1628"     # 合計線
_BG_PRIMARY = "#FFFFFF"


# ---------------------------------------------------------------------------
# calc_institutional_net
# ---------------------------------------------------------------------------


def calc_institutional_net(
    foreign: pd.Series,
    trust: pd.Series,
    dealer: pd.Series,
    days: int = 20,
) -> pd.DataFrame:
    """
    取最近 days 筆資料，回傳三大法人買賣超彙總 DataFrame。

    Args:
        foreign: 外資買賣超（張），index 為日期。
        trust:   投信買賣超（張），index 為日期。
        dealer:  自營商買賣超（張），index 為日期。
        days:    取最近幾筆；若實際長度 < days，取全部。

    Returns:
        DataFrame，columns = ["date", "foreign", "trust", "dealer", "total"]。
        total = foreign + trust + dealer。
    """
    # 取最近 days 筆（tail 安全處理長度不足的情況）
    foreign = foreign.tail(days)
    trust = trust.tail(days)
    dealer = dealer.tail(days)

    # 對齊 index（取交集，以外資 index 為基準）
    idx = foreign.index

    df = pd.DataFrame(
        {
            "date": idx,
            "foreign": foreign.values,
            "trust": trust.reindex(idx).values,
            "dealer": dealer.reindex(idx).values,
        }
    )
    df["total"] = df["foreign"] + df["trust"] + df["dealer"]

    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# calc_consecutive_buy
# ---------------------------------------------------------------------------


def calc_consecutive_buy(series: pd.Series, threshold: int = 0) -> int:
    """
    計算 series 末端連續買超天數（> threshold）。

    從 series 最後一筆往前數，統計連續大於 threshold 的天數。
    若最後一筆 <= threshold，立即回傳 0。

    Args:
        series:    買賣超數列。
        threshold: 超過此值才視為買超（預設 0，即 > 0）。

    Returns:
        連續買超天數（int）；空 Series 或末端不符合條件時回傳 0。
    """
    if series.empty:
        return 0

    count = 0
    for val in reversed(series.values):
        if val > threshold:
            count += 1
        else:
            break
    return count


# ---------------------------------------------------------------------------
# build_institutional_chart
# ---------------------------------------------------------------------------


def build_institutional_chart(df_inst: pd.DataFrame) -> go.Figure:
    """
    建立三大法人籌碼 grouped bar chart。

    Args:
        df_inst: calc_institutional_net 的輸出，
                 columns = ["date", "foreign", "trust", "dealer", "total"]。

    Returns:
        Plotly Figure，包含三條 Bar trace（外資、投信、自營商）
        與一條 Scatter 合計線。

    規格：
    - barmode="group"
    - plot_bgcolor / paper_bgcolor = "#0D1117"
    - height=300，margin l=60 r=60 t=30 b=30
    - Y 軸 side="right"，xaxis.type="category"
    - hovermode="x unified"
    - legend 水平排列（orientation="h"，y=1.05）
    """
    x_labels = df_inst["date"].astype(str)

    fig = go.Figure()

    # --- 外資 Bar ---
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=df_inst["foreign"],
            name="外資",
            marker_color=_COLOR_FOREIGN,
        )
    )

    # --- 投信 Bar ---
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=df_inst["trust"],
            name="投信",
            marker_color=_COLOR_TRUST,
        )
    )

    # --- 自營商 Bar ---
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=df_inst["dealer"],
            name="自營商",
            marker_color=_COLOR_DEALER,
        )
    )

    # --- 合計 Scatter 線 ---
    fig.add_trace(
        go.Scatter(
            x=x_labels,
            y=df_inst["total"],
            name="合計",
            mode="lines",
            line=dict(color=_COLOR_TOTAL, width=1.5, dash="dot"),
        )
    )

    fig.update_layout(
        barmode="group",
        plot_bgcolor=_BG_PRIMARY,
        paper_bgcolor=_BG_PRIMARY,
        height=300,
        margin=dict(l=60, r=60, t=30, b=30),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#FFFFFF",
            bordercolor="#DDE1E9",
            font=dict(color="#0A1628", family="JetBrains Mono"),
        ),
        legend=dict(
            orientation="h",
            y=1.05,
            font=dict(color="#4A5568"),
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#DDE1E9",
            borderwidth=1,
        ),
        xaxis=dict(
            type="category",
            gridcolor="#DDE1E9",
            tickfont=dict(color="#4A5568", family="JetBrains Mono"),
        ),
        yaxis=dict(
            side="right",
            gridcolor="#DDE1E9",
            tickfont=dict(color="#4A5568", family="JetBrains Mono"),
        ),
    )

    return fig
