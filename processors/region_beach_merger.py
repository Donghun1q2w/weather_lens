"""Region-Beach Merger - Merges region weather data with beach weather data"""
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite

from config.settings import SQLITE_DB_PATH


async def get_region_beach_mapping(db_path: Path = SQLITE_DB_PATH) -> dict[str, list[int]]:
    """
    Get region-beach mapping from database.

    Queries the beaches table to build a mapping of region codes to beach numbers.
    Uses beaches.region_code -> regions.code relationship.

    Args:
        db_path: Path to SQLite database file

    Returns:
        dict[str, list[int]]: Mapping of region_code to list of beach_nums
            Example: {"1168010100": [1, 2, 3], "2611010100": [4, 5]}
    """
    mapping: dict[str, list[int]] = {}

    async with aiosqlite.connect(db_path) as db:
        # Query beaches table for region_code and beach_num
        async with db.execute(
            "SELECT region_code, beach_num FROM beaches WHERE region_code IS NOT NULL ORDER BY region_code, beach_num"
        ) as cursor:
            async for row in cursor:
                region_code = row[0]
                beach_num = row[1]

                if region_code not in mapping:
                    mapping[region_code] = []
                mapping[region_code].append(beach_num)

    return mapping


def merge_region_with_beaches(
    region_data: dict[str, Any],
    beach_data: dict[int, Any],
    mapping: dict[str, list[int]]
) -> dict[str, dict[str, Any]]:
    """
    Merge region weather data with corresponding beach weather data.

    For each region, attaches all beaches that belong to that region based on
    the region_code -> beach_num mapping.

    Args:
        region_data: Dictionary of region weather data, keyed by region_code
            Example: {"1168010100": {...weather...}, "2611010100": {...weather...}}
        beach_data: Dictionary of beach weather data, keyed by beach_num
            Example: {1: {"name": "해운대", ...weather...}, 2: {...}}
        mapping: Region to beach mapping from get_region_beach_mapping()
            Example: {"1168010100": [1, 2], "2611010100": [3]}

    Returns:
        dict[str, dict[str, Any]]: Merged data structure
            Example:
            {
                "1168010100": {
                    "region": {...region_weather_data...},
                    "beaches": [
                        {"beach_num": 1, "name": "해운대", "weather": {...}},
                        {"beach_num": 2, "name": "광안리", "weather": {...}}
                    ]
                },
                "2611010100": {
                    "region": {...region_weather_data...},
                    "beaches": [
                        {"beach_num": 3, "name": "속초", "weather": {...}}
                    ]
                }
            }
    """
    merged: dict[str, dict[str, Any]] = {}

    # Iterate through all regions
    for region_code, region_weather in region_data.items():
        merged[region_code] = {
            "region": region_weather,
            "beaches": []
        }

        # Add beaches if this region has any
        if region_code in mapping:
            beach_nums = mapping[region_code]
            for beach_num in beach_nums:
                if beach_num in beach_data:
                    beach_info = beach_data[beach_num]
                    merged[region_code]["beaches"].append({
                        "beach_num": beach_num,
                        "name": beach_info.get("name", f"Beach {beach_num}"),
                        "weather": beach_info
                    })

    return merged


async def get_merged_forecast_data(
    regions_weather: dict[str, Any],
    beaches_weather: dict[int, Any],
    db_path: Path = SQLITE_DB_PATH
) -> dict[str, Any]:
    """
    Get complete merged forecast data with metadata.

    This is the main integration function that combines region and beach weather
    data with metadata about the merge operation.

    Args:
        regions_weather: Dictionary of region weather data, keyed by region_code
        beaches_weather: Dictionary of beach weather data, keyed by beach_num
        db_path: Path to SQLite database file

    Returns:
        dict[str, Any]: Complete merged data with metadata
            Example:
            {
                "metadata": {
                    "timestamp": "2025-01-15T12:00:00",
                    "total_regions": 3500,
                    "regions_with_beaches": 150,
                    "total_beaches": 420,
                    "regions_with_data": 3500,
                    "beaches_with_data": 420
                },
                "data": {
                    "1168010100": {
                        "region": {...},
                        "beaches": [...]
                    },
                    ...
                }
            }
    """
    # Get the region-beach mapping
    mapping = await get_region_beach_mapping(db_path)

    # Merge the data
    merged_data = merge_region_with_beaches(regions_weather, beaches_weather, mapping)

    # Calculate metadata
    regions_with_beaches = len([
        region_code for region_code in merged_data
        if len(merged_data[region_code]["beaches"]) > 0
    ])

    total_beaches_in_merged = sum(
        len(merged_data[region_code]["beaches"])
        for region_code in merged_data
    )

    # Build complete response
    result = {
        "metadata": {
            "timestamp": datetime.utcnow().isoformat(),
            "total_regions": len(regions_weather),
            "regions_with_beaches": regions_with_beaches,
            "total_beaches": len(beaches_weather),
            "regions_with_data": len(merged_data),
            "beaches_with_data": total_beaches_in_merged,
        },
        "data": merged_data
    }

    return result
