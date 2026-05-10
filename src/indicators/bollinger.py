"""
bollinger.py — 布林通道與移動平均線計算，及 M2+M4 整合圖表建構

提供：
- calc_bollinger: 計算布林通道（中軌、上軌、下軌）
- calc_ma: 計算簡單移動平均（SMA）
- build_main_chart: 建立 M2 K線+布林通道 與 M4 成交量整合的 Plotly figure

設計規格參考：docs/design_spec.md M2 / M4 章節
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# ---------------------------------------------------------------------------
# 技術指標計算函式
# ---------------------------------------------------------------------------


def calc_bollinger(
    close: pd.Series,
    window: int = 20,
    std: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    計算布林通道（Bollinger Bands）。

    計算方式：
    - mid   = close.rolling(window).mean()
    - upper = mid + std * close.rolling(window).std()
    - lower = mid - std * close.rolling(window).std()

    pandas rolling std 預設使用樣本標準差（ddof=1）。

    Args:
        close:  收盤價 Series，index 為日期。
        window: 移動窗格（天數），預設 20。
        std:    標準差倍數，預設 2.0。

    Returns:
        (mid, upper, lower) 三個等長 pd.Series，
        前 window-1 筆為 NaN。
    """
    rolling_mean = close.rolling(window).mean()
    rolling_std = close.rolling(window).std()
    mid = rolling_mean
    upper = rolling_mean + std * rolling_std
    lower = rolling_mean - std * rolling_std
    return mid, upper, lower


def calc_ma(close: pd.Series, window: int) -> pd.Series:
    """
    計算簡單移動平均（SMA）。

    Args:
        close:  收盤價 Series，index 為日期。
        window: 移動窗格（天數）。

    Returns:
        長度與 close 相同的 pd.Series，前 window-1 筆為 NaN。
    """
    return close.rolling(window).mean()


# ---------------------------------------------------------------------------
# 圖表建構函式
# ---------------------------------------------------------------------------


def build_main_chart(df: pd.DataFrame) -> go.Figure:
    """
    建立 M2（K線+布林通道）與 M4（成交量）整合的 Plotly figure。

    df 必須包含以下欄位（index 為日期）：
        Open, High, Low, Close, Volume

    子圖配置：
        row=1（高度 78%）：K線 + 布林通道 + MA5/MA20/MA60
        row=2（高度 22%）：成交量 Bar

    Trace 加入順序（row=1）：
        1. Candlestick（K棒）
        2. Scatter 布林下軌（fill=None）
        3. Scatter 布林上軌（fill="tonexty"，半透明填充）
        4. Scatter 布林中軌 / MA20
        5. Scatter MA5
        6. Scatter MA60

    Trace 加入順序（row=2）：
        7. Bar 成交量（顏色依漲跌逐日指定）

    Args:
        df: 含 Open/High/Low/Close/Volume 欄位的 DataFrame，index 為日期。

    Returns:
        已完整設定 layout 的 go.Figure，高度 540px。
    """
    # ------------------------------------------------------------------
    # 準備日期序列與技術指標
    # ------------------------------------------------------------------
    dates = df.index.strftime("%Y-%m-%d").tolist()
    close = df["Close"]
    open_ = df["Open"]

    mid, upper, lower = calc_bollinger(close, window=20, std=2.0)
    ma5 = calc_ma(close, window=5)
    ma60 = calc_ma(close, window=60)

    # 成交量顏色：收盤 >= 開盤 → 上漲紅色；收盤 < 開盤 → 下跌綠色
    # 平盤（close == open）歸入次要色 #8B949E
    vol_colors = [
        "#F85149" if c > o else "#3FB950" if c < o else "#8B949E"
        for c, o in zip(close, open_)
    ]

    # ------------------------------------------------------------------
    # 建立 subplots
    # ------------------------------------------------------------------
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=[0.78, 0.22],
    )

    # ------------------------------------------------------------------
    # row=1：K線 + 布林通道 + MA 線
    # ------------------------------------------------------------------

    # 1. Candlestick（K棒）
    fig.add_trace(
        go.Candlestick(
            x=dates,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=close,
            name="K線",
            increasing_line_color="#F85149",
            increasing_fillcolor="#F85149",
            decreasing_line_color="#3FB950",
            decreasing_fillcolor="#3FB950",
        ),
        row=1,
        col=1,
    )

    # 2. 布林下軌（fill=None，先加入以便上軌 tonexty 填充用）
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=lower,
            name="布林下軌",
            mode="lines",
            line=dict(color="#3FB950", width=1, dash="dot"),
            fill=None,
        ),
        row=1,
        col=1,
    )

    # 3. 布林上軌（fill="tonexty" 填充至下軌）
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=upper,
            name="布林上軌",
            mode="lines",
            line=dict(color="#F0883E", width=1, dash="dot"),
            fill="tonexty",
            fillcolor="rgba(88,166,255,0.05)",
        ),
        row=1,
        col=1,
    )

    # 4. 布林中軌 / MA20
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=mid,
            name="MA20/中軌",
            mode="lines",
            line=dict(color="#58A6FF", width=1.5),
        ),
        row=1,
        col=1,
    )

    # 5. MA5
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=ma5,
            name="MA5",
            mode="lines",
            line=dict(color="#FFA657", width=1.5),
        ),
        row=1,
        col=1,
    )

    # 6. MA60
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=ma60,
            name="MA60",
            mode="lines",
            line=dict(color="#A371F7", width=1.5),
        ),
        row=1,
        col=1,
    )

    # ------------------------------------------------------------------
    # row=2：成交量 Bar
    # ------------------------------------------------------------------
    fig.add_trace(
        go.Bar(
            x=dates,
            y=df["Volume"],
            name="成交量",
            marker=dict(
                color=vol_colors,
                line=dict(width=0),
            ),
            showlegend=True,
            hovertemplate="%{x}<br>成交量：%{y:,} 張<extra></extra>",
        ),
        row=2,
        col=1,
    )

    # ------------------------------------------------------------------
    # Layout 設定
    # ------------------------------------------------------------------
    fig.update_layout(
        height=540,
        plot_bgcolor="#0D1117",
        paper_bgcolor="#0D1117",
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#161B22",
            bordercolor="#30363D",
            font=dict(color="#E6EDF3", family="JetBrains Mono"),
        ),
        # Legend：水平排列，位於圖表上方
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(color="#8B949E", family="JetBrains Mono", size=11),
            bgcolor="rgba(0,0,0,0)",
        ),
        margin=dict(l=60, r=60, t=40, b=20),
    )

    # ------------------------------------------------------------------
    # X 軸設定
    # ------------------------------------------------------------------

    # row=1 的 X 軸：type=category，隱藏 tick labels，關閉 rangeslider
    fig.update_xaxes(
        type="category",
        showgrid=True,
        gridcolor="#30363D",
        tickfont=dict(color="#8B949E", family="JetBrains Mono"),
        showticklabels=False,
        rangeslider_visible=False,
        row=1,
        col=1,
    )

    # row=2 的 X 軸：type=category，顯示 tick labels
    fig.update_xaxes(
        type="category",
        showgrid=True,
        gridcolor="#30363D",
        tickfont=dict(color="#8B949E", family="JetBrains Mono"),
        showticklabels=True,
        nticks=8,
        row=2,
        col=1,
    )

    # ------------------------------------------------------------------
    # Y 軸設定
    # ------------------------------------------------------------------

    # row=1 的 Y 軸（價格）
    fig.update_yaxes(
        showgrid=True,
        gridcolor="#30363D",
        tickfont=dict(color="#8B949E", family="JetBrains Mono"),
        side="right",
        row=1,
        col=1,
    )

    # row=2 的 Y 軸（成交量）
    fig.update_yaxes(
        showgrid=True,
        gridcolor="#30363D",
        tickfont=dict(color="#8B949E", family="JetBrains Mono"),
        side="right",
        nticks=3,
        row=2,
        col=1,
    )

    return fig
