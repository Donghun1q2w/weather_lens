# Data Collectors

Weather and ocean data collection modules for PhotoSpot Korea.

## Overview

This package provides async collectors for various weather and ocean data sources:

1. **KMAForecastCollector** - 기상청 단기예보 API
2. **OpenMeteoCollector** - Open-Meteo Weather API
3. **AirKoreaCollector** - 에어코리아 대기질 API
4. **KHOAOceanCollector** - 바다누리 해양 데이터 API

## Architecture

All collectors inherit from `BaseCollector` which provides:
- Async context manager support
- HTTP request handling with error management
- Standardized interface

## Usage

### Basic Pattern

```python
from collectors import KMAForecastCollector
from config.settings import KMA_API_KEY

async with KMAForecastCollector(KMA_API_KEY) as collector:
    data = await collector.collect(
        region_code="1168010100",
        nx=60,
        ny=127
    )
```

### KMA Forecast Collector

Collects short-term weather forecast from 기상청.

```python
from collectors import KMAForecastCollector

async with KMAForecastCollector(api_key) as collector:
    result = await collector.collect(
        region_code="1168010100",  # 서울특별시 강남구 역삼동
        nx=60,                      # Grid X coordinate
        ny=127                      # Grid Y coordinate
    )
```

**Returns:**
```json
{
  "source": "kma",
  "region_code": "1168010100",
  "collected_at": "2026-01-30T10:00:00",
  "base_date": "20260130",
  "base_time": "0800",
  "forecast": [
    {
      "datetime": "2026-01-30T11:00:00",
      "temp": -3.0,
      "humidity": 65,
      "wind_speed": 2.5,
      "rain_prob": 10,
      "precipitation": 0.0,
      "sky": 1,
      "cloud_cover": 20
    }
  ]
}
```

### Open-Meteo Collector

Collects weather forecast from Open-Meteo (no API key required).

```python
from collectors import OpenMeteoCollector

async with OpenMeteoCollector() as collector:
    result = await collector.collect(
        region_code="1168010100",
        lat=37.5000,
        lng=127.0364
    )
```

**Returns:**
```json
{
  "source": "open_meteo",
  "region_code": "1168010100",
  "collected_at": "2026-01-30T10:00:00",
  "coordinates": {
    "lat": 37.5000,
    "lng": 127.0364
  },
  "forecast": [
    {
      "datetime": "2026-01-30T11:00:00",
      "temp": -2.8,
      "humidity": 63,
      "rain_prob": 12,
      "precipitation": 0.0,
      "cloud_cover": 35,
      "wind_speed": 2.3
    }
  ]
}
```

### AirKorea Collector

Collects air quality data (PM2.5, PM10).

```python
from collectors import AirKoreaCollector

async with AirKoreaCollector(api_key) as collector:
    result = await collector.collect(
        region_code="1168010100",
        station_name="강남구"  # or use sido_name="서울"
    )
```

**Returns:**
```json
{
  "source": "airkorea",
  "region_code": "1168010100",
  "collected_at": "2026-01-30T10:00:00",
  "station_name": "강남구",
  "air_quality": {
    "pm25": 18.0,
    "pm25_grade": "좋음",
    "pm10": 32.0,
    "pm10_grade": "보통",
    "measured_at": "2026-01-30 09:00"
  }
}
```

### KHOA Ocean Collector

Collects ocean data (tide, wave, water temperature).

```python
from collectors import KHOAOceanCollector

async with KHOAOceanCollector(api_key) as collector:
    result = await collector.collect(
        region_code="4671025000",
        ocean_station_id="DT_0001",
        collect_tide=True,
        collect_wave=True,
        collect_temp=True
    )
```

**Returns:**
```json
{
  "source": "khoa",
  "region_code": "4671025000",
  "ocean_station_id": "DT_0001",
  "collected_at": "2026-01-30T10:00:00",
  "data": {
    "tide": {
      "station_name": "주문진항",
      "forecasts": [
        {
          "datetime": "2026-01-30T06:23",
          "type": "고조",
          "height": 52.3
        }
      ]
    },
    "wave": {
      "station_name": "주문진항",
      "observed_at": "2026-01-30T09:00",
      "significant_wave_height": 0.8,
      "wave_period": 6.5,
      "max_wave_height": 1.2
    },
    "water_temp": {
      "station_name": "주문진항",
      "observed_at": "2026-01-30T09:00",
      "surface_temp": 8.5,
      "depth_1m_temp": 8.3,
      "depth_5m_temp": 8.0
    }
  }
}
```

## Error Handling

All collectors raise `CollectorError` on failure:

```python
from collectors import KMAForecastCollector, CollectorError

try:
    async with KMAForecastCollector(api_key) as collector:
        data = await collector.collect(...)
except CollectorError as e:
    print(f"Collection failed: {e}")
```

## Configuration

API keys are loaded from environment variables via `config/settings.py`:

```python
KMA_API_KEY = os.getenv("KMA_API_KEY", "")
AIRKOREA_API_KEY = os.getenv("AIRKOREA_API_KEY", "")
KHOA_API_KEY = os.getenv("KHOA_API_KEY", "")
```

## Data Update Frequency

- **KMA Forecast**: 12 hours (발표: 02:10, 05:10, 08:10, 11:10, 14:10, 17:10, 20:10, 23:10)
- **Open-Meteo**: Real-time (hourly updates)
- **AirKorea**: Real-time (hourly updates)
- **KHOA Ocean**: 12 hours

## Dependencies

- `httpx` - Async HTTP client
- `aiohttp` - Alternative async HTTP support
- `python-dateutil` - Date parsing utilities

## Next Steps

1. Implement coordinate conversion (읍면동 코드 → Grid coordinates for KMA)
2. Populate `ocean_mapping.db` with actual station mappings
3. Create data merger module to combine KMA + Open-Meteo data
4. Implement caching layer for JSON files
