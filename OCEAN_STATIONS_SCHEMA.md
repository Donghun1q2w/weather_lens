# Ocean Stations Database Schema

## Overview

This document describes the database schema for KHOA (Korea Hydrographic and Oceanographic Agency) ocean observation stations and their integration with the regions system.

## Schema Design

### Ocean Stations Table

```sql
CREATE TABLE ocean_stations (
    station_id TEXT PRIMARY KEY,        -- Station ID (e.g., DT_0001, TW_0069, IE_0062)
    station_name TEXT NOT NULL,         -- Station name in Korean
    station_type TEXT NOT NULL,         -- Station type: 'tide', 'wave', 'buoy'
    lat REAL NOT NULL,                  -- Latitude
    lon REAL NOT NULL,                  -- Longitude
    provides_tide INTEGER DEFAULT 0,    -- Provides tide data (0 or 1)
    provides_wave INTEGER DEFAULT 0,    -- Provides wave data (0 or 1)
    provides_temp INTEGER DEFAULT 0,    -- Provides water temperature data (0 or 1)
    region_code TEXT,                   -- Linked region code (읍면동)
    marine_zone_code TEXT,              -- Linked marine zone code
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (marine_zone_code) REFERENCES marine_zones(zone_code)
);
```

### Station Types

1. **Tide Stations (`tide`)**: DT_* prefix
   - Provide tidal height data
   - Most common type (30+ stations nationwide)
   - Examples: DT_0063 (제주), DT_0001 (인천), DT_0028 (성산포)

2. **Wave Stations (`wave`)**: TW_* prefix
   - Provide wave height and period data
   - Located in offshore areas
   - Examples: TW_0069 (제주 외해), TW_0062 (거문도 외해)

3. **Buoy Stations (`buoy`)**: IE_* prefix
   - Comprehensive ocean meteorological data
   - Ocean weather buoys
   - Examples: IE_0062 (제주 해양기상부이)

## Integration with Regions

### Existing Schema

The `regions` table already has an `ocean_station_id` field:

```sql
CREATE TABLE regions (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    ...
    ocean_station_id TEXT,  -- Links to ocean_stations.station_id
    ...
);
```

### Mapping Strategy

Coastal regions (`is_coastal = 1`) are automatically mapped to the nearest ocean station:

1. **Same Marine Zone Preference**: Stations in the same marine zone are preferred (50% distance bonus)
2. **Maximum Distance**: Default 50km radius
3. **Haversine Distance**: Great circle distance calculation for accuracy

## Initial Station Data

### Coverage by Marine Zone

| Marine Zone | Zone Name | Stations |
|------------|-----------|----------|
| 12A10000 | 서해북부 (West Sea North) | 3 |
| 12A20000 | 서해중부 (West Sea Central) | 2 |
| 12A30000 | 서해남부 (West Sea South) | 4 |
| 12B10000 | 남해서부 (South Sea West) | 3 |
| 12B20000 | 남해동부 (South Sea East) | 3 |
| 12C10000 | 동해남부 (East Sea South) | 2 |
| 12C20000 | 동해중부 (East Sea Central) | 3 |
| 12C30000 | 동해북부 (East Sea North) | 2 |
| 12D10000 | 제주도 (Jeju Island) | 7 |

**Total: 29 tide stations + 3 wave stations + 2 buoy stations = 34 stations**

### Major Stations by Region

#### Jeju Island (제주도)
- DT_0063: 제주 (Jeju Port)
- DT_0028: 성산포 (Seongsan)
- DT_0029: 서귀포 (Seogwipo)
- DT_0062: 모슬포 (Moseulpo)
- DT_0060: 추자도 (Chuja Island)
- TW_0069: 제주 외해 (wave)
- IE_0062: 제주 해양기상부이 (buoy)

#### West Sea (서해)
- DT_0001: 인천 (Incheon)
- DT_0088: 평택 (Pyeongtaek)
- DT_0081: 대천 (Daecheon Beach)
- DT_0023: 군산 (Gunsan)
- DT_0026: 목포 (Mokpo)
- DT_0044: 흑산도 (Heuksan Island)

#### South Sea (남해)
- DT_0042: 여수 (Yeosu)
- DT_0025: 거문도 (Geomundo)
- DT_0013: 통영 (Tongyeong)
- DT_0014: 거제도 (Geoje Island)

#### East Sea (동해)
- DT_0016: 부산 (Busan)
- DT_0017: 울산 (Ulsan)
- DT_0018: 포항 (Pohang)
- DT_0020: 울릉도 (Ulleungdo)
- DT_0032: 속초 (Sokcho)

## Setup Instructions

### 1. Create Table and Populate Data

```bash
python3 scripts/setup_ocean_stations.py
```

This script will:
1. Create the `ocean_stations` table
2. Populate it with 34 initial stations
3. Optionally update regions with nearest station IDs

### 2. Verify Installation

```python
import sqlite3
conn = sqlite3.connect('data/regions.db')
cursor = conn.cursor()

# Count stations
cursor.execute("SELECT COUNT(*) FROM ocean_stations")
print(f"Total stations: {cursor.fetchone()[0]}")

# List stations by type
cursor.execute("""
    SELECT station_type, COUNT(*)
    FROM ocean_stations
    GROUP BY station_type
""")
for station_type, count in cursor.fetchall():
    print(f"{station_type}: {count}")
```

### 3. Query Examples

**Find nearest station for a region:**
```sql
SELECT os.station_id, os.station_name
FROM regions r
JOIN ocean_stations os ON r.ocean_station_id = os.station_id
WHERE r.code = '5011025021';  -- 제주시 건입동
```

**Get all tide stations in Jeju:**
```sql
SELECT station_id, station_name
FROM ocean_stations
WHERE marine_zone_code = '12D10000'
  AND provides_tide = 1;
```

**Find coastal regions with their ocean stations:**
```sql
SELECT r.name, os.station_name, os.station_type
FROM regions r
JOIN ocean_stations os ON r.ocean_station_id = os.station_id
WHERE r.is_coastal = 1
ORDER BY r.sido, r.sigungu, r.emd;
```

## Python API

### Import Module

```python
from data.ocean_stations import (
    OCEAN_STATIONS,
    get_station_by_id,
    get_stations_by_zone,
    get_stations_by_type,
    get_tide_stations,
    get_wave_stations
)
```

### Usage Examples

```python
# Get specific station
station = get_station_by_id("DT_0063")
print(station["station_name"])  # "제주"

# Get all Jeju stations
jeju_stations = get_stations_by_zone("12D10000")
print(len(jeju_stations))  # 7

# Get tide stations only
tide_stations = get_tide_stations()
print(len(tide_stations))  # 29

# Get wave stations
wave_stations = get_wave_stations()
print(len(wave_stations))  # 5 (3 TW_* + 2 IE_*)
```

## Data Sources

Station data is compiled from:
- KHOA (Korea Hydrographic and Oceanographic Agency) official station list
- KMA (Korea Meteorological Administration) marine observation network
- Field-verified coordinates for accuracy

## Future Enhancements

1. **Station Metadata**: Add operational status, data update frequency
2. **Historical Data**: Store recent observations for caching
3. **Multi-Station Support**: Allow regions to reference multiple stations
4. **Distance Caching**: Pre-calculate distances for faster lookups
5. **API Integration**: Direct KHOA API integration for real-time data

## Files

- `/data/init_ocean_stations.sql`: Table schema definition
- `/data/ocean_stations.py`: Station data and Python API
- `/scripts/setup_ocean_stations.py`: Setup and initialization script
- `/OCEAN_STATIONS_SCHEMA.md`: This documentation
