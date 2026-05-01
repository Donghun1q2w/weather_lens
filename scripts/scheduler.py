"""PhotoSpot Korea - Scheduled Jobs with APScheduler"""
import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from scripts.api.routes.internal import calculate_scores, collect_weather, send_notification
from scripts.config.logging import configure_logging
from scripts.config.settings import ENVIRONMENT
from scripts.ops.collect_weather_report import run_collection

configure_logging()
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


@scheduler.scheduled_job(CronTrigger(hour="6,18"), id="collect_weather")
async def collect_weather_data():
    """Runs at 6:00 and 18:00 (KST) daily."""
    logger.info("=== Starting weather data collection ===")
    try:
        result = await collect_weather()
        logger.info(f"[WeatherCollection] {result}")
        logger.info("=== Weather data collection completed ===")
    except Exception as e:
        logger.error(f"Weather data collection failed: {e}")


@scheduler.scheduled_job(CronTrigger(hour="3,15"), id="generate_weather_report")
async def generate_weather_report():
    """매일 03:00, 15:00 (KST) 실행."""
    logger.info("=== Starting weather report generation ===")
    try:
        await asyncio.wait_for(
            asyncio.to_thread(run_collection, sample_mode=False, hourly_mode=False),
            timeout=1800,
        )
        logger.info("Weather report generated successfully")
        logger.info("=== Weather report generation completed ===")
    except asyncio.TimeoutError:
        logger.error("Weather report generation timed out (>1800s)")
    except Exception as e:
        logger.error(f"Weather report generation failed: {e}")


@scheduler.scheduled_job(CronTrigger(hour="7,19"), id="recalculate_scores")
async def recalculate_scores():
    """Runs at 7:00 and 19:00 (KST) daily, 1 hour after data collection."""
    logger.info("=== Starting score recalculation ===")
    try:
        result = await calculate_scores()
        logger.info(f"[ScoreCalculation] {result}")
        logger.info("=== Score recalculation completed ===")
    except Exception as e:
        logger.error(f"Score recalculation failed: {e}")


@scheduler.scheduled_job(CronTrigger(hour="20"), id="send_daily_recommendations")
async def send_daily_recommendations():
    """Runs at 20:00 (KST) daily."""
    logger.info("=== Starting daily recommendation notification ===")
    try:
        result = await send_notification()
        logger.info(f"[DailyRecommendation] {result}")
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
    logger.info(f"Running in {ENVIRONMENT} mode")
    start_scheduler()
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        stop_scheduler()
