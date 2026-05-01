"""Example usage of data collectors"""
import asyncio
from datetime import datetime, timedelta
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from collectors import (
    KMAForecastCollector,
    OpenMeteoCollector,
    AirKoreaCollector,
    KHOAOceanCollector,
    CollectorError
)
from config import settings


async def example_kma_forecast():
    """Example: Collect KMA forecast data"""
    print("\n=== KMA Forecast Collector ===")

    try:
        async with KMAForecastCollector(settings.KMA_API_KEY) as collector:
            result = await collector.collect(
                region_code="1168010100",  # 서울특별시 강남구 역삼동
                nx=60,  # Example grid coordinate
                ny=127  # Example grid coordinate
            )

            print(f"✓ Collected {len(result['forecast'])} forecast entries")
            print(f"  Base time: {result['base_date']} {result['base_time']}")

            # Show first entry
            if result['forecast']:
                first = result['forecast'][0]
                print(f"  First entry: {first['datetime']}")
                print(f"    Temp: {first['temp']}°C")
                print(f"    Humidity: {first['humidity']}%")
                print(f"    Cloud cover: {first['cloud_cover']}%")

    except CollectorError as e:
        print(f"✗ KMA collection failed: {e}")


async def example_open_meteo():
    """Example: Collect Open-Meteo forecast data"""
    print("\n=== Open-Meteo Collector ===")

    try:
        async with OpenMeteoCollector() as collector:
            result = await collector.collect(
                region_code="1168010100",
                lat=37.5000,
                lng=127.0364
            )

            print(f"✓ Collected {len(result['forecast'])} forecast entries")

            # Show first entry
            if result['forecast']:
                first = result['forecast'][0]
                print(f"  First entry: {first['datetime']}")
                print(f"    Temp: {first['temp']}°C")
                print(f"    Humidity: {first['humidity']}%")
                print(f"    Cloud cover: {first['cloud_cover']}%")

    except CollectorError as e:
        print(f"✗ Open-Meteo collection failed: {e}")


async def example_airkorea():
    """Example: Collect AirKorea air quality data"""
    print("\n=== AirKorea Collector ===")

    try:
        async with AirKoreaCollector(settings.AIRKOREA_API_KEY) as collector:
            result = await collector.collect(
                region_code="1168010100",
                station_name="강남구"
            )

            aq = result['air_quality']
            print(f"✓ Collected air quality data for {result['station_name']}")
            print(f"  PM2.5: {aq['pm25']} μg/m³ ({aq['pm25_grade']})")
            print(f"  PM10: {aq['pm10']} μg/m³ ({aq['pm10_grade']})")
            print(f"  Measured at: {aq['measured_at']}")

    except CollectorError as e:
        print(f"✗ AirKorea collection failed: {e}")


async def example_khoa_ocean():
    """Example: Collect ocean data (tide from data.go.kr, wave/temp from KHOA)"""
    print("\n=== Ocean Data Collector ===")

    api_key = settings.BEACH_API_KEY or settings.KMA_API_KEY
    try:
        async with KHOAOceanCollector(api_key) as collector:
            # 조석예보(고, 저조) - 공공데이터포털 API
            tide_result = await collector.collect_tide("DT_0018")  # 군산
            print(f"✓ Tide station: {tide_result['station_name']}")
            for fc in tide_result["forecasts"][:4]:
                print(f"  {fc['datetime']} {fc['type']} {fc['height']}cm")

            # Full collection (tide + wave + temp)
            result = await collector.collect(
                region_code="4671025000",  # 강원 강릉시 주문진읍
                ocean_station_id="DT_0001"
            )
            print(f"✓ Collected ocean data for station {result['ocean_station_id']}")

    except CollectorError as e:
        print(f"✗ Ocean collection failed: {e}")


async def main():
    """Run all examples"""
    print("=" * 60)
    print("Data Collector Examples")
    print("=" * 60)

    # Check for API keys
    if not settings.KMA_API_KEY:
        print("\n⚠ Warning: KMA_API_KEY not set. KMA example will fail.")

    if not settings.AIRKOREA_API_KEY:
        print("⚠ Warning: AIRKOREA_API_KEY not set. AirKorea example will fail.")

    if not (settings.BEACH_API_KEY or settings.KMA_API_KEY):
        print("⚠ Warning: BEACH_API_KEY/KMA_API_KEY not set. Ocean example will fail.")

    # Run examples
    await example_kma_forecast()
    await example_open_meteo()
    await example_airkorea()
    await example_khoa_ocean()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
