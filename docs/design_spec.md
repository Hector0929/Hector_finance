# Design Spec — Phase 1 M1~M4
版本：v1.0  日期：2026-05-02

---

## 全域設定

### st.set_page_config 參數

| 參數 | 值 |
|------|----|
| `page_title` | `"台股個股分析儀表板"` |
| `page_icon` | `"📈"` |
| `layout` | `"wide"` |
| `initial_sidebar_state` | `"collapsed"` |

### Google Fonts 載入

透過 `st.markdown(..., unsafe_allow_html=True)` 在頁面最頂端注入以下 HTML：

```
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Noto+Sans+TC:wght@400;500;700&display=swap" rel="stylesheet">
```

### 全域 CSS（透過 st.markdown 注入）

以下 CSS 變數與 class 需透過 `<style>` 標籤注入：

**CSS 變數定義（:root）**

| 變數名稱 | 值 |
|----------|----|
| `--bg-primary` | `#0D1117` |
| `--bg-card` | `#161B22` |
| `--border-color` | `#30363D` |
| `--color-up` | `#F85149` |
| `--color-down` | `#3FB950` |
| `--color-accent` | `#58A6FF` |
| `--text-primary` | `#E6EDF3` |
| `--text-secondary` | `#8B949E` |

**全域樣式規則**

| 選擇器 | 屬性 | 值 |
|--------|------|----|
| `body` | `background-color` | `#0D1117` |
| `body` | `color` | `#E6EDF3` |
| `body` | `font-family` | `'Noto Sans TC', sans-serif` |
| `.stApp` | `background-color` | `#0D1117` |
| `.metric-value` | `font-family` | `'JetBrains Mono', monospace` |
| `.metric-value` | `font-size` | `24px` |
| `.metric-value` | `font-weight` | `600` |
| `.metric-label` | `font-family` | `'Noto Sans TC', sans-serif` |
| `.metric-label` | `font-size` | `12px` |
| `.metric-label` | `color` | `#8B949E` |
| `.card` | `background-color` | `#161B22` |
| `.card` | `border` | `1px solid #30363D` |
| `.card` | `border-radius` | `8px` |
| `.card` | `padding` | `16px` |

**Streamlit 元件覆寫（隱藏預設邊框/背景）**

| 選擇器 | 屬性 | 值 |
|--------|------|----|
| `[data-testid="stTextInput"] input` | `background-color` | `#161B22` |
| `[data-testid="stTextInput"] input` | `color` | `#E6EDF3` |
| `[data-testid="stTextInput"] input` | `border` | `1px solid #30363D` |
| `[data-testid="stTextInput"] input` | `font-family` | `'JetBrains Mono', monospace` |
| `[data-testid="stSelectbox"] div` | `background-color` | `#161B22` |
| `[data-testid="stSelectbox"] div` | `color` | `#E6EDF3` |
| `[data-testid="stSelectbox"] div` | `border-color` | `#30363D` |

---

## M1 — 個股搜尋標頭

### 1. 功能概述

頁面頂部的搜尋與基本資訊展示區塊。使用者輸入台股股票代號（4位數字，如「2330」），系統查詢後顯示：股票名稱、最新收盤價、當日漲跌金額、漲跌幅百分比、成交量、52週高低。搜尋成功後，此資訊持續顯示於所有圖表上方，直到下次搜尋更新。

### 2. Layout 規格

整體為一個全寬容器（`st.container`），內部垂直分為兩列：

**第一列：搜尋列**

| 欄位寬度比例 | 內容 |
|--------------|------|
| 2 | 股票代號輸入框 |
| 1 | 週期選擇下拉選單 |
| 1 | 查詢按鈕 |
| 6 | 空白（佔位） |

使用 `st.columns([2, 1, 1, 6])` 實現。

**第二列：指標展示列**

共 7 個指標欄，使用 `st.columns(7)` 均分，每欄顯示一個 metric card：

| 欄位索引 | 指標名稱 | 說明 |
|----------|----------|------|
| 0 | 股票代號 + 名稱 | 代號粗體大字，名稱小字次要色 |
| 1 | 最新收盤價 | 數值 + 「元」單位 |
| 2 | 漲跌金額 | 帶正負號，依漲跌套用顏色 |
| 3 | 漲跌幅 | 帶正負號 + 百分比符號，依漲跌套用顏色 |
| 4 | 成交量 | 數值 + 「張」單位 |
| 5 | 52週高 | 數值 + 「元」單位，紅色顯示 |
| 6 | 52週低 | 數值 + 「元」單位，綠色顯示 |

### 3. 元件清單

| 元件 | Streamlit 函式 | 參數說明 | 備註 |
|------|---------------|---------|------|
| 外層容器 | `st.container` | 無特殊參數 | 包覆整個 M1 區塊 |
| 搜尋列欄位 | `st.columns` | `[2, 1, 1, 6]` | 4 欄不等寬 |
| 股票代號輸入 | `st.text_input` | `label=""`, `placeholder="輸入股票代號，如 2330"`, `max_chars=6`, `key="stock_code_input"` | label 設為空字串，用 placeholder 提示 |
| 週期選擇 | `st.selectbox` | `label=""`, `options=["日K", "週K", "月K"]`, `index=0`, `key="period_select"` | 預設日K |
| 查詢按鈕 | `st.button` | `label="查詢"`, `type="primary"`, `key="search_btn"`, `use_container_width=True` | 按下觸發搜尋 |
| 指標展示列 | `st.columns` | `7` | 7 欄等寬 |
| 各指標 HTML 卡片 | `st.markdown` | `unsafe_allow_html=True` | 每欄用 `.card` + `.metric-value` class 渲染 |
| 分隔線 | `st.divider` | 無 | M1 底部與 M2 之間 |

### 4. 互動行為

| 觸發條件 | 行為 |
|----------|------|
| 使用者在輸入框按 Enter | 觸發搜尋（等同點擊查詢按鈕） |
| 點擊「查詢」按鈕 | 呼叫資料查詢函式，更新 `st.session_state["current_stock"]` |
| 查詢成功 | 第二列指標卡片以新資料渲染 |
| 查詢失敗（代號不存在） | 顯示錯誤提示（見「錯誤狀態 UI」） |
| 週期選擇變更 | 更新 `st.session_state["current_period"]`，觸發 M2/M3/M4 重新繪圖 |
| 頁面初始載入（無查詢紀錄） | 第二列顯示灰色佔位符（skeleton）文字 `--` |

`st.session_state` 關鍵 key：

| Key | 型別 | 初始值 | 說明 |
|-----|------|--------|------|
| `current_stock` | `str` | `""` | 當前查詢的股票代號 |
| `current_period` | `str` | `"日K"` | 當前選擇的週期 |
| `stock_data` | `dict` | `{}` | 從 API 取回的原始資料快取 |

### 5. 色彩與樣式

| 元素 | 色彩規則 |
|------|----------|
| 漲跌金額（正值） | `#F85149`（`--color-up`） |
| 漲跌金額（負值） | `#3FB950`（`--color-down`） |
| 漲跌幅（正值） | `#F85149`（`--color-up`） |
| 漲跌幅（負值） | `#3FB950`（`--color-down`） |
| 52週高數值 | `#F85149`（`--color-up`） |
| 52週低數值 | `#3FB950`（`--color-down`） |
| 最新收盤價 | `#E6EDF3`（`--text-primary`） |
| 指標卡片背景 | `#161B22`（`--bg-card`） |
| 指標卡片邊框 | `1px solid #30363D` |
| 指標標籤文字 | `#8B949E`（`--text-secondary`），12px |
| 指標數值文字 | `#E6EDF3`，`JetBrains Mono`，24px，font-weight 600 |
| 查詢按鈕背景 | `#58A6FF`（`--color-accent`） |
| 查詢按鈕文字 | `#0D1117`（`--bg-primary`） |

### 6. 錯誤狀態 UI

| 錯誤類型 | 顯示方式 | 元件 |
|----------|----------|------|
| 股票代號不存在 | 紅色 error 提示框，文字：「找不到股票代號「XXXX」，請確認後重新輸入」 | `st.error` |
| 輸入非數字字元 | 橘色 warning 提示框，文字：「請輸入純數字的台股代號（如 2330）」 | `st.warning` |
| API 連線失敗 | 紅色 error 提示框，文字：「資料載入失敗，請稍後再試（API 連線逾時）」 | `st.error` |
| 載入中 | 顯示 spinner，文字：「資料載入中...」 | `st.spinner` |

錯誤訊息顯示在搜尋列下方、指標卡片上方，寬度與搜尋列相同。

### 7. 開發者注意事項

- 輸入框的 Enter 送出行為：使用 `st.form` + `st.form_submit_button` 包裹搜尋列，確保 Enter 與按鈕點擊行為一致，form key 設為 `"search_form"`。
- 指標卡片使用純 HTML + CSS（透過 `st.markdown`），不使用 `st.metric`，以便完整控制色彩與字型。
- 漲跌幅正值前須加 `+` 號（Python f-string：`f"+{value:.2f}%"`），負值自動帶負號。
- 成交量超過 10,000 張時，以「萬張」為單位顯示（如「12.3 萬張」），格式化函式由 Developer 自行實作。
- 頁面初始狀態（`session_state["current_stock"] == ""`）時，指標欄顯示 `--` 佔位符，色彩為 `#8B949E`。

---

## M2 — K線+布林通道

### 1. 功能概述

主要技術分析圖表，顯示指定股票在選定週期（日/週/月）內的：
- 日本蠟燭圖（K線）
- 布林通道（Bollinger Bands）：上軌、中軌（MA20）、下軌
- 移動平均線：MA5、MA20、MA60

圖表為互動式（可縮放、拖拉、懸停查看數值），並與 M4 成交量圖整合為同一 Plotly figure（共用 X 軸）。

### 2. Layout 規格

- 使用 `st.plotly_chart` 全寬顯示（`use_container_width=True`）
- M2 圖高：**420px**
- M4 圖高：**120px**
- 兩者整合為單一 figure，使用 `make_subplots(rows=2, cols=1, row_heights=[0.78, 0.22], shared_xaxes=True)` 建立
- M2 佔 row 1，M4 佔 row 2
- 兩個子圖之間的垂直間距（`vertical_spacing`）：`0.02`
- 整體 figure 總高度：**540px**

### 3. 元件清單

| 元件 | Streamlit 函式 | 參數說明 | 備註 |
|------|---------------|---------|------|
| 圖表標題列 | `st.markdown` | `unsafe_allow_html=True` | 「K線圖 + 布林通道」標題文字 |
| 整合圖表 | `st.plotly_chart` | `figure=fig_main`, `use_container_width=True`, `config={"displayModeBar": False}` | 包含 M2+M4 |

### 4. 互動行為

| 觸發條件 | 行為 |
|----------|------|
| 滑鼠懸停於 K 棒 | 顯示 tooltip：日期、開、高、低、收、成交量 |
| 滑鼠懸停於 MA 線 | 顯示 tooltip：指標名稱、數值（保留 2 位小數） |
| 滑鼠懸停於布林通道線 | 顯示 tooltip：軌道名稱（上軌/中軌/下軌）、數值 |
| 框選（Box Select）或區間拖拉 | 縮放至選取區間，X 軸聯動（M2 與 M4 同步） |
| 雙擊圖表 | 還原至完整時間區間 |
| `current_stock` 或 `current_period` 變更 | 重新繪製整個 figure |

### 5. 色彩與樣式

**圖表整體背景**

| 屬性 | 值 |
|------|----|
| `plot_bgcolor` | `#0D1117` |
| `paper_bgcolor` | `#0D1117` |

**X 軸（row 1）**

| 屬性 | 值 |
|------|----|
| `showgrid` | `True` |
| `gridcolor` | `#30363D` |
| `tickfont.color` | `#8B949E` |
| `tickfont.family` | `JetBrains Mono` |
| `showticklabels` | `False`（row 1 隱藏，由 row 2 的 X 軸顯示） |
| `rangeslider.visible` | `False` |

**Y 軸（row 1，價格軸）**

| 屬性 | 值 |
|------|----|
| `showgrid` | `True` |
| `gridcolor` | `#30363D` |
| `tickfont.color` | `#8B949E` |
| `tickfont.family` | `JetBrains Mono` |
| `side` | `right` |

**Trace 設定**

| Trace | 型別 | 色彩 | 線寬/其他 |
|-------|------|------|-----------|
| K 棒（上漲） | `Candlestick` | increasing: `#F85149` | line.color 同填充色 |
| K 棒（下跌） | `Candlestick` | decreasing: `#3FB950` | line.color 同填充色 |
| 布林上軌 | `Scatter`, mode=`lines` | `#F0883E` | line.width=1, line.dash=`dot` |
| 布林中軌（MA20） | `Scatter`, mode=`lines` | `#58A6FF` | line.width=1.5 |
| 布林下軌 | `Scatter`, mode=`lines` | `#3FB950` | line.width=1, line.dash=`dot` |
| 布林通道填充 | `Scatter`, fill=`tonexty` | `rgba(88,166,255,0.05)` | 上軌與下軌之間的半透明填充 |
| MA5 | `Scatter`, mode=`lines` | `#FFA657` | line.width=1.5 |
| MA20 | `Scatter`, mode=`lines` | `#D2A21E` | line.width=1.5 |
| MA60 | `Scatter`, mode=`lines` | `#A371F7` | line.width=1.5 |

### 6. Plotly 圖表規格

**Subplots 建立**

```
make_subplots(
    rows=2,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.02,
    row_heights=[0.78, 0.22]
)
```

**Trace 加入順序（row=1）**

1. Candlestick（K 棒），name=`"K線"`
2. Scatter 布林下軌，name=`"布林下軌"`，fill=`None`
3. Scatter 布林上軌，name=`"布林上軌"`，fill=`"tonexty"`，fillcolor=`"rgba(88,166,255,0.05)"`
4. Scatter 布林中軌，name=`"MA20/中軌"`
5. Scatter MA5，name=`"MA5"`
6. Scatter MA60，name=`"MA60"`

**Legend 設定**

| 屬性 | 值 |
|------|----|
| `showlegend` | `True` |
| `legend.orientation` | `"h"`（水平） |
| `legend.yanchor` | `"bottom"` |
| `legend.y` | `1.02` |
| `legend.xanchor` | `"left"` |
| `legend.x` | `0` |
| `legend.font.color` | `#8B949E` |
| `legend.font.family` | `JetBrains Mono` |
| `legend.font.size` | `11` |
| `legend.bgcolor` | `rgba(0,0,0,0)` |

**Margin 設定**

| 方向 | 值（px） |
|------|----------|
| `margin.l` | `60` |
| `margin.r` | `60` |
| `margin.t` | `40` |
| `margin.b` | `20` |

**Hover 設定**

| 屬性 | 值 |
|------|----|
| `hovermode` | `"x unified"` |
| `hoverlabel.bgcolor` | `#161B22` |
| `hoverlabel.bordercolor` | `#30363D` |
| `hoverlabel.font.color` | `#E6EDF3` |
| `hoverlabel.font.family` | `JetBrains Mono` |

### 7. 錯誤狀態 UI

| 錯誤類型 | 顯示方式 |
|----------|----------|
| 尚未搜尋 | 圖表區域顯示灰色空白佔位框（高度 540px），中央文字「請先搜尋股票代號」，色彩 `#8B949E` |
| 資料不足（少於 60 筆） | `st.warning`：「歷史資料不足，MA60 可能不完整」 |
| 圖表繪製異常 | `st.error`：「圖表繪製失敗，請重新整理頁面」 |

### 8. 開發者注意事項

- MA5 = 5日收盤價簡單移動平均（SMA）；MA20 = 20日 SMA；MA60 = 60日 SMA
- 布林通道 = MA20 ± 2 * 20日標準差（使用 `pandas` 的 `.rolling(20).std()`）
- K 棒顏色規則：收盤價 >= 開盤價 → 上漲色（`#F85149`）；收盤價 < 開盤價 → 下跌色（`#3FB950`）
- Plotly Candlestick trace 的 `increasing_line_color` 與 `decreasing_line_color` 須與填充色相同
- 布林通道填充：先加入下軌 trace（fill=None），再加入上軌 trace（fill=`"tonexty"`），順序不可顛倒
- X 軸使用日期字串格式（`YYYY-MM-DD`），Plotly 自動處理時間軸
- 非交易日（週末/假日）的 X 軸缺口：設定 `xaxis.type="category"` 以消除缺口（對所有 row 的 X 軸均設定）

---

## M3 — KD+MACD

### 1. 功能概述

技術指標副圖，包含兩組指標整合於單一 Plotly figure（使用 `make_subplots` 分兩列）：
- **上半：KD 指標**：K 線（橘）、D 線（藍），帶 20/80 超買超賣參考線
- **下半：MACD 指標**：DIF（橘）、Signal（藍）、OSC 柱狀圖（紅/綠）

此圖為獨立 Plotly figure，不與 M2/M4 共用。

### 2. Layout 規格

- 使用 `st.plotly_chart` 全寬顯示（`use_container_width=True`）
- M3 figure 總高度：**280px**
- KD 子圖高度：row 1，佔比 **0.45**
- MACD 子圖高度：row 2，佔比 **0.55**
- 兩個子圖之間的垂直間距（`vertical_spacing`）：`0.08`

### 3. 元件清單

| 元件 | Streamlit 函式 | 參數說明 | 備註 |
|------|---------------|---------|------|
| 區塊標題 | `st.markdown` | `unsafe_allow_html=True` | 「技術指標：KD + MACD」 |
| KD+MACD 圖 | `st.plotly_chart` | `figure=fig_indicator`, `use_container_width=True`, `config={"displayModeBar": False}` | 獨立 figure |

### 4. 互動行為

| 觸發條件 | 行為 |
|----------|------|
| 滑鼠懸停於 KD 線 | 顯示 tooltip：日期、K 值、D 值（保留 2 位小數） |
| 滑鼠懸停於 MACD 線 | 顯示 tooltip：日期、DIF 值、Signal 值、OSC 值（保留 4 位小數） |
| 懸停於 OSC 柱 | tooltip 顯示 OSC 數值，正值標示「多頭動能」，負值標示「空頭動能」 |
| 框選 / 拖拉縮放 | KD 與 MACD 子圖的 X 軸聯動（shared_xaxes=True） |
| `current_stock` 或 `current_period` 變更 | 重新繪製整個 figure |

### 5. 色彩與樣式

**圖表整體背景**

| 屬性 | 值 |
|------|----|
| `plot_bgcolor` | `#0D1117` |
| `paper_bgcolor` | `#0D1117` |

**KD Trace**

| Trace | 型別 | 色彩 | 線寬 |
|-------|------|------|------|
| K 線 | `Scatter`, mode=`lines` | `#F0883E` | 1.5px |
| D 線 | `Scatter`, mode=`lines` | `#58A6FF` | 1.5px |
| 超買線（80） | `Scatter`, mode=`lines` | `#30363D` | 1px, dash=`dot` |
| 超賣線（20） | `Scatter`, mode=`lines` | `#30363D` | 1px, dash=`dot` |
| 中線（50） | `Scatter`, mode=`lines` | `#30363D` | 0.5px, dash=`dash` |

**MACD Trace**

| Trace | 型別 | 色彩 | 線寬/說明 |
|-------|------|------|-----------|
| DIF 線 | `Scatter`, mode=`lines` | `#F0883E` | 1.5px |
| Signal 線 | `Scatter`, mode=`lines` | `#58A6FF` | 1.5px |
| OSC 正柱 | `Bar` | `#F85149` | OSC > 0 時顯示 |
| OSC 負柱 | `Bar` | `#3FB950` | OSC <= 0 時顯示 |

OSC 柱狀圖實作說明：OSC 正負值需分拆為兩條 `Bar` trace，正值 trace 的負值位置填 0（或 None），負值 trace 的正值位置填 0（或 None）。

**Y 軸設定**

KD Y 軸：`range=[0, 100]`，ticks 顯示 0、20、50、80、100
MACD Y 軸：自動範圍（`autorange=True`），tickformat=`.3f`

**X 軸（兩 row 共通設定）**

| 屬性 | 值 |
|------|----|
| `gridcolor` | `#30363D` |
| `tickfont.color` | `#8B949E` |
| `tickfont.family` | `JetBrains Mono` |
| `type` | `"category"` |

**Y 軸（兩 row 共通）**

| 屬性 | 值 |
|------|----|
| `gridcolor` | `#30363D` |
| `tickfont.color` | `#8B949E` |
| `tickfont.family` | `JetBrains Mono` |
| `side` | `right` |

### 6. Plotly 圖表規格

**Subplots 建立**

```
make_subplots(
    rows=2,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.08,
    row_heights=[0.45, 0.55],
    subplot_titles=["KD", "MACD"]
)
```

`subplot_titles` 字型顏色統一設為 `#8B949E`，字型大小 12px（透過 `fig.layout.annotations` 迴圈設定）。

**Trace 加入順序（row=1，KD）**

1. Bar OSC 負值（name=`"OSC 空頭"`）
2. Bar OSC 正值（name=`"OSC 多頭"`）
3. Scatter K 線（name=`"K"`）
4. Scatter D 線（name=`"D"`）
5. Scatter 超賣線 20（name=`"超賣 20"`, showlegend=False）
6. Scatter 超買線 80（name=`"超買 80"`, showlegend=False）
7. Scatter 中線 50（name=`"中線 50"`, showlegend=False）

**Trace 加入順序（row=2，MACD）**

1. Bar OSC 負值（name=`"OSC 空頭"`）
2. Bar OSC 正值（name=`"OSC 多頭"`）
3. Scatter DIF（name=`"DIF"`）
4. Scatter Signal（name=`"Signal"`）

**Legend 設定**

| 屬性 | 值 |
|------|----|
| `showlegend` | `True` |
| `legend.orientation` | `"h"` |
| `legend.y` | `1.05` |
| `legend.x` | `0` |
| `legend.font.color` | `#8B949E` |
| `legend.font.size` | `11` |
| `legend.bgcolor` | `rgba(0,0,0,0)` |

**Margin 設定**

| 方向 | 值（px） |
|------|----------|
| `margin.l` | `60` |
| `margin.r` | `60` |
| `margin.t` | `30` |
| `margin.b` | `30` |

**Hover 設定**

| 屬性 | 值 |
|------|----|
| `hovermode` | `"x unified"` |
| `hoverlabel.bgcolor` | `#161B22` |
| `hoverlabel.bordercolor` | `#30363D` |
| `hoverlabel.font.color` | `#E6EDF3` |
| `hoverlabel.font.family` | `JetBrains Mono` |

### 7. 錯誤狀態 UI

| 錯誤類型 | 顯示方式 |
|----------|----------|
| 尚未搜尋 | 圖表區域顯示灰色空白佔位框（高度 280px），中央文字「請先搜尋股票代號」 |
| 資料不足（少於 9 筆） | `st.warning`：「歷史資料不足，KD 指標可能不準確」 |
| 圖表繪製異常 | `st.error`：「指標圖表繪製失敗，請重新整理頁面」 |

### 8. 開發者注意事項

**KD 計算規格**

- 週期：9 日（`period=9`）
- RSV = (當日收盤 - 最近 9 日最低) / (最近 9 日最高 - 最近 9 日最低) × 100
- K = 前日 K × (2/3) + 當日 RSV × (1/3)（初始值 50）
- D = 前日 D × (2/3) + 當日 K × (1/3)（初始值 50）

**MACD 計算規格**

- 快線 EMA：12 日（`span=12`）
- 慢線 EMA：26 日（`span=26`）
- DIF = EMA12 - EMA26
- Signal = DIF 的 9 日 EMA（`span=9`）
- OSC（Histogram）= DIF - Signal
- pandas EMA 使用 `ewm(span=N, adjust=False).mean()`

- 參考線（KD 的 20/50/80）使用 `showlegend=False`，避免圖例過於雜亂
- OSC 正負分兩條 Bar trace（不使用條件色彩），原因：Plotly Bar 的 marker.color 接受 list，但分兩條 trace 更易維護

---

## M4 — 成交量

### 1. 功能概述

成交量長條圖，顯示在 M2 K 線圖的正下方，共用 X 軸（同一個 Plotly figure，row=2）。每根 bar 的顏色依當日 K 棒方向（漲/跌）決定：上漲為紅（`#F85149`）、下跌為綠（`#3FB950`）。此模組的圖表為 M2 figure 的一部分，不獨立存在。

### 2. Layout 規格

- M4 為 M2 主 figure 的 row 2，不獨立使用 `st.plotly_chart`
- M4 子圖高度：佔整體 figure 的 **0.22**（即 540px 中的約 120px）
- X 軸與 M2（row 1）共用（`shared_xaxes=True`）
- X 軸 tick labels 僅在 M4（row 2）顯示，M2（row 1）隱藏

### 3. 元件清單

M4 無獨立 Streamlit 元件，所有內容透過 `fig.add_trace(..., row=2, col=1)` 加入至 M2 的 figure 中。

| Trace | 說明 |
|-------|------|
| 成交量 Bar | 加入至 `row=2, col=1` |

### 4. 互動行為

| 觸發條件 | 行為 |
|----------|------|
| 滑鼠懸停於成交量 bar | 顯示 tooltip：日期、成交量（單位：張），格式化為千分位（如「12,345 張」） |
| X 軸縮放（M2 拖拉） | M4 X 軸同步縮放（shared_xaxes 自動處理） |

### 5. 色彩與樣式

| 元素 | 色彩規則 |
|------|----------|
| 上漲日成交量 bar | `#F85149`（`--color-up`） |
| 下跌日成交量 bar | `#3FB950`（`--color-down`） |
| 平盤日成交量 bar | `#8B949E`（`--text-secondary`） |
| Bar 邊框 | `rgba(0,0,0,0)`（無邊框） |
| Y 軸 grid | `#30363D` |
| Y 軸 tick 文字 | `#8B949E`，`JetBrains Mono` |
| X 軸 tick 文字 | `#8B949E`，`JetBrains Mono` |

**成交量 Y 軸標籤格式化規則**

| 數值範圍 | 顯示格式 |
|----------|----------|
| < 1,000 | 直接顯示整數，加「張」 |
| 1,000 ~ 9,999 | 顯示千分位，加「張」（如 1,234 張） |
| >= 10,000 | 以萬張為單位，保留 1 位小數（如 1.2 萬）|

Y 軸 tickformat 使用 `ticksuffix` 搭配自訂 `tickvals` 實現，或交由 Developer 以合適方式實作。

### 6. Plotly 圖表規格

**Trace 加入（row=2, col=1）**

成交量 Bar trace 參數：

| 參數 | 值 |
|------|----|
| `name` | `"成交量"` |
| `x` | 日期序列（與 M2 K 棒相同） |
| `y` | 成交量數列（單位：張） |
| `marker.color` | `list`，依漲跌條件逐日指定顏色（見色彩規則） |
| `marker.line.width` | `0`（無邊框） |
| `showlegend` | `True` |
| `hovertemplate` | `"%{x}<br>成交量：%{y:,} 張<extra></extra>"` |

**Y 軸設定（row=2 的 yaxis2）**

| 屬性 | 值 |
|------|----|
| `showgrid` | `True` |
| `gridcolor` | `#30363D` |
| `tickfont.color` | `#8B949E` |
| `tickfont.family` | `JetBrains Mono` |
| `side` | `right` |
| `nticks` | `3`（僅顯示少量刻度，避免擁擠） |

**X 軸設定（row=2 的 xaxis2）**

| 屬性 | 值 |
|------|----|
| `showgrid` | `True` |
| `gridcolor` | `#30363D` |
| `tickfont.color` | `#8B949E` |
| `tickfont.family` | `JetBrains Mono` |
| `tickformat` | `"%Y-%m-%d"` |
| `type` | `"category"` |
| `showticklabels` | `True` |
| `nticks` | `8`（顯示約 8 個日期刻度） |

### 7. 錯誤狀態 UI

M4 無獨立錯誤狀態，錯誤統一由 M2 的錯誤狀態 UI 處理（因為兩者共用同一個 figure）。

### 8. 開發者注意事項

- 成交量顏色 list 的建立方式：以 `pandas` 的 `np.where` 或 list comprehension 逐行比較收盤價與開盤價，輸出色碼字串 list
- 漲跌判斷：`close >= open` → 上漲色；`close < open` → 下跌色（平盤歸入上漲色或次要色，由 Developer 決定，建議使用 `#8B949E`）
- 成交量單位統一為「張」（1 張 = 1,000 股），資料來源若為「股」需除以 1,000
- Y 軸 `nticks=3` 的目的是避免成交量子圖的刻度過密，影響閱讀
- M4 不額外顯示圖表標題（避免與 M2 標題重複），若需標識，可在 subplot_titles 中傳入空字串或「成交量」

---

*文件結束 — Design Spec v1.0 — 由 Designer Agent 產出 — 2026-05-02*
