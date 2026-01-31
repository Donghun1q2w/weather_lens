"""Internal API endpoints for scheduled operations"""
from fastapi import APIRouter, HTTPException, Header, BackgroundTasks
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import os
import logging
import asyncio

from config.settings import (
    KMA_API_KEY,
    AIRKOREA_API_KEY,
    KHOA_API_KEY,
    GEMINI_API_KEY,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    THEME_IDS,
    NATIONAL_TOP,
    DATA_DIR,
)
from collectors import (
    KMAForecastCollector,
    OpenMeteoCollector,
    AirKoreaCollector,
    KHOAOceanCollector,
    CollectorError,
)
from processors import (
    merge_weather_data,
    CacheWriter,
    RegionLoader,
    weather_data_to_dict,
)
from scorers import get_all_scorers, get_scorer_by_theme_id
from recommenders import RegionRecommender
from curators import GeminiCurator
from messengers import TelegramMessenger

logger = logging.getLogger(__name__)

router = APIRouter()

# Simple authentication for internal endpoints
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "dev-internal-key")


def verify_internal_key(x_api_key: Optional[str] = Header(None)):
    """Verify internal API key"""
    if x_api_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return True


async def _collect_region_data(
    region_code: str,
    lat: float,
    lon: float,
    nx: int,
    ny: int,
    kma_collector: KMAForecastCollector,
    openmeteo_collector: OpenMeteoCollector,
) -> Dict[str, Any]:
    """Collect and merge weather data for a single region"""
    try:
        # Collect from both sources concurrently
        kma_task = kma_collector.collect(region_code, nx=nx, ny=ny)
        openmeteo_task = openmeteo_collector.collect(region_code, lat=lat, lon=lon)

        kma_result, openmeteo_result = await asyncio.gather(
            kma_task, openmeteo_task, return_exceptions=True
        )

        # Handle partial failures
        kma_data = kma_result if not isinstance(kma_result, Exception) else None
        openmeteo_data = openmeteo_result if not isinstance(openmeteo_result, Exception) else None

        if kma_data is None and openmeteo_data is None:
            logger.error(f"All collectors failed for region {region_code}")
            return None

        # Merge data (handles None gracefully)
        merged = merge_weather_data(kma_data, openmeteo_data)
        return merged

    except Exception as e:
        logger.error(f"Error collecting data for region {region_code}: {e}")
        return None


@router.post("/collect")
async def trigger_data_collection(
    background_tasks: BackgroundTasks,
    authorized: bool = verify_internal_key,
) -> Dict[str, Any]:
    """
    Trigger weather data collection from all sources.
    Runs in background to avoid timeout.

    Returns:
        Collection status and timestamp
    """
    async def run_collection():
        start_time = datetime.now()
        results = {"success": 0, "failed": 0, "regions": []}

        try:
            # Initialize collectors
            async with KMAForecastCollector(KMA_API_KEY) as kma_collector, \
                       OpenMeteoCollector() as openmeteo_collector:

                # Load regions
                async with RegionLoader() as loader:
                    regions = await loader.load_all()

                cache_writer = CacheWriter(DATA_DIR / "cache")

                # Process regions in batches
                batch_size = 50
                for i in range(0, len(regions), batch_size):
                    batch = regions[i:i + batch_size]

                    tasks = []
                    for region in batch:
                        # Note: nx, ny conversion needed - using placeholder
                        # In production, use region.nx, region.ny from database
                        task = _collect_region_data(
                            region.code,
                            region.lat,
                            region.lon,
                            region.nx if hasattr(region, 'nx') else 60,
                            region.ny if hasattr(region, 'ny') else 127,
                            kma_collector,
                            openmeteo_collector,
                        )
                        tasks.append((region.code, task))

                    # Execute batch
                    for region_code, task in tasks:
                        try:
                            data = await task
                            if data:
                                await cache_writer.write(region_code, data)
                                results["success"] += 1
                            else:
                                results["failed"] += 1
                        except Exception as e:
                            logger.error(f"Failed to process {region_code}: {e}")
                            results["failed"] += 1

                    # Rate limiting between batches
                    await asyncio.sleep(1)

                results["duration_seconds"] = (datetime.now() - start_time).total_seconds()
                logger.info(f"Collection complete: {results}")

        except Exception as e:
            logger.error(f"Collection failed: {e}")
            results["error"] = str(e)

    # Run in background
    background_tasks.add_task(run_collection)

    return {
        "status": "triggered",
        "operation": "data_collection",
        "timestamp": datetime.utcnow().isoformat(),
        "note": "Collection started in background",
    }


@router.post("/score")
async def trigger_score_calculation(
    background_tasks: BackgroundTasks,
    authorized: bool = verify_internal_key,
) -> Dict[str, Any]:
    """
    Trigger score recalculation for all regions and themes.
    Runs in background to avoid timeout.

    Returns:
        Calculation status and timestamp
    """
    async def run_scoring():
        start_time = datetime.now()
        results = {"themes_processed": 0, "regions_scored": 0}

        try:
            # Initialize components
            recommender = RegionRecommender()
            scorers = get_all_scorers()
            cache_writer = CacheWriter(DATA_DIR / "cache")

            # Load regions
            async with RegionLoader() as loader:
                regions = await loader.load_all()

            # Process each theme
            for theme_id, theme_name in THEME_IDS.items():
                try:
                    scorer = get_scorer_by_theme_id(theme_id)
                    if not scorer:
                        logger.warning(f"No scorer for theme {theme_id}")
                        continue

                    theme_scores = []

                    # Score each region
                    for region in regions:
                        try:
                            # Load cached weather data
                            cache_data = await cache_writer.read(region.code)
                            if not cache_data:
                                continue

                            # Calculate score (async method)
                            score_value = await scorer.calculate_score(cache_data)
                            if score_value is not None:
                                theme_scores.append({
                                    "region_code": region.code,
                                    "region_name": region.name,
                                    "sido": region.sido if hasattr(region, 'sido') else "",
                                    "lat": region.lat if hasattr(region, 'lat') else 0.0,
                                    "lng": region.lon if hasattr(region, 'lon') else 0.0,
                                    "score": score_value,
                                    "factors": {},  # Could extract from scorer if needed
                                    "uncertainty": getattr(scorer, 'uncertainty_note', None),
                                })
                                results["regions_scored"] += 1

                        except Exception as e:
                            logger.error(f"Scoring error for {region.code}/{theme_name}: {e}")

                    # Cache theme scores
                    if theme_scores:
                        await recommender.cache_theme_scores(theme_id, theme_scores)

                    results["themes_processed"] += 1

                except Exception as e:
                    logger.error(f"Theme {theme_name} scoring failed: {e}")

            results["duration_seconds"] = (datetime.now() - start_time).total_seconds()
            logger.info(f"Scoring complete: {results}")

        except Exception as e:
            logger.error(f"Scoring failed: {e}")
            results["error"] = str(e)

    # Run in background
    background_tasks.add_task(run_scoring)

    return {
        "status": "triggered",
        "operation": "score_calculation",
        "timestamp": datetime.utcnow().isoformat(),
        "note": "Scoring started in background",
    }


@router.post("/notify")
async def trigger_notification(
    background_tasks: BackgroundTasks,
    authorized: bool = verify_internal_key,
) -> Dict[str, Any]:
    """
    Trigger Telegram notification for daily recommendations.
    Runs in background to avoid timeout.

    Returns:
        Notification status and timestamp
    """
    async def run_notification():
        results = {"themes_sent": 0, "curated": 0}

        try:
            # Initialize components
            recommender = RegionRecommender()
            curator = GeminiCurator(GEMINI_API_KEY) if GEMINI_API_KEY else None
            messenger = TelegramMessenger(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)

            if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
                logger.warning("Telegram not configured, skipping notification")
                results["skipped"] = "Telegram not configured"
                return

            all_recommendations = []

            # Get recommendations for each theme
            for theme_id, theme_name in THEME_IDS.items():
                try:
                    # Get top regions for theme
                    top_regions = await recommender.get_national_top(theme_id, limit=NATIONAL_TOP)

                    if not top_regions:
                        continue

                    # Curate with Gemini if available
                    curated_text = None
                    if curator:
                        try:
                            curated_text = await curator.curate(theme_name, top_regions)
                            results["curated"] += 1
                        except Exception as e:
                            logger.warning(f"Curation failed for {theme_name}: {e}")

                    all_recommendations.append({
                        "theme_id": theme_id,
                        "theme_name": theme_name,
                        "regions": top_regions,
                        "curated_text": curated_text,
                    })

                except Exception as e:
                    logger.error(f"Recommendation failed for {theme_name}: {e}")

            # Send daily summary via Telegram
            if all_recommendations:
                try:
                    await messenger.send_daily_summary(all_recommendations)
                    results["themes_sent"] = len(all_recommendations)
                except Exception as e:
                    logger.error(f"Telegram send failed: {e}")
                    results["send_error"] = str(e)

            logger.info(f"Notification complete: {results}")

        except Exception as e:
            logger.error(f"Notification failed: {e}")
            results["error"] = str(e)

    # Run in background
    background_tasks.add_task(run_notification)

    return {
        "status": "triggered",
        "operation": "notification",
        "timestamp": datetime.utcnow().isoformat(),
        "note": "Notification started in background",
    }


@router.get("/status")
async def get_system_status(
    authorized: bool = verify_internal_key,
) -> Dict[str, Any]:
    """
    Get system status including last run times and health.

    Returns:
        System status information
    """
    cache_dir = DATA_DIR / "cache"
    today = datetime.now().strftime("%Y-%m-%d")
    today_cache = cache_dir / today

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "cache": {
            "directory": str(cache_dir),
            "today_exists": today_cache.exists() if cache_dir.exists() else False,
            "today_files": len(list(today_cache.glob("*.json"))) if today_cache.exists() else 0,
        },
        "config": {
            "kma_configured": bool(KMA_API_KEY),
            "airkorea_configured": bool(AIRKOREA_API_KEY),
            "khoa_configured": bool(KHOA_API_KEY),
            "gemini_configured": bool(GEMINI_API_KEY),
            "telegram_configured": bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID),
        },
    }
