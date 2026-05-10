"""
src/notes/notion.py — M7 個人筆記：Notion 後端整合

提供 create_note / get_notes / delete_note / format_note_display
四個公開函式，供 Streamlit 儀表板與 Telegram Bot 使用。

Notion properties schema：
  stock_id  : rich_text
  note_type : select  (買入 / 賣出 / 觀察 / 其他)
  date      : date
  price     : number
  shares    : number
  content   : rich_text
"""

from __future__ import annotations

import logging
import os
from datetime import date
from typing import Optional

from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

logger = logging.getLogger(__name__)

NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_client():
    """Build and return a Notion Client instance."""
    return Client(auth=NOTION_TOKEN)


def _build_properties(
    stock_id: str,
    note_type: str,
    price: float,
    shares: int,
    content: str,
    note_date: str,
) -> dict:
    """Return a Notion properties dict matching the database schema."""
    return {
        "stock_id": {
            "rich_text": [{"text": {"content": stock_id}}]
        },
        "note_type": {
            "select": {"name": note_type}
        },
        "date": {
            "date": {"start": note_date}
        },
        "price": {
            "number": price
        },
        "shares": {
            "number": shares
        },
        "content": {
            "rich_text": [{"text": {"content": content}}]
        },
    }


def _parse_page(page: dict) -> dict:
    """
    Convert a raw Notion page object into the internal note dict format.

    Returns:
        dict with keys: page_id, stock_id, note_type, date, price, shares, content
    """
    props = page.get("properties", {})

    def _rich_text(field: str) -> str:
        items = props.get(field, {}).get("rich_text", [])
        return items[0]["plain_text"] if items else ""

    def _select(field: str) -> str:
        sel = props.get(field, {}).get("select")
        return sel["name"] if sel else ""

    def _date(field: str) -> str:
        d = props.get(field, {}).get("date")
        return d["start"] if d else ""

    def _number(field: str) -> float:
        return props.get(field, {}).get("number") or 0

    return {
        "page_id": page.get("id", ""),
        "stock_id": _rich_text("stock_id"),
        "note_type": _select("note_type"),
        "date": _date("date"),
        "price": float(_number("price")),
        "shares": int(_number("shares")),
        "content": _rich_text("content"),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_note(
    stock_id: str,
    note_type: str,
    price: float,
    shares: int,
    content: str,
    date: Optional[str] = None,
) -> dict:
    """
    在 Notion 資料庫建立一筆筆記。

    Args:
        stock_id:  股票代碼（例如 "2330"）
        note_type: 筆記分類，"買入" / "賣出" / "觀察" / "其他"
        price:     成交價格
        shares:    交易張數（0 表示非交易類型筆記）
        content:   備註文字
        date:      日期字串 YYYY-MM-DD；None 時自動填入今日

    Returns:
        {"success": True,  "page_id": "<id>", "message": "筆記已建立"}
        {"success": False, "page_id": "",     "message": "<error>"}
    """
    from datetime import date as _date_cls  # avoid shadowing parameter name

    note_date = date if date is not None else _date_cls.today().isoformat()

    try:
        client = _get_client()
        response = client.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties=_build_properties(
                stock_id=stock_id,
                note_type=note_type,
                price=price,
                shares=shares,
                content=content,
                note_date=note_date,
            ),
        )
        page_id = response.get("id", "")
        logger.info("create_note: stock=%s page_id=%s", stock_id, page_id)
        return {"success": True, "page_id": page_id, "message": "筆記已建立"}

    except Exception as exc:  # noqa: BLE001
        msg = f"建立筆記失敗：{exc}"
        logger.error("create_note error: %s", msg)
        return {"success": False, "page_id": "", "message": msg}


def get_notes(stock_id: str) -> list[dict]:
    """
    查詢指定股票的所有筆記（按日期降冪排列）。

    Args:
        stock_id: 股票代碼（例如 "2330"）

    Returns:
        list of dicts，每筆格式見 _parse_page()；失敗時回傳 []
    """
    try:
        client = _get_client()
        response = client.databases.query(
            database_id=NOTION_DATABASE_ID,
            filter={
                "property": "stock_id",
                "rich_text": {"equals": stock_id},
            },
        )
        pages = response.get("results", [])
        notes = [_parse_page(p) for p in pages]
        logger.info("get_notes: stock=%s count=%d", stock_id, len(notes))
        return notes

    except Exception as exc:  # noqa: BLE001
        logger.error("get_notes error: stock=%s %s", stock_id, exc)
        return []


def delete_note(page_id: str) -> dict:
    """
    刪除（archive）指定 page_id 的筆記。

    Notion 不支援硬刪除，改用 archived=True 將頁面封存。

    Args:
        page_id: Notion page UUID

    Returns:
        {"success": True,  "message": "筆記已刪除"}
        {"success": False, "message": "<error>"}
    """
    try:
        client = _get_client()
        client.pages.update(page_id=page_id, archived=True)
        logger.info("delete_note: page_id=%s archived", page_id)
        return {"success": True, "message": "筆記已刪除"}

    except Exception as exc:  # noqa: BLE001
        msg = f"刪除筆記失敗：{exc}"
        logger.error("delete_note error: page_id=%s %s", page_id, exc)
        return {"success": False, "message": msg}


def format_note_display(note: dict) -> str:
    """
    將 note dict 格式化為人類可讀字串。

    範例輸出：
        [2026-05-02] 買入 2330 × 1張 @ 850.0 | 備註：布林通道突破

    Args:
        note: 由 get_notes() / _parse_page() 回傳的 dict

    Returns:
        格式化字串；content 為空時省略「備註：」段落
    """
    date_str = note.get("date", "")
    note_type = note.get("note_type", "")
    stock_id = note.get("stock_id", "")
    shares = note.get("shares", 0)
    price = note.get("price", 0.0)
    content = note.get("content", "")

    base = f"[{date_str}] {note_type} {stock_id} × {shares}張 @ {price}"

    if content:
        return f"{base} | 備註：{content}"
    return base
