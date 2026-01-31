"""
Ocean Observation Stations Data

KHOA (Korea Hydrographic and Oceanographic Agency) observation station definitions.
These stations provide tide, wave, and water temperature data for coastal regions.

Station Types:
- tide: Tide observation stations (DT_*)
- wave: Wave observation stations (TW_*)
- buoy: Ocean buoy stations (IE_*)
"""
from __future__ import annotations

from typing import Dict, List, TypedDict


class OceanStation(TypedDict):
    """Ocean observation station definition."""
    station_id: str
    station_name: str
    station_type: str
    lat: float
    lon: float
    provides_tide: int
    provides_wave: int
    provides_temp: int
    marine_zone_code: str | None


# Ocean observation stations data
# Based on confirmed KHOA API stations and major coastal locations
OCEAN_STATIONS: List[OceanStation] = [
    # ===== 제주도 (Jeju Island) - 12D10000 =====
    {
        "station_id": "DT_0063",
        "station_name": "제주",
        "station_type": "tide",
        "lat": 33.5271,
        "lon": 126.5433,
        "provides_tide": 1,
        "provides_wave": 0,
        "provides_temp": 1,
        "marine_zone_code": "12D10000",
    },
    {
        "station_id": "DT_0028",
        "station_name": "성산포",
        "station_type": "tide",
        "lat": 33.4747,
        "lon": 126.9272,
        "provides_tide": 1,
        "provides_wave": 0,
        "provides_temp": 1,
        "marine_zone_code": "12D10000",
    },
    {
        "station_id": "DT_0029",
        "station_name": "서귀포",
        "station_type": "tide",
        "lat": 33.2403,
        "lon": 126.5619,
        "provides_tide": 1,
        "provides_wave": 0,
        "provides_temp": 1,
        "marine_zone_code": "12D10000",
    },
    {
        "station_id": "DT_0062",
        "station_name": "모슬포",
        "station_type": "tide",
        "lat": 33.2142,
        "lon": 126.2503,
        "provides_tide": 1,
        "provides_wave": 0,
        "provides_temp": 1,
        "marine_zone_code": "12D10000",
    },
    {
        "station_id": "DT_0060",
        "station_name": "추자도",
        "station_type": "tide",
        "lat": 33.9614,
        "lon": 126.3000,
        "provides_tide": 1,
        "provides_wave": 0,
        "provides_temp": 1,
        "marine_zone_code": "12D10000",
    },

    # ===== 서해북부 (West Sea North) - 12A10000 =====
    {
        "station_id": "DT_0001",
        "station_name": "인천",
        "station_type": "tide",
        "lat": 37.4517,
        "lon": 126.5917,
        "provides_tide": 1,
        "provides_wave": 0,
        "provides_temp": 1,
        "marine_zone_code": "12A10000",
    },
    {
        "station_id": "DT_0088",
        "station_name": "평택",
        "station_type": "tide",
        "lat": 36.9667,
        "lon": 126.8217,
        "provides_tide": 1,
        "provides_wave": 0,
        "provides_temp": 1,
        "marine_zone_code": "12A10000",
    },
    {
        "station_id": "DT_0006",
        "station_name": "안흥",
        "station_type": "tide",
        "lat": 36.6742,
        "lon": 126.1289,
        "provides_tide": 1,
        "provides_wave": 0,
        "provides_temp": 1,
        "marine_zone_code": "12A10000",
    },

    # ===== 서해중부 (West Sea Central) - 12A20000 =====
    {
        "station_id": "DT_0081",
        "station_name": "대천",
        "station_type": "tide",
        "lat": 36.3500,
        "lon": 126.4833,
        "provides_tide": 1,
        "provides_wave": 0,
        "provides_temp": 1,
        "marine_zone_code": "12A20000",
    },
    {
        "station_id": "DT_0007",
        "station_name": "보령",
        "station_type": "tide",
        "lat": 36.4067,
        "lon": 126.4850,
        "provides_tide": 1,
        "provides_wave": 0,
        "provides_temp": 1,
        "marine_zone_code": "12A20000",
    },

    # ===== 서해남부 (West Sea South) - 12A30000 =====
    {
        "station_id": "DT_0023",
        "station_name": "군산",
        "station_type": "tide",
        "lat": 35.9753,
        "lon": 126.5633,
        "provides_tide": 1,
        "provides_wave": 0,
        "provides_temp": 1,
        "marine_zone_code": "12A30000",
    },
    {
        "station_id": "DT_0057",
        "station_name": "위도",
        "station_type": "tide",
        "lat": 35.6181,
        "lon": 126.3006,
        "provides_tide": 1,
        "provides_wave": 0,
        "provides_temp": 1,
        "marine_zone_code": "12A30000",
    },
    {
        "station_id": "DT_0026",
        "station_name": "목포",
        "station_type": "tide",
        "lat": 34.7797,
        "lon": 126.3750,
        "provides_tide": 1,
        "provides_wave": 0,
        "provides_temp": 1,
        "marine_zone_code": "12A30000",
    },
    {
        "station_id": "DT_0044",
        "station_name": "흑산도",
        "station_type": "tide",
        "lat": 34.6842,
        "lon": 125.4356,
        "provides_tide": 1,
        "provides_wave": 0,
        "provides_temp": 1,
        "marine_zone_code": "12A30000",
    },

    # ===== 남해서부 (South Sea West) - 12B10000 =====
    {
        "station_id": "DT_0012",
        "station_name": "완도",
        "station_type": "tide",
        "lat": 34.3153,
        "lon": 126.7594,
        "provides_tide": 1,
        "provides_wave": 0,
        "provides_temp": 1,
        "marine_zone_code": "12B10000",
    },
    {
        "station_id": "DT_0042",
        "station_name": "여수",
        "station_type": "tide",
        "lat": 34.7478,
        "lon": 127.7650,
        "provides_tide": 1,
        "provides_wave": 0,
        "provides_temp": 1,
        "marine_zone_code": "12B10000",
    },
    {
        "station_id": "DT_0025",
        "station_name": "거문도",
        "station_type": "tide",
        "lat": 34.0281,
        "lon": 127.3058,
        "provides_tide": 1,
        "provides_wave": 0,
        "provides_temp": 1,
        "marine_zone_code": "12B10000",
    },

    # ===== 남해동부 (South Sea East) - 12B20000 =====
    {
        "station_id": "DT_0013",
        "station_name": "통영",
        "station_type": "tide",
        "lat": 34.8267,
        "lon": 128.4342,
        "provides_tide": 1,
        "provides_wave": 0,
        "provides_temp": 1,
        "marine_zone_code": "12B20000",
    },
    {
        "station_id": "DT_0014",
        "station_name": "거제도",
        "station_type": "tide",
        "lat": 34.8008,
        "lon": 128.7008,
        "provides_tide": 1,
        "provides_wave": 0,
        "provides_temp": 1,
        "marine_zone_code": "12B20000",
    },
    {
        "station_id": "DT_0091",
        "station_name": "가덕도",
        "station_type": "tide",
        "lat": 35.0242,
        "lon": 128.8153,
        "provides_tide": 1,
        "provides_wave": 0,
        "provides_temp": 1,
        "marine_zone_code": "12B20000",
    },

    # ===== 동해남부 (East Sea South) - 12C10000 =====
    {
        "station_id": "DT_0016",
        "station_name": "부산",
        "station_type": "tide",
        "lat": 35.0961,
        "lon": 129.0350,
        "provides_tide": 1,
        "provides_wave": 0,
        "provides_temp": 1,
        "marine_zone_code": "12C10000",
    },
    {
        "station_id": "DT_0017",
        "station_name": "울산",
        "station_type": "tide",
        "lat": 35.5011,
        "lon": 129.3850,
        "provides_tide": 1,
        "provides_wave": 0,
        "provides_temp": 1,
        "marine_zone_code": "12C10000",
    },

    # ===== 동해중부 (East Sea Central) - 12C20000 =====
    {
        "station_id": "DT_0018",
        "station_name": "포항",
        "station_type": "tide",
        "lat": 36.0489,
        "lon": 129.3811,
        "provides_tide": 1,
        "provides_wave": 0,
        "provides_temp": 1,
        "marine_zone_code": "12C20000",
    },
    {
        "station_id": "DT_0019",
        "station_name": "후포",
        "station_type": "tide",
        "lat": 36.6778,
        "lon": 129.4536,
        "provides_tide": 1,
        "provides_wave": 0,
        "provides_temp": 1,
        "marine_zone_code": "12C20000",
    },
    {
        "station_id": "DT_0020",
        "station_name": "울릉도",
        "station_type": "tide",
        "lat": 37.4914,
        "lon": 130.9128,
        "provides_tide": 1,
        "provides_wave": 0,
        "provides_temp": 1,
        "marine_zone_code": "12C20000",
    },

    # ===== 동해북부 (East Sea North) - 12C30000 =====
    {
        "station_id": "DT_0085",
        "station_name": "묵호",
        "station_type": "tide",
        "lat": 37.5508,
        "lon": 129.1161,
        "provides_tide": 1,
        "provides_wave": 0,
        "provides_temp": 1,
        "marine_zone_code": "12C30000",
    },
    {
        "station_id": "DT_0032",
        "station_name": "속초",
        "station_type": "tide",
        "lat": 38.2072,
        "lon": 128.5933,
        "provides_tide": 1,
        "provides_wave": 0,
        "provides_temp": 1,
        "marine_zone_code": "12C30000",
    },

    # ===== Wave Observation Stations (TW_*) =====
    # Major wave observation stations covering key coastal areas
    {
        "station_id": "TW_0069",
        "station_name": "제주 외해",
        "station_type": "wave",
        "lat": 33.2333,
        "lon": 126.1500,
        "provides_tide": 0,
        "provides_wave": 1,
        "provides_temp": 1,
        "marine_zone_code": "12D10000",
    },
    {
        "station_id": "TW_0062",
        "station_name": "거문도 외해",
        "station_type": "wave",
        "lat": 34.0000,
        "lon": 127.5000,
        "provides_tide": 0,
        "provides_wave": 1,
        "provides_temp": 1,
        "marine_zone_code": "12B10000",
    },
    {
        "station_id": "TW_0101",
        "station_name": "부산 외해",
        "station_type": "wave",
        "lat": 35.0000,
        "lon": 129.2000,
        "provides_tide": 0,
        "provides_wave": 1,
        "provides_temp": 1,
        "marine_zone_code": "12C10000",
    },

    # ===== Buoy Stations (IE_*) =====
    # Ocean buoy stations providing comprehensive data
    {
        "station_id": "IE_0062",
        "station_name": "제주 해양기상부이",
        "station_type": "buoy",
        "lat": 33.3000,
        "lon": 126.0333,
        "provides_tide": 0,
        "provides_wave": 1,
        "provides_temp": 1,
        "marine_zone_code": "12D10000",
    },
    {
        "station_id": "IE_0063",
        "station_name": "거문도 해양기상부이",
        "station_type": "buoy",
        "lat": 34.0000,
        "lon": 127.5000,
        "provides_tide": 0,
        "provides_wave": 1,
        "provides_temp": 1,
        "marine_zone_code": "12B10000",
    },
]


def get_stations_by_zone(zone_code: str) -> List[OceanStation]:
    """
    Get all ocean stations in a specific marine zone.

    Args:
        zone_code: Marine zone code (e.g., "12D10000")

    Returns:
        List of ocean stations in the zone
    """
    return [s for s in OCEAN_STATIONS if s["marine_zone_code"] == zone_code]


def get_station_by_id(station_id: str) -> OceanStation | None:
    """
    Get ocean station by ID.

    Args:
        station_id: Station ID (e.g., "DT_0063")

    Returns:
        Ocean station data or None if not found
    """
    for station in OCEAN_STATIONS:
        if station["station_id"] == station_id:
            return station
    return None


def get_stations_by_type(station_type: str) -> List[OceanStation]:
    """
    Get all ocean stations of a specific type.

    Args:
        station_type: Station type ('tide', 'wave', 'buoy')

    Returns:
        List of ocean stations of the specified type
    """
    return [s for s in OCEAN_STATIONS if s["station_type"] == station_type]


def get_tide_stations() -> List[OceanStation]:
    """Get all tide observation stations."""
    return [s for s in OCEAN_STATIONS if s["provides_tide"] == 1]


def get_wave_stations() -> List[OceanStation]:
    """Get all wave observation stations."""
    return [s for s in OCEAN_STATIONS if s["provides_wave"] == 1]
