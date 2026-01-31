# Processors Module

Data processing and transformation layer for Weather Lens.

## Overview

The processors module handles:
1. **Data Merging** - Combines weather data from multiple API sources (KMA, Open-Meteo) using weighted averaging
2. **Cache Writing** - Stores processed data in date-organized JSON files
3. **Region Loading** - Manages Korean administrative region data (~3,500 읍면동)

## Architecture

```
processors/
├── data_merger.py      # Weighted averaging & data structures
├── cache_writer.py     # JSON cache management
├── region_loader.py    # SQLite region database
└── __init__.py         # Public API
```

## Quick Start

### 1. Merge Weather Data

```python
from datetime import datetime
from processors import merge_weather_data, WeatherData

# Prepare source data
kma_data = {
    "temp": -3.2,
    "cloud": 30,
    "rain_prob": 10,
    "humidity": 65,
    "wind_speed": 2.5,
}

openmeteo_data = {
    "temp": -2.8,
    "cloud": 35,
    "rain_prob": 12,
    "humidity": 68,
    "wind_speed": 2.8,
}

airkorea_data = {
    "pm25": 18,
    "pm10": 32,
}

# Merge with 60/40 weighting (KMA/Open-Meteo)
weather = merge_weather_data(
    datetime_obj=datetime(2026, 1, 29, 6, 0),
    kma_data=kma_data,
    openmeteo_data=openmeteo_data,
    airkorea_data=airkorea_data,
)

# Access merged data
print(weather.temp.avg)  # -3.0 (weighted average)
print(weather.temp.deviation_flag)  # False (difference < threshold)
```

### 2. Write to Cache

```python
from processors import write_weather_cache

# Write forecast to JSON cache
cache_path = await write_weather_cache(
    region_code="1168010100",
    region_name="서울특별시 강남구 역삼동",
    coordinates={"lat": 37.5000, "lng": 127.0364},
    forecast=[weather],  # List of WeatherData objects
    ocean_station_id="DT_0001",  # Optional
)

print(f"Cache written to: {cache_path}")
# Output: /data/cache/2026-01-29/서울특별시_강남구_역삼동.json
```

### 3. Load Regions

```python
from processors import RegionLoader, initialize_regions_db

# Initialize database schema
await initialize_regions_db()

# Load regions
loader = RegionLoader()

# Get all regions
all_regions = await loader.get_all_regions()
print(f"Total regions: {len(all_regions)}")  # ~3,500

# Get coastal regions for sunrise/sunset themes
coastal_regions = await loader.get_coastal_regions()

# Get high-elevation regions for 운해 (sea of clouds) theme
high_regions = await loader.get_high_elevation_regions(min_elevation=500)

# Get specific region
region = await loader.get_region("1168010100")
print(region.full_name)  # "서울특별시 강남구 역삼동"
print(region.coordinates)  # {"lat": 37.5, "lng": 127.036}
```

## Data Structures

### WeatherValue

Stores values from both APIs plus computed average:

```python
@dataclass
class WeatherValue:
    kma: Optional[float] = None           # KMA source value
    openmeteo: Optional[float] = None     # Open-Meteo source value
    avg: Optional[float] = None           # Weighted average (60/40)
    deviation_flag: bool = False          # True if |kma - openmeteo| > threshold
```

### WeatherData

Complete weather data for a single datetime:

```python
@dataclass
class WeatherData:
    datetime: datetime
    temp: WeatherValue                    # Temperature (°C)
    cloud: WeatherValue                   # Cloud cover (%)
    rain_prob: WeatherValue               # Rain probability (%)
    rain_amount: WeatherValue             # Rain amount (mm)
    humidity: WeatherValue                # Humidity (%)
    wind_speed: WeatherValue              # Wind speed (m/s)
    pm25: Optional[float] = None          # PM2.5 (µg/m³) - Airkorea only
    pm10: Optional[float] = None          # PM10 (µg/m³) - Airkorea only
    sunrise: Optional[str] = None         # Sunrise time (HH:MM)
    sunset: Optional[str] = None          # Sunset time (HH:MM)
    visibility: Optional[float] = None    # Visibility (km)
```

### Region

Korean administrative region (읍면동):

```python
@dataclass
class Region:
    region_code: str                      # e.g., "1168010100"
    sido: str                             # e.g., "서울특별시"
    sigungu: str                          # e.g., "강남구"
    emd: str                              # e.g., "역삼동"
    lat: float                            # Latitude
    lng: float                            # Longitude
    is_coastal: bool = False              # True if within 30km of coast
    elevation: Optional[int] = None       # Elevation in meters

    @property
    def full_name(self) -> str:
        return f"{self.sido} {self.sigungu} {self.emd}"

    @property
    def coordinates(self) -> dict[str, float]:
        return {"lat": self.lat, "lng": self.lng}
```

## Weighted Averaging Algorithm

The merger uses configurable weighted averaging:

```python
# Default weights (config/settings.py)
KMA_WEIGHT = 0.6              # 60% weight for KMA
OPENMETEO_WEIGHT = 0.4        # 40% weight for Open-Meteo
DEVIATION_THRESHOLD = 5.0     # Flag if difference > 5.0

# Calculation
avg = (kma_value * 0.6) + (openmeteo_value * 0.4)

# Deviation check
if abs(kma_value - openmeteo_value) > 5.0:
    deviation_flag = True
```

**Rationale**: KMA is the official Korean meteorological service and gets higher priority. Open-Meteo provides validation and fill gaps.

## Cache Structure

JSON cache files follow this structure (matching spec.md):

```json
{
  "region_code": "1168010100",
  "region_name": "서울특별시 강남구 역삼동",
  "coordinates": {
    "lat": 37.5000,
    "lng": 127.0364
  },
  "updated_at": "2026-01-29T06:00:00+09:00",
  "forecast": [
    {
      "datetime": "2026-01-29T06:00:00",
      "temp": {
        "kma": -3.2,
        "openmeteo": -2.8,
        "avg": -3.0,
        "deviation_flag": false
      },
      "cloud": {
        "kma": 30,
        "openmeteo": 35,
        "avg": 32,
        "deviation_flag": false
      },
      "rain_prob": {
        "kma": 10,
        "openmeteo": 12,
        "avg": 11,
        "deviation_flag": false
      },
      "pm25": 18,
      "sunrise": "07:35",
      "sunset": "17:52"
    }
  ],
  "ocean_station_id": "DT_0001"
}
```

**File path**: `/data/cache/{date}/{sido}_{sigungu}_{emd}.json`

## Database Schema

SQLite database for region data:

```sql
CREATE TABLE regions (
    region_code TEXT PRIMARY KEY,
    sido TEXT NOT NULL,
    sigungu TEXT NOT NULL,
    emd TEXT NOT NULL,
    lat REAL NOT NULL,
    lng REAL NOT NULL,
    is_coastal BOOLEAN DEFAULT FALSE,
    elevation INTEGER
);

-- Indices for common queries
CREATE INDEX idx_sido ON regions(sido);
CREATE INDEX idx_sigungu ON regions(sigungu);
CREATE INDEX idx_coastal ON regions(is_coastal);
CREATE INDEX idx_elevation ON regions(elevation);
```

## API Reference

### Data Merger

- `merge_weather_data()` - Merge data from multiple APIs
- `merge_weather_value()` - Merge single weather value
- `calculate_weighted_average()` - Core averaging logic
- `weather_data_to_dict()` - Convert to JSON-serializable dict

### Cache Writer

- `write_weather_cache()` - Convenience function to write cache
- `CacheWriter` - Class for advanced cache operations
  - `write_cache()` - Write forecast to cache
  - `read_cache()` - Read forecast from cache
  - `clear_old_caches()` - Remove old cache directories

### Region Loader

- `initialize_regions_db()` - Create database schema
- `load_all_regions()` - Load all ~3,500 regions
- `load_region()` - Load specific region by code
- `RegionLoader` - Class for database operations
  - `get_region()` - Get single region
  - `get_all_regions()` - Get all regions
  - `get_regions_by_sido()` - Filter by sido
  - `get_regions_by_sigungu()` - Filter by sigungu
  - `get_coastal_regions()` - Get coastal regions only
  - `get_high_elevation_regions()` - Get regions above elevation
  - `insert_region()` - Insert single region
  - `insert_regions_bulk()` - Bulk insert (efficient)
  - `count_regions()` - Get total count
  - `get_sidos()` - Get list of all sidos

## Performance Considerations

### Async Operations
All I/O operations are async to prevent blocking:
- File operations use `asyncio.run_in_executor()`
- Database operations use `aiosqlite`

### JSON Serialization
Uses `orjson` for 2-3x faster serialization than stdlib json.

### Bulk Operations
Use `insert_regions_bulk()` for loading region data (much faster than individual inserts).

### Cache Cleanup
```python
writer = CacheWriter()
removed = writer.clear_old_caches(days_to_keep=3)
print(f"Removed {removed} old cache directories")
```

## Integration with Other Modules

### Collectors → Processors
Collectors provide raw API data:
```python
from collectors import KMACollector, OpenMeteoCollector
from processors import merge_weather_data

kma = KMACollector()
om = OpenMeteoCollector()

kma_data = await kma.get_forecast(lat, lng)
om_data = await om.get_forecast(lat, lng)

weather = merge_weather_data(datetime, kma_data, om_data)
```

### Processors → Scorers
Scorers use cached data for theme scoring:
```python
from processors import CacheWriter
from scorers import SunriseScorer

writer = CacheWriter()
cache_data = await writer.read_cache(region_code, region_name)

scorer = SunriseScorer()
score = scorer.calculate(cache_data['forecast'])
```

## Configuration

Key settings in `config/settings.py`:

```python
# Weighted averaging
KMA_WEIGHT = 0.6                      # 60% for KMA
OPENMETEO_WEIGHT = 0.4                # 40% for Open-Meteo
DEVIATION_THRESHOLD = 5.0             # Flag threshold

# Cache settings
CACHE_DIR = BASE_DIR / "data/cache"

# Database settings
SQLITE_DB_PATH = DATA_DIR / "regions.db"

# Forecast settings
FORECAST_DAYS = 3                     # D-day ~ D+2
UPDATE_INTERVAL_HOURS = 12            # Update frequency
```

## Testing

Run import test:
```bash
python test_processors_import.py
```

Expected output:
```
✓ All imports successful
✓ WeatherData: <class 'processors.data_merger.WeatherData'>
✓ Region: <class 'processors.region_loader.Region'>
✓ CacheWriter: <class 'processors.cache_writer.CacheWriter'>

Module structure validated successfully!
```

## Dependencies

- `orjson` - Fast JSON serialization
- `aiosqlite` - Async SQLite operations
- `dataclasses` - Structured data types
- `pathlib` - Modern path handling
- `asyncio` - Async runtime

## Future Enhancements

1. **Cache Versioning** - Invalidate cache on schema changes
2. **Compression** - Gzip cache files for storage efficiency
3. **Batch Processing** - Process multiple regions in parallel
4. **Migration Tool** - SQLite → Postgres migration script
5. **Validation** - Pydantic schemas for API contract validation
