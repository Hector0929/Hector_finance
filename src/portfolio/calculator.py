"""
calculator.py — 持倉損益計算

從 Firebase 筆記（買入/賣出 note_type）以 FIFO 原則計算：
- 每支股票的持倉張數與平均成本
- 已實現損益（出清部位）
- 未實現損益（持倉 × 當前價格）

單位：元（每張 = 1,000 股；所有金額為「元 / 每張」基準）
"""

from __future__ import annotations

from collections import defaultdict


def calc_stock_position(
    notes: list[dict],
) -> dict:
    """
    計算單一股票的持倉（FIFO 配對買賣）。

    notes 須已依 date 升冪排列，每筆至少含：
        note_type: "買入" | "賣出" | 其他
        price:     每張成交價（元）
        shares:    張數（正整數）

    Returns dict 含：
        shares       現有持倉張數
        avg_cost     平均每張成本（持倉 == 0 時為 0.0）
        realized_pnl 已實現損益（元）
        buy_queue    [(price, shares)] 未出清的買入佇列（FIFO 順序）
    """
    buy_queue: list[tuple[float, int]] = []
    realized_pnl = 0.0

    for note in notes:
        ntype = note.get("note_type", "")
        price = float(note.get("price", 0.0))
        shares = int(note.get("shares", 0))

        if shares <= 0 or price <= 0:
            continue

        if ntype == "買入":
            buy_queue.append((price, shares))

        elif ntype == "賣出":
            remaining_sell = shares
            while remaining_sell > 0 and buy_queue:
                buy_price, buy_shares = buy_queue[0]
                matched = min(remaining_sell, buy_shares)
                realized_pnl += matched * (price - buy_price)
                remaining_sell -= matched
                if matched == buy_shares:
                    buy_queue.pop(0)
                else:
                    buy_queue[0] = (buy_price, buy_shares - matched)

    total_shares = sum(s for _, s in buy_queue)
    avg_cost = (
        sum(p * s for p, s in buy_queue) / total_shares
        if total_shares > 0
        else 0.0
    )

    return {
        "shares": total_shares,
        "avg_cost": round(avg_cost, 2),
        "realized_pnl": round(realized_pnl, 2),
        "buy_queue": buy_queue,
    }


def calc_portfolio(
    notes: list[dict],
    current_prices: dict[str, float],
) -> dict:
    """
    從所有筆記計算完整持倉損益。

    Args:
        notes:          所有筆記列表（可跨股票），每筆含 stock_id, note_type,
                        price, shares, date。
        current_prices: {stock_id: 最新收盤價（元）}

    Returns dict 含：
        positions             list of position dicts（僅含持倉 > 0 的股票）
        realized_pnl          所有股票的已實現損益合計
        total_cost            所有持倉的總成本
        total_value           所有持倉的當前市值
        total_unrealized_pnl  未實現損益合計
        total_unrealized_pnl_pct 未實現損益率（%）

    position dict 含：
        stock_id, shares, avg_cost, current_price,
        cost_basis, current_value,
        unrealized_pnl, unrealized_pnl_pct
    """
    # 按 stock_id 分組，每組依日期升冪排列
    by_stock: dict[str, list[dict]] = defaultdict(list)
    for note in sorted(notes, key=lambda n: n.get("date", "")):
        sid = note.get("stock_id", "")
        if sid:
            by_stock[sid].append(note)

    positions = []
    total_realized = 0.0
    total_cost = 0.0
    total_value = 0.0

    for sid, stock_notes in by_stock.items():
        pos = calc_stock_position(stock_notes)
        total_realized += pos["realized_pnl"]

        if pos["shares"] <= 0:
            continue

        current_price = current_prices.get(sid, 0.0)
        cost_basis = round(pos["avg_cost"] * pos["shares"], 2)
        current_value = round(current_price * pos["shares"], 2)
        unrealized_pnl = round(current_value - cost_basis, 2)
        unrealized_pnl_pct = (
            round(unrealized_pnl / cost_basis * 100, 2) if cost_basis != 0 else 0.0
        )

        total_cost += cost_basis
        total_value += current_value

        positions.append(
            {
                "stock_id": sid,
                "shares": pos["shares"],
                "avg_cost": pos["avg_cost"],
                "current_price": current_price,
                "cost_basis": cost_basis,
                "current_value": current_value,
                "unrealized_pnl": unrealized_pnl,
                "unrealized_pnl_pct": unrealized_pnl_pct,
            }
        )

    total_unrealized = round(total_value - total_cost, 2)
    total_unrealized_pct = (
        round(total_unrealized / total_cost * 100, 2) if total_cost != 0 else 0.0
    )

    return {
        "positions": positions,
        "realized_pnl": round(total_realized, 2),
        "total_cost": round(total_cost, 2),
        "total_value": round(total_value, 2),
        "total_unrealized_pnl": total_unrealized,
        "total_unrealized_pnl_pct": total_unrealized_pct,
    }
