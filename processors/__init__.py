"""
Processors Module - Data processing and transformation

This module handles:
- Merging weather data from multiple API sources (KMA, Open-Meteo)
- Writing processed data to JSON cache files
- Loading and managing regional data (읍면동)
"""

from processors.cache_writer import CacheWriter, write_weather_cache
from processors.data_merger import (
    WeatherData,
    WeatherValue,
    calculate_weighted_average,
    merge_weather_data,
    merge_weather_value,
    weather_data_to_dict,
)
from processors.region_loader import (
    Region,
    RegionLoader,
    initialize_regions_db,
    load_all_regions,
    load_region,
)

__all__ = [
    # Data merger
    "WeatherData",
    "WeatherValue",
    "calculate_weighted_average",
    "merge_weather_data",
    "merge_weather_value",
    "weather_data_to_dict",
    # Cache writer
    "CacheWriter",
    "write_weather_cache",
    # Region loader
    "Region",
    "RegionLoader",
    "initialize_regions_db",
    "load_all_regions",
    "load_region",
]
