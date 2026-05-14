"""
macd_kd.py — KD 與 MACD 技術指標計算，及 M3 獨立圖表建構

提供：
- calc_kd:  計算 KD 隨機指標（Stochastic Oscillator）
- calc_macd: 計算 MACD 指標（DIF / Signal / OSC）
- build_indicator_chart: 建立 M3 KD+MACD 獨立 Plotly figure

設計規格參考：docs/design_spec.md M3 章節
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# ---------------------------------------------------------------------------
# 技術指標計算函式
# ---------------------------------------------------------------------------


def calc_kd(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 9,
) -> tuple[pd.Series, pd.Series]:
    """
    計算 KD 指標（隨機指標）。

    計算方式：
        RSV = (close - low.rolling(period).min()) /
              (high.rolling(period).max() - low.rolling(period).min()) * 100
        RSV 前 period-1 筆為 NaN；分母為 0 時 RSV 為 NaN（不拋出例外）。
        RSV.fillna(50) 後進行 EWM 平滑：
        K = RSV_filled.ewm(com=2, adjust=False).mean()  # 等同 1/3 加權平滑
        D = K.ewm(com=2, adjust=False).mean()

    Args:
        high:   最高價 Series，index 為日期。
        low:    最低價 Series，index 為日期。
        close:  收盤價 Series，index 為日期。
        period: 計算週期（天數），預設 9。

    Returns:
        (K, D) 兩個等長 pd.Series，全部有效（無 NaN）。
    """
    lowest_low = low.rolling(period).min()
    highest_high = high.rolling(period).max()
    denominator = highest_high - lowest_low

    # 分母為 0 時使用 where 保持 NaN，避免 ZeroDivisionError 或 inf
    rsv = (close - lowest_low) / denominator.where(denominator != 0) * 100

    # 以 50 填補 NaN（RSV 初始值與 high==low 情境）
    rsv_filled = rsv.fillna(50.0)

    # ewm(com=2) 等同每次加權 1/3（新值）和 2/3（舊值）
    k = rsv_filled.ewm(com=2, adjust=False).mean()
    d = k.ewm(com=2, adjust=False).mean()

    return k, d


def calc_macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    計算 MACD 指標。

    計算方式：
        EMA_fast  = close.ewm(span=fast, adjust=False).mean()
        EMA_slow  = close.ewm(span=slow, adjust=False).mean()
        DIF       = EMA_fast - EMA_slow
        Signal    = DIF.ewm(span=signal, adjust=False).mean()
        OSC       = DIF - Signal

    Args:
        close:  收盤價 Series，index 為日期。
        fast:   快線 EMA 週期，預設 12。
        slow:   慢線 EMA 週期，預設 26。
        signal: Signal 線 EMA 週期，預設 9。

    Returns:
        (DIF, Signal, OSC) 三個等長 pd.Series，全部有效（ewm 不產生 NaN）。
    """
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    signal_line = dif.ewm(span=signal, adjust=False).mean()
    osc = dif - signal_line
    return dif, signal_line, osc


# ---------------------------------------------------------------------------
# 圖表建構函式
# ---------------------------------------------------------------------------


def build_indicator_chart(df: pd.DataFrame) -> go.Figure:
    """
    建立 M3 KD+MACD 獨立 Plotly figure。

    df 必須包含以下欄位（index 為日期）：
        Open, High, Low, Close, Volume

    子圖配置：
        row=1（高度 45%）：KD 指標（K 線、D 線、參考線）
        row=2（高度 55%）：MACD 指標（OSC 柱、DIF 線、Signal 線）

    Trace 加入順序（row=1，KD）：
        1. Scatter K 線（name="K"，color=#F0883E，width=1.5）
        2. Scatter D 線（name="D"，color=#58A6FF，width=1.5）
        3. Scatter 超賣線 20（color=#30363D，width=1，dash="dot"，showlegend=False）
        4. Scatter 超買線 80（color=#30363D，width=1，dash="dot"，showlegend=False）
        5. Scatter 中線 50（color=#30363D，width=0.5，dash="dash"，showlegend=False）

    Trace 加入順序（row=2，MACD）：
        1. Bar OSC 負值（name="OSC 空頭"，color=#3FB950）：正值位置填 None
        2. Bar OSC 正值（name="OSC 多頭"，color=#F85149）：負值位置填 None
        3. Scatter DIF（name="DIF"，color=#F0883E，width=1.5）
        4. Scatter Signal（name="Signal"，color=#58A6FF，width=1.5）

    Args:
        df: 含 Open/High/Low/Close/Volume 欄位的 DataFrame，index 為日期。

    Returns:
        已完整設定 layout 的 go.Figure，高度 280px。
    """
    # ------------------------------------------------------------------
    # 準備日期序列與技術指標
    # ------------------------------------------------------------------
    dates = df.index.strftime("%Y-%m-%d").tolist()
    n = len(dates)

    k, d = calc_kd(df["High"], df["Low"], df["Close"])
    dif, signal_line, osc = calc_macd(df["Close"])

    # OSC 正負分拆：負值 trace（空頭）保留負值，正值填 None；正值 trace 反之
    osc_bear_y = [v if v <= 0 else None for v in osc]
    osc_bull_y = [v if v > 0 else None for v in osc]

    # 參考線水平值（與 K/D 共用 X 軸）
    ref_x = dates

    # ------------------------------------------------------------------
    # 建立 subplots
    # ------------------------------------------------------------------
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.45, 0.55],
        subplot_titles=["KD", "MACD"],
    )

    # ------------------------------------------------------------------
    # row=1：KD 指標
    # ------------------------------------------------------------------

    # 1. K 線
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=k,
            name="K",
            mode="lines",
            line=dict(color="#B85C00", width=1.5),
        ),
        row=1,
        col=1,
    )

    # 2. D 線
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=d,
            name="D",
            mode="lines",
            line=dict(color="#0057B8", width=1.5),
        ),
        row=1,
        col=1,
    )

    # 3. 超賣線 20
    fig.add_trace(
        go.Scatter(
            x=ref_x,
            y=[20] * n,
            name="超賣 20",
            mode="lines",
            line=dict(color="#DDE1E9", width=1, dash="dot"),
            showlegend=False,
        ),
        row=1,
        col=1,
    )

    # 4. 超買線 80
    fig.add_trace(
        go.Scatter(
            x=ref_x,
            y=[80] * n,
            name="超買 80",
            mode="lines",
            line=dict(color="#DDE1E9", width=1, dash="dot"),
            showlegend=False,
        ),
        row=1,
        col=1,
    )

    # 5. 中線 50
    fig.add_trace(
        go.Scatter(
            x=ref_x,
            y=[50] * n,
            name="中線 50",
            mode="lines",
            line=dict(color="#DDE1E9", width=0.5, dash="dash"),
            showlegend=False,
        ),
        row=1,
        col=1,
    )

    # ------------------------------------------------------------------
    # row=2：MACD 指標
    # ------------------------------------------------------------------

    # 1. OSC 負值（空頭，綠色）
    fig.add_trace(
        go.Bar(
            x=dates,
            y=osc_bear_y,
            name="OSC 空頭",
            marker=dict(color="#1A7F4B", line=dict(width=0)),
        ),
        row=2,
        col=1,
    )

    # 2. OSC 正值（多頭，紅色）
    fig.add_trace(
        go.Bar(
            x=dates,
            y=osc_bull_y,
            name="OSC 多頭",
            marker=dict(color="#D92B2B", line=dict(width=0)),
        ),
        row=2,
        col=1,
    )

    # 3. DIF 線
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=dif,
            name="DIF",
            mode="lines",
            line=dict(color="#B85C00", width=1.5),
        ),
        row=2,
        col=1,
    )

    # 4. Signal 線
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=signal_line,
            name="Signal",
            mode="lines",
            line=dict(color="#0057B8", width=1.5),
        ),
        row=2,
        col=1,
    )

    # ------------------------------------------------------------------
    # Layout 設定
    # ------------------------------------------------------------------
    fig.update_layout(
        height=280,
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#FFFFFF",
            bordercolor="#DDE1E9",
            font=dict(color="#0A1628", family="JetBrains Mono"),
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            y=1.05,
            x=0,
            font=dict(color="#4A5568", size=11),
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#DDE1E9",
            borderwidth=1,
        ),
        margin=dict(l=60, r=60, t=30, b=30),
        barmode="overlay",
    )

    # subplot_titles 字型顏色與大小
    for annotation in fig.layout.annotations:
        annotation.update(font=dict(color="#4A5568", size=12))

    # ------------------------------------------------------------------
    # X 軸設定（type=category，消除非交易日缺口）
    # ------------------------------------------------------------------
    fig.update_xaxes(
        type="category",
        showgrid=True,
        gridcolor="#DDE1E9",
        tickfont=dict(color="#4A5568", family="JetBrains Mono"),
        showticklabels=False,
        row=1,
        col=1,
    )

    fig.update_xaxes(
        type="category",
        showgrid=True,
        gridcolor="#DDE1E9",
        tickfont=dict(color="#4A5568", family="JetBrains Mono"),
        showticklabels=True,
        row=2,
        col=1,
    )

    # ------------------------------------------------------------------
    # Y 軸設定
    # ------------------------------------------------------------------

    # row=1 KD Y 軸：固定範圍 [0, 100]
    fig.update_yaxes(
        range=[0, 100],
        tickvals=[0, 20, 50, 80, 100],
        showgrid=True,
        gridcolor="#DDE1E9",
        tickfont=dict(color="#4A5568", family="JetBrains Mono"),
        side="right",
        row=1,
        col=1,
    )

    # row=2 MACD Y 軸：自動範圍
    fig.update_yaxes(
        autorange=True,
        tickformat=".3f",
        showgrid=True,
        gridcolor="#DDE1E9",
        tickfont=dict(color="#4A5568", family="JetBrains Mono"),
        side="right",
        row=2,
        col=1,
    )

    return fig
