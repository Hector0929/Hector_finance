"""
manager.py — 自選清單管理模組

提供自選股清單的讀取、寫入、新增、移除等操作。
資料儲存於本機 JSON 檔，不需外部 API。
"""

from pathlib import Path
import json
import logging
from datetime import datetime

WATCHLIST_PATH = Path.home() / ".stock_dashboard_watchlist.json"
logger = logging.getLogger(__name__)


def load_watchlist() -> list[dict]:
    """
    從 JSON 檔讀取自選清單。

    每筆格式：{"stock_id": str, "name": str, "added_at": str}
    檔案不存在時回傳 []，不拋出例外。
    JSON 格式錯誤時回傳 []，並記錄 warning。

    Returns:
        list[dict]: 自選清單，空清單代表無資料或發生錯誤。
    """
    if not WATCHLIST_PATH.exists():
        return []
    try:
        with WATCHLIST_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            logger.warning("watchlist 格式錯誤，應為 list，回傳空清單")
            return []
        return data
    except json.JSONDecodeError as e:
        logger.warning("watchlist JSON 解析失敗，回傳空清單：%s", e)
        return []
    except OSError as e:
        logger.error("讀取 watchlist 失敗：%s", e)
        return []


def save_watchlist(watchlist: list[dict]) -> bool:
    """
    將自選清單寫入 JSON 檔。

    Args:
        watchlist: 要儲存的自選清單。

    Returns:
        bool: True 表示成功，False 表示失敗（含 logger.error）。
    """
    try:
        with WATCHLIST_PATH.open("w", encoding="utf-8") as f:
            json.dump(watchlist, f, ensure_ascii=False, indent=2)
        return True
    except OSError as e:
        logger.error("寫入 watchlist 失敗：%s", e)
        return False


def add_stock(stock_id: str, name: str = "") -> dict:
    """
    新增股票到自選清單。

    Args:
        stock_id: 股票代號（例如 "2330"）。
        name: 股票名稱，預設為空字串。

    Returns:
        dict: 操作結果。
            - 已存在：{"success": False, "message": "已在自選清單中"}
            - 成功：{"success": True, "message": "已加入自選清單"}
    """
    watchlist = load_watchlist()
    for item in watchlist:
        if item.get("stock_id") == stock_id:
            return {"success": False, "message": "已在自選清單中"}

    entry = {
        "stock_id": stock_id,
        "name": name,
        "added_at": datetime.now().isoformat(),
    }
    watchlist.append(entry)
    save_watchlist(watchlist)
    return {"success": True, "message": "已加入自選清單"}


def remove_stock(stock_id: str) -> dict:
    """
    從自選清單移除股票。

    Args:
        stock_id: 要移除的股票代號。

    Returns:
        dict: 操作結果。
            - 不存在：{"success": False, "message": "股票不在自選清單中"}
            - 成功：{"success": True, "message": "已移除"}
    """
    watchlist = load_watchlist()
    new_watchlist = [item for item in watchlist if item.get("stock_id") != stock_id]

    if len(new_watchlist) == len(watchlist):
        return {"success": False, "message": "股票不在自選清單中"}

    save_watchlist(new_watchlist)
    return {"success": True, "message": "已移除"}


def is_in_watchlist(stock_id: str) -> bool:
    """
    回傳 stock_id 是否在自選清單中。

    Args:
        stock_id: 股票代號。

    Returns:
        bool: True 表示在清單中，False 表示不在清單中。
    """
    watchlist = load_watchlist()
    return any(item.get("stock_id") == stock_id for item in watchlist)


def get_watchlist_ids() -> list[str]:
    """
    回傳自選清單的所有 stock_id 列表。

    Returns:
        list[str]: 所有 stock_id 的列表，清單為空時回傳 []。
    """
    watchlist = load_watchlist()
    return [item["stock_id"] for item in watchlist if "stock_id" in item]
