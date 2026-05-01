"""PhotoSpot Korea - Data Models"""
from .weather import WeatherData, ForecastData
from .region import Region, RegionScore
from .feedback import Feedback, ScorePenalty
from .ocean import OceanData, TideData

__all__ = [
    "WeatherData",
    "ForecastData",
    "Region",
    "RegionScore",
    "Feedback",
    "ScorePenalty",
    "OceanData",
    "TideData",
]
