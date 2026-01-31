"""Cache Writer - Writes weather data to JSON cache files"""
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

import orjson

from config.settings import CACHE_DIR
from processors.data_merger import WeatherData, weather_data_to_dict


class CacheWriter:
    """Handles writing weather forecast data to JSON cache files"""

    def __init__(self, cache_dir: Path = CACHE_DIR):
        """
        Initialize cache writer.

        Args:
            cache_dir: Base directory for cache storage
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, date: datetime, region_code: str) -> Path:
        """
        Get cache file path for a specific date and region.

        Args:
            date: Date for the cache file
            region_code: Region code in format "sido_sigungu_emd"

        Returns:
            Path: Full path to cache file
        """
        date_str = date.strftime("%Y-%m-%d")
        date_dir = self.cache_dir / date_str
        date_dir.mkdir(parents=True, exist_ok=True)
        return date_dir / f"{region_code}.json"

    async def write_cache(
        self,
        region_code: str,
        region_name: str,
        coordinates: dict[str, float],
        forecast: list[WeatherData],
        ocean_station_id: Optional[str] = None,
        date: Optional[datetime] = None,
    ) -> Path:
        """
        Write weather forecast to JSON cache file.

        Args:
            region_code: Region code (e.g., "1168010100")
            region_name: Full region name (e.g., "서울특별시 강남구 역삼동")
            coordinates: Dictionary with 'lat' and 'lng' keys
            forecast: List of WeatherData objects
            ocean_station_id: Optional ocean station ID for coastal regions
            date: Date for cache (defaults to today)

        Returns:
            Path: Path to written cache file

        Raises:
            ValueError: If coordinates missing lat/lng
        """
        if "lat" not in coordinates or "lng" not in coordinates:
            raise ValueError("Coordinates must contain 'lat' and 'lng' keys")

        if date is None:
            date = datetime.now()

        # Construct cache data matching spec.md schema
        cache_data = {
            "region_code": region_code,
            "region_name": region_name,
            "coordinates": {
                "lat": coordinates["lat"],
                "lng": coordinates["lng"],
            },
            "updated_at": datetime.now().isoformat(),
            "forecast": [weather_data_to_dict(w) for w in forecast],
            "ocean_station_id": ocean_station_id,
        }

        # Get cache file path
        cache_path = self._get_cache_path(date, self._format_region_code(region_name))

        # Write to file using orjson for performance
        await self._write_json_async(cache_path, cache_data)

        return cache_path

    @staticmethod
    def _format_region_code(region_name: str) -> str:
        """
        Format region name to filename format: sido_sigungu_emd.

        Args:
            region_name: Full region name (e.g., "서울특별시 강남구 역삼동")

        Returns:
            str: Formatted code (e.g., "서울특별시_강남구_역삼동")
        """
        parts = region_name.strip().split()
        if len(parts) >= 3:
            return f"{parts[0]}_{parts[1]}_{parts[2]}"
        return region_name.replace(" ", "_")

    async def _write_json_async(self, path: Path, data: dict) -> None:
        """
        Asynchronously write JSON data to file.

        Args:
            path: Path to write to
            data: Data to serialize

        Uses orjson for fast serialization and async I/O for non-blocking writes.
        """
        # Serialize with orjson (faster than json module)
        json_bytes = orjson.dumps(
            data,
            option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS,
        )

        # Write asynchronously
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, path.write_bytes, json_bytes)

    async def read_cache(
        self,
        region_code: str,
        region_name: str,
        date: Optional[datetime] = None,
    ) -> Optional[dict]:
        """
        Read weather forecast from cache.

        Args:
            region_code: Region code
            region_name: Full region name
            date: Date for cache (defaults to today)

        Returns:
            Optional[dict]: Cache data if exists, None otherwise
        """
        if date is None:
            date = datetime.now()

        cache_path = self._get_cache_path(date, self._format_region_code(region_name))

        if not cache_path.exists():
            return None

        # Read asynchronously
        loop = asyncio.get_event_loop()
        json_bytes = await loop.run_in_executor(None, cache_path.read_bytes)

        return orjson.loads(json_bytes)

    async def write(self, region_code: str, data: dict, date: Optional[datetime] = None) -> Path:
        """
        Simple write method using region_code directly.

        Args:
            region_code: Region code
            data: Data dictionary to write
            date: Date for cache (defaults to today)

        Returns:
            Path: Path to written cache file
        """
        if date is None:
            date = datetime.now()

        cache_path = self._get_cache_path(date, region_code)
        await self._write_json_async(cache_path, data)
        return cache_path

    async def read(self, region_code: str, date: Optional[datetime] = None) -> Optional[dict]:
        """
        Simple read method using region_code directly.

        Args:
            region_code: Region code
            date: Date for cache (defaults to today)

        Returns:
            Optional[dict]: Cache data if exists, None otherwise
        """
        if date is None:
            date = datetime.now()

        cache_path = self._get_cache_path(date, region_code)

        if not cache_path.exists():
            return None

        # Read asynchronously
        loop = asyncio.get_event_loop()
        json_bytes = await loop.run_in_executor(None, cache_path.read_bytes)

        return orjson.loads(json_bytes)

    def clear_old_caches(self, days_to_keep: int = 3) -> int:
        """
        Clear cache directories older than specified days.

        Args:
            days_to_keep: Number of days to keep (default: 3)

        Returns:
            int: Number of directories removed
        """
        import shutil
        from datetime import timedelta

        removed_count = 0
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        for date_dir in self.cache_dir.iterdir():
            if not date_dir.is_dir():
                continue

            try:
                # Parse directory name as date
                dir_date = datetime.strptime(date_dir.name, "%Y-%m-%d")
                if dir_date < cutoff_date:
                    shutil.rmtree(date_dir)
                    removed_count += 1
            except ValueError:
                # Skip directories with invalid date format
                continue

        return removed_count


# Convenience function for simple usage
async def write_weather_cache(
    region_code: str,
    region_name: str,
    coordinates: dict[str, float],
    forecast: list[WeatherData],
    ocean_station_id: Optional[str] = None,
) -> Path:
    """
    Convenience function to write weather cache.

    Args:
        region_code: Region code
        region_name: Full region name
        coordinates: Dictionary with 'lat' and 'lng'
        forecast: List of WeatherData objects
        ocean_station_id: Optional ocean station ID

    Returns:
        Path: Path to written cache file
    """
    writer = CacheWriter()
    return await writer.write_cache(
        region_code=region_code,
        region_name=region_name,
        coordinates=coordinates,
        forecast=forecast,
        ocean_station_id=ocean_station_id,
    )
