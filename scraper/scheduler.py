"""
Step 5 — 排程器
每天自動執行爬蟲 + 匯率更新

執行方式：
    python scheduler.py

排程時間（台灣時間 UTC+8）：
    02:00  更新匯率
    03:00  重新爬取 JP + TW 商品資料
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

from exchange_rate import update_rate
from main import main as run_scraper

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


async def job_update_rate():
    logger.info("=== 開始更新匯率 ===")
    try:
        rate = await update_rate()
        logger.info(f"匯率更新完成：1 JPY = {rate} TWD")
    except Exception as e:
        logger.error(f"匯率更新失敗：{e}", exc_info=True)


async def job_scrape():
    logger.info("=== 開始爬取商品資料 ===")
    try:
        await run_scraper()
        logger.info("商品爬取完成")
    except Exception as e:
        logger.error(f"商品爬取失敗：{e}", exc_info=True)


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Asia/Taipei")

    # 每天 02:00 更新匯率
    scheduler.add_job(
        job_update_rate,
        trigger=CronTrigger(hour=2, minute=0, timezone="Asia/Taipei"),
        id="update_rate",
        name="每日匯率更新",
        replace_existing=True,
    )

    # 每天 03:00 爬取商品
    scheduler.add_job(
        job_scrape,
        trigger=CronTrigger(hour=3, minute=0, timezone="Asia/Taipei"),
        id="scrape_products",
        name="每日商品爬取",
        replace_existing=True,
    )

    return scheduler


async def run():
    scheduler = create_scheduler()
    scheduler.start()

    # 列出已排定的任務
    logger.info("排程器已啟動，任務列表：")
    for job in scheduler.get_jobs():
        logger.info(f"  - {job.name}：下次執行 {job.next_run_time}")

    try:
        # 持續運行，等待排程觸發
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        logger.info("排程器關閉中...")
        scheduler.shutdown()


if __name__ == "__main__":
    # 支援 --now 參數，立即執行一次（用於測試或手動觸發）
    if "--now" in sys.argv:
        logger.info("手動觸發：立即執行匯率更新 + 商品爬取")
        async def run_now():
            await job_update_rate()
            await job_scrape()
        asyncio.run(run_now())
    else:
        asyncio.run(run())
