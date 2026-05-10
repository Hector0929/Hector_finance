"""
scheduler.py — 台股個股分析儀表板每日排程器

功能：
  每個交易日收盤後（預設 14:40）自動執行：
  1. 從 FinLab 取得全市場資料
  2. 執行條件篩選（M10）
  3. 透過 Telegram 推播結果（M11）

使用方式：
  python scheduler.py              # 啟動排程器（背景持續執行）
  python scheduler.py --run-now    # 立即執行一次（測試用）
"""

import argparse
import logging
import os
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_daily_task() -> None:
    """
    每日排程主任務：篩選 + 推播。

    篩選條件（可依需求調整）：
    - 成交量 >= 3000 張
    - 漲幅 >= 2%
    - 漲幅 <= 9.5%（避免漲停鎖死）
    """
    logger.info("=== 每日選股任務開始 ===")
    today = datetime.now().strftime("%Y-%m-%d")

    try:
        from src.data.finlab_client import get_price_df, get_volume_df
        from src.screener.filter import run_screener
        from src.notifier.telegram import send_screener_result

        logger.info("取得全市場資料中...")
        price_df = get_price_df()
        volume_df = get_volume_df()

        if price_df.empty or volume_df.empty:
            logger.error("市場資料取得失敗，跳過本次篩選")
            send_screener_result([], date=today)
            return

        logger.info("執行條件篩選...")
        results = run_screener(
            price_df=price_df,
            volume_df=volume_df,
            min_volume=3000,
            min_change_pct=2.0,
            max_change_pct=9.5,
        )
        logger.info("篩選完成，共 %d 檔符合條件", len(results))

        logger.info("推播結果至 Telegram...")
        outcome = send_screener_result(results, date=today)
        if outcome.get("success"):
            logger.info("推播成功（message_id=%s）", outcome.get("message_id"))
        else:
            logger.warning("推播失敗：%s", outcome.get("error", "未知錯誤"))

    except Exception as exc:
        logger.error("每日任務執行失敗：%s", exc, exc_info=True)

    logger.info("=== 每日選股任務結束 ===")


def start_scheduler() -> None:
    """
    啟動 APScheduler，每個交易日 14:40 執行 run_daily_task。
    """
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.error("APScheduler 未安裝，請執行：pip install apscheduler")
        return

    scheduler = BlockingScheduler(timezone="Asia/Taipei")
    scheduler.add_job(
        run_daily_task,
        trigger=CronTrigger(
            day_of_week="mon-fri",
            hour=14,
            minute=40,
            timezone="Asia/Taipei",
        ),
        id="daily_screener",
        name="每日選股推播",
        replace_existing=True,
    )

    logger.info("排程器啟動，每個交易日 14:40 執行選股任務")
    logger.info("按 Ctrl+C 停止")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("排程器已停止")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="台股每日選股排程器")
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="立即執行一次（不啟動排程，用於測試）",
    )
    args = parser.parse_args()

    if args.run_now:
        logger.info("手動觸發模式")
        run_daily_task()
    else:
        start_scheduler()
