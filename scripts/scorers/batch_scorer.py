"""Batch Scorer for PhotoSpot Korea - Daily score calculation for merged forecast data"""
import asyncio
import logging
from collections import defaultdict
from datetime import datetime
from typing import Optional, List, Dict, Any

from scripts.scorers.theme_scorers import get_all_scorers, get_scorer_by_theme_id

logger = logging.getLogger(__name__)


# =============================================================================
# Legacy per-timeslot scoring (kept for backward compat with api routes)
# =============================================================================

async def calculate_photo_scores(
    weather_data: dict,
    themes: Optional[List[int]] = None,
    ocean_data: Optional[dict] = None
) -> dict:
    """Calculate photo scores for a single time slot (legacy interface)"""
    scores = {}

    if themes:
        scorers = [get_scorer_by_theme_id(tid) for tid in themes]
        scorers = [s for s in scorers if s is not None]
    else:
        scorers = get_all_scorers()

    tasks = []
    for scorer in scorers:
        tasks.append(scorer.calculate_score(weather_data, ocean_data))

    results = await asyncio.gather(*tasks)

    for scorer, score in zip(scorers, results):
        scores[scorer.theme_name] = round(score, 1)

    return scores


async def batch_calculate_scores(merged_data: dict) -> dict:
    """Legacy batch scoring (per-timeslot). Kept for backward compat."""
    result = {}

    for region_code, region_data in merged_data.items():
        region_result = {
            "region_name": region_data.get("region_name", ""),
            "region_scores": {},
            "beach_scores": []
        }

        if "forecasts" in region_data:
            for forecast in region_data["forecasts"]:
                timestamp = forecast.get("datetime")
                if timestamp:
                    scores = await calculate_photo_scores(forecast, ocean_data=None)
                    region_result["region_scores"][timestamp] = scores

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
                            ocean_data = forecast.get("ocean")
                            scores = await calculate_photo_scores(forecast, ocean_data=ocean_data)
                            beach_result["scores"][timestamp] = scores

                region_result["beach_scores"].append(beach_result)

        result[region_code] = region_result

    return result


# =============================================================================
# NEW: Daily scoring pipeline
# =============================================================================

def _group_timeslots_by_date(weather_list: list) -> Dict[str, list]:
    """Group weather timeslots by date string (YYYY-MM-DD).

    Args:
        weather_list: List of hourly weather dicts with 'datetime' key

    Returns:
        Dict mapping date string to list of timeslots for that date
    """
    by_date = defaultdict(list)
    for slot in weather_list:
        dt_str = slot.get("datetime", "")
        if not dt_str:
            continue
        # Extract date portion (YYYY-MM-DD) from ISO format
        date_key = dt_str[:10]
        by_date[date_key].append(slot)

    # Sort timeslots within each day by time
    for date_key in by_date:
        by_date[date_key].sort(key=lambda s: s.get("datetime", ""))

    return dict(by_date)


def _build_night_timeslots(day_slots: list, next_day_slots: list) -> list:
    """Build night timeslots for a given day.

    "Night of day D" = D@21:00 + D+1@00:00 + D+1@03:00

    Args:
        day_slots: Timeslots for day D
        next_day_slots: Timeslots for day D+1 (may be empty)

    Returns:
        Combined list of night-relevant timeslots
    """
    night_slots = []

    # D@21:00
    for slot in day_slots:
        dt_str = slot.get("datetime", "")
        try:
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            if dt.hour == 21:
                night_slots.append(slot)
        except (ValueError, AttributeError):
            continue

    # D+1@00:00 and D+1@03:00
    for slot in next_day_slots:
        dt_str = slot.get("datetime", "")
        try:
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            if dt.hour in (0, 3):
                night_slots.append(slot)
        except (ValueError, AttributeError):
            continue

    return night_slots


def _pre_compute_astronomy(date_str: str, lat: float, lon: float) -> Optional[dict]:
    """Pre-compute astronomy data for a date+location.

    Returns dict with: moon_phase, moon_times, twilight, dark_window,
    core_altitude, season_quality, sunrise, sunset
    """
    try:
        from scripts.utils.astronomy import (
            get_moon_phase, get_moon_times, get_astronomical_twilight,
            calculate_dark_window, get_milky_way_visibility,
            get_sunrise_sunset
        )

        date = datetime.fromisoformat(date_str)

        moon_phase = get_moon_phase(date)
        moon_times = get_moon_times(date, lat, lon)
        twilight = get_astronomical_twilight(date, lat, lon)
        dark_window = calculate_dark_window(twilight, moon_times, moon_phase)
        sun_info = get_sunrise_sunset(date, lat, lon)

        # Milky Way visibility for season/altitude info
        mw_vis = get_milky_way_visibility(date, lat, lon)

        return {
            "moon_phase": moon_phase,
            "moon_times": moon_times,
            "twilight": twilight,
            "dark_window": dark_window,
            "core_altitude": mw_vis.get("core_altitude", 0),
            "season_quality": mw_vis.get("season_quality", "off"),
            "sunrise": sun_info.get("sunrise"),
            "sunset": sun_info.get("sunset"),
        }
    except Exception as e:
        logger.warning(f"Astronomy pre-compute failed for {date_str} ({lat}, {lon}): {e}")
        return None


async def batch_calculate_daily_scores(merged_data: dict) -> dict:
    """
    New daily scoring pipeline.

    Input: merged_data from generate_forecast_report.py
        {
            region_code: {
                "region": {"name": str, "weather": [hourly_data]},
                "beaches": [{
                    "beach_num": int, "name": str,
                    "weather": [hourly_data],
                    "marine": {wave_height, sea_temperature, tide_info, sun_info, moon_info}
                }]
            }
        }

    Output:
        {
            region_code: {
                "region_name": str,
                "daily_scores": {
                    "2026-02-08": {
                        "일출": {score: 85.5, factors: {...}, time_used: "06:00"},
                        "일몰": {score: 72.3, factors: {...}, time_used: "18:00"},
                        ...16 themes
                    },
                    "2026-02-09": {...},
                    "2026-02-10": {...}
                },
                "beach_daily_scores": [{
                    "beach_num": 1, "name": "해운대",
                    "daily_scores": { same structure }
                }]
            }
        }
    """
    print("\n[4/5] 테마별 일별 점수 계산 중...")

    scorers = get_all_scorers()
    result = {}

    # Cache astronomy data per (date, lat_rounded, lon_rounded)
    astronomy_cache = {}

    total_regions = len(merged_data)
    processed = 0

    for region_code, data in merged_data.items():
        processed += 1
        if processed % 50 == 0 or processed == total_regions:
            print(f"\r  진행: {processed}/{total_regions} 지역...", end="", flush=True)

        region_info = data.get("region", {})
        region_name = region_info.get("name", "알 수 없음")
        region_weather = region_info.get("weather", [])

        # Build location_meta from first forecast or region info
        is_east = data.get("is_east_coast", False)
        is_west = data.get("is_west_coast", False)
        is_coastal = data.get("is_coastal", False)
        location_meta = {
            "lat": data.get("lat", 0),
            "lon": data.get("lon", 0),
            "is_east_coast": is_east,
            "is_west_coast": is_west,
            "is_south_coast": is_coastal and not is_east and not is_west,
            "is_coastal": is_coastal,
            "elevation": data.get("elevation", 0),
        }

        # Group timeslots by date
        day_groups = _group_timeslots_by_date(region_weather)
        sorted_dates = sorted(day_groups.keys())

        # --- Region daily scores ---
        daily_scores = {}

        for i, date_str in enumerate(sorted_dates):
            day_slots = day_groups[date_str]

            # Build night slots (D@21 + D+1@00 + D+1@03)
            next_day_slots = day_groups.get(sorted_dates[i + 1], []) if i + 1 < len(sorted_dates) else []
            night_slots = _build_night_timeslots(day_slots, next_day_slots)

            # Merge night slots into day_weather for scorers that need them
            all_day_weather = day_slots + [s for s in night_slots if s not in day_slots]

            # Pre-compute astronomy (cached)
            lat = location_meta.get("lat", 37.5)
            lon = location_meta.get("lon", 127.0)
            cache_key = (date_str, round(lat, 2), round(lon, 2))

            if cache_key not in astronomy_cache:
                astronomy_cache[cache_key] = _pre_compute_astronomy(date_str, lat, lon)
            astro = astronomy_cache[cache_key]

            # Calculate all 16 theme scores for this day
            day_scores = {}
            tasks = []
            for scorer in scorers:
                tasks.append(scorer.calculate_daily_score(
                    day_weather=all_day_weather,
                    date=date_str,
                    location_meta=location_meta,
                    marine_data=None,  # No marine data for region-level
                    astronomy=astro,
                ))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for scorer, res in zip(scorers, results):
                if isinstance(res, Exception):
                    logger.warning(f"Scorer {scorer.theme_name} failed for {region_code}/{date_str}: {res}")
                    day_scores[scorer.theme_name] = {"score": 0, "factors": {"error": str(res)}, "time_used": "N/A"}
                else:
                    day_scores[scorer.theme_name] = res

            daily_scores[date_str] = day_scores

        # --- Beach daily scores ---
        beach_daily_scores = []

        for beach in data.get("beaches", []):
            beach_weather = beach.get("weather", [])
            beach_marine = beach.get("marine", {})
            beach_wave_fc = beach.get("wave_forecast") or {}  # {date: wave_m} (fct_afs_do 해상예보)
            beach_day_groups = _group_timeslots_by_date(beach_weather)
            beach_sorted_dates = sorted(beach_day_groups.keys())

            beach_location_meta = dict(location_meta)
            beach_location_meta["is_coastal"] = True  # Beaches are always coastal
            beach_location_meta["is_south_coast"] = not beach_location_meta.get("is_east_coast", False) and not beach_location_meta.get("is_west_coast", False)

            beach_scores = {}
            for i, date_str in enumerate(beach_sorted_dates):
                day_slots = beach_day_groups[date_str]
                next_day_slots = beach_day_groups.get(beach_sorted_dates[i + 1], []) if i + 1 < len(beach_sorted_dates) else []
                night_slots = _build_night_timeslots(day_slots, next_day_slots)
                all_day_weather = day_slots + [s for s in night_slots if s not in day_slots]

                # Use beach lat/lon for astronomy if available
                b_lat = beach.get("lat", lat)
                b_lon = beach.get("lon", lon)
                cache_key = (date_str, round(b_lat, 2), round(b_lon, 2))

                if cache_key not in astronomy_cache:
                    astronomy_cache[cache_key] = _pre_compute_astronomy(date_str, b_lat, b_lon)
                astro = astronomy_cache[cache_key]

                # 날짜별 파고 예보(fct_afs_do) 주입 → 바다 장노출(동해)이 예보 파고로 채점.
                # marine이 없던(육상 전용) 해수욕장도 wave_height를 얻어 동해 테마가 살아난다.
                day_marine = beach_marine
                if date_str in beach_wave_fc:
                    day_marine = dict(beach_marine)
                    day_marine["wave_height"] = {"height": beach_wave_fc[date_str]}

                day_scores = {}
                tasks = []
                for scorer in scorers:
                    tasks.append(scorer.calculate_daily_score(
                        day_weather=all_day_weather,
                        date=date_str,
                        location_meta=beach_location_meta,
                        marine_data=day_marine,
                        astronomy=astro,
                    ))

                results = await asyncio.gather(*tasks, return_exceptions=True)

                for scorer, res in zip(scorers, results):
                    if isinstance(res, Exception):
                        logger.warning(f"Scorer {scorer.theme_name} failed for beach {beach.get('name')}/{date_str}: {res}")
                        day_scores[scorer.theme_name] = {"score": 0, "factors": {"error": str(res)}, "time_used": "N/A"}
                    else:
                        day_scores[scorer.theme_name] = res

                beach_scores[date_str] = day_scores

            beach_daily_scores.append({
                "beach_num": beach.get("beach_num"),
                "name": beach.get("name", ""),
                "daily_scores": beach_scores,
            })

        result[region_code] = {
            "region_name": region_name,
            "daily_scores": daily_scores,
            "beach_daily_scores": beach_daily_scores,
        }

    total_beaches = sum(len(d.get("beach_daily_scores", [])) for d in result.values())
    print(f"\r  일별 점수 계산 완료: {len(result)}개 지역, {total_beaches}개 해수욕장              ")
    return result


# =============================================================================
# Query helpers (work with both old and new format)
# =============================================================================

def get_best_times(
    scores_data: dict,
    theme: str,
    top_n: int = 5,
    min_score: float = 50.0
) -> List[Dict[str, Any]]:
    """Get best dates for a specific theme across all locations (daily format)"""
    candidates = []

    for region_code, region_data in scores_data.items():
        region_name = region_data.get("region_name", "")

        # Check region-level daily scores
        daily_scores = region_data.get("daily_scores", {})
        for date_str, theme_scores in daily_scores.items():
            if theme in theme_scores:
                score_data = theme_scores[theme]
                score = score_data.get("score", 0) if isinstance(score_data, dict) else score_data
                if score >= min_score:
                    candidates.append({
                        "region_code": region_code,
                        "region_name": region_name,
                        "location_type": "region",
                        "date": date_str,
                        "score": score,
                        "time_used": score_data.get("time_used", "N/A") if isinstance(score_data, dict) else "N/A",
                    })

        # Check beach-level daily scores
        for beach in region_data.get("beach_daily_scores", []):
            beach_num = beach.get("beach_num")
            beach_name = beach.get("name", "")

            for date_str, theme_scores in beach.get("daily_scores", {}).items():
                if theme in theme_scores:
                    score_data = theme_scores[theme]
                    score = score_data.get("score", 0) if isinstance(score_data, dict) else score_data
                    if score >= min_score:
                        candidates.append({
                            "region_code": region_code,
                            "region_name": region_name,
                            "location_type": "beach",
                            "beach_num": beach_num,
                            "beach_name": beach_name,
                            "date": date_str,
                            "score": score,
                            "time_used": score_data.get("time_used", "N/A") if isinstance(score_data, dict) else "N/A",
                        })

    candidates.sort(key=lambda x: (-x["score"], x["date"]))
    return candidates[:top_n]


def get_location_best_themes(
    scores_data: dict,
    region_code: str,
    date_str: str,
    location_type: str = "region",
    beach_num: Optional[int] = None,
    top_n: int = 3
) -> List[Dict[str, Any]]:
    """Get best themes for a specific location and date"""
    if region_code not in scores_data:
        return []

    region_data = scores_data[region_code]
    theme_scores = {}

    if location_type == "region":
        daily = region_data.get("daily_scores", {})
        if date_str in daily:
            theme_scores = daily[date_str]

    elif location_type == "beach" and beach_num is not None:
        for beach in region_data.get("beach_daily_scores", []):
            if beach.get("beach_num") == beach_num:
                daily = beach.get("daily_scores", {})
                if date_str in daily:
                    theme_scores = daily[date_str]
                break

    results = []
    for theme, score_data in theme_scores.items():
        score = score_data.get("score", 0) if isinstance(score_data, dict) else score_data
        results.append({
            "theme": theme,
            "score": score,
            "time_used": score_data.get("time_used", "N/A") if isinstance(score_data, dict) else "N/A",
        })

    results.sort(key=lambda x: -x["score"])
    return results[:top_n]


async def calculate_scores_for_timerange(
    merged_data: dict,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
) -> dict:
    """Calculate scores for a specific time range (legacy compat)"""
    filtered_data = {}

    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00')) if start_time else None
    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00')) if end_time else None

    for region_code, region_data in merged_data.items():
        filtered_region = {
            "region_name": region_data.get("region_name", ""),
            "forecasts": [],
            "beaches": []
        }

        if "forecasts" in region_data:
            for forecast in region_data["forecasts"]:
                dt_str = forecast.get("datetime")
                if dt_str:
                    dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                    if (not start_dt or dt >= start_dt) and (not end_dt or dt <= end_dt):
                        filtered_region["forecasts"].append(forecast)

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

    return await batch_calculate_scores(filtered_data)
