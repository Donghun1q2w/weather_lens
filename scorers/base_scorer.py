"""Base Scorer for PhotoSpot Korea - Abstract Base Class for Theme Scoring"""
from abc import ABC, abstractmethod
from typing import Optional


class BaseScorer(ABC):
    """Abstract base class for theme-specific scorers"""

    theme_id: int
    theme_name: str

    def __init__(self, theme_id: int, theme_name: str):
        """Initialize base scorer with theme information

        Args:
            theme_id: Unique identifier for the theme (1-8)
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
        """Calculate score for this theme based on weather and ocean data

        Args:
            weather_data: Dictionary containing weather forecast data
                - datetime: ISO format timestamp
                - temp: Temperature data with kma/openmeteo/avg
                - cloud: Cloud cover data (0-100%)
                - rain_prob: Precipitation probability (0-100%)
                - wind_speed: Wind speed (m/s)
                - pm25: PM2.5 concentration
                - humidity: Relative humidity (0-100%)
                - visibility: Visibility (km)
                - sunrise: Sunrise time (HH:MM)
                - sunset: Sunset time (HH:MM)
            ocean_data: Optional dictionary containing ocean data
                - sea_temp: Sea surface temperature (Celsius)
                - wave_height: Significant wave height (m)
                - tide_time: High/low tide times
                - storm_warning: Boolean flag for storm warnings

        Returns:
            float: Score between 0 and 100
        """
        pass

    def _normalize_score(self, value: float, min_val: float, max_val: float,
                        reverse: bool = False) -> float:
        """Normalize a value to 0-100 scale

        Args:
            value: The value to normalize
            min_val: Minimum expected value
            max_val: Maximum expected value
            reverse: If True, higher input values result in lower scores

        Returns:
            float: Normalized score (0-100)
        """
        if value < min_val:
            return 0.0 if not reverse else 100.0
        if value > max_val:
            return 100.0 if not reverse else 0.0

        normalized = (value - min_val) / (max_val - min_val)
        if reverse:
            normalized = 1 - normalized

        return normalized * 100.0

    def _calculate_range_score(self, value: float, min_val: float, max_val: float) -> float:
        """Calculate score for values within an optimal range

        Values within the range get higher scores, outside get lower.

        Args:
            value: The value to score
            min_val: Minimum optimal value
            max_val: Maximum optimal value

        Returns:
            float: Score (0-100)
        """
        if min_val <= value <= max_val:
            # Value is in optimal range
            range_center = (min_val + max_val) / 2
            range_width = (max_val - min_val) / 2

            if range_width == 0:
                return 100.0

            # Score decreases as distance from center increases
            distance_from_center = abs(value - range_center)
            score = 100.0 - (distance_from_center / range_width) * 20.0
            return max(80.0, score)
        else:
            # Value is outside optimal range
            if value < min_val:
                deviation = min_val - value
                penalty = min(deviation * 10, 80)
            else:
                deviation = value - max_val
                penalty = min(deviation * 10, 80)

            return max(0.0, 100.0 - penalty)

    def _safe_get(self, data: dict, key: str, default=None):
        """Safely get value from nested dictionary

        Args:
            data: Dictionary to extract from
            key: Key to look for
            default: Default value if key not found

        Returns:
            Value from dictionary or default
        """
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
