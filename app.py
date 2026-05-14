"""
app.py — 台股個股分析儀表板 Streamlit 主程式

模組：
  M1 — 個股搜尋標頭
  M2 — K線+布林通道（與 M4 成交量整合）
  M3 — KD+MACD 技術指標副圖
  M5 — 三大法人籌碼
  M6 — AI 綜合評估
  M7 — 個人筆記（Notion）

設計規格參考：docs/design_spec.md
"""

import json
import logging
import yaml

import pandas as pd
import streamlit as st
import streamlit_authenticator as stauth
from dotenv import load_dotenv


def _write_secrets_to_files() -> None:
    """
    Streamlit Community Cloud 環境：從 st.secrets 寫出設定檔案。
    本機開發時 secrets 不存在，直接略過。
    """
    try:
        # Firebase 服務帳戶
        if "firebase_credentials" in st.secrets:
            creds = dict(st.secrets["firebase_credentials"])
            with open("firebase_credentials.json", "w") as f:
                json.dump(creds, f)

        # 登入設定
        if "AUTH_USERS" in st.secrets:
            users: dict = {}
            for uname, udata in st.secrets["AUTH_USERS"].items():
                users[uname] = {
                    "name": str(udata.get("name", uname)),
                    "password": str(udata["password"]),
                }
            auth_cfg = {
                "credentials": {"usernames": users},
                "cookie": {
                    "expiry_days": 30,
                    "key": str(st.secrets.get("AUTH_COOKIE_KEY", "stock_dashboard_secret_key")),
                    "name": "stock_dashboard_auth",
                },
            }
            with open("auth_config.yaml", "w") as f:
                yaml.dump(auth_cfg, f, allow_unicode=True)
    except Exception:
        pass

from src.data.finlab_client import (
    fetch_stock_info as _fetch_stock_info,
    fetch_ohlcv as _fetch_ohlcv,
    fetch_institutional as _fetch_institutional,
    format_volume,
    format_change,
    validate_stock_id,
    get_change_color,
)
from src.indicators.bollinger import build_main_chart, calc_bollinger, calc_ma
from src.indicators.macd_kd import build_indicator_chart, calc_kd, calc_macd
from src.indicators.institutional import build_institutional_chart, calc_institutional_net, calc_consecutive_buy
from src.ai.gemini_client import get_ai_analysis
from src.data.firebase_client import (
    create_note, get_notes, get_all_notes, delete_note, format_note_display,
    save_recent_search, get_recent_searches,
)
from src.portfolio.calculator import calc_portfolio
from src.watchlist.manager import (
    load_watchlist, add_stock, remove_stock, is_in_watchlist, get_watchlist_ids
)
from src.indicators.resample import resample_ohlcv, get_period_label

# ---------------------------------------------------------------------------
# 環境初始化
# ---------------------------------------------------------------------------

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 頁面設定（必須是第一個 Streamlit 呼叫）
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="台股個股分析儀表板",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# 快取包裝（在 app 層加 @st.cache_data，讓 src/ 保持無 Streamlit 依賴）
# ---------------------------------------------------------------------------


@st.cache_data(ttl=300)
def fetch_stock_info(stock_id: str) -> dict:
    """透過 finlab 取得個股基本資訊，快取 300 秒。"""
    return _fetch_stock_info(stock_id)


@st.cache_data(ttl=300)
def fetch_ohlcv(stock_id: str, days: int = 300) -> pd.DataFrame:
    """取得個股 OHLCV 歷史資料，快取 300 秒。"""
    return _fetch_ohlcv(stock_id, days)


@st.cache_data(ttl=300)
def fetch_institutional(stock_id: str, days: int = 60) -> pd.DataFrame:
    """取得三大法人買賣超資料，快取 300 秒。"""
    return _fetch_institutional(stock_id, days)


# ---------------------------------------------------------------------------
# 全域 CSS 注入
# ---------------------------------------------------------------------------


def inject_global_css() -> None:
    """注入 Google Fonts 及全域 CSS 變數與樣式（v2 Light Theme）。"""

    # Google Fonts
    st.markdown(
        """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Noto+Sans+TC:wght@300;400;500;700&display=swap" rel="stylesheet">
""",
        unsafe_allow_html=True,
    )

    # 全域 CSS
    st.markdown(
        """
<style>
/* ── CSS 變數 ───────────────────────────────────────────── */
:root {
    --color-primary:     #0057B8;
    --color-secondary:   #003B7A;
    --color-accent:      #0057B8;
    --color-up:          #D92B2B;
    --color-down:        #1A7F4B;
    --color-warning:     #B85C00;
    --bg-primary:        #FFFFFF;
    --bg-surface:        #F7F8FA;
    --bg-hover:          #EEF2F8;
    --bg-input:          #FFFFFF;
    --surface-border:    #DDE1E9;
    --border-focus:      #0057B8;
    --text-primary:      #0A1628;
    --text-secondary:    #4A5568;
    --text-muted:        #9AA5B4;
    --text-inverse:      #FFFFFF;
}

/* ── 全域重置 ────────────────────────────────────────────── */
body, .stApp {
    background-color: #FFFFFF;
    color: #0A1628;
    font-family: 'Noto Sans TC', sans-serif;
    font-size: 14px;
    line-height: 1.6;
}

.stApp {
    background-color: #FFFFFF !important;
}

section.main > div {
    padding-top: 24px;
    padding-bottom: 32px;
}

/* ── Typography ─────────────────────────────────────────── */
h1, h2, h3, h4 {
    font-family: 'Noto Sans TC', sans-serif;
    color: #0A1628;
    font-weight: 700;
    letter-spacing: -0.01em;
}

h1 { font-size: 24px; line-height: 1.2; }
h2 { font-size: 18px; line-height: 1.3; }
h3 { font-size: 15px; line-height: 1.4; font-weight: 500; }

[data-testid="stMarkdownContainer"] h3 {
    font-size: 15px;
    font-weight: 500;
    color: #0A1628;
    border-bottom: 1px solid #DDE1E9;
    padding-bottom: 6px;
    margin-bottom: 12px;
    margin-top: 8px;
}

/* ── Metric 元件 ─────────────────────────────────────────── */
.metric-label {
    font-family: 'Noto Sans TC', sans-serif;
    font-size: 11px;
    font-weight: 400;
    color: #4A5568;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    margin-bottom: 6px;
}

.metric-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 22px;
    font-weight: 600;
    color: #0A1628;
    line-height: 1.0;
}

/* ── Card ────────────────────────────────────────────────── */
.card {
    background-color: #F7F8FA;
    border: 1px solid #DDE1E9;
    border-radius: 4px;
    padding: 16px 20px;
    box-shadow: none;
}

.metric-card {
    background-color: #FFFFFF;
    border: 1px solid #DDE1E9;
    border-top: 3px solid #DDE1E9;
    border-radius: 4px;
    padding: 14px 16px;
    min-height: 80px;
}

.metric-card.up   { border-top-color: #D92B2B; }
.metric-card.down { border-top-color: #1A7F4B; }

/* ── Button ──────────────────────────────────────────────── */
[data-testid="baseButton-primary"] {
    background-color: #0057B8 !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 4px !important;
    font-family: 'Noto Sans TC', sans-serif !important;
    font-size: 13px !important;
    font-weight: 500 !important;
}

[data-testid="baseButton-primary"]:hover {
    background-color: #003B7A !important;
}

[data-testid="baseButton-secondary"] {
    background-color: #FFFFFF !important;
    color: #0057B8 !important;
    border: 1px solid #0057B8 !important;
    border-radius: 4px !important;
    font-family: 'Noto Sans TC', sans-serif !important;
    font-size: 13px !important;
    font-weight: 500 !important;
}

[data-testid="baseButton-secondary"]:hover {
    background-color: #EEF2F8 !important;
}

/* ── Tabs ────────────────────────────────────────────────── */
[data-testid="stTabs"] > div:first-child {
    border-bottom: 2px solid #DDE1E9;
    background-color: #FFFFFF;
    gap: 0;
}

button[data-baseweb="tab"] {
    font-family: 'Noto Sans TC', sans-serif !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    color: #4A5568 !important;
    background-color: transparent !important;
    border-bottom: 2px solid transparent !important;
    padding: 10px 20px !important;
    margin-bottom: -2px;
}

button[data-baseweb="tab"][aria-selected="true"] {
    color: #0057B8 !important;
    border-bottom-color: #0057B8 !important;
    background-color: transparent !important;
}

button[data-baseweb="tab"]:hover {
    color: #0057B8 !important;
    background-color: #EEF2F8 !important;
}

/* ── Sidebar ─────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background-color: #F7F8FA !important;
    border-right: 1px solid #DDE1E9 !important;
}

[data-testid="stSidebar"] h2 {
    font-size: 14px;
    font-weight: 700;
    color: #0A1628;
    letter-spacing: 0.02em;
    text-transform: uppercase;
    padding-bottom: 8px;
    border-bottom: 1px solid #DDE1E9;
    margin-bottom: 12px;
}

[data-testid="stSidebar"] [data-testid="baseButton-secondary"] {
    background-color: #FFFFFF !important;
    color: #0057B8 !important;
    border: 1px solid #DDE1E9 !important;
    border-radius: 4px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 13px !important;
    text-align: left !important;
}

[data-testid="stSidebar"] [data-testid="baseButton-secondary"]:hover {
    border-color: #0057B8 !important;
    background-color: #EEF2F8 !important;
}

/* ── Input ───────────────────────────────────────────────── */
[data-testid="stTextInput"] input {
    background-color: #FFFFFF;
    color: #0A1628;
    border: 1px solid #DDE1E9;
    border-radius: 4px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 14px;
    padding: 8px 12px;
}

[data-testid="stTextInput"] input:focus {
    border-color: #0057B8;
    outline: none;
    box-shadow: 0 0 0 3px rgba(0, 87, 184, 0.12);
}

[data-testid="stTextInput"] input::placeholder {
    color: #9AA5B4;
}

/* ── Selectbox ───────────────────────────────────────────── */
[data-testid="stSelectbox"] > div > div {
    background-color: #FFFFFF !important;
    color: #0A1628 !important;
    border: 1px solid #DDE1E9 !important;
    border-radius: 4px !important;
    font-family: 'Noto Sans TC', sans-serif !important;
    font-size: 13px !important;
}

/* ── Expander ────────────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid #DDE1E9 !important;
    border-radius: 4px !important;
    background-color: #FFFFFF !important;
    margin-bottom: 8px;
}

[data-testid="stExpander"] summary {
    font-family: 'Noto Sans TC', sans-serif !important;
    font-size: 13px !important;
    color: #0A1628 !important;
    padding: 12px 16px !important;
    font-weight: 500 !important;
}

[data-testid="stExpander"] summary:hover {
    background-color: #EEF2F8 !important;
}

/* ── Divider ─────────────────────────────────────────────── */
hr {
    border: none;
    border-top: 1px solid #DDE1E9;
    margin: 16px 0;
}

/* ── st.metric ────────────────────────────────────────────── */
[data-testid="metric-container"] {
    background-color: #FFFFFF;
    border: 1px solid #DDE1E9;
    border-radius: 4px;
    padding: 12px 16px;
}

[data-testid="stMetricLabel"] {
    font-family: 'Noto Sans TC', sans-serif !important;
    font-size: 11px !important;
    color: #4A5568 !important;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}

[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 20px !important;
    font-weight: 600 !important;
    color: #0A1628 !important;
}

[data-testid="stMetricDelta"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 12px !important;
}

/* ── Caption / Alert ─────────────────────────────────────── */
[data-testid="stCaptionContainer"] {
    color: #9AA5B4 !important;
    font-size: 12px !important;
}

[data-testid="stAlert"] {
    border-radius: 4px !important;
    font-family: 'Noto Sans TC', sans-serif !important;
    font-size: 13px !important;
}

/* ── Spinner ─────────────────────────────────────────────── */
[data-testid="stSpinner"] {
    color: #0057B8 !important;
}

/* ── Number Input ────────────────────────────────────────── */
[data-testid="stNumberInput"] input {
    background-color: #FFFFFF !important;
    color: #0A1628 !important;
    border: 1px solid #DDE1E9 !important;
    border-radius: 4px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 13px !important;
}

/* ── Textarea ────────────────────────────────────────────── */
textarea {
    background-color: #FFFFFF !important;
    color: #0A1628 !important;
    border: 1px solid #DDE1E9 !important;
    border-radius: 4px !important;
    font-family: 'Noto Sans TC', sans-serif !important;
    font-size: 13px !important;
}

textarea:focus {
    border-color: #0057B8 !important;
    box-shadow: 0 0 0 3px rgba(0, 87, 184, 0.12) !important;
}

/* ── Checkbox ────────────────────────────────────────────── */
[data-testid="stCheckbox"] label {
    font-family: 'Noto Sans TC', sans-serif !important;
    font-size: 13px !important;
    color: #0A1628 !important;
}

/* ── Table ───────────────────────────────────────────────── */
table {
    border-collapse: collapse;
    width: 100%;
}

th {
    font-family: 'Noto Sans TC', sans-serif;
    font-size: 11px;
    font-weight: 700;
    color: #4A5568;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    padding: 8px 12px;
    border-bottom: 2px solid #DDE1E9;
    background-color: #F7F8FA;
    text-align: right;
}

td {
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    color: #0A1628;
    padding: 8px 12px;
    border-bottom: 1px solid #DDE1E9;
    text-align: right;
}

td:first-child, th:first-child {
    text-align: left;
    font-family: 'Noto Sans TC', sans-serif;
    color: #4A5568;
}

tr:hover td {
    background-color: #EEF2F8;
}
</style>
""",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# session_state 初始化
# ---------------------------------------------------------------------------


def init_session_state() -> None:
    """初始化 session_state 關鍵 key。"""
    defaults = {
        "current_stock": "",
        "current_period": "日K",
        "stock_data": {},
        "ohlcv_data": pd.DataFrame(),
        "institutional_data": None,
        "ai_analysis": None,
        "financial_data": {},
        "notes_data": [],
        "watchlist": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ---------------------------------------------------------------------------
# M1 指標卡片 HTML 生成
# ---------------------------------------------------------------------------


def _metric_card_html(label: str, value: str, color: str = "#0A1628",
                      border_top_color: str = "#DDE1E9") -> str:
    return f"""
<div style="
    background-color:#FFFFFF;
    border:1px solid #DDE1E9;
    border-top:3px solid {border_top_color};
    border-radius:4px;
    padding:14px 16px;
    min-height:80px;
">
  <div style="
      font-family:'Noto Sans TC',sans-serif;
      font-size:11px;
      color:#4A5568;
      text-transform:uppercase;
      letter-spacing:0.03em;
      margin-bottom:6px;
  ">{label}</div>
  <div style="
      font-family:'JetBrains Mono',monospace;
      font-size:22px;
      font-weight:600;
      color:{color};
      line-height:1.0;
  ">{value}</div>
</div>
"""


def _placeholder_card_html(label: str) -> str:
    return f"""
<div style="
    background-color:#FFFFFF;
    border:1px solid #DDE1E9;
    border-top:3px solid #DDE1E9;
    border-radius:4px;
    padding:14px 16px;
    min-height:80px;
">
  <div style="
      font-family:'Noto Sans TC',sans-serif;
      font-size:11px;
      color:#9AA5B4;
      text-transform:uppercase;
      letter-spacing:0.03em;
      margin-bottom:6px;
  ">{label}</div>
  <div style="
      font-family:'JetBrains Mono',monospace;
      font-size:22px;
      font-weight:600;
      color:#9AA5B4;
      line-height:1.0;
  ">--</div>
</div>
"""


# ---------------------------------------------------------------------------
# M1 — render_header()
# ---------------------------------------------------------------------------


def render_header() -> None:
    """
    依照 design_spec.md M1 規格實作個股搜尋標頭。

    包含：
    1. 搜尋列（股票代號輸入 / 週期選擇 / 查詢按鈕）
    2. 7 欄指標卡片展示列
    3. 底部分隔線
    """

    with st.container():
        # ---------------------------------------------------------------
        # 第一列：搜尋列（使用 st.form 讓 Enter 與按鈕行為一致）
        # ---------------------------------------------------------------
        with st.form("search_form"):
            col_input, col_period, col_btn, col_spacer = st.columns([2, 1, 1, 6])

            with col_input:
                stock_input = st.text_input(
                    label="",
                    placeholder="輸入股票代號，如 2330",
                    max_chars=6,
                    key="stock_code_input",
                )

            with col_period:
                period = st.selectbox(
                    label="",
                    options=["日K", "週K", "月K"],
                    index=["日K", "週K", "月K"].index(
                        st.session_state.get("current_period", "日K")
                    ),
                    key="period_select",
                )

            with col_btn:
                submitted = st.form_submit_button(
                    label="查詢",
                    type="primary",
                    use_container_width=True,
                )

        # ---------------------------------------------------------------
        # 處理搜尋邏輯
        # ---------------------------------------------------------------
        if submitted and stock_input:
            stock_input = stock_input.strip()

            if not validate_stock_id(stock_input):
                st.warning("請輸入純數字的台股代號（如 2330）")
            else:
                with st.spinner("資料載入中..."):
                    data = fetch_stock_info(stock_input)

                if not data:
                    st.error(f"找不到股票代號「{stock_input}」，請確認後重新輸入")
                else:
                    st.session_state["current_stock"] = stock_input
                    st.session_state["stock_data"] = data
                    # 同步載入 OHLCV 與三大法人資料
                    ohlcv = fetch_ohlcv(stock_input)
                    if not ohlcv.empty:
                        st.session_state["ohlcv_data"] = ohlcv
                    inst = fetch_institutional(stock_input)
                    if not inst.empty:
                        st.session_state["institutional_data"] = inst
                    # 清除舊的 AI 分析、財報與筆記快取
                    st.session_state["ai_analysis"] = None
                    st.session_state["financial_data"] = {}
                    st.session_state["notes_data"] = []
                    # 記錄最近搜尋（不阻塞主流程）
                    _current_user = st.session_state.get("username", "default")
                    save_recent_search(stock_input, _current_user)

        # 週期選擇更新
        if period != st.session_state.get("current_period"):
            st.session_state["current_period"] = period

        # ---------------------------------------------------------------
        # 第二列：9 欄指標卡片
        # ---------------------------------------------------------------
        (
            col0, col1, col2, col3, col4, col5, col6, col7, col8
        ) = st.columns(9)

        data: dict = st.session_state.get("stock_data", {})
        has_data = bool(data)

        with col0:
            if has_data:
                st.markdown(
                    f"""
<div style="
    background-color:#FFFFFF;
    border:1px solid #DDE1E9;
    border-top:3px solid #0057B8;
    border-radius:4px;
    padding:14px 16px;
    min-height:80px;
">
  <div style="font-family:'Noto Sans TC',sans-serif;font-size:11px;color:#4A5568;text-transform:uppercase;letter-spacing:0.03em;margin-bottom:6px;">股票代號</div>
  <div style="font-family:'JetBrains Mono',monospace;font-size:22px;font-weight:700;color:#0A1628;line-height:1.0;">
    {data["stock_id"]}
  </div>
  <div style="font-family:'Noto Sans TC',sans-serif;font-size:11px;color:#4A5568;margin-top:4px;">{data["name"]}</div>
</div>
""",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    _placeholder_card_html("股票代號"), unsafe_allow_html=True
                )

        with col1:
            if has_data:
                st.markdown(
                    _metric_card_html(
                        "最新收盤價",
                        f"{data['close']:.2f} 元",
                        "#0A1628",
                    ),
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(_placeholder_card_html("最新收盤價"), unsafe_allow_html=True)

        with col2:
            if has_data:
                chg_color = get_change_color(data["change"])
                st.markdown(
                    _metric_card_html(
                        "漲跌金額",
                        f"{format_change(data['change'])} 元",
                        chg_color,
                        border_top_color=chg_color,
                    ),
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(_placeholder_card_html("漲跌金額"), unsafe_allow_html=True)

        with col3:
            if has_data:
                pct_color = get_change_color(data["change_pct"])
                st.markdown(
                    _metric_card_html(
                        "漲跌幅",
                        format_change(data["change_pct"], is_pct=True),
                        pct_color,
                        border_top_color=pct_color,
                    ),
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(_placeholder_card_html("漲跌幅"), unsafe_allow_html=True)

        with col4:
            if has_data:
                st.markdown(
                    _metric_card_html(
                        "成交量",
                        format_volume(data["volume"]),
                        "#0A1628",
                    ),
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(_placeholder_card_html("成交量"), unsafe_allow_html=True)

        with col5:
            if has_data:
                st.markdown(
                    _metric_card_html(
                        "52週高",
                        f"{data['high_52w']:.2f} 元",
                        "#D92B2B",
                        border_top_color="#D92B2B",
                    ),
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(_placeholder_card_html("52週高"), unsafe_allow_html=True)

        with col6:
            if has_data:
                st.markdown(
                    _metric_card_html(
                        "52週低",
                        f"{data['low_52w']:.2f} 元",
                        "#1A7F4B",
                        border_top_color="#1A7F4B",
                    ),
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(_placeholder_card_html("52週低"), unsafe_allow_html=True)

        with col7:
            if has_data and data.get("pe_ratio") is not None:
                st.markdown(
                    _metric_card_html("本益比 P/E", f"{data['pe_ratio']:.1f} x", "#0A1628"),
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(_placeholder_card_html("本益比 P/E"), unsafe_allow_html=True)

        with col8:
            if has_data and data.get("market_cap") is not None:
                mc = data["market_cap"]
                mc_str = f"{mc / 10000:.1f} 兆" if mc >= 10000 else f"{mc:.0f} 億"
                st.markdown(
                    _metric_card_html("市值", mc_str, "#0A1628"),
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(_placeholder_card_html("市值"), unsafe_allow_html=True)

        # 分隔線（M1 底部與 M2 之間）
        st.divider()


# ---------------------------------------------------------------------------
# M2+M4 — render_main_chart()
# ---------------------------------------------------------------------------


def render_main_chart() -> None:
    """
    依照 design_spec.md M2/M4 規格渲染 K線+布林通道與成交量整合圖表。

    尚未搜尋時顯示 540px 灰色佔位框；
    資料筆數少於 60 筆時顯示 warning；
    繪製失敗時顯示 error。
    """
    df: pd.DataFrame = st.session_state.get("ohlcv_data", pd.DataFrame())
    if df.empty:
        st.markdown(
            """<div style="height:540px;background:#F7F8FA;
                   border:1px solid #DDE1E9;border-radius:4px;
                   display:flex;align-items:center;justify-content:center;
                   color:#9AA5B4;font-family:'Noto Sans TC',sans-serif;font-size:13px;">
                   請先搜尋股票代號</div>""",
            unsafe_allow_html=True,
        )
        return

    period = st.session_state.get("current_period", "日K")
    df_plot = resample_ohlcv(df, period)

    if len(df_plot) < 60:
        st.warning("歷史資料不足，MA60 可能不完整")

    st.markdown(f"### K線圖 + 布林通道（{get_period_label(period)}）")
    try:
        fig = build_main_chart(df_plot)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    except Exception:
        st.error("圖表繪製失敗，請重新整理頁面")


# ---------------------------------------------------------------------------
# M3 — render_indicator_chart()
# ---------------------------------------------------------------------------


def render_indicator_chart() -> None:
    """
    依照 design_spec.md M3 規格渲染 KD+MACD 技術指標副圖。

    尚未搜尋時顯示 280px 灰色佔位框；
    資料筆數少於 9 筆時顯示 warning；
    繪製失敗時顯示 error。
    """
    st.markdown("### 技術指標：KD + MACD")

    df: pd.DataFrame = st.session_state.get("ohlcv_data", pd.DataFrame())
    if df.empty:
        st.markdown(
            """<div style="height:280px;background:#F7F8FA;
                   border:1px solid #DDE1E9;border-radius:4px;
                   display:flex;align-items:center;justify-content:center;
                   color:#9AA5B4;font-family:'Noto Sans TC',sans-serif;font-size:13px;">
                   請先搜尋股票代號</div>""",
            unsafe_allow_html=True,
        )
        return

    period = st.session_state.get("current_period", "日K")
    df_plot = resample_ohlcv(df, period)

    if len(df_plot) < 9:
        st.warning("歷史資料不足，KD 指標可能不準確")

    try:
        fig = build_indicator_chart(df_plot)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    except Exception:
        st.error("指標圖表繪製失敗，請重新整理頁面")


# ---------------------------------------------------------------------------
# M5 — render_institutional_chart()
# ---------------------------------------------------------------------------


def render_institutional_chart() -> None:
    """
    依照 design_spec.md M5 規格渲染三大法人籌碼 grouped bar chart。

    尚未搜尋時顯示 300px 灰色佔位框；
    institutional_data 存在時呼叫 build_institutional_chart 繪製圖表。
    """
    st.markdown("### 三大法人籌碼")

    if st.session_state.get("institutional_data") is None:
        st.markdown(
            """<div style="height:300px;background:#F7F8FA;border:1px solid #DDE1E9;
                   border-radius:4px;display:flex;align-items:center;
                   justify-content:center;color:#9AA5B4;font-family:'Noto Sans TC',sans-serif;font-size:13px;">
                   請先搜尋股票代號</div>""",
            unsafe_allow_html=True,
        )
        return

    df_inst = st.session_state["institutional_data"]
    fig = build_institutional_chart(df_inst)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ---------------------------------------------------------------------------
# M6 — render_ai_analysis()
# ---------------------------------------------------------------------------


def render_ai_analysis() -> None:
    """
    依照 design_spec.md M6 規格渲染 AI 綜合評估卡片。

    點擊「AI 分析」按鈕後呼叫 Claude API，顯示趨勢、建議、風險等級。
    """
    st.markdown("### AI 綜合評估")

    data: dict = st.session_state.get("stock_data", {})
    if not data or not isinstance(data, dict) or "stock_id" not in data:
        st.markdown(
            """<div style="height:160px;background:#F7F8FA;border:1px solid #DDE1E9;
                   border-radius:4px;display:flex;align-items:center;
                   justify-content:center;color:#9AA5B4;font-family:'Noto Sans TC',sans-serif;font-size:13px;">
                   請先搜尋股票代號</div>""",
            unsafe_allow_html=True,
        )
        return

    col_btn, col_spacer = st.columns([2, 8])
    with col_btn:
        if st.button("取得 AI 分析", key="ai_btn", use_container_width=True):
            with st.spinner("AI 分析中..."):
                ohlcv: pd.DataFrame = st.session_state.get("ohlcv_data", pd.DataFrame())
                inst_df: pd.DataFrame = st.session_state.get("institutional_data", pd.DataFrame())

                # 計算技術指標（取最後一筆有效值）
                ma5_val = ma20_val = ma60_val = 0.0
                bb_upper_val = bb_lower_val = 0.0
                k_val = d_val = 50.0
                dif_val = signal_val = osc_val = 0.0
                foreign_consec = 0

                if not ohlcv.empty and "Close" in ohlcv.columns:
                    close = ohlcv["Close"].dropna()
                    if len(close) >= 5:
                        ma5_val = float(calc_ma(close, 5).iloc[-1] or 0)
                    if len(close) >= 20:
                        ma20_val = float(calc_ma(close, 20).iloc[-1] or 0)
                        _, bb_upper_s, bb_lower_s = calc_bollinger(close)
                        bb_upper_val = float(bb_upper_s.iloc[-1] or 0)
                        bb_lower_val = float(bb_lower_s.iloc[-1] or 0)
                    if len(close) >= 60:
                        ma60_val = float(calc_ma(close, 60).iloc[-1] or 0)

                    dif_s, signal_s, osc_s = calc_macd(close)
                    dif_val = float(dif_s.iloc[-1] or 0)
                    signal_val = float(signal_s.iloc[-1] or 0)
                    osc_val = float(osc_s.iloc[-1] or 0)

                    if "High" in ohlcv.columns and "Low" in ohlcv.columns:
                        k_s, d_s = calc_kd(ohlcv["High"], ohlcv["Low"], close)
                        k_val = float(k_s.iloc[-1] or 50)
                        d_val = float(d_s.iloc[-1] or 50)

                if not inst_df.empty and "foreign" in inst_df.columns:
                    foreign_consec = calc_consecutive_buy(inst_df["foreign"])
                    if inst_df["foreign"].iloc[-1] < 0:
                        foreign_consec = -calc_consecutive_buy(-inst_df["foreign"])

                indicators = {
                    "close": data.get("close", 0),
                    "change_pct": data.get("change_pct", 0),
                    "ma5": ma5_val, "ma20": ma20_val, "ma60": ma60_val,
                    "bb_upper": bb_upper_val, "bb_lower": bb_lower_val,
                    "k": k_val, "d": d_val,
                    "dif": dif_val, "signal": signal_val, "osc": osc_val,
                    "foreign_consecutive": foreign_consec,
                }
                result = get_ai_analysis(
                    data["stock_id"], data.get("name", ""), indicators
                )
                st.session_state["ai_analysis"] = result

    analysis = st.session_state.get("ai_analysis")
    if analysis:
        if analysis.get("error"):
            st.error(f"AI 分析失敗：{analysis['error']}")
        else:
            trend_color = {"多頭": "#D92B2B", "空頭": "#1A7F4B"}.get(
                analysis.get("trend", ""), "#4A5568"
            )
            risk_color = {"低": "#1A7F4B", "中": "#B85C00", "高": "#D92B2B"}.get(
                analysis.get("risk_level", ""), "#4A5568"
            )
            st.markdown(
                f"""<div class="card" style="margin-top:12px;">
  <span style="font-family:'Noto Sans TC';color:#4A5568;font-size:12px;">趨勢方向</span>
  <span style="font-family:'JetBrains Mono';color:{trend_color};font-size:18px;font-weight:600;margin-left:8px;">{analysis.get("trend","N/A")}</span>
  &nbsp;&nbsp;
  <span style="font-family:'Noto Sans TC';color:#4A5568;font-size:12px;">風險等級</span>
  <span style="font-family:'JetBrains Mono';color:{risk_color};font-size:18px;font-weight:600;margin-left:8px;">{analysis.get("risk_level","N/A")}</span>
  <div style="margin-top:8px;color:#0A1628;font-size:14px;">{analysis.get("suggestion","")}</div>
</div>""",
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# M7 — render_notes()
# ---------------------------------------------------------------------------


def render_notes(user_id: str = "default") -> None:
    """
    依照 design_spec.md M7 規格渲染個人筆記區塊。

    包含新增筆記表單與已有筆記列表（含刪除按鈕）。
    """
    st.markdown("### 個人筆記")

    stock_id = st.session_state.get("current_stock", "")
    if not stock_id:
        st.markdown(
            """<div style="height:120px;background:#F7F8FA;border:1px solid #DDE1E9;
                   border-radius:4px;display:flex;align-items:center;
                   justify-content:center;color:#9AA5B4;font-family:'Noto Sans TC',sans-serif;font-size:13px;">
                   請先搜尋股票代號</div>""",
            unsafe_allow_html=True,
        )
        return

    # 新增筆記表單
    with st.expander("新增筆記", expanded=False):
        with st.form("note_form"):
            col_type, col_price, col_shares = st.columns([2, 2, 2])
            with col_type:
                note_type = st.selectbox("類型", ["買入", "賣出", "觀察", "其他"])
            with col_price:
                price = st.number_input("價格", min_value=0.0, value=0.0, step=0.5)
            with col_shares:
                shares = st.number_input("張數", min_value=0, value=1, step=1)
            content = st.text_area("備註", placeholder="輸入筆記內容...")
            if st.form_submit_button("儲存筆記", type="primary"):
                result = create_note(
                    stock_id=stock_id,
                    note_type=note_type,
                    price=float(price),
                    shares=int(shares),
                    content=content,
                    user_id=user_id,
                )
                if result.get("success"):
                    st.success("筆記已儲存")
                    st.session_state["notes_data"] = get_notes(stock_id, user_id)
                else:
                    st.error(f"儲存失敗：{result.get('message','')}")

    # 載入並顯示筆記列表
    if st.button("重新載入筆記", key="reload_notes"):
        st.session_state["notes_data"] = get_notes(stock_id, user_id)

    notes = st.session_state.get("notes_data", [])
    if not notes:
        st.caption("尚無筆記，請先新增。")
    else:
        for note in notes:
            col_text, col_del = st.columns([9, 1])
            with col_text:
                st.markdown(
                    f'<div style="padding:8px;color:#0A1628;font-size:13px;">'
                    f'{format_note_display(note)}</div>',
                    unsafe_allow_html=True,
                )
            with col_del:
                if st.button("🗑", key=f"del_{note['page_id']}"):
                    result = delete_note(note["page_id"])
                    if result.get("success"):
                        st.session_state["notes_data"] = get_notes(stock_id, user_id)
                        st.rerun()


# ---------------------------------------------------------------------------
# 財務分析 — render_financial_analysis()
# ---------------------------------------------------------------------------


def _metric_card(label: str, values: dict, years: list, fmt: str = "{:.1f}") -> str:
    """產生單一財務指標的 HTML 卡片（三年數值）。"""
    cells = ""
    for yr in years:
        val = values.get(yr)
        display = fmt.format(val) if val is not None else "N/A"
        cells += f'<td style="padding:4px 12px;text-align:right;color:#0A1628;">{display}</td>'
    return (
        f'<tr><td style="padding:4px 8px;color:#4A5568;white-space:nowrap;">{label}</td>'
        f"{cells}</tr>"
    )


def render_financial_analysis() -> None:
    """財務分析區塊：從 Goodinfo.tw 抓取財報並以 Plotly 圖表呈現。"""
    import plotly.graph_objects as go
    from src.data.goodinfo_client import get_financial_analysis

    stock_id = st.session_state.get("current_stock", "")
    if not stock_id:
        st.markdown(
            """<div style="height:200px;background:#F7F8FA;border:1px solid #DDE1E9;
                   border-radius:4px;display:flex;align-items:center;
                   justify-content:center;color:#9AA5B4;font-family:'Noto Sans TC',sans-serif;font-size:13px;">
                   請先搜尋股票代號</div>""",
            unsafe_allow_html=True,
        )
        return

    col_btn, col_cache, _ = st.columns([2, 3, 5])
    with col_btn:
        fetch_clicked = st.button("載入財報", key="fetch_fin", use_container_width=True)
    with col_cache:
        use_cache = st.checkbox("使用快取（24h）", value=True, key="fin_use_cache")

    if fetch_clicked:
        with st.spinner("從 Goodinfo.tw 抓取財報中..."):
            result = get_financial_analysis(stock_id, use_cache=use_cache)
        if "error" in result:
            st.error(f"財報抓取失敗：{result['error']}")
            return
        st.session_state["financial_data"] = result

    fin: dict = st.session_state.get("financial_data", {})
    if not fin or fin.get("stock_id") != stock_id:
        st.caption("點擊「載入財報」取得近三年財務數據。")
        return

    years = fin.get("years", [])[:3]
    metrics = fin.get("metrics", {})
    meta = fin.get("metadata", {})
    verification = fin.get("verification", {})

    # ── 資料來源 + 合理性檢查 ──────────────────────────────────
    src_time = meta.get("fetched_at", "")[:16].replace("T", " ")
    sanity_ok = verification.get("sanity_pass", True)
    badge = "✅ 合理性通過" if sanity_ok else "⚠️ 資料有警示"
    mops_url = meta.get("mops_url", "#")
    st.markdown(
        f'<div style="font-size:12px;color:#4A5568;margin-bottom:8px;">'
        f'資料來源：Goodinfo.tw｜抓取時間：{src_time}｜{badge}　'
        f'<a href="{mops_url}" target="_blank" style="color:#0057B8;">MOPS 官方申報</a></div>',
        unsafe_allow_html=True,
    )

    warnings = verification.get("sanity", [])
    for w in warnings:
        icon = "❌" if w["level"] == "error" else "⚠️"
        st.warning(f"{icon} [{w['field']}] {w['msg']}")

    # ── KPI 卡片（關鍵指標三年表） ────────────────────────────
    st.markdown("#### 關鍵財務指標")
    yr_header = "".join(
        f'<th style="padding:4px 12px;text-align:right;color:#0057B8;">{y}</th>'
        for y in years
    )
    rows = (
        _metric_card("營收（億元）",   {y: metrics.get(y, {}).get("revenue")     for y in years}, years, "{:.0f}")
        + _metric_card("毛利率（%）",  {y: metrics.get(y, {}).get("gross_margin") for y in years}, years, "{:.1f}%")
        + _metric_card("營業利益率（%）", {y: metrics.get(y, {}).get("op_margin")  for y in years}, years, "{:.1f}%")
        + _metric_card("淨利率（%）",  {y: metrics.get(y, {}).get("net_margin")   for y in years}, years, "{:.1f}%")
        + _metric_card("EPS（元）",    {y: metrics.get(y, {}).get("eps")          for y in years}, years, "{:.2f}")
        + _metric_card("ROE（%）",     {y: metrics.get(y, {}).get("roe")          for y in years}, years, "{:.1f}%")
        + _metric_card("ROA（%）",     {y: metrics.get(y, {}).get("roa")          for y in years}, years, "{:.1f}%")
        + _metric_card("流動比率（%）", {y: metrics.get(y, {}).get("current_ratio") for y in years}, years, "{:.0f}%")
        + _metric_card("負債比率（%）", {y: metrics.get(y, {}).get("debt_ratio")   for y in years}, years, "{:.1f}%")
    )
    st.markdown(
        f'<div class="card"><table style="width:100%;border-collapse:collapse;">'
        f'<thead><tr><th style="padding:4px 8px;text-align:left;color:#4A5568;">指標</th>'
        f'{yr_header}</tr></thead><tbody>{rows}</tbody></table></div>',
        unsafe_allow_html=True,
    )

    # ── Plotly 圖表 ───────────────────────────────────────────
    st.markdown("#### 財務趨勢圖")
    col_left, col_right = st.columns(2)

    # 營收 + 毛利率
    with col_left:
        rev_vals = [metrics.get(y, {}).get("revenue") for y in years]
        gm_vals  = [metrics.get(y, {}).get("gross_margin") for y in years]
        fig1 = go.Figure()
        fig1.add_bar(x=years, y=rev_vals, name="營收（億）", marker_color="#0057B8", yaxis="y")
        fig1.add_scatter(x=years, y=gm_vals, name="毛利率（%）", mode="lines+markers",
                         line=dict(color="#B85C00", width=2), yaxis="y2")
        fig1.update_layout(
            title="營收 & 毛利率", paper_bgcolor="#FFFFFF",
            plot_bgcolor="#FFFFFF", height=260, margin=dict(l=0, r=0, t=32, b=0),
            legend=dict(orientation="h", y=-0.2, font=dict(color="#4A5568")),
            yaxis=dict(title="億元", color="#4A5568", gridcolor="#DDE1E9"),
            yaxis2=dict(title="%", overlaying="y", side="right", color="#B85C00"),
        )
        st.plotly_chart(fig1, use_container_width=True, config={"displayModeBar": False})

    # EPS + ROE
    with col_right:
        eps_vals = [metrics.get(y, {}).get("eps") for y in years]
        roe_vals = [metrics.get(y, {}).get("roe") for y in years]
        fig2 = go.Figure()
        fig2.add_bar(x=years, y=eps_vals, name="EPS（元）", marker_color="#1A7F4B", yaxis="y")
        fig2.add_scatter(x=years, y=roe_vals, name="ROE（%）", mode="lines+markers",
                         line=dict(color="#D92B2B", width=2), yaxis="y2")
        fig2.update_layout(
            title="EPS & ROE", paper_bgcolor="#FFFFFF",
            plot_bgcolor="#FFFFFF", height=260, margin=dict(l=0, r=0, t=32, b=0),
            legend=dict(orientation="h", y=-0.2, font=dict(color="#4A5568")),
            yaxis=dict(title="元", color="#4A5568", gridcolor="#DDE1E9"),
            yaxis2=dict(title="%", overlaying="y", side="right", color="#D92B2B"),
        )
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    col_left2, col_right2 = st.columns(2)

    # 三層利潤率
    with col_left2:
        fig3 = go.Figure()
        for label, key, color in [
            ("毛利率", "gross_margin", "#0057B8"),
            ("營業利益率", "op_margin", "#B85C00"),
            ("淨利率", "net_margin", "#1A7F4B"),
        ]:
            vals = [metrics.get(y, {}).get(key) for y in years]
            fig3.add_scatter(x=years, y=vals, name=label, mode="lines+markers",
                             line=dict(color=color, width=2))
        fig3.update_layout(
            title="三層利潤率（%）", paper_bgcolor="#FFFFFF",
            plot_bgcolor="#FFFFFF", height=260, margin=dict(l=0, r=0, t=32, b=0),
            legend=dict(orientation="h", y=-0.2, font=dict(color="#4A5568")),
            yaxis=dict(title="%", color="#4A5568", gridcolor="#DDE1E9"),
        )
        st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})

    # 流動比率 + 負債比率
    with col_right2:
        cr_vals = [metrics.get(y, {}).get("current_ratio") for y in years]
        dr_vals = [metrics.get(y, {}).get("debt_ratio") for y in years]
        fig4 = go.Figure()
        fig4.add_bar(x=years, y=cr_vals, name="流動比率（%）", marker_color="#1A7F4B", yaxis="y")
        fig4.add_scatter(x=years, y=dr_vals, name="負債比率（%）", mode="lines+markers",
                         line=dict(color="#D92B2B", width=2), yaxis="y2")
        fig4.update_layout(
            title="財務健全度", paper_bgcolor="#FFFFFF",
            plot_bgcolor="#FFFFFF", height=260, margin=dict(l=0, r=0, t=32, b=0),
            legend=dict(orientation="h", y=-0.2, font=dict(color="#4A5568")),
            yaxis=dict(title="流動比率%", color="#4A5568", gridcolor="#DDE1E9"),
            yaxis2=dict(title="負債比率%", overlaying="y", side="right", color="#D92B2B"),
        )
        st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar": False})


# ---------------------------------------------------------------------------
# 獨立筆記頁面 — render_notes_page()
# ---------------------------------------------------------------------------

def _get_indicators_for_date(stock_id: str, target_date: str) -> dict:
    """
    從歷史 OHLCV 資料計算指定日期的技術指標。
    回傳 close, change_pct, k, d, bb_upper, bb_mid, bb_lower, bb_pos。
    """
    import pandas as pd
    ohlcv = fetch_ohlcv(stock_id)
    if ohlcv.empty:
        return {}

    target = pd.Timestamp(target_date)
    df = ohlcv[ohlcv.index <= target].copy()
    if df.empty:
        return {}

    close = df["Close"].dropna()
    if len(close) < 2:
        return {}

    # 漲跌幅
    change_pct = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100 if len(close) >= 2 else 0.0

    # KD
    k_val = d_val = 50.0
    if len(df) >= 9 and "High" in df.columns and "Low" in df.columns:
        k_s, d_s = calc_kd(df["High"], df["Low"], close)
        k_val = round(float(k_s.iloc[-1]), 2)
        d_val = round(float(d_s.iloc[-1]), 2)

    # 布林通道
    bb_upper_val = bb_mid_val = bb_lower_val = None
    bb_pos = "資料不足"
    if len(close) >= 20:
        bb_mid_s, bb_upper_s, bb_lower_s = calc_bollinger(close)
        bb_upper_val = round(float(bb_upper_s.iloc[-1]), 2)
        bb_mid_val   = round(float(bb_mid_s.iloc[-1]), 2)
        bb_lower_val = round(float(bb_lower_s.iloc[-1]), 2)
        c = float(close.iloc[-1])
        if c >= bb_upper_val * 0.97:
            bb_pos = "接近上軌（強勢）"
        elif c <= bb_lower_val * 1.03:
            bb_pos = "接近下軌（弱勢）"
        else:
            bb_pos = "中間區域"

    # 取當天前後 30 天的 OHLCV 供迷你圖
    idx = df.index.get_loc(df.index[-1]) if not df.empty else -1
    chart_df = ohlcv.iloc[max(0, idx - 29): idx + 1]

    return {
        "close": round(float(close.iloc[-1]), 2),
        "change_pct": round(change_pct, 2),
        "k": k_val, "d": d_val,
        "bb_upper": bb_upper_val, "bb_mid": bb_mid_val, "bb_lower": bb_lower_val,
        "bb_pos": bb_pos,
        "chart_df": chart_df,
    }


def render_notes_page(user_id: str = "default") -> None:
    """獨立筆記頁面：跨股票、可查看當日指標的筆記管理。"""
    import plotly.graph_objects as go
    from datetime import date as _date_cls

    st.markdown("### 📝 我的筆記")

    # ── 新增筆記 ───────────────────────────────────────────────
    with st.expander("➕ 新增筆記", expanded=False):
        with st.form("standalone_note_form"):
            col_sid, col_date, col_type = st.columns([2, 2, 2])
            with col_sid:
                new_stock = st.text_input("股票代號", placeholder="如 2330")
            with col_date:
                new_date = st.date_input("日期", value=_date_cls.today())
            with col_type:
                new_type = st.selectbox("類型", ["觀察", "買入", "賣出", "其他"])
            col_price, col_shares = st.columns([3, 3])
            with col_price:
                new_price = st.number_input("價格（選填）", min_value=0.0, value=0.0, step=0.5)
            with col_shares:
                new_shares = st.number_input("張數（選填）", min_value=0, value=0, step=1)
            new_content = st.text_area("筆記內容", placeholder="記錄你的觀察、想法...")
            if st.form_submit_button("儲存筆記", type="primary"):
                if not new_stock.strip():
                    st.warning("請輸入股票代號")
                elif not new_content.strip():
                    st.warning("筆記內容不能為空")
                else:
                    result = create_note(
                        stock_id=new_stock.strip(),
                        note_type=new_type,
                        price=float(new_price),
                        shares=int(new_shares),
                        content=new_content,
                        date=str(new_date),
                        user_id=user_id,
                    )
                    if result["success"]:
                        st.success("筆記已儲存")
                        st.session_state.pop("all_notes_cache", None)
                    else:
                        st.error(f"儲存失敗：{result['message']}")

    # ── 載入筆記列表 ───────────────────────────────────────────
    col_reload, col_filter, _ = st.columns([2, 3, 5])
    with col_reload:
        if st.button("重新整理", key="reload_all_notes"):
            st.session_state.pop("all_notes_cache", None)
    with col_filter:
        filter_stock = st.text_input("篩選股票", placeholder="輸入代號篩選", label_visibility="collapsed")

    if "all_notes_cache" not in st.session_state:
        with st.spinner("載入筆記中..."):
            st.session_state["all_notes_cache"] = get_all_notes(user_id)

    all_notes: list = st.session_state.get("all_notes_cache", [])
    if filter_stock.strip():
        all_notes = [n for n in all_notes if n.get("stock_id", "").startswith(filter_stock.strip())]

    if not all_notes:
        st.caption("尚無筆記，點上方「新增筆記」開始記錄。")
        return

    # ── 筆記卡片列表 ───────────────────────────────────────────
    for note in all_notes:
        sid       = note.get("stock_id", "")
        note_date = note.get("date", "")
        ntype     = note.get("note_type", "")
        content   = note.get("content", "")
        price     = note.get("price", 0.0)
        shares    = note.get("shares", 0)
        page_id   = note.get("page_id", "")

        type_color = {"買入": "#1A7F4B", "賣出": "#D92B2B", "觀察": "#0057B8", "其他": "#9AA5B4"}.get(ntype, "#9AA5B4")

        with st.expander(
            f"**{note_date}**　{sid}　"
            f"[{ntype}]　{content[:30]}{'...' if len(content) > 30 else ''}",
            expanded=False,
        ):
            col_info, col_del = st.columns([10, 1])
            with col_del:
                if st.button("🗑", key=f"np_del_{page_id}"):
                    result = delete_note(page_id)
                    if result["success"]:
                        st.session_state.pop("all_notes_cache", None)
                        st.rerun()

            with col_info:
                # 筆記內容
                st.markdown(
                    f'<div style="padding:8px 0;color:#0A1628;">{content}</div>',
                    unsafe_allow_html=True,
                )
                if price > 0 or shares > 0:
                    st.caption(f"價格：{price}　張數：{shares}")

                st.divider()

                # 載入當日指標
                cache_key = f"note_ind_{page_id}"
                if cache_key not in st.session_state:
                    with st.spinner(f"載入 {sid} {note_date} 指標中..."):
                        st.session_state[cache_key] = _get_indicators_for_date(sid, note_date)

                ind = st.session_state.get(cache_key, {})

                if not ind:
                    st.caption("無法取得該日技術指標（可能日期超出資料範圍）")
                else:
                    # 指標數字列
                    c1, c2, c3, c4 = st.columns(4)
                    close_color = "#D92B2B" if ind.get("change_pct", 0) >= 0 else "#1A7F4B"
                    c1.metric("收盤價", f"{ind['close']}", f"{ind['change_pct']:+.2f}%")
                    c2.metric("K 值", f"{ind['k']:.1f}")
                    c3.metric("D 值", f"{ind['d']:.1f}")
                    c4.metric("布林位置", ind.get("bb_pos", "N/A"))

                    # KD 狀態說明
                    k, d = ind["k"], ind["d"]
                    kd_desc = "超買區（K > 80）" if k > 80 else "超賣區（K < 20）" if k < 20 else "中性區間"
                    kd_color = "#D92B2B" if k > 80 else "#1A7F4B" if k < 20 else "#4A5568"
                    st.markdown(
                        f'<span style="font-size:12px;color:{kd_color};">KD 狀態：{kd_desc}</span>',
                        unsafe_allow_html=True,
                    )

                    # 布林通道數值
                    if ind.get("bb_upper"):
                        st.markdown(
                            f'<span style="font-size:12px;color:#4A5568;">'
                            f'BB 上軌：{ind["bb_upper"]}　中軌：{ind["bb_mid"]}　下軌：{ind["bb_lower"]}'
                            f'</span>',
                            unsafe_allow_html=True,
                        )

                    # 迷你布林通道圖（近 30 天）
                    chart_df = ind.get("chart_df")
                    if chart_df is not None and not chart_df.empty and len(chart_df) >= 5:
                        close_s = chart_df["Close"].dropna()
                        bb_mid_s, bb_up_s, bb_low_s = calc_bollinger(close_s)
                        dates = [str(d.date()) for d in chart_df.index]

                        fig = go.Figure()
                        fig.add_scatter(x=dates, y=bb_up_s.values, name="上軌",
                                        line=dict(color="#B85C00", width=1, dash="dot"), showlegend=False)
                        fig.add_scatter(x=dates, y=bb_mid_s.values, name="中軌",
                                        line=dict(color="#0057B8", width=1, dash="dash"), showlegend=False)
                        fig.add_scatter(x=dates, y=bb_low_s.values, name="下軌",
                                        line=dict(color="#1A7F4B", width=1, dash="dot"), showlegend=False,
                                        fill="tonexty", fillcolor="rgba(0,87,184,0.06)")
                        fig.add_scatter(x=dates, y=close_s.values, name="收盤",
                                        line=dict(color="#0A1628", width=2))
                        # 標記筆記當天
                        if note_date in dates:
                            note_idx = dates.index(note_date)
                            fig.add_scatter(
                                x=[note_date], y=[float(close_s.iloc[note_idx])],
                                mode="markers", marker=dict(color=type_color, size=10, symbol="diamond"),
                                name=ntype, showlegend=False,
                            )
                        fig.update_layout(
                            paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
                            height=200, margin=dict(l=0, r=0, t=8, b=0),
                            yaxis=dict(color="#4A5568", gridcolor="#DDE1E9"),
                            xaxis=dict(color="#4A5568", gridcolor="#DDE1E9"),
                        )
                        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key=f"note_chart_{page_id}")


# ---------------------------------------------------------------------------
# 持倉損益 — render_portfolio()
# ---------------------------------------------------------------------------


def render_portfolio(user_id: str = "default") -> None:
    """持倉損益頁面：從筆記計算 FIFO 持倉，顯示未實現/已實現損益。"""
    st.markdown("### 💼 持倉損益")

    # 載入所有筆記
    if "portfolio_notes_cache" not in st.session_state:
        with st.spinner("載入筆記資料中..."):
            st.session_state["portfolio_notes_cache"] = get_all_notes(user_id)

    col_reload, _ = st.columns([2, 8])
    with col_reload:
        if st.button("重新整理", key="reload_portfolio"):
            st.session_state.pop("portfolio_notes_cache", None)
            st.rerun()

    all_notes: list = st.session_state.get("portfolio_notes_cache", [])
    buy_sell = [n for n in all_notes if n.get("note_type") in ("買入", "賣出")]

    if not buy_sell:
        st.info("尚無買入／賣出筆記，請先在「我的筆記」頁面新增交易記錄。")
        return

    # 取得現價（從已載入的 OHLCV 快取，或直接用 fetch_stock_info）
    stock_ids = list({n["stock_id"] for n in buy_sell})
    current_prices: dict[str, float] = {}
    for sid in stock_ids:
        cached = st.session_state.get("stock_data", {})
        if cached.get("stock_id") == sid:
            current_prices[sid] = cached.get("close", 0.0)
        else:
            info = fetch_stock_info(sid)
            current_prices[sid] = info.get("close", 0.0) if info else 0.0

    portfolio = calc_portfolio(buy_sell, current_prices)

    # ── 總覽卡片 ──────────────────────────────────────────────
    pnl = portfolio["total_unrealized_pnl"]
    pnl_pct = portfolio["total_unrealized_pnl_pct"]
    pnl_color = "#D92B2B" if pnl >= 0 else "#1A7F4B"
    realized = portfolio["realized_pnl"]
    realized_color = "#D92B2B" if realized >= 0 else "#1A7F4B"

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            _metric_card_html("總成本（元）", f"{portfolio['total_cost']:,.0f}"),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            _metric_card_html("當前市值（元）", f"{portfolio['total_value']:,.0f}"),
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            _metric_card_html(
                "未實現損益",
                f"{'+' if pnl >= 0 else ''}{pnl:,.0f}（{pnl_pct:+.1f}%）",
                pnl_color,
                border_top_color=pnl_color,
            ),
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            _metric_card_html(
                "已實現損益",
                f"{'+' if realized >= 0 else ''}{realized:,.0f}",
                realized_color,
                border_top_color=realized_color,
            ),
            unsafe_allow_html=True,
        )

    st.markdown("")

    # ── 持倉明細 ──────────────────────────────────────────────
    positions = portfolio["positions"]
    if not positions:
        st.caption("目前無持倉（買入已全數賣出）。")
    else:
        st.markdown("#### 持倉明細")
        for pos in sorted(positions, key=lambda p: abs(p["unrealized_pnl"]), reverse=True):
            upnl = pos["unrealized_pnl"]
            upnl_pct = pos["unrealized_pnl_pct"]
            pos_color = "#D92B2B" if upnl >= 0 else "#1A7F4B"

            with st.expander(
                f"**{pos['stock_id']}**　"
                f"{pos['shares']} 張　"
                f"均成本 {pos['avg_cost']:.2f}　"
                f"現價 {pos['current_price']:.2f}　"
                f"損益 {'+' if upnl >= 0 else ''}{upnl:,.0f}（{upnl_pct:+.1f}%）",
                expanded=False,
            ):
                d1, d2, d3, d4 = st.columns(4)
                with d1:
                    st.metric("持倉張數", f"{pos['shares']} 張")
                with d2:
                    st.metric("平均成本", f"{pos['avg_cost']:.2f}")
                with d3:
                    st.metric("當前價格", f"{pos['current_price']:.2f}")
                with d4:
                    st.metric(
                        "損益",
                        f"{'+' if upnl >= 0 else ''}{upnl:,.0f}",
                        delta=f"{upnl_pct:+.1f}%",
                    )

    # ── 已實現損益說明 ──────────────────────────────────────────
    if realized != 0:
        st.markdown("---")
        st.caption(
            f"已實現損益（歷史出場）：{'+' if realized >= 0 else ''}{realized:,.0f} 元"
        )


# ---------------------------------------------------------------------------
# M9 — render_watchlist()
# ---------------------------------------------------------------------------


def render_watchlist(user_id: str = "default") -> None:
    """
    渲染自選清單側邊欄區塊。

    顯示目前清單、提供加入/移除當前股票的按鈕。
    """
    from src.data.firebase_client import (
        get_watchlist as fb_get_watchlist,
        save_watchlist as fb_save_watchlist,
    )

    st.sidebar.markdown("## 自選清單")

    # 初始化當前使用者的自選清單
    if "watchlist" not in st.session_state or st.session_state.get("_wl_user") != user_id:
        st.session_state["watchlist"] = fb_get_watchlist(user_id)
        st.session_state["_wl_user"] = user_id

    watchlist_ids: list[str] = st.session_state.get("watchlist", [])

    def _reload():
        st.session_state["watchlist"] = fb_get_watchlist(user_id)

    def _save(ids: list[str]):
        fb_save_watchlist(ids, user_id)
        st.session_state["watchlist"] = ids

    # 加入/移除當前股票
    stock_id = st.session_state.get("current_stock", "")
    if stock_id:
        in_list = stock_id in watchlist_ids
        label = "➖ 移除自選" if in_list else "➕ 加入自選"
        if st.sidebar.button(label, key="watchlist_toggle", use_container_width=True):
            if in_list:
                _save([s for s in watchlist_ids if s != stock_id])
            else:
                _save(watchlist_ids + [stock_id])
            st.rerun()

    # 顯示清單
    if not watchlist_ids:
        st.sidebar.caption("自選清單為空，搜尋股票後加入。")
    else:
        for sid in watchlist_ids:
            col_id, col_del = st.sidebar.columns([4, 1])
            with col_id:
                if st.button(sid, key=f"wl_{sid}", use_container_width=True):
                    with st.spinner("資料載入中..."):
                        data = fetch_stock_info(sid)
                    if data:
                        st.session_state["current_stock"] = sid
                        st.session_state["stock_data"] = data
                        ohlcv = fetch_ohlcv(sid)
                        if not ohlcv.empty:
                            st.session_state["ohlcv_data"] = ohlcv
                        inst = fetch_institutional(sid)
                        if not inst.empty:
                            st.session_state["institutional_data"] = inst
                        st.session_state["ai_analysis"] = None
                        st.session_state["financial_data"] = {}
                        st.session_state["notes_data"] = []
                    st.rerun()
            with col_del:
                if st.button("✕", key=f"wl_del_{sid}"):
                    _save([s for s in watchlist_ids if s != sid])
                    st.rerun()

    # ── 最近搜尋 ──────────────────────────────────────────────
    st.sidebar.divider()
    st.sidebar.markdown("## 最近搜尋")
    if "recent_searches" not in st.session_state or st.session_state.get("_rs_user") != user_id:
        st.session_state["recent_searches"] = get_recent_searches(user_id)
        st.session_state["_rs_user"] = user_id

    recent: list[str] = st.session_state.get("recent_searches", [])
    if not recent:
        st.sidebar.caption("尚無搜尋紀錄。")
    else:
        for sid in recent:
            if st.sidebar.button(sid, key=f"rs_{sid}", use_container_width=True):
                with st.spinner("資料載入中..."):
                    data = fetch_stock_info(sid)
                if data:
                    st.session_state["current_stock"] = sid
                    st.session_state["stock_data"] = data
                    ohlcv = fetch_ohlcv(sid)
                    if not ohlcv.empty:
                        st.session_state["ohlcv_data"] = ohlcv
                    inst = fetch_institutional(sid)
                    if not inst.empty:
                        st.session_state["institutional_data"] = inst
                    st.session_state["ai_analysis"] = None
                    st.session_state["financial_data"] = {}
                    st.session_state["notes_data"] = []
                st.rerun()


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


def main() -> None:
    """Streamlit 主程式入口。"""
    _write_secrets_to_files()
    inject_global_css()

    # ── 登入驗證 ──────────────────────────────────────────────
    import os
    if os.path.exists("auth_config.yaml"):
        with open("auth_config.yaml") as f:
            auth_cfg = yaml.safe_load(f)
    elif "AUTH_USERS" in st.secrets:
        # Streamlit Cloud：直接從 secrets 建構設定（不依賴寫檔成功）
        users = {}
        for uname, udata in st.secrets["AUTH_USERS"].items():
            users[uname] = {
                "name": str(udata.get("name", uname)),
                "password": str(udata["password"]),
            }
        auth_cfg = {
            "credentials": {"usernames": users},
            "cookie": {
                "expiry_days": 30,
                "key": str(st.secrets.get("AUTH_COOKIE_KEY", "stock_dashboard_secret_key")),
                "name": "stock_dashboard_auth",
            },
        }
    else:
        st.error("找不到登入設定檔（auth_config.yaml），請確認 Streamlit Secrets 已設定 AUTH_USERS。")
        st.stop()

    authenticator = stauth.Authenticate(
        auth_cfg["credentials"],
        auth_cfg["cookie"]["name"],
        auth_cfg["cookie"]["key"],
        auth_cfg["cookie"]["expiry_days"],
    )
    authenticator.login()

    if st.session_state.get("authentication_status") is False:
        st.error("帳號或密碼錯誤")
        return
    if st.session_state.get("authentication_status") is None:
        st.warning("請輸入帳號與密碼")
        return

    # 登入成功 — 取得當前使用者名稱
    current_user: str = st.session_state.get("username", "default")
    authenticator.logout("登出", "sidebar")

    # ── 主程式 ────────────────────────────────────────────────
    init_session_state()
    render_watchlist(current_user)
    render_header()

    tab_tech, tab_fin, tab_notes, tab_portfolio = st.tabs(
        ["📈 技術分析", "📊 財務分析", "📝 我的筆記", "💼 持倉損益"]
    )

    with tab_tech:
        render_main_chart()
        render_indicator_chart()
        render_institutional_chart()
        render_ai_analysis()
        render_notes(current_user)

    with tab_fin:
        render_financial_analysis()

    with tab_notes:
        render_notes_page(current_user)

    with tab_portfolio:
        render_portfolio(current_user)


if __name__ == "__main__":
    main()
