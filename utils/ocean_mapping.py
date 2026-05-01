"""해수욕장-해양관측소 매핑 유틸리티"""
from typing import List, Optional, Tuple
import math

from data.ocean_stations import OCEAN_STATIONS, OceanStation


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    두 지점 간 거리 계산 (Haversine 공식)

    Args:
        lat1, lon1: 첫 번째 지점 좌표
        lat2, lon2: 두 번째 지점 좌표

    Returns:
        거리 (km)
    """
    R = 6371  # 지구 반경 (km)

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = math.sin(delta_lat / 2) ** 2 + \
        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def find_nearest_tide_station(lat: float, lon: float) -> Tuple[Optional[OceanStation], float]:
    """
    해수욕장 좌표에서 가장 가까운 조석 관측소 찾기

    Args:
        lat: 해수욕장 위도
        lon: 해수욕장 경도

    Returns:
        (nearest_station, distance_km) 또는 (None, float('inf'))
    """
    tide_stations = [s for s in OCEAN_STATIONS if s["provides_tide"] == 1]

    if not tide_stations:
        return None, float('inf')

    nearest = None
    min_distance = float('inf')

    for station in tide_stations:
        distance = haversine_distance(lat, lon, station["lat"], station["lon"])
        if distance < min_distance:
            min_distance = distance
            nearest = station

    return nearest, min_distance


def find_nearest_temp_station(lat: float, lon: float) -> Tuple[Optional[OceanStation], float]:
    """
    해수욕장 좌표에서 가장 가까운 수온 관측소 찾기

    Args:
        lat: 해수욕장 위도
        lon: 해수욕장 경도

    Returns:
        (nearest_station, distance_km) 또는 (None, float('inf'))
    """
    temp_stations = [s for s in OCEAN_STATIONS if s["provides_temp"] == 1]

    if not temp_stations:
        return None, float('inf')

    nearest = None
    min_distance = float('inf')

    for station in temp_stations:
        distance = haversine_distance(lat, lon, station["lat"], station["lon"])
        if distance < min_distance:
            min_distance = distance
            nearest = station

    return nearest, min_distance


def find_nearest_wave_station(lat: float, lon: float) -> Tuple[Optional[OceanStation], float]:
    """
    해수욕장 좌표에서 가장 가까운 파고 관측소 찾기

    Args:
        lat: 해수욕장 위도
        lon: 해수욕장 경도

    Returns:
        (nearest_station, distance_km) 또는 (None, float('inf'))
    """
    wave_stations = [s for s in OCEAN_STATIONS if s["provides_wave"] == 1]

    if not wave_stations:
        return None, float('inf')

    nearest = None
    min_distance = float('inf')

    for station in wave_stations:
        distance = haversine_distance(lat, lon, station["lat"], station["lon"])
        if distance < min_distance:
            min_distance = distance
            nearest = station

    return nearest, min_distance
