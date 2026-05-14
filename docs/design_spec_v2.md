# Design Spec — 台股個股分析儀表板 v2（Light Theme）
版本：v2.0  日期：2026-05-03

---

## 設計方向說明

參考 ASML 官網風格（https://www.asml.com/en/company/sustainability）：
- 白色背景，大量留白，呼吸感強
- 深海軍藍主文字，層次清晰
- 扁平無陰影卡片，邊框極細（1px，淺灰）
- 無圓角或小圓角（4px），現代感
- sans-serif 中文主體字型（Noto Sans TC）
- 數字使用等寬字型（JetBrains Mono）
- 唯一的色彩強調點：台股慣例紅漲綠跌，以及品牌藍 (#0057B8)

此規格為 v1.0（深色主題）的完整替代，兩者不共存。

---

## 1. 完整色彩系統

### CSS 變數定義

| 變數名稱 | Hex 值 | 用途說明 |
|----------|--------|----------|
| `--color-primary` | `#0057B8` | 品牌藍：按鈕、連結、強調邊框、圖表主色 |
| `--color-secondary` | `#003B7A` | 深藍：Hover 狀態、按鈕 pressed 狀態 |
| `--color-accent` | `#0057B8` | 與 primary 同值，保留供 Plotly 圖表引用 |
| `--color-up` | `#D92B2B` | 上漲（台股慣例紅）|
| `--color-down` | `#1A7F4B` | 下跌（台股慣例綠）|
| `--color-warning` | `#B85C00` | 警示橘（警告文字、MACD OSC 邊緣）|
| `--bg-primary` | `#FFFFFF` | 頁面主背景 |
| `--bg-surface` | `#F7F8FA` | 卡片、Sidebar、Tab 面板背景 |
| `--bg-hover` | `#EEF2F8` | 互動元件 Hover 背景 |
| `--bg-input` | `#FFFFFF` | 輸入框背景 |
| `--surface-border` | `#DDE1E9` | 卡片邊框、分隔線 |
| `--border-focus` | `#0057B8` | 輸入框 Focus 邊框 |
| `--text-primary` | `#0A1628` | 深海軍藍：主標題、數值 |
| `--text-secondary` | `#4A5568` | 次要說明、標籤文字 |
| `--text-muted` | `#9AA5B4` | 佔位符、已停用文字 |
| `--text-inverse` | `#FFFFFF` | 深色按鈕上的文字 |

### 台股顏色對應（設計系統 v1 → v2 對照）

| 用途 | v1（深色） | v2（淺色） |
|------|-----------|-----------|
| 上漲/多頭 | `#F85149` | `#D92B2B` |
| 下跌/空頭 | `#3FB950` | `#1A7F4B` |
| 強調藍 | `#58A6FF` | `#0057B8` |
| 頁面背景 | `#0D1117` | `#FFFFFF` |
| 卡片背景 | `#161B22` | `#F7F8FA` |
| 邊框 | `#30363D` | `#DDE1E9` |
| 主文字 | `#E6EDF3` | `#0A1628` |
| 次要文字 | `#8B949E` | `#4A5568` |

---

## 2. 字型規格

### Google Fonts 載入字串

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Noto+Sans+TC:wght@300;400;500;700&display=swap" rel="stylesheet">
```

### 字型對照表

| 用途 | font-family | weight | size | line-height |
|------|------------|--------|------|-------------|
| 頁面主體 | `'Noto Sans TC', sans-serif` | 400 | 14px | 1.6 |
| H1（股票名稱大標） | `'Noto Sans TC', sans-serif` | 700 | 24px | 1.2 |
| H2（區塊標題） | `'Noto Sans TC', sans-serif` | 500 | 18px | 1.3 |
| H3（子標題） | `'Noto Sans TC', sans-serif` | 500 | 15px | 1.4 |
| Metric 數值（大） | `'JetBrains Mono', monospace` | 600 | 22px | 1.0 |
| Metric 數值（小） | `'JetBrains Mono', monospace` | 400 | 14px | 1.0 |
| 標籤 / Caption | `'Noto Sans TC', sans-serif` | 400 | 11px | 1.4 |
| 表格數值 | `'JetBrains Mono', monospace` | 400 | 13px | 1.5 |
| 按鈕文字 | `'Noto Sans TC', sans-serif` | 500 | 13px | 1.0 |
| 圖表軸標 | `'JetBrains Mono', monospace` | 400 | 11px | — |

---

## 3. 元件規格

### 3.1 Card（卡片容器）

```css
.card {
    background-color: #F7F8FA;          /* --bg-surface */
    border: 1px solid #DDE1E9;          /* --surface-border */
    border-radius: 4px;
    padding: 16px 20px;
    box-shadow: none;                   /* 扁平無陰影 */
}
```

Hover 狀態（可點擊卡片）：
```css
.card:hover {
    border-color: #0057B8;
    background-color: #EEF2F8;
    cursor: pointer;
}
```

### 3.2 Metric Card（指標卡片）

沿用 `.card` 基礎，內部結構：

```css
.metric-card {
    background-color: #FFFFFF;
    border: 1px solid #DDE1E9;
    border-top: 3px solid #DDE1E9;     /* 頂部強調線，漲跌時覆蓋色彩 */
    border-radius: 4px;
    padding: 14px 16px;
    min-height: 80px;
}

.metric-card.up {
    border-top-color: #D92B2B;
}

.metric-card.down {
    border-top-color: #1A7F4B;
}

.metric-label {
    font-family: 'Noto Sans TC', sans-serif;
    font-size: 11px;
    font-weight: 400;
    color: #4A5568;                     /* --text-secondary */
    letter-spacing: 0.03em;
    text-transform: uppercase;
    margin-bottom: 6px;
}

.metric-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 22px;
    font-weight: 600;
    color: #0A1628;                     /* --text-primary，預設 */
    line-height: 1.0;
}

.metric-value.up    { color: #D92B2B; }
.metric-value.down  { color: #1A7F4B; }
.metric-value.muted { color: #9AA5B4; } /* 佔位符狀態 */
```

### 3.3 Button（按鈕）

Primary 按鈕（查詢、儲存筆記、AI 分析）：
```css
/* Streamlit 覆寫選擇器 */
[data-testid="baseButton-primary"] {
    background-color: #0057B8 !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 4px !important;
    font-family: 'Noto Sans TC', sans-serif !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 8px 16px !important;
    transition: background-color 0.15s ease;
}

[data-testid="baseButton-primary"]:hover {
    background-color: #003B7A !important;
}
```

Secondary 按鈕（重新整理、移除、次要操作）：
```css
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
```

### 3.4 Tab（頁籤）

```css
/* 頁籤列背景 */
[data-testid="stTabs"] > div:first-child {
    border-bottom: 2px solid #DDE1E9;
    background-color: #FFFFFF;
    gap: 0;
}

/* 單一頁籤 */
button[data-baseweb="tab"] {
    font-family: 'Noto Sans TC', sans-serif !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    color: #4A5568 !important;
    background-color: transparent !important;
    border-bottom: 2px solid transparent !important;
    padding: 10px 20px !important;
    margin-bottom: -2px;
    transition: color 0.15s ease, border-color 0.15s ease;
}

/* 選中頁籤 */
button[data-baseweb="tab"][aria-selected="true"] {
    color: #0057B8 !important;
    border-bottom-color: #0057B8 !important;
    background-color: transparent !important;
}

button[data-baseweb="tab"]:hover {
    color: #0057B8 !important;
    background-color: #EEF2F8 !important;
}
```

### 3.5 Sidebar（自選清單側邊欄）

```css
[data-testid="stSidebar"] {
    background-color: #F7F8FA !important;
    border-right: 1px solid #DDE1E9 !important;
}

[data-testid="stSidebar"] * {
    color: #0A1628 !important;
}

/* Sidebar 內的股票代號按鈕 */
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
```

### 3.6 Input（輸入框）

```css
[data-testid="stTextInput"] input {
    background-color: #FFFFFF;
    color: #0A1628;
    border: 1px solid #DDE1E9;
    border-radius: 4px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 14px;
    padding: 8px 12px;
    transition: border-color 0.15s ease;
}

[data-testid="stTextInput"] input:focus {
    border-color: #0057B8;
    outline: none;
    box-shadow: 0 0 0 3px rgba(0, 87, 184, 0.12);
}

[data-testid="stTextInput"] input::placeholder {
    color: #9AA5B4;
}
```

### 3.7 Selectbox（下拉選單）

```css
[data-testid="stSelectbox"] > div > div {
    background-color: #FFFFFF !important;
    color: #0A1628 !important;
    border: 1px solid #DDE1E9 !important;
    border-radius: 4px !important;
    font-family: 'Noto Sans TC', sans-serif !important;
    font-size: 13px !important;
}
```

### 3.8 Divider（分隔線）

```css
hr {
    border: none;
    border-top: 1px solid #DDE1E9;
    margin: 16px 0;
}
```

### 3.9 Expander（展開收合）

```css
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
}
```

---

## 4. Streamlit config.toml 設定

完整取代 `.streamlit/config.toml` 中的 `[theme]` 區段：

```toml
[server]
headless = true
enableCORS = false

[theme]
base = "light"
primaryColor = "#0057B8"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F7F8FA"
textColor = "#0A1628"
font = "sans serif"
```

說明：
- `base = "light"` 讓 Streamlit 預設使用淺色主題，避免深色覆蓋殘留
- `primaryColor` 控制按鈕、checkbox、slider、progress bar 等互動元件的主色
- `secondaryBackgroundColor` 控制 Sidebar、程式碼區塊、Expander 背景
- `font = "sans serif"` 設定為系統 sans-serif，再由 CSS 注入 Noto Sans TC 覆蓋

---

## 5. inject_global_css() 完整 CSS 字串

以下為可直接貼入 `app.py` 的完整 `inject_global_css()` 函式實作（取代現有版本）：

```python
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

/* Streamlit 主容器強制白底 */
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

/* Streamlit markdown 標題 */
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

/* ── st.metric（Streamlit 原生 metric 元件）────────────────── */
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

/* ── Caption / Info / Warning / Error ───────────────────── */
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

/* ── Table（財報指標表格）───────────────────────────────── */
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
```

---

## 6. Plotly 圖表主題設定（v2 Light）

v2 中所有 Plotly 圖表的 `layout` 必須從深色改為淺色底。以下為通用更新規則：

### 全域背景

| 屬性 | v1 值 | v2 值 |
|------|-------|-------|
| `plot_bgcolor` | `#0D1117` | `#FFFFFF` |
| `paper_bgcolor` | `#0D1117` | `#FFFFFF` |

### 軸線顏色

| 屬性 | v1 值 | v2 值 |
|------|-------|-------|
| `gridcolor` | `#30363D` | `#DDE1E9` |
| `tickfont.color` | `#8B949E` | `#4A5568` |
| `zerolinecolor` | `#30363D` | `#DDE1E9` |
| `linecolor` | `#30363D` | `#DDE1E9` |

### Legend

| 屬性 | v1 值 | v2 值 |
|------|-------|-------|
| `legend.font.color` | `#8B949E` | `#4A5568` |
| `legend.bgcolor` | `rgba(0,0,0,0)` | `rgba(255,255,255,0.9)` |
| `legend.bordercolor` | （無） | `#DDE1E9` |
| `legend.borderwidth` | （無） | `1` |

### Hover Label

| 屬性 | v1 值 | v2 值 |
|------|-------|-------|
| `hoverlabel.bgcolor` | `#161B22` | `#FFFFFF` |
| `hoverlabel.bordercolor` | `#30363D` | `#DDE1E9` |
| `hoverlabel.font.color` | `#E6EDF3` | `#0A1628` |

### Subplot Titles

| 屬性 | v1 值 | v2 值 |
|------|-------|-------|
| `annotation.font.color` | `#8B949E` | `#4A5568` |

### Plotly Trace 色彩（保持不變，僅略作調整）

| Trace | v1 值 | v2 值 | 說明 |
|-------|-------|-------|------|
| K棒上漲 | `#F85149` | `#D92B2B` | 稍深，在白底上對比更足 |
| K棒下跌 | `#3FB950` | `#1A7F4B` | 稍深，在白底上對比更足 |
| 布林上軌 | `#F0883E` | `#B85C00` | 橘色加深 |
| 布林中軌 | `#58A6FF` | `#0057B8` | 品牌藍 |
| 布林下軌 | `#3FB950` | `#1A7F4B` | 同下跌色 |
| 布林填充 | `rgba(88,166,255,0.05)` | `rgba(0,87,184,0.06)` | |
| MA5 | `#FFA657` | `#D4720A` | 橘黃加深 |
| MA20 | `#D2A21E` | `#A67C00` | 金色加深 |
| MA60 | `#A371F7` | `#6B3DD1` | 紫色加深 |
| 成交量上漲 | `#F85149` | `#D92B2B` | |
| 成交量下跌 | `#3FB950` | `#1A7F4B` | |
| KD K線 | `#F0883E` | `#B85C00` | |
| KD D線 | `#58A6FF` | `#0057B8` | |
| KD 參考線 | `#30363D` | `#DDE1E9` | |
| MACD DIF | `#F0883E` | `#B85C00` | |
| MACD Signal | `#58A6FF` | `#0057B8` | |
| MACD OSC 正 | `#F85149` | `#D92B2B` | |
| MACD OSC 負 | `#3FB950` | `#1A7F4B` | |
| 三大法人外資 | `#58A6FF` | `#0057B8` | |
| 三大法人投信 | `#F0883E` | `#B85C00` | |
| 三大法人自營 | `#A371F7` | `#6B3DD1` | |
| 財報圖表 bar 1 | `#58A6FF` | `#0057B8` | |
| 財報圖表 bar 2 | `#3FB950` | `#1A7F4B` | |
| 財報線圖 1 | `#F0883E` | `#B85C00` | |
| 財報線圖 2 | `#F85149` | `#D92B2B` | |
| 筆記迷你圖收盤線 | `#E6EDF3` | `#0A1628` | 白底改深色 |

---

## 7. 佔位框（Placeholder）樣式更新

深色主題的佔位框 `background:#161B22` 一律更新為：

```html
<div style="
    height: {HEIGHT}px;
    background: #F7F8FA;
    border: 1px solid #DDE1E9;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #9AA5B4;
    font-family: 'Noto Sans TC', sans-serif;
    font-size: 13px;
">請先搜尋股票代號</div>
```

---

## 8. Metric Card HTML 樣板更新

`_metric_card_html()` 中的卡片樣式需更新：

```python
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
```

漲跌幅卡片調用範例（border_top 顯示漲跌色）：
- 上漲：`color="#D92B2B"`, `border_top_color="#D92B2B"`
- 下跌：`color="#1A7F4B"`, `border_top_color="#1A7F4B"`
- 中性：`color="#0A1628"`, `border_top_color="#DDE1E9"`

佔位符卡片：
```python
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
```

---

## 9. 開發者注意事項

### config.toml 優先級
Streamlit 的 `config.toml` `[theme]` 設定會被 `inject_global_css()` 的 `<style>` 注入進一步覆蓋。兩者同時設定可確保：Streamlit 互動元件（slider、checkbox 等）使用品牌藍；深度客製的元件（card、tab）由 CSS 精細控制。

### 深色主題清除
`inject_global_css()` 中的 `body, .stApp { background-color: #FFFFFF; }` 必須確保選擇器優先級足以覆蓋 Streamlit 預設的深色背景。若仍出現殘留深色，加入 `!important`。

### Plotly template 取消使用
現有程式碼中部分財報圖表使用 `template="plotly_dark"`，v2 中一律改為 `template=None`（或移除此參數），再手動設定 `paper_bgcolor="#FFFFFF"` 與 `plot_bgcolor="#FFFFFF"`，避免 template 覆蓋手動設定。

### 顏色對比度（WCAG AA）
以下色彩組合在白色背景上的對比度均達 WCAG AA 標準（4.5:1 以上）：
- `#0A1628`（主文字）on `#FFFFFF`：contrast 16.1:1
- `#4A5568`（次要文字）on `#FFFFFF`：contrast 7.0:1
- `#D92B2B`（上漲紅）on `#FFFFFF`：contrast 4.8:1
- `#1A7F4B`（下跌綠）on `#FFFFFF`：contrast 5.3:1
- `#0057B8`（品牌藍）on `#FFFFFF`：contrast 7.3:1

### 修改範圍摘要（給 Developer）
1. `.streamlit/config.toml` — 替換 `[theme]` 區段（第 5~6 行）
2. `app.py` — 替換 `inject_global_css()` 整個函式
3. `app.py` — 替換 `_metric_card_html()` 與 `_placeholder_card_html()`
4. `src/indicators/bollinger.py` — 更新 `build_main_chart()` 中的 Plotly layout 設定（bgcolor、gridcolor、tickfont.color、hoverlabel）
5. `src/indicators/macd_kd.py` — 更新 `build_indicator_chart()` 中的 Plotly layout 設定
6. `src/indicators/institutional.py` — 更新 `build_institutional_chart()` 中的 Plotly layout 設定
7. `app.py` `render_financial_analysis()` — 移除 `template="plotly_dark"`，改為手動設定 bgcolor
8. `app.py` `render_notes_page()` — 更新迷你布林圖的 `paper_bgcolor`、`plot_bgcolor`、`yaxis.color`、`xaxis.color`、收盤線顏色（`#E6EDF3` → `#0A1628`）
9. 所有佔位框 HTML — 將 `background:#161B22` 替換為 `background:#F7F8FA`，將 `color:#8B949E` 替換為 `color:#9AA5B4`，將 `border:1px solid #30363D` 替換為 `border:1px solid #DDE1E9`

---

*文件結束 — Design Spec v2.0 Light Theme — 由 Designer Agent 產出 — 2026-05-03*
