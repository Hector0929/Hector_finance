"""
telegram.py — Telegram 推播模組（M11）

透過 Telegram Bot API（requests）發送訊息與每日選股結果推播。
不依賴 python-telegram-bot 套件。
"""

import logging
import os

import requests
from dotenv import load_dotenv

from src.screener.filter import format_screener_message

load_dotenv()
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")


def send_message(
    text: str,
    chat_id: str = "",
    parse_mode: str = "Markdown",
) -> dict:
    """
    透過 Telegram Bot API 發送訊息（同步，使用 requests）。

    Parameters
    ----------
    text : str
        要發送的訊息內容。
    chat_id : str, optional
        目標 Chat ID；省略時使用環境變數 TELEGRAM_CHAT_ID。
    parse_mode : str, optional
        訊息格式，預設 "Markdown"。

    Returns
    -------
    dict
        成功：{"success": True, "message_id": int}
        失敗：{"success": False, "error": str}，不拋出例外。
    """
    effective_chat_id = chat_id or TELEGRAM_CHAT_ID

    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN 未設定，無法發送訊息。")
        return {"success": False, "error": "TELEGRAM_BOT_TOKEN 未設定"}

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    try:
        response = requests.post(
            url,
            json={
                "chat_id": effective_chat_id,
                "text": text,
                "parse_mode": parse_mode,
            },
            timeout=10,
        )
        data = response.json()

        if response.status_code == 200 and data.get("ok"):
            message_id = data["result"]["message_id"]
            logger.info("訊息發送成功，message_id=%s", message_id)
            return {"success": True, "message_id": message_id}
        else:
            error_desc = data.get("description", f"HTTP {response.status_code}")
            logger.error("Telegram API 回傳錯誤：%s", error_desc)
            return {"success": False, "error": error_desc}

    except Exception as exc:
        logger.error("發送訊息時發生例外：%s", exc)
        return {"success": False, "error": str(exc)}


def send_screener_result(
    results: list,
    date: str = "",
    chat_id: str = "",
) -> dict:
    """
    推播每日選股結果。

    results 為空時仍推播「今日無符合條件股票」，不沉默略過。
    使用 format_screener_message 格式化訊息後，呼叫 send_message 發送。

    Parameters
    ----------
    results : list[dict]
        run_screener() 回傳的股票清單，可為空列表。
    date : str, optional
        交易日期字串，例如 "2026-05-02"。
    chat_id : str, optional
        目標 Chat ID；省略時使用環境變數 TELEGRAM_CHAT_ID。

    Returns
    -------
    dict
        send_message 的回傳結果。
    """
    message = format_screener_message(results, date=date)
    logger.info("推播選股結果，日期=%s，股票數=%d", date, len(results))
    return send_message(message, chat_id=chat_id)
