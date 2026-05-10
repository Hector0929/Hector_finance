"""
bot.py — Telegram Bot 主程式（長輪詢模式）

使用方式：python bot.py
"""
import os
import re
import time
import logging
from typing import Union
import requests
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

HELP_TEXT = (
    "📋 *支援的指令*\n\n"
    "/start — 歡迎訊息\n"
    "/help — 顯示此說明\n"
    "/watchlist — 查看自選清單\n"
    "輸入股票代號（4\\~5 位數字，如 `2330`）— 取得技術分析摘要"
)

WELCOME_TEXT = (
    "👋 歡迎使用台股分析 Bot！\n\n"
    "您可以輸入股票代號（如 `2330`）來查詢技術分析摘要，"
    "或使用以下指令：\n\n"
    "/help — 查看所有支援指令\n"
    "/watchlist — 查看自選清單"
)

STOCK_CODE_PATTERN = re.compile(r"^\d{4,5}$")


def get_updates(offset: int = 0, timeout: int = 30) -> list[dict]:
    """
    呼叫 Telegram getUpdates API。

    Args:
        offset: 上次處理的 update_id + 1，用於取得新訊息。
        timeout: long polling 等待秒數。

    Returns:
        list[dict]: update 列表；失敗時回傳 []，不拋出例外。
    """
    try:
        url = f"{BASE_URL}/getUpdates"
        resp = requests.get(
            url,
            params={"offset": offset, "timeout": timeout},
            timeout=timeout + 5,
        )
        data = resp.json()
        if data.get("ok"):
            return data.get("result", [])
        logger.warning("getUpdates 回應 ok=False：%s", data)
        return []
    except Exception as e:
        logger.error("getUpdates 失敗：%s", e)
        return []


def send_reply(chat_id: Union[int, str], text: str) -> bool:
    """
    回覆指定 chat_id，使用 Markdown 格式。

    Args:
        chat_id: Telegram 聊天室 ID。
        text: 要傳送的訊息文字（支援 Markdown）。

    Returns:
        bool: True 成功，False 失敗。
    """
    try:
        url = f"{BASE_URL}/sendMessage"
        resp = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
            },
            timeout=10,
        )
        data = resp.json()
        if data.get("ok"):
            return True
        logger.warning("sendMessage 回應 ok=False：chat_id=%s, resp=%s", chat_id, data)
        return False
    except Exception as e:
        logger.error("sendMessage 失敗：chat_id=%s, error=%s", chat_id, e)
        return False


def handle_message(chat_id: Union[int, str], text: str) -> str:
    """
    解析使用者訊息，回傳要回覆的文字。

    支援指令：
    - /start → 歡迎訊息，說明支援的指令
    - /help  → 指令說明
    - /watchlist → 回傳自選清單（呼叫 src.watchlist.manager.get_watchlist_ids）
    - 4~5 位數字（如 2330）→ 回傳股票摘要（目前回傳佔位訊息）
    - 其他 → 無法識別的指令提示

    Args:
        chat_id: Telegram 聊天室 ID（本函式中僅供擴充使用）。
        text: 使用者傳入的訊息文字。

    Returns:
        str: 要回傳給使用者的文字。
    """
    text = text.strip()

    if text == "/start":
        return WELCOME_TEXT

    if text == "/help":
        return HELP_TEXT

    if text == "/watchlist":
        try:
            from src.watchlist.manager import get_watchlist_ids
            ids = get_watchlist_ids()
            if not ids:
                return "自選清單目前為空，您可以在儀表板中新增股票。"
            ids_str = "\n".join(f"• {sid}" for sid in ids)
            return f"📌 *自選清單*\n\n{ids_str}"
        except Exception as e:
            logger.error("取得自選清單失敗：%s", e)
            return "取得自選清單時發生錯誤，請稍後再試。"

    if STOCK_CODE_PATTERN.match(text):
        return (
            f"🔍 *{text}* 查詢中，功能開發中...\n\n"
            "（技術分析摘要將於後續版本提供）"
        )

    return "無法識別的指令，請輸入 /help 查看說明。"


def run_bot() -> None:
    """
    啟動 Bot 長輪詢主迴圈。

    TELEGRAM_BOT_TOKEN 未設定時 logger.error 並直接 return。
    """
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN 未設定，Bot 無法啟動")
        return

    logger.info("Bot 啟動中...")
    offset = 0
    while True:
        updates = get_updates(offset=offset)
        for update in updates:
            offset = update["update_id"] + 1
            message = update.get("message", {})
            chat_id = message.get("chat", {}).get("id")
            text = message.get("text", "")
            if chat_id and text:
                reply = handle_message(chat_id, text)
                send_reply(chat_id, reply)
        time.sleep(1)


if __name__ == "__main__":
    run_bot()
