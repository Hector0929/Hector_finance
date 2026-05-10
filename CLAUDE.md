# 台股個股分析儀表板 — CLAUDE.md

## 專案概述

三層個人台股分析系統：
- **Layer 1**：Streamlit 儀表板（互動分析 + 個人筆記）
- **Layer 2**：本機排程器（APScheduler，每日條件篩選）
- **Layer 3**：Telegram Bot（主動推播 + 被動查詢）

技術棧：Python · Streamlit · Plotly · FinLab VIP · FinMind · Claude API · Notion API · Telegram Bot API

---

## Sub-agents 角色一覽

| Agent | 職責 | 輸出物 |
|-------|------|--------|
| `designer` | UI 規格設計 | `design_spec.md` |
| `developer` | Python 實作 + 單元測試 | `src/` + `tests/unit/` |
| `qa` | 整合測試 + 測試報告 | `tests/integration/` + `test_report.md` |

---

## Dispatch 路由規則

### Sequential Dispatch（預設，有依賴順序）

每個新功能模組的標準開發流程：

```
designer → developer → qa
```

1. `designer`：先產出 `design_spec.md`
2. `developer`：讀取 spec，實作程式碼 + 單元測試
3. `qa`：執行整合測試，產出 `test_report.md`

若 QA 回報 P0/P1 bug：
```
qa（回報）→ developer（修復）→ qa（重測）
```

### Parallel Dispatch（條件：任務互相獨立，無共用檔案）

以下情況可平行派遣：

```
## Parallel Dispatch Rules
## ALL conditions must be met:
## - 3+ independent tasks
## - No shared files between tasks
## - Clear module boundaries
```

範例：M9（自選清單）、M10（條件篩選）、M11（Telegram 推播）三個模組
的 UI 規格可同時設計，因為它們的 `design_spec` 區塊互不依賴：

```
designer（M9 spec）  ─┐
designer（M10 spec） ─┼─ 平行執行（各自獨立區塊）
designer（M11 spec） ─┘
         ↓
developer（M9 實作）  ─┐
developer（M10 實作） ─┼─ 平行執行（各自獨立 src/ 路徑）
developer（M11 實作） ─┘
         ↓
qa（整合測試，需等待以上全部完成）
```

### Background Dispatch（研究或分析，不阻塞主線程）

```
## Background Dispatch Rules
## Use when:
## - Research or analysis tasks
## - Results are NOT blocking current work
## - No file modifications
```

範例：QA Agent 跑完整測試套件時，可切換為 Background，
讓 Primary Agent 繼續與你討論下一個模組的需求，QA 完成後再浮現結果。

---

## 模組開發順序（依優先級）

### Phase 1 — P0 基礎建設（Week 1-2）
```
designer（M1+M2+M3+M4 整體 UI spec）
  ↓
developer（M1 個股搜尋標頭）
  ↓
developer（M2 K線+布林通道）
  ↓
developer（M3 KD+MACD）
  ↓
developer（M4 成交量）
  ↓
qa（Phase 1 整合測試）
```

### Phase 2 — P1 核心功能（Week 3-5）
```
developer（M5 三大法人籌碼）  ─┐
developer（M6 AI 綜合評估）   ─┼─ 可平行（各自獨立模組）
developer（M7 個人筆記）       ─┘
         ↓
developer（M9 自選清單）
developer（M10 條件篩選）
developer（M11 Telegram 推播）
         ↓
qa（Phase 2 整合測試）
```

### Phase 3 — P2 進階功能（Week 6-7）
```
developer（M8 多週期切換）
developer（M12 Telegram Bot 查詢）
  ↓
qa（全系統整合測試 + 最終報告）
```

---

## 關鍵限制（Primary Agent 必須確認）

### 不可同時修改的檔案
以下檔案同一時間只能有一個 agent 操作：

- `app.py`（Streamlit 主程式）
- `scheduler.py`（排程器）
- `bot.py`（Telegram Bot）
- `requirements.txt`

### 測試隔離原則
- `tests/unit/` 由 Developer Agent 負責，QA Agent 不修改
- `tests/integration/` 由 QA Agent 負責，Developer Agent 不修改
- `tests/fixtures/` 共用，修改前先確認另一個 agent 未在使用

### API Keys 安全
- 任何 agent 都不可把 API key 硬寫在程式碼中
- 所有 key 透過 `os.getenv()` 從 `.env` 讀取
- `.env` 已加入 `.gitignore`，任何 agent 不可 commit 此檔案

---

## 重要參考文件

- `docs/PRD_v1.1.md`：產品需求規格
- `docs/dev_process.md`：開發流程規範（TDD+BDD）
- `.claude/agents/designer.md`：Designer Agent 完整規格
- `.claude/agents/developer.md`：Developer Agent 完整規格
- `.claude/agents/qa.md`：QA Agent 完整規格

---

## 本機執行指令速查

```bash
# 啟動 Streamlit 儀表板
streamlit run app.py

# 手動觸發排程（測試用）
python scheduler.py --run-now

# 啟動 Telegram Bot
python bot.py

# 執行單元測試
pytest tests/unit/ -v

# 執行整合測試
pytest tests/integration/ -v

# 執行完整測試 + 覆蓋率
pytest tests/ -m "not slow" --cov=src --cov-report=term-missing

# 安裝所有依賴
pip install -r requirements.txt
```
