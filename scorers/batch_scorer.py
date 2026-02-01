"""Batch Scorer for PhotoSpot Korea - Batch score calculation for merged forecast data"""
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime

from scorers.theme_scorers import get_all_scorers, get_scorer_by_theme_id


async def calculate_photo_scores(
    weather_data: dict,
    themes: Optional[List[int]] = None,
    ocean_data: Optional[dict] = None
) -> dict:
    """Calculate photo scores for a single time slot

    Args:
        weather_data: Dictionary containing weather forecast data for a specific time
            - datetime: ISO format timestamp
            - temp: Temperature data with avg
            - cloud: Cloud cover data (0-100%)
            - rain_prob: Precipitation probability
            - wind_speed: Wind speed (m/s)
            - pm25: PM2.5 concentration
            - humidity: Relative humidity
            - visibility: Visibility (km)
            - Other location-specific flags
        themes: Optional list of theme IDs to calculate (None = all themes)
        ocean_data: Optional dictionary containing ocean data
            - sea_temp: Sea surface temperature
            - wave_height: Wave height (m)
            - tide_time: Tide information
            - storm_warning: Storm warning flag

    Returns:
        dict: Theme scores mapping theme_name -> score
            Example: {"sunrise": 85.5, "sunset": 42.3, ...}
    """
    scores = {}

    # Get scorers to use
    if themes:
        scorers = [get_scorer_by_theme_id(tid) for tid in themes]
        scorers = [s for s in scorers if s is not None]
    else:
        scorers = get_all_scorers()

    # Calculate scores for each theme
    tasks = []
    for scorer in scorers:
        tasks.append(scorer.calculate_score(weather_data, ocean_data))

    results = await asyncio.gather(*tasks)

    for scorer, score in zip(scorers, results):
        scores[scorer.theme_name] = round(score, 1)

    return scores


async def batch_calculate_scores(merged_data: dict) -> dict:
    """Batch calculate scores for all regions and time slots

    Args:
        merged_data: Dictionary with structure:
            {
                "region_code": {
                    "region_name": str,
                    "forecasts": [
                        {
                            "datetime": "2026-02-01T09:00:00",
                            "temp": {"avg": 5.2},
                            "cloud": {"avg": 30},
                            ...
                        }
                    ],
                    "beaches": [
                        {
                            "beach_num": 1,
                            "name": "해운대",
                            "forecasts": [
                                {
                                    "datetime": "2026-02-01T09:00:00",
                                    "temp": {"avg": 6.0},
                                    ...
                                    "ocean": {
                                        "sea_temp": 15.5,
                                        "wave_height": 0.8
                                    }
                                }
                            ]
                        }
                    ]
                }
            }

    Returns:
        dict: Scores organized by region and time
            {
                "region_code": {
                    "region_name": str,
                    "region_scores": {
                        "2026-02-01T09:00:00": {
                            "sunrise": 85.5,
                            "sunset": 0.0,
                            ...
                        },
                        ...
                    },
                    "beach_scores": [
                        {
                            "beach_num": 1,
                            "name": "해운대",
                            "scores": {
                                "2026-02-01T09:00:00": {
                                    "sunrise": 88.2,
                                    ...
                                }
                            }
                        }
                    ]
                }
            }
    """
    result = {}

    for region_code, region_data in merged_data.items():
        region_result = {
            "region_name": region_data.get("region_name", ""),
            "region_scores": {},
            "beach_scores": []
        }

        # Calculate scores for region forecasts
        if "forecasts" in region_data:
            for forecast in region_data["forecasts"]:
                timestamp = forecast.get("datetime")
                if timestamp:
                    # No ocean data for region-level forecasts
                    scores = await calculate_photo_scores(forecast, ocean_data=None)
                    region_result["region_scores"][timestamp] = scores

        # Calculate scores for each beach
        if "beaches" in region_data:
            for beach in region_data["beaches"]:
                beach_result = {
                    "beach_num": beach.get("beach_num"),
                    "name": beach.get("name", ""),
                    "scores": {}
                }

                if "forecasts" in beach:
                    for forecast in beach["forecasts"]:
                        timestamp = forecast.get("datetime")
                        if timestamp:
                            # Extract ocean data if available
                            ocean_data = forecast.get("ocean")
                            scores = await calculate_photo_scores(forecast, ocean_data=ocean_data)
                            beach_result["scores"][timestamp] = scores

                region_result["beach_scores"].append(beach_result)

        result[region_code] = region_result

    return result


def get_best_times(
    scores_data: dict,
    theme: str,
    top_n: int = 5,
    min_score: float = 50.0
) -> List[Dict[str, Any]]:
    """Get best time slots for a specific theme across all locations

    Args:
        scores_data: Output from batch_calculate_scores
        theme: Theme name (e.g., "일출", "일몰", "은하수")
        top_n: Number of top results to return
        min_score: Minimum score threshold (default: 50.0)

    Returns:
        List of dictionaries with best times, sorted by score descending:
            [
                {
                    "region_code": "4825051000",
                    "region_name": "부산 해운대구",
                    "location_type": "beach",  # or "region"
                    "beach_num": 1,  # only for beaches
                    "beach_name": "해운대",  # only for beaches
                    "datetime": "2026-02-01T06:30:00",
                    "score": 92.5
                },
                ...
            ]
    """
    candidates = []

    for region_code, region_data in scores_data.items():
        region_name = region_data.get("region_name", "")

        # Check region-level scores
        region_scores = region_data.get("region_scores", {})
        for timestamp, theme_scores in region_scores.items():
            if theme in theme_scores:
                score = theme_scores[theme]
                if score >= min_score:
                    candidates.append({
                        "region_code": region_code,
                        "region_name": region_name,
                        "location_type": "region",
                        "datetime": timestamp,
                        "score": score
                    })

        # Check beach-level scores
        beach_scores = region_data.get("beach_scores", [])
        for beach in beach_scores:
            beach_num = beach.get("beach_num")
            beach_name = beach.get("name", "")
            scores_by_time = beach.get("scores", {})

            for timestamp, theme_scores in scores_by_time.items():
                if theme in theme_scores:
                    score = theme_scores[theme]
                    if score >= min_score:
                        candidates.append({
                            "region_code": region_code,
                            "region_name": region_name,
                            "location_type": "beach",
                            "beach_num": beach_num,
                            "beach_name": beach_name,
                            "datetime": timestamp,
                            "score": score
                        })

    # Sort by score descending, then by datetime
    candidates.sort(key=lambda x: (-x["score"], x["datetime"]))

    return candidates[:top_n]


def get_location_best_themes(
    scores_data: dict,
    region_code: str,
    datetime_str: str,
    location_type: str = "region",
    beach_num: Optional[int] = None,
    top_n: int = 3
) -> List[Dict[str, Any]]:
    """Get best themes for a specific location and time

    Args:
        scores_data: Output from batch_calculate_scores
        region_code: Region code to check
        datetime_str: ISO format datetime string
        location_type: "region" or "beach"
        beach_num: Beach number (required if location_type is "beach")
        top_n: Number of top themes to return

    Returns:
        List of best themes sorted by score:
            [
                {"theme": "일출", "score": 92.5},
                {"theme": "골든아워", "score": 88.3},
                ...
            ]
    """
    if region_code not in scores_data:
        return []

    region_data = scores_data[region_code]
    theme_scores = {}

    if location_type == "region":
        region_scores = region_data.get("region_scores", {})
        if datetime_str in region_scores:
            theme_scores = region_scores[datetime_str]

    elif location_type == "beach" and beach_num is not None:
        beach_scores_list = region_data.get("beach_scores", [])
        for beach in beach_scores_list:
            if beach.get("beach_num") == beach_num:
                scores_by_time = beach.get("scores", {})
                if datetime_str in scores_by_time:
                    theme_scores = scores_by_time[datetime_str]
                break

    # Convert to list and sort
    results = [
        {"theme": theme, "score": score}
        for theme, score in theme_scores.items()
    ]
    results.sort(key=lambda x: -x["score"])

    return results[:top_n]


async def calculate_scores_for_timerange(
    merged_data: dict,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
) -> dict:
    """Calculate scores for a specific time range

    Args:
        merged_data: Merged forecast data
        start_time: ISO format start time (inclusive)
        end_time: ISO format end time (inclusive)

    Returns:
        dict: Same structure as batch_calculate_scores but filtered by time range
    """
    filtered_data = {}

    # Parse datetime bounds if provided
    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00')) if start_time else None
    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00')) if end_time else None

    # Filter forecasts by time range
    for region_code, region_data in merged_data.items():
        filtered_region = {
            "region_name": region_data.get("region_name", ""),
            "forecasts": [],
            "beaches": []
        }

        # Filter region forecasts
        if "forecasts" in region_data:
            for forecast in region_data["forecasts"]:
                dt_str = forecast.get("datetime")
                if dt_str:
                    dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                    if (not start_dt or dt >= start_dt) and (not end_dt or dt <= end_dt):
                        filtered_region["forecasts"].append(forecast)

        # Filter beach forecasts
        if "beaches" in region_data:
            for beach in region_data["beaches"]:
                filtered_beach = {
                    "beach_num": beach.get("beach_num"),
                    "name": beach.get("name", ""),
                    "forecasts": []
                }

                if "forecasts" in beach:
                    for forecast in beach["forecasts"]:
                        dt_str = forecast.get("datetime")
                        if dt_str:
                            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                            if (not start_dt or dt >= start_dt) and (not end_dt or dt <= end_dt):
                                filtered_beach["forecasts"].append(forecast)

                if filtered_beach["forecasts"]:
                    filtered_region["beaches"].append(filtered_beach)

        if filtered_region["forecasts"] or filtered_region["beaches"]:
            filtered_data[region_code] = filtered_region

    # Calculate scores on filtered data
    return await batch_calculate_scores(filtered_data)
