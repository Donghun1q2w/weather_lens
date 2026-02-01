"""
Weather Data Integration Module

Provides functions to:
1. Fetch all weather data for regions and beaches using Open-Meteo Bulk API
2. Filter hourly data to 3-hour intervals for +2 days
3. Return integrated weather data with metadata
"""
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests

from config.settings import SQLITE_DB_PATH

# Open-Meteo API
OPENMETEO_URL = "https://api.open-meteo.com/v1/forecast"


def fetch_all_weather_data(hourly_mode: bool = True) -> Dict[str, Any]:
    """
    Fetch weather data for all regions and beaches using Open-Meteo Bulk API.

    Args:
        hourly_mode: If True, fetch 72-hour hourly data; if False, current hour only

    Returns:
        Dictionary with structure:
        {
            "regions": {region_code: weather_data},
            "beaches": {beach_num: weather_data},
            "metadata": {
                "collected_at": ISO timestamp,
                "mode": "hourly" or "current",
                "total_regions": count,
                "total_beaches": count,
                "success_regions": count,
                "success_beaches": count,
            }
        }
    """
    print(f"\n{'='*60}")
    print(f"날씨 데이터 통합 수집 시작")
    print(f"모드: {'72시간 hourly' if hourly_mode else '현재 시간만'}")
    print(f"{'='*60}")

    collected_at = datetime.now()

    # Load all regions from database
    print("\n[1/4] 지역 데이터 로드 중...")
    regions = _load_regions()
    print(f"  총 {len(regions)}개 지역 로드됨")

    # Load all beaches from database
    print("\n[2/4] 해수욕장 데이터 로드 중...")
    beaches = _load_beaches()
    print(f"  총 {len(beaches)}개 해수욕장 로드됨")

    # Fetch weather data for regions using Bulk API
    print("\n[3/4] 지역 날씨 수집 중 (Bulk API)...")
    regions_weather = _fetch_openmeteo_bulk(
        locations=regions,
        location_type="region",
        hourly_mode=hourly_mode,
        batch_size=100
    )

    # Fetch weather data for beaches using Bulk API
    print("\n[4/4] 해수욕장 날씨 수집 중 (Bulk API)...")
    beaches_weather = _fetch_openmeteo_bulk(
        locations=beaches,
        location_type="beach",
        hourly_mode=hourly_mode,
        batch_size=100
    )

    # Prepare metadata
    metadata = {
        "collected_at": collected_at.isoformat(),
        "mode": "hourly" if hourly_mode else "current",
        "total_regions": len(regions),
        "total_beaches": len(beaches),
        "success_regions": len(regions_weather),
        "success_beaches": len(beaches_weather),
        "forecast_days": 3,
        "forecast_hours": 72,
    }

    print(f"\n{'='*60}")
    print(f"수집 완료")
    print(f"  지역: {metadata['success_regions']}/{metadata['total_regions']} 성공")
    print(f"  해수욕장: {metadata['success_beaches']}/{metadata['total_beaches']} 성공")
    print(f"{'='*60}\n")

    return {
        "regions": regions_weather,
        "beaches": beaches_weather,
        "metadata": metadata,
    }


def filter_3hour_intervals(weather_data: Dict[str, Any], days: int = 2) -> Dict[str, Any]:
    """
    Filter hourly weather data to 3-hour intervals for specified days.

    Args:
        weather_data: Dictionary with "regions" and "beaches" hourly data
        days: Number of days from now to include (default: 2 for +2 days)

    Returns:
        Filtered weather data with 3-hour intervals (00, 03, 06, 09, 12, 15, 18, 21)
        Maximum of 17 timepoints for 2 days (current hour + 48 hours)
    """
    print(f"\n3시간 간격 필터링 시작 (D-day ~ D+{days})")

    now = datetime.now()
    # Calculate end time (current + days * 24 hours)
    end_time = now + timedelta(days=days)

    # Target hours for 3-hour intervals
    target_hours = [0, 3, 6, 9, 12, 15, 18, 21]

    filtered_regions = {}
    filtered_beaches = {}

    # Filter regions
    if "regions" in weather_data:
        print(f"\n[1/2] 지역 데이터 필터링 중...")
        for region_code, data in weather_data["regions"].items():
            if "hourly" in data:
                filtered_hourly = _filter_hourly_to_3hour(
                    data["hourly"],
                    now,
                    end_time,
                    target_hours
                )
                filtered_regions[region_code] = {
                    "hourly": filtered_hourly,
                    "current": data.get("current"),
                }
        print(f"  {len(filtered_regions)}개 지역 필터링 완료")

    # Filter beaches
    if "beaches" in weather_data:
        print(f"\n[2/2] 해수욕장 데이터 필터링 중...")
        for beach_num, data in weather_data["beaches"].items():
            if "hourly" in data:
                filtered_hourly = _filter_hourly_to_3hour(
                    data["hourly"],
                    now,
                    end_time,
                    target_hours
                )
                filtered_beaches[beach_num] = {
                    "hourly": filtered_hourly,
                    "current": data.get("current"),
                }
        print(f"  {len(filtered_beaches)}개 해수욕장 필터링 완료")

    # Update metadata
    metadata = weather_data.get("metadata", {}).copy()
    metadata["filtered_at"] = datetime.now().isoformat()
    metadata["filter_interval_hours"] = 3
    metadata["filter_days"] = days

    result = {
        "regions": filtered_regions,
        "beaches": filtered_beaches,
        "metadata": metadata,
    }

    print(f"\n3시간 간격 필터링 완료")
    print(f"  예상 시점 수: 최대 {(days * 24 // 3) + 1}개")

    return result


def get_integrated_weather() -> Dict[str, Any]:
    """
    Get integrated weather data with 3-hour intervals.

    Combines fetch_all_weather_data() and filter_3hour_intervals()
    to provide a single function for easy access.

    Returns:
        Dictionary with structure:
        {
            "regions": {region_code: {"hourly": [...], "current": {...}}},
            "beaches": {beach_num: {"hourly": [...], "current": {...}}},
            "metadata": {
                "collected_at": ISO timestamp,
                "filtered_at": ISO timestamp,
                "mode": "hourly",
                "filter_interval_hours": 3,
                "filter_days": 2,
                ...
            }
        }
    """
    print("\n통합 날씨 데이터 수집 (3시간 간격)")

    # Step 1: Fetch all hourly data
    weather_data = fetch_all_weather_data(hourly_mode=True)

    # Step 2: Filter to 3-hour intervals for +2 days
    filtered_data = filter_3hour_intervals(weather_data, days=2)

    print("\n통합 수집 완료")

    return filtered_data


# ============================================================================
# Internal Helper Functions
# ============================================================================

def _load_regions() -> List[Dict[str, Any]]:
    """Load all regions from database."""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT code, name, sido, lat, lon, elevation,
               is_coastal, is_east_coast, is_west_coast
        FROM regions
        ORDER BY sido, name
    """)

    regions = []
    for row in cursor.fetchall():
        regions.append({
            "code": row[0],
            "name": row[1],
            "sido": row[2],
            "lat": row[3],
            "lon": row[4],
            "elevation": row[5] or 0,
            "is_coastal": bool(row[6]),
            "is_east_coast": bool(row[7]),
            "is_west_coast": bool(row[8]),
        })

    conn.close()
    return regions


def _load_beaches() -> List[Dict[str, Any]]:
    """Load all beaches from database."""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT beach_num, name, lat, lon, region_code
        FROM beaches
        ORDER BY beach_num
    """)

    beaches = []
    for row in cursor.fetchall():
        beaches.append({
            "beach_num": row[0],
            "name": row[1],
            "lat": row[2],
            "lon": row[3],
            "region_code": row[4],
        })

    conn.close()
    return beaches


def _fetch_openmeteo_bulk(
    locations: List[Dict[str, Any]],
    location_type: str,
    hourly_mode: bool = False,
    batch_size: int = 100
) -> Dict[str, Any]:
    """
    Fetch weather data from Open-Meteo Bulk API.

    Args:
        locations: List of location dicts with lat/lon
        location_type: "region" or "beach" for key identification
        hourly_mode: If True, return 72-hour hourly data
        batch_size: Number of locations per API request (max 100 recommended)

    Returns:
        Dictionary mapping location keys to weather data
    """
    results = {}

    # Filter locations with valid lat/lon
    valid_locations = [loc for loc in locations if loc.get("lat") and loc.get("lon")]
    total_batches = (len(valid_locations) + batch_size - 1) // batch_size

    print(f"  총 {len(valid_locations)}개 위치, {total_batches}개 배치")

    for batch_idx in range(0, len(valid_locations), batch_size):
        batch = valid_locations[batch_idx:batch_idx + batch_size]
        batch_num = batch_idx // batch_size + 1

        print(f"\r  배치 {batch_num}/{total_batches} ({len(batch)}개 좌표)...", end="", flush=True)

        # Prepare comma-separated coordinates
        lats = ",".join(str(loc["lat"]) for loc in batch)
        lons = ",".join(str(loc["lon"]) for loc in batch)

        try:
            params = {
                "latitude": lats,
                "longitude": lons,
                "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,cloud_cover,wind_speed_10m",
                "timezone": "Asia/Seoul",
                "forecast_days": 3,
            }

            response = requests.get(OPENMETEO_URL, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()

            # Handle single or multiple location responses
            responses = data if isinstance(data, list) else [data]

            # Process each location in batch
            for idx, location in enumerate(batch):
                if idx >= len(responses):
                    continue

                location_data = responses[idx]
                if "hourly" not in location_data:
                    continue

                hourly = location_data["hourly"]
                times = hourly.get("time", [])

                # Determine location key
                if location_type == "region":
                    loc_key = location["code"]
                else:  # beach
                    loc_key = str(location["beach_num"])

                if hourly_mode:
                    # Build hourly data array
                    hourly_data = []
                    for i in range(len(times)):
                        hourly_data.append({
                            "datetime": times[i],
                            "temperature": hourly["temperature_2m"][i] if i < len(hourly["temperature_2m"]) else None,
                            "humidity": hourly["relative_humidity_2m"][i] if i < len(hourly["relative_humidity_2m"]) else None,
                            "rain_probability": hourly["precipitation_probability"][i] if i < len(hourly["precipitation_probability"]) else None,
                            "cloud_cover": hourly["cloud_cover"][i] if i < len(hourly["cloud_cover"]) else None,
                            "wind_speed": hourly["wind_speed_10m"][i] if i < len(hourly["wind_speed_10m"]) else None,
                        })

                    # Current hour as first element
                    current_hour = datetime.now().hour
                    current_data = hourly_data[current_hour] if current_hour < len(hourly_data) else None

                    results[loc_key] = {
                        "hourly": hourly_data,
                        "current": current_data,
                    }
                else:
                    # Only current hour
                    current_hour = datetime.now().hour
                    idx_h = current_hour
                    results[loc_key] = {
                        "temperature": hourly["temperature_2m"][idx_h] if idx_h < len(hourly["temperature_2m"]) else None,
                        "humidity": hourly["relative_humidity_2m"][idx_h] if idx_h < len(hourly["relative_humidity_2m"]) else None,
                        "rain_probability": hourly["precipitation_probability"][idx_h] if idx_h < len(hourly["precipitation_probability"]) else None,
                        "cloud_cover": hourly["cloud_cover"][idx_h] if idx_h < len(hourly["cloud_cover"]) else None,
                        "wind_speed": hourly["wind_speed_10m"][idx_h] if idx_h < len(hourly["wind_speed_10m"]) else None,
                    }

            # Rate limit prevention
            time.sleep(2)

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                # Rate limit - wait and retry
                print(f"\n  ⚠️  배치 {batch_num} Rate Limit 초과, 5초 대기 후 재시도...")
                time.sleep(5)

                # Retry once
                try:
                    response = requests.get(OPENMETEO_URL, params=params, timeout=60)
                    response.raise_for_status()
                    data = response.json()

                    responses = data if isinstance(data, list) else [data]

                    for idx, location in enumerate(batch):
                        if idx >= len(responses):
                            continue
                        location_data = responses[idx]
                        if "hourly" not in location_data:
                            continue

                        hourly = location_data["hourly"]
                        times = hourly.get("time", [])

                        loc_key = location["code"] if location_type == "region" else str(location["beach_num"])

                        if hourly_mode:
                            hourly_data = []
                            for i in range(len(times)):
                                hourly_data.append({
                                    "datetime": times[i],
                                    "temperature": hourly["temperature_2m"][i] if i < len(hourly["temperature_2m"]) else None,
                                    "humidity": hourly["relative_humidity_2m"][i] if i < len(hourly["relative_humidity_2m"]) else None,
                                    "rain_probability": hourly["precipitation_probability"][i] if i < len(hourly["precipitation_probability"]) else None,
                                    "cloud_cover": hourly["cloud_cover"][i] if i < len(hourly["cloud_cover"]) else None,
                                    "wind_speed": hourly["wind_speed_10m"][i] if i < len(hourly["wind_speed_10m"]) else None,
                                })
                            current_hour = datetime.now().hour
                            current_data = hourly_data[current_hour] if current_hour < len(hourly_data) else None
                            results[loc_key] = {"hourly": hourly_data, "current": current_data}
                        else:
                            current_hour = datetime.now().hour
                            idx_h = current_hour
                            results[loc_key] = {
                                "temperature": hourly["temperature_2m"][idx_h] if idx_h < len(hourly["temperature_2m"]) else None,
                                "humidity": hourly["relative_humidity_2m"][idx_h] if idx_h < len(hourly["relative_humidity_2m"]) else None,
                                "rain_probability": hourly["precipitation_probability"][idx_h] if idx_h < len(hourly["precipitation_probability"]) else None,
                                "cloud_cover": hourly["cloud_cover"][idx_h] if idx_h < len(hourly["cloud_cover"]) else None,
                                "wind_speed": hourly["wind_speed_10m"][idx_h] if idx_h < len(hourly["wind_speed_10m"]) else None,
                            }

                    print(f"  재시도 성공")
                    time.sleep(2)

                except Exception as retry_e:
                    print(f"\n  ⚠️  배치 {batch_num} 재시도 실패: {retry_e}")
                    # Skip failed batch - individual fallback could be added here
            else:
                print(f"\n  ⚠️  배치 {batch_num} HTTP 오류: {e}")

        except Exception as e:
            print(f"\n  ⚠️  배치 {batch_num} 오류: {e}")

    print(f"\r  Bulk API 완료: {len(results)}/{len(valid_locations)} 성공                    ")
    return results


def _filter_hourly_to_3hour(
    hourly_data: List[Dict[str, Any]],
    start_time: datetime,
    end_time: datetime,
    target_hours: List[int]
) -> List[Dict[str, Any]]:
    """
    Filter hourly data to only include 3-hour intervals.

    Args:
        hourly_data: List of hourly weather data dicts
        start_time: Start datetime (now)
        end_time: End datetime (now + days)
        target_hours: List of target hours [0, 3, 6, 9, 12, 15, 18, 21]

    Returns:
        Filtered list with only 3-hour interval entries
    """
    filtered = []

    for entry in hourly_data:
        dt_str = entry.get("datetime")
        if not dt_str:
            continue

        # Parse datetime
        try:
            entry_dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            # Remove timezone for comparison
            entry_dt = entry_dt.replace(tzinfo=None)
        except (ValueError, AttributeError):
            continue

        # Check if within time range
        if entry_dt < start_time or entry_dt > end_time:
            continue

        # Check if hour matches 3-hour interval
        if entry_dt.hour in target_hours:
            filtered.append(entry)

    return filtered
