"""PhotoSpot Korea - Scheduled Jobs with APScheduler"""
import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import httpx

from config.settings import ENVIRONMENT, INTERNAL_API_KEY

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize scheduler
scheduler = AsyncIOScheduler()

# Internal API base URL
INTERNAL_API_BASE = "http://localhost:8000/internal"


async def call_internal_api(endpoint: str, operation: str):
    """
    Call internal API endpoint.

    Args:
        endpoint: API endpoint path
        operation: Operation name for logging
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{INTERNAL_API_BASE}/{endpoint}",
                headers={"X-API-Key": INTERNAL_API_KEY},
                timeout=300.0,  # 5 minutes timeout
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"[{operation}] Success: {result}")
            return result
    except Exception as e:
        logger.error(f"[{operation}] Failed: {e}")
        raise


@scheduler.scheduled_job(CronTrigger(hour="6,18"), id="collect_weather")
async def collect_weather_data():
    """
    Collect weather data from all sources.
    Runs at 6:00 and 18:00 (KST) daily.
    """
    logger.info("=== Starting weather data collection ===")
    try:
        await call_internal_api("collect", "WeatherCollection")
        logger.info("=== Weather data collection completed ===")
    except Exception as e:
        logger.error(f"Weather data collection failed: {e}")


@scheduler.scheduled_job(CronTrigger(hour="3,15"), id="generate_weather_report")
async def generate_weather_report():
    """
    날씨 수집 및 MD 리포트 생성.
    매일 03:00, 15:00 (KST) 실행.
    """
    logger.info("=== Starting weather report generation ===")
    try:
        import subprocess
        import sys
        from pathlib import Path

        script_path = Path(__file__).parent / "scripts" / "collect_weather_report.py"
        result = subprocess.run(
            [sys.executable, str(script_path), "--full"],
            capture_output=True,
            text=True,
            timeout=1800,  # 30 minutes timeout
        )

        if result.returncode == 0:
            logger.info(f"Weather report generated successfully")
            logger.info(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
        else:
            logger.error(f"Weather report generation failed: {result.stderr}")

        logger.info("=== Weather report generation completed ===")
    except Exception as e:
        logger.error(f"Weather report generation failed: {e}")


@scheduler.scheduled_job(CronTrigger(hour="7,19"), id="recalculate_scores")
async def recalculate_scores():
    """
    Recalculate scores for all regions and themes.
    Runs at 7:00 and 19:00 (KST) daily, 1 hour after data collection.
    """
    logger.info("=== Starting score recalculation ===")
    try:
        await call_internal_api("score", "ScoreCalculation")
        logger.info("=== Score recalculation completed ===")
    except Exception as e:
        logger.error(f"Score recalculation failed: {e}")


@scheduler.scheduled_job(CronTrigger(hour="20"), id="send_daily_recommendations")
async def send_daily_recommendations():
    """
    Send daily recommendations via Telegram.
    Runs at 20:00 (KST) daily.
    """
    logger.info("=== Starting daily recommendation notification ===")
    try:
        await call_internal_api("notify", "DailyRecommendation")
        logger.info("=== Daily recommendation notification completed ===")
    except Exception as e:
        logger.error(f"Daily recommendation notification failed: {e}")


def start_scheduler():
    """Start the APScheduler"""
    logger.info("Starting APScheduler...")
    logger.info("Scheduled jobs:")
    for job in scheduler.get_jobs():
        logger.info(f"  - {job.id}: {job.trigger}")

    scheduler.start()
    logger.info("APScheduler started successfully")


def stop_scheduler():
    """Stop the APScheduler"""
    logger.info("Stopping APScheduler...")
    scheduler.shutdown()
    logger.info("APScheduler stopped")


if __name__ == "__main__":
    # For testing: run scheduler standalone
    logger.info(f"Running in {ENVIRONMENT} mode")
    start_scheduler()

    # Keep the script running
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        stop_scheduler()
