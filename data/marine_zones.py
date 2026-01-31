"""
Marine Zone Definitions and Mappings

KMA 해상예보구역 (Marine Forecast Zones) definitions and
coastal region to marine zone mapping logic.
"""
from __future__ import annotations

from typing import Dict, Optional

# KMA Marine Forecast Zones (해상예보구역)
MARINE_ZONES = {
    "12A10000": {"name": "서해북부", "name_en": "West Sea North"},
    "12A20000": {"name": "서해중부", "name_en": "West Sea Central"},
    "12A30000": {"name": "서해남부", "name_en": "West Sea South"},
    "12B10000": {"name": "남해서부", "name_en": "South Sea West"},
    "12B20000": {"name": "남해동부", "name_en": "South Sea East"},
    "12C10000": {"name": "동해남부", "name_en": "East Sea South"},
    "12C20000": {"name": "동해중부", "name_en": "East Sea Central"},
    "12C30000": {"name": "동해북부", "name_en": "East Sea North"},
    "12D10000": {"name": "제주도", "name_en": "Jeju Island"},
}

# Sido (시도) to Marine Zone Mapping
# Maps sido names to their corresponding marine zones based on coastal location
SIDO_MARINE_ZONE_MAPPING = {
    # West Sea North (서해북부)
    "인천광역시": "12A10000",
    "경기도": "12A10000",

    # West Sea Central (서해중부)
    "충청남도": "12A20000",

    # West Sea South (서해남부) - 전북/전남 서해안
    # Note: 전남 has both west and south coasts, determined by is_west_coast flag
    "전라북도": "12A30000",
    "전북특별자치도": "12A30000",

    # South Sea West (남해서부) - 전남 남해안
    # Handled by is_west_coast=False for 전라남도/전남특별자치도

    # South Sea East (남해동부) - 경남 해안
    "경상남도": "12B20000",

    # East Sea South (동해남부) - 부산/울산 해안
    "부산광역시": "12C10000",
    "울산광역시": "12C10000",

    # East Sea Central (동해중부) - 경북 해안
    "경상북도": "12C20000",

    # East Sea North (동해북부) - 강원 해안
    "강원도": "12C30000",
    "강원특별자치도": "12C30000",

    # Jeju Island (제주도)
    "제주특별자치도": "12D10000",
}

# Special handling for regions with multiple coast types
# 전라남도/전남특별자치도: West coast → 서해남부, South coast → 남해서부
SPECIAL_COAST_MAPPING = {
    "전라남도": {
        "west_coast": "12A30000",  # 서해남부
        "south_coast": "12B10000",  # 남해서부
    },
    "전남특별자치도": {
        "west_coast": "12A30000",  # 서해남부
        "south_coast": "12B10000",  # 남해서부
    },
}


def get_marine_zone(sido: str, is_coastal: bool, is_west_coast: bool = False, is_east_coast: bool = False) -> str | None:
    """
    Determine the marine zone code for a given region.

    Args:
        sido: 시도 name (e.g., "서울특별시", "강원특별자치도")
        is_coastal: Whether the region is coastal
        is_west_coast: Whether the region is on the west coast
        is_east_coast: Whether the region is on the east coast

    Returns:
        Marine zone code (e.g., "12A10000") or None if not coastal
    """
    if not is_coastal:
        return None

    # Special handling for 전라남도/전남특별자치도
    if sido in SPECIAL_COAST_MAPPING:
        if is_west_coast:
            return SPECIAL_COAST_MAPPING[sido]["west_coast"]
        else:
            # Assume south coast if not explicitly west coast
            return SPECIAL_COAST_MAPPING[sido]["south_coast"]

    # Standard mapping
    return SIDO_MARINE_ZONE_MAPPING.get(sido)


def get_zone_name(zone_code: str, lang: str = "ko") -> str | None:
    """
    Get the name of a marine zone.

    Args:
        zone_code: Marine zone code (e.g., "12A10000")
        lang: Language code ("ko" or "en")

    Returns:
        Zone name or None if not found
    """
    zone = MARINE_ZONES.get(zone_code)
    if not zone:
        return None

    return zone["name"] if lang == "ko" else zone["name_en"]


def list_all_zones() -> dict[str, dict[str, str]]:
    """
    Get all marine zones.

    Returns:
        Dictionary of all marine zones
    """
    return MARINE_ZONES.copy()
