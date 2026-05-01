"""Base Scorer for PhotoSpot Korea - Abstract Base Class for Theme Scoring"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional


# Field mapping: canonical name -> list of possible keys in data
# Handles both flat keys (from Open-Meteo) and nested keys (from KMA merged format)
FIELD_MAP = {
    "cloud_cover": ["cloud_cover", "cloud.avg"],
    "rain_probability": ["rain_probability", "rain_prob.avg"],
    "temperature": ["temperature", "temp.avg"],
    "wind_speed": ["wind_speed", "wind_speed.avg"],
    "humidity": ["humidity", "humidity.avg"],
    "visibility": ["visibility"],  # Always in meters from Open-Meteo, convert to km
}


class BaseScorer(ABC):
    """Abstract base class for theme-specific scorers"""

    theme_id: int
    theme_name: str

    # Each scorer declares its relevant time windows (hours in KST)
    relevant_hours: list = []  # e.g., [6, 9] for sunrise
    time_selection: str = "closest"  # "closest", "range", "worst_case"

    def __init__(self, theme_id: int, theme_name: str):
        """Initialize base scorer with theme information

        Args:
            theme_id: Unique identifier for the theme (1-16)
            theme_name: Display name of the theme
        """
        self.theme_id = theme_id
        self.theme_name = theme_name

    @abstractmethod
    async def calculate_score(
        self,
        weather_data: dict,
        ocean_data: Optional[dict] = None
    ) -> float:
        """Legacy per-timeslot scoring (kept for backward compat with api routes)"""
        pass

    @abstractmethod
    async def calculate_daily_score(
        self,
        day_weather: list,
        date: str,
        location_meta: dict,
        marine_data: Optional[dict] = None,
        astronomy: Optional[dict] = None,
    ) -> dict:
        """Calculate daily score for this theme

        Args:
            day_weather: All 8 timeslots for one day (list of dicts with datetime, cloud_cover, etc.)
            date: Date string "YYYY-MM-DD"
            location_meta: {lat, lon, is_east_coast, is_west_coast, is_coastal, elevation}
            marine_data: {wave_height, sea_temperature, tide_info, sun_info, moon_info} or None
            astronomy: Pre-computed from astronomy.py for this date+location or None

        Returns:
            dict: {score: float, factors: dict, time_used: str}
        """
        pass

    # =========================================================================
    # Time-selection helpers
    # =========================================================================

    def _find_closest_timeslot(self, day_weather: list, target_hour: int,
                                target_minute: int = 0) -> Optional[dict]:
        """Find the timeslot closest to target_hour:target_minute"""
        if not day_weather:
            return None

        target_minutes = target_hour * 60 + target_minute
        best = None
        best_diff = float('inf')

        for slot in day_weather:
            dt_str = slot.get("datetime", "")
            try:
                dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                slot_minutes = dt.hour * 60 + dt.minute
                diff = abs(slot_minutes - target_minutes)
                # Handle wrap-around midnight
                diff = min(diff, 1440 - diff)
                if diff < best_diff:
                    best_diff = diff
                    best = slot
            except (ValueError, AttributeError):
                continue

        return best

    def _get_timeslots_in_range(self, day_weather: list,
                                 start_hour: int, end_hour: int) -> list:
        """Get timeslots within [start_hour, end_hour] range.
        Handles overnight ranges where end_hour < start_hour (e.g., 21-03).
        """
        if not day_weather:
            return []

        result = []
        for slot in day_weather:
            dt_str = slot.get("datetime", "")
            try:
                dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                h = dt.hour
                if start_hour <= end_hour:
                    if start_hour <= h <= end_hour:
                        result.append(slot)
                else:
                    # Overnight range (e.g., 21-03)
                    if h >= start_hour or h <= end_hour:
                        result.append(slot)
            except (ValueError, AttributeError):
                continue

        return result

    def _worst_case_field(self, timeslots: list, field: str,
                           mode: str = "max") -> Optional[float]:
        """Get worst-case value for a field across timeslots.
        mode="max" for fields where higher is worse (cloud cover).
        mode="min" for fields where lower is worse (visibility).
        """
        if not timeslots:
            return None

        values = []
        for slot in timeslots:
            val = self._get_weather_value(slot, field)
            if val is not None:
                values.append(val)

        if not values:
            return None

        return max(values) if mode == "max" else min(values)

    def _avg_field(self, timeslots: list, field: str) -> Optional[float]:
        """Get average value for a field across timeslots."""
        if not timeslots:
            return None

        values = []
        for slot in timeslots:
            val = self._get_weather_value(slot, field)
            if val is not None:
                values.append(val)

        if not values:
            return None

        return sum(values) / len(values)

    def _get_weather_value(self, data: dict, field: str,
                            default=None) -> Optional[float]:
        """Get weather value, handling BOTH flat and nested key formats.
        Also handles unit conversion (visibility m -> km).
        """
        if not data:
            return default

        # Check canonical field map first
        candidates = FIELD_MAP.get(field, [field])

        for key in candidates:
            val = self._safe_get(data, key)
            if val is not None:
                # Visibility: convert meters to km if value > 1000
                # (Open-Meteo gives meters, old format assumed km)
                if field == "visibility" and val > 1000:
                    val = val / 1000.0
                try:
                    return float(val)
                except (ValueError, TypeError):
                    continue

        return default

    # =========================================================================
    # Score calculation helpers (unchanged)
    # =========================================================================

    def _normalize_score(self, value: float, min_val: float, max_val: float,
                        reverse: bool = False) -> float:
        """Normalize a value to 0-100 scale"""
        if min_val == max_val:
            return 100.0 if value == min_val else (0.0 if not reverse else 100.0)
        if value < min_val:
            return 0.0 if not reverse else 100.0
        if value > max_val:
            return 100.0 if not reverse else 0.0

        normalized = (value - min_val) / (max_val - min_val)
        if reverse:
            normalized = 1 - normalized

        return normalized * 100.0

    def _calculate_range_score(self, value: float, min_val: float, max_val: float) -> float:
        """Calculate score for values within an optimal range"""
        if min_val <= value <= max_val:
            range_center = (min_val + max_val) / 2
            range_width = (max_val - min_val) / 2

            if range_width == 0:
                return 100.0

            distance_from_center = abs(value - range_center)
            score = 100.0 - (distance_from_center / range_width) * 20.0
            return max(80.0, score)
        else:
            if value < min_val:
                deviation = min_val - value
                penalty = min(deviation * 10, 80)
            else:
                deviation = value - max_val
                penalty = min(deviation * 10, 80)

            return max(0.0, 100.0 - penalty)

    def _safe_get(self, data: dict, key: str, default=None):
        """Safely get value from nested dictionary"""
        if not data:
            return default

        # Handle nested keys like 'temp.avg'
        if '.' in key:
            keys = key.split('.')
            value = data
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k, default)
                else:
                    return default
            return value

        return data.get(key, default)
