"""
Processors Module - Data processing and transformation

This module handles:
- Merging weather data from multiple API sources (KMA, Open-Meteo)
- Writing processed data to JSON cache files
- Loading and managing regional data (읍면동)
"""

from processors.cache_writer import (
    CacheWriter,
    write_weather_cache,
    write_beach_weather_cache,
    write_marine_forecast_cache,
)
from processors.batch_cache import (
    BatchCacheProcessor,
    CacheResult,
    batch_cache_regions,
    batch_cache_beaches,
)
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
from processors.region_beach_merger import (
    get_region_beach_mapping,
    merge_region_with_beaches,
    get_merged_forecast_data,
)
from processors.weather_integrator import (
    fetch_all_weather_data,
    filter_3hour_intervals,
    get_integrated_weather,
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
    "write_beach_weather_cache",
    "write_marine_forecast_cache",
    # Batch cache
    "BatchCacheProcessor",
    "CacheResult",
    "batch_cache_regions",
    "batch_cache_beaches",
    # Region loader
    "Region",
    "RegionLoader",
    "initialize_regions_db",
    "load_all_regions",
    "load_region",
    # Region-beach merger
    "get_region_beach_mapping",
    "merge_region_with_beaches",
    "get_merged_forecast_data",
    # Weather integrator
    "fetch_all_weather_data",
    "filter_3hour_intervals",
    "get_integrated_weather",
]
