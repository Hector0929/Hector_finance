"""
test_portfolio.py — src/portfolio/calculator 單元測試

覆蓋 calc_stock_position 和 calc_portfolio 的核心邏輯。
所有測試不需外部相依（無 Firebase / FinLab）。
"""

import pytest
from src.portfolio.calculator import calc_stock_position, calc_portfolio


# ─── calc_stock_position ─────────────────────────────────────────────────────

class TestCalcStockPosition:
    def test_only_buys_no_sells(self):
        notes = [
            {"note_type": "買入", "price": 100.0, "shares": 3, "date": "2024-01-01"},
            {"note_type": "買入", "price": 110.0, "shares": 2, "date": "2024-01-02"},
        ]
        result = calc_stock_position(notes)
        assert result["shares"] == 5
        # avg_cost = (100*3 + 110*2) / 5 = 520/5 = 104
        assert result["avg_cost"] == pytest.approx(104.0)
        assert result["realized_pnl"] == pytest.approx(0.0)

    def test_full_sell_clears_position(self):
        notes = [
            {"note_type": "買入", "price": 100.0, "shares": 5, "date": "2024-01-01"},
            {"note_type": "賣出", "price": 120.0, "shares": 5, "date": "2024-01-10"},
        ]
        result = calc_stock_position(notes)
        assert result["shares"] == 0
        assert result["avg_cost"] == pytest.approx(0.0)
        # realized = 5 * (120 - 100) = 100
        assert result["realized_pnl"] == pytest.approx(100.0)

    def test_partial_sell_fifo(self):
        notes = [
            {"note_type": "買入", "price": 50.0,  "shares": 3, "date": "2024-01-01"},
            {"note_type": "買入", "price": 80.0,  "shares": 2, "date": "2024-01-05"},
            {"note_type": "賣出", "price": 100.0, "shares": 2, "date": "2024-01-10"},
        ]
        result = calc_stock_position(notes)
        # FIFO: sell 2 from the first lot (cost 50)
        assert result["shares"] == 3
        # remaining: 1 張 @ 50, 2 張 @ 80 → avg = (50 + 160) / 3
        assert result["avg_cost"] == pytest.approx(70.0)
        # realized = 2 * (100 - 50) = 100
        assert result["realized_pnl"] == pytest.approx(100.0)

    def test_sell_loss(self):
        notes = [
            {"note_type": "買入", "price": 200.0, "shares": 1, "date": "2024-01-01"},
            {"note_type": "賣出", "price": 150.0, "shares": 1, "date": "2024-01-15"},
        ]
        result = calc_stock_position(notes)
        assert result["shares"] == 0
        assert result["realized_pnl"] == pytest.approx(-50.0)

    def test_observation_notes_ignored(self):
        notes = [
            {"note_type": "觀察", "price": 100.0, "shares": 10, "date": "2024-01-01"},
            {"note_type": "買入", "price": 90.0,  "shares": 2,  "date": "2024-01-05"},
        ]
        result = calc_stock_position(notes)
        # 觀察筆記不影響持倉
        assert result["shares"] == 2
        assert result["avg_cost"] == pytest.approx(90.0)

    def test_zero_price_or_shares_skipped(self):
        notes = [
            {"note_type": "買入", "price": 0.0,   "shares": 5, "date": "2024-01-01"},
            {"note_type": "買入", "price": 100.0, "shares": 0, "date": "2024-01-02"},
            {"note_type": "買入", "price": 100.0, "shares": 2, "date": "2024-01-03"},
        ]
        result = calc_stock_position(notes)
        assert result["shares"] == 2
        assert result["avg_cost"] == pytest.approx(100.0)

    def test_empty_notes(self):
        result = calc_stock_position([])
        assert result["shares"] == 0
        assert result["avg_cost"] == pytest.approx(0.0)
        assert result["realized_pnl"] == pytest.approx(0.0)

    def test_sell_exceeds_buy_does_not_go_negative(self):
        # 賣超持倉（資料不完整），剩餘空賣單直接忽略
        notes = [
            {"note_type": "買入", "price": 100.0, "shares": 2, "date": "2024-01-01"},
            {"note_type": "賣出", "price": 120.0, "shares": 5, "date": "2024-01-10"},
        ]
        result = calc_stock_position(notes)
        assert result["shares"] == 0
        # 只有 2 張能配對，realized = 2 * 20 = 40
        assert result["realized_pnl"] == pytest.approx(40.0)

    def test_multiple_buy_sell_cycles(self):
        notes = [
            {"note_type": "買入", "price": 50.0,  "shares": 4, "date": "2024-01-01"},
            {"note_type": "賣出", "price": 60.0,  "shares": 4, "date": "2024-02-01"},
            {"note_type": "買入", "price": 70.0,  "shares": 3, "date": "2024-03-01"},
        ]
        result = calc_stock_position(notes)
        assert result["shares"] == 3
        assert result["avg_cost"] == pytest.approx(70.0)
        # realized = 4 * (60 - 50) = 40
        assert result["realized_pnl"] == pytest.approx(40.0)


# ─── calc_portfolio ───────────────────────────────────────────────────────────

class TestCalcPortfolio:
    def _make_note(self, stock_id, note_type, price, shares, date):
        return {
            "stock_id": stock_id,
            "note_type": note_type,
            "price": price,
            "shares": shares,
            "date": date,
        }

    def test_single_stock_open_position(self):
        notes = [self._make_note("2330", "買入", 500.0, 2, "2024-01-01")]
        prices = {"2330": 600.0}
        result = calc_portfolio(notes, prices)

        assert len(result["positions"]) == 1
        pos = result["positions"][0]
        assert pos["stock_id"] == "2330"
        assert pos["shares"] == 2
        assert pos["avg_cost"] == pytest.approx(500.0)
        assert pos["current_price"] == pytest.approx(600.0)
        assert pos["cost_basis"] == pytest.approx(1000.0)
        assert pos["current_value"] == pytest.approx(1200.0)
        assert pos["unrealized_pnl"] == pytest.approx(200.0)
        assert pos["unrealized_pnl_pct"] == pytest.approx(20.0)

    def test_fully_sold_stock_excluded_from_positions(self):
        notes = [
            self._make_note("2330", "買入", 500.0, 2, "2024-01-01"),
            self._make_note("2330", "賣出", 600.0, 2, "2024-02-01"),
        ]
        prices = {"2330": 700.0}
        result = calc_portfolio(notes, prices)

        assert result["positions"] == []
        assert result["realized_pnl"] == pytest.approx(200.0)
        assert result["total_cost"] == pytest.approx(0.0)
        assert result["total_value"] == pytest.approx(0.0)

    def test_multi_stock_portfolio(self):
        notes = [
            self._make_note("2330", "買入", 500.0, 1, "2024-01-01"),
            self._make_note("2454", "買入", 200.0, 3, "2024-01-02"),
        ]
        prices = {"2330": 550.0, "2454": 180.0}
        result = calc_portfolio(notes, prices)

        assert len(result["positions"]) == 2
        assert result["total_cost"] == pytest.approx(500 + 600)       # 1100
        assert result["total_value"] == pytest.approx(550 + 540)      # 1090
        assert result["total_unrealized_pnl"] == pytest.approx(-10.0)

    def test_empty_notes_returns_zeroes(self):
        result = calc_portfolio([], {})
        assert result["positions"] == []
        assert result["realized_pnl"] == pytest.approx(0.0)
        assert result["total_cost"] == pytest.approx(0.0)
        assert result["total_unrealized_pnl"] == pytest.approx(0.0)
        assert result["total_unrealized_pnl_pct"] == pytest.approx(0.0)

    def test_missing_price_treated_as_zero(self):
        notes = [self._make_note("9999", "買入", 100.0, 2, "2024-01-01")]
        result = calc_portfolio(notes, {})

        pos = result["positions"][0]
        assert pos["current_price"] == pytest.approx(0.0)
        assert pos["current_value"] == pytest.approx(0.0)
        assert pos["unrealized_pnl"] == pytest.approx(-200.0)

    def test_notes_sorted_by_date_across_stocks(self):
        notes = [
            self._make_note("2330", "賣出", 600.0, 1, "2024-01-03"),
            self._make_note("2330", "買入", 500.0, 1, "2024-01-01"),
        ]
        prices = {"2330": 700.0}
        result = calc_portfolio(notes, prices)
        # 正確排序後：先買後賣，持倉 = 0，realized = +100
        assert result["positions"] == []
        assert result["realized_pnl"] == pytest.approx(100.0)

    def test_unrealized_pct_zero_when_no_cost(self):
        result = calc_portfolio([], {})
        assert result["total_unrealized_pnl_pct"] == pytest.approx(0.0)
