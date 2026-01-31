"""Batch Cache Processor - Bulk weather data caching with concurrency control"""
import asyncio
import time
from dataclasses import dataclass
from typing import Callable, Optional

from processors.cache_writer import CacheWriter


@dataclass
class CacheResult:
    """Result of batch caching operation"""
    total: int
    success: int
    failed: int
    errors: list[str]
    elapsed_seconds: float


class BatchCacheProcessor:
    """Batch processor for caching weather data for multiple regions/beaches"""

    def __init__(self, cache_writer: Optional[CacheWriter] = None, concurrency: int = 10):
        """
        Initialize batch cache processor.

        Args:
            cache_writer: CacheWriter instance (creates new if None)
            concurrency: Maximum concurrent operations (default: 10)
        """
        self.cache_writer = cache_writer or CacheWriter()
        self.concurrency = concurrency

    async def cache_all_regions(
        self,
        regions: list,
        weather_data: dict,
    ) -> CacheResult:
        """
        Cache weather data for all regions.

        Args:
            regions: List of region objects (with region_code, region_name, coordinates)
            weather_data: Dictionary mapping region_code to forecast data

        Returns:
            CacheResult: Summary of caching operation
        """
        start_time = time.time()
        total = len(regions)
        success = 0
        failed = 0
        errors = []

        async def cache_region(region):
            nonlocal success, failed
            try:
                region_code = region.get("region_code") or region.get("code")
                region_name = region.get("region_name") or region.get("name")
                coordinates = region.get("coordinates")
                forecast = weather_data.get(region_code, [])

                if not forecast:
                    errors.append(f"No forecast data for region {region_code}")
                    failed += 1
                    return

                ocean_station_id = region.get("ocean_station_id")

                await self.cache_writer.write_cache(
                    region_code=region_code,
                    region_name=region_name,
                    coordinates=coordinates,
                    forecast=forecast,
                    ocean_station_id=ocean_station_id,
                )
                success += 1
            except Exception as e:
                errors.append(f"Failed to cache region {region.get('region_code', 'unknown')}: {str(e)}")
                failed += 1

        # Execute with concurrency control
        await self.parallel_cache(regions, cache_region, self.concurrency)

        elapsed = time.time() - start_time

        return CacheResult(
            total=total,
            success=success,
            failed=failed,
            errors=errors,
            elapsed_seconds=elapsed,
        )

    async def cache_all_beaches(
        self,
        beaches: list,
        beach_data: dict,
    ) -> CacheResult:
        """
        Cache weather data for all beaches.

        Args:
            beaches: List of beach objects (with beach_num, name, coordinates)
            beach_data: Dictionary mapping beach_num to forecast data

        Returns:
            CacheResult: Summary of caching operation
        """
        start_time = time.time()
        total = len(beaches)
        success = 0
        failed = 0
        errors = []

        async def cache_beach(beach):
            nonlocal success, failed
            try:
                beach_num = beach.get("beach_num") or beach.get("num")
                beach_name = beach.get("name")
                coordinates = beach.get("coordinates")
                forecast = beach_data.get(beach_num, [])

                if not forecast:
                    errors.append(f"No forecast data for beach {beach_num}")
                    failed += 1
                    return

                # Use beach_num as region_code for cache
                await self.cache_writer.write_cache(
                    region_code=f"beach_{beach_num}",
                    region_name=beach_name,
                    coordinates=coordinates,
                    forecast=forecast,
                )
                success += 1
            except Exception as e:
                errors.append(f"Failed to cache beach {beach.get('beach_num', 'unknown')}: {str(e)}")
                failed += 1

        # Execute with concurrency control
        await self.parallel_cache(beaches, cache_beach, self.concurrency)

        elapsed = time.time() - start_time

        return CacheResult(
            total=total,
            success=success,
            failed=failed,
            errors=errors,
            elapsed_seconds=elapsed,
        )

    async def cache_marine_zones(
        self,
        zones: list,
        marine_data: dict,
    ) -> CacheResult:
        """
        Cache marine forecast data for all zones.

        Args:
            zones: List of marine zone objects (with zone_id, name, coordinates)
            marine_data: Dictionary mapping zone_id to forecast data

        Returns:
            CacheResult: Summary of caching operation
        """
        start_time = time.time()
        total = len(zones)
        success = 0
        failed = 0
        errors = []

        async def cache_zone(zone):
            nonlocal success, failed
            try:
                zone_id = zone.get("zone_id") or zone.get("id")
                zone_name = zone.get("name")
                coordinates = zone.get("coordinates")
                forecast = marine_data.get(zone_id, [])

                if not forecast:
                    errors.append(f"No forecast data for zone {zone_id}")
                    failed += 1
                    return

                # Use zone_id as region_code for cache
                await self.cache_writer.write_cache(
                    region_code=f"marine_{zone_id}",
                    region_name=zone_name,
                    coordinates=coordinates,
                    forecast=forecast,
                )
                success += 1
            except Exception as e:
                errors.append(f"Failed to cache marine zone {zone.get('zone_id', 'unknown')}: {str(e)}")
                failed += 1

        # Execute with concurrency control
        await self.parallel_cache(zones, cache_zone, self.concurrency)

        elapsed = time.time() - start_time

        return CacheResult(
            total=total,
            success=success,
            failed=failed,
            errors=errors,
            elapsed_seconds=elapsed,
        )

    async def parallel_cache(
        self,
        items: list,
        cache_func: Callable,
        concurrency: int = 10,
    ) -> list:
        """
        Execute cache operations in parallel with concurrency control.

        Args:
            items: List of items to cache
            cache_func: Async function to call for each item
            concurrency: Maximum concurrent operations (default: 10)

        Returns:
            list: Results from all cache operations
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def bounded_cache(item):
            async with semaphore:
                return await cache_func(item)

        tasks = [bounded_cache(item) for item in items]
        return await asyncio.gather(*tasks, return_exceptions=True)


# Helper functions for convenient batch caching

async def batch_cache_regions(
    region_codes: list[str],
    data_fetcher: Callable,
) -> CacheResult:
    """
    Convenience function to batch cache regions.

    Args:
        region_codes: List of region codes to cache
        data_fetcher: Async function that fetches data for a region code
            Should return dict with keys: region_name, coordinates, forecast, ocean_station_id

    Returns:
        CacheResult: Summary of caching operation

    Example:
        async def fetch_data(code):
            return {
                'region_name': 'Seoul',
                'coordinates': {'lat': 37.5, 'lng': 127.0},
                'forecast': [...],
                'ocean_station_id': None
            }

        result = await batch_cache_regions(['1168010100', '1168010200'], fetch_data)
    """
    start_time = time.time()
    processor = BatchCacheProcessor()
    total = len(region_codes)
    success = 0
    failed = 0
    errors = []

    async def cache_one(code):
        nonlocal success, failed
        try:
            data = await data_fetcher(code)
            await processor.cache_writer.write_cache(
                region_code=code,
                region_name=data["region_name"],
                coordinates=data["coordinates"],
                forecast=data["forecast"],
                ocean_station_id=data.get("ocean_station_id"),
            )
            success += 1
        except Exception as e:
            errors.append(f"Failed to cache region {code}: {str(e)}")
            failed += 1

    await processor.parallel_cache(region_codes, cache_one)

    elapsed = time.time() - start_time

    return CacheResult(
        total=total,
        success=success,
        failed=failed,
        errors=errors,
        elapsed_seconds=elapsed,
    )


async def batch_cache_beaches(
    beach_nums: list[str],
    data_fetcher: Callable,
) -> CacheResult:
    """
    Convenience function to batch cache beaches.

    Args:
        beach_nums: List of beach numbers to cache
        data_fetcher: Async function that fetches data for a beach number
            Should return dict with keys: name, coordinates, forecast

    Returns:
        CacheResult: Summary of caching operation

    Example:
        async def fetch_data(num):
            return {
                'name': 'Haeundae Beach',
                'coordinates': {'lat': 35.1, 'lng': 129.1},
                'forecast': [...]
            }

        result = await batch_cache_beaches(['1', '2', '3'], fetch_data)
    """
    start_time = time.time()
    processor = BatchCacheProcessor()
    total = len(beach_nums)
    success = 0
    failed = 0
    errors = []

    async def cache_one(num):
        nonlocal success, failed
        try:
            data = await data_fetcher(num)
            await processor.cache_writer.write_cache(
                region_code=f"beach_{num}",
                region_name=data["name"],
                coordinates=data["coordinates"],
                forecast=data["forecast"],
            )
            success += 1
        except Exception as e:
            errors.append(f"Failed to cache beach {num}: {str(e)}")
            failed += 1

    await processor.parallel_cache(beach_nums, cache_one)

    elapsed = time.time() - start_time

    return CacheResult(
        total=total,
        success=success,
        failed=failed,
        errors=errors,
        elapsed_seconds=elapsed,
    )
