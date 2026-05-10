"""
firebase_client.py — Firebase Firestore 資料庫存取層

提供自選清單、個人筆記的讀寫功能，取代本機存儲。
所有操作在 Firebase 不可用時自動降級（fallback 為空資料）。
"""

import logging
import os

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

_db = None


def _get_db():
    global _db
    if _db is not None:
        return _db

    creds_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase_credentials.json")
    if not os.path.exists(creds_path):
        logger.warning(f"Firebase 金鑰檔案不存在：{creds_path}，將跳過 Firebase 連線")
        return None

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        if not firebase_admin._apps:
            cred = credentials.Certificate(creds_path)
            firebase_admin.initialize_app(cred)

        _db = firestore.client(database_id="stock-dashboard")
        logger.info("Firebase Firestore 連線成功（stock-dashboard）")
        return _db
    except Exception as e:
        logger.error(f"Firebase 初始化失敗：{e}")
        return None


# ── 自選清單 ──────────────────────────────────────────────────

def get_watchlist(user_id: str = "default") -> list[str]:
    """讀取自選清單，回傳股票代號列表。Firebase 不可用時回傳空列表。"""
    db = _get_db()
    if db is None:
        return []
    try:
        doc = db.collection("watchlists").document(user_id).get()
        if doc.exists:
            return doc.to_dict().get("stocks", [])
        return []
    except Exception as e:
        logger.error(f"get_watchlist 失敗：{e}")
        return []


def save_watchlist(stocks: list[str], user_id: str = "default") -> bool:
    """儲存自選清單。回傳是否成功。"""
    db = _get_db()
    if db is None:
        return False
    try:
        db.collection("watchlists").document(user_id).set({"stocks": stocks})
        return True
    except Exception as e:
        logger.error(f"save_watchlist 失敗：{e}")
        return False


# ── 個人筆記 ──────────────────────────────────────────────────

def create_note(
    stock_id: str,
    note_type: str,
    price: float,
    shares: int,
    content: str,
    date: str | None = None,
    user_id: str = "default",
) -> dict:
    """建立一筆筆記，存至 Firestore notes collection。"""
    import time as _time
    from datetime import date as _date_cls
    db = _get_db()
    if db is None:
        return {"success": False, "page_id": "", "message": "Firebase 未連線"}
    note_date = date if date is not None else _date_cls.today().isoformat()
    try:
        doc_ref = db.collection("notes").document()
        doc_ref.set({
            "stock_id": stock_id,
            "user_id": user_id,
            "note_type": note_type,
            "date": note_date,
            "price": price,
            "shares": shares,
            "content": content,
            "created_at": _time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        })
        logger.info(f"create_note 成功 stock_id={stock_id} id={doc_ref.id}")
        return {"success": True, "page_id": doc_ref.id, "message": "筆記已建立"}
    except Exception as e:
        msg = f"建立筆記失敗：{e}"
        logger.error(msg)
        return {"success": False, "page_id": "", "message": msg}


def get_notes(stock_id: str, user_id: str = "default") -> list[dict]:
    """讀取某股票的所有筆記，按日期降冪排列。"""
    db = _get_db()
    if db is None:
        return []
    try:
        docs = (
            db.collection("notes")
            .where("stock_id", "==", stock_id)
            .where("user_id", "==", user_id)
            .order_by("date", direction="DESCENDING")
            .stream()
        )
        notes = []
        for doc in docs:
            data = doc.to_dict()
            data["page_id"] = doc.id
            notes.append(data)
        return notes
    except Exception as e:
        logger.error(f"get_notes 失敗 stock_id={stock_id}：{e}")
        return []


def delete_note(note_id: str) -> dict:
    """刪除指定 note_id 的筆記。"""
    db = _get_db()
    if db is None:
        return {"success": False, "message": "Firebase 未連線"}
    try:
        db.collection("notes").document(note_id).delete()
        logger.info(f"delete_note 成功 id={note_id}")
        return {"success": True, "message": "筆記已刪除"}
    except Exception as e:
        msg = f"刪除筆記失敗：{e}"
        logger.error(msg)
        return {"success": False, "message": msg}


def get_all_notes(user_id: str = "default") -> list[dict]:
    """讀取使用者所有股票的筆記，按日期降冪排列。"""
    db = _get_db()
    if db is None:
        return []
    try:
        docs = (
            db.collection("notes")
            .where("user_id", "==", user_id)
            .order_by("date", direction="DESCENDING")
            .stream()
        )
        notes = []
        for doc in docs:
            data = doc.to_dict()
            data["page_id"] = doc.id
            notes.append(data)
        return notes
    except Exception as e:
        logger.error(f"get_all_notes 失敗：{e}")
        return []


def format_note_display(note: dict) -> str:
    """將 note dict 格式化為人類可讀字串。"""
    date_str = note.get("date", "")
    note_type = note.get("note_type", "")
    stock_id = note.get("stock_id", "")
    shares = note.get("shares", 0)
    price = note.get("price", 0.0)
    content = note.get("content", "")
    base = f"[{date_str}] {note_type} {stock_id} × {shares}張 @ {price}"
    return f"{base} | 備註：{content}" if content else base


# ── 財報快取 ──────────────────────────────────────────────────

def get_financials_cache(stock_id: str) -> dict | None:
    """讀取財報快取。不存在或過期（超過 24 小時）時回傳 None。"""
    db = _get_db()
    if db is None:
        return None
    try:
        import time
        doc = db.collection("financials_cache").document(stock_id).get()
        if not doc.exists:
            return None
        data = doc.to_dict()
        cached_at = data.get("cached_at_ts", 0)
        if time.time() - cached_at > 86400:
            return None
        return data.get("payload")
    except Exception as e:
        logger.error(f"get_financials_cache 失敗 stock_id={stock_id}：{e}")
        return None


def save_financials_cache(stock_id: str, payload: dict) -> bool:
    """儲存財報快取（含抓取時間戳記）。回傳是否成功。"""
    db = _get_db()
    if db is None:
        return False
    try:
        import time
        db.collection("financials_cache").document(stock_id).set({
            "stock_id": stock_id,
            "payload": payload,
            "cached_at_ts": time.time(),
            "cached_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        })
        return True
    except Exception as e:
        logger.error(f"save_financials_cache 失敗 stock_id={stock_id}：{e}")
        return False
