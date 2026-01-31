"""Data Merger - Merges weather data from multiple APIs with weighted averaging"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from config.settings import DEVIATION_THRESHOLD, KMA_WEIGHT, OPENMETEO_WEIGHT


@dataclass
class WeatherValue:
    """Weather value with source data and averaged result"""
    kma: Optional[float] = None
    openmeteo: Optional[float] = None
    avg: Optional[float] = None
    deviation_flag: bool = False


@dataclass
class WeatherData:
    """Complete weather data for a specific datetime"""
    datetime: datetime
    temp: WeatherValue = field(default_factory=WeatherValue)
    cloud: WeatherValue = field(default_factory=WeatherValue)
    rain_prob: WeatherValue = field(default_factory=WeatherValue)
    rain_amount: WeatherValue = field(default_factory=WeatherValue)
    humidity: WeatherValue = field(default_factory=WeatherValue)
    wind_speed: WeatherValue = field(default_factory=WeatherValue)
    pm25: Optional[float] = None  # Single source (Airkorea only)
    pm10: Optional[float] = None  # Single source (Airkorea only)
    sunrise: Optional[str] = None
    sunset: Optional[str] = None
    visibility: Optional[float] = None


def calculate_weighted_average(
    kma_value: Optional[float],
    openmeteo_value: Optional[float],
    kma_weight: float = KMA_WEIGHT,
    openmeteo_weight: float = OPENMETEO_WEIGHT,
    deviation_threshold: float = DEVIATION_THRESHOLD,
) -> tuple[Optional[float], bool]:
    """
    Calculate weighted average between two API sources.

    Args:
        kma_value: Value from KMA (Korea Meteorological Administration)
        openmeteo_value: Value from Open-Meteo API
        kma_weight: Weight for KMA value (default: 0.6)
        openmeteo_weight: Weight for Open-Meteo value (default: 0.4)
        deviation_threshold: Threshold for deviation flag (default: 5.0)

    Returns:
        tuple[Optional[float], bool]: (averaged_value, deviation_flag)
    """
    # If both values are missing, return None
    if kma_value is None and openmeteo_value is None:
        return None, False

    # If only one value is available, use it directly
    if kma_value is None:
        return openmeteo_value, False
    if openmeteo_value is None:
        return kma_value, False

    # Calculate weighted average
    avg_value = (kma_value * kma_weight) + (openmeteo_value * openmeteo_weight)

    # Check for deviation
    deviation = abs(kma_value - openmeteo_value)
    deviation_flag = deviation > deviation_threshold

    return avg_value, deviation_flag


def merge_weather_value(
    kma_value: Optional[float],
    openmeteo_value: Optional[float],
) -> WeatherValue:
    """
    Merge weather values from two APIs into a WeatherValue object.

    Args:
        kma_value: Value from KMA
        openmeteo_value: Value from Open-Meteo

    Returns:
        WeatherValue: Merged weather value with deviation flag
    """
    avg_value, deviation_flag = calculate_weighted_average(kma_value, openmeteo_value)

    return WeatherValue(
        kma=kma_value,
        openmeteo=openmeteo_value,
        avg=avg_value,
        deviation_flag=deviation_flag,
    )


def merge_weather_data(
    datetime_obj: datetime,
    kma_data: dict,
    openmeteo_data: dict,
    airkorea_data: Optional[dict] = None,
) -> WeatherData:
    """
    Merge weather data from multiple API sources.

    Args:
        datetime_obj: Forecast datetime
        kma_data: Data from KMA API
            Expected keys: temp, cloud, rain_prob, rain_amount, humidity, wind_speed
        openmeteo_data: Data from Open-Meteo API
            Expected keys: temp, cloud, rain_prob, rain_amount, humidity, wind_speed
        airkorea_data: Data from Airkorea API (optional)
            Expected keys: pm25, pm10

    Returns:
        WeatherData: Merged weather data object
    """
    weather = WeatherData(datetime=datetime_obj)

    # Merge temperature
    weather.temp = merge_weather_value(
        kma_data.get("temp"),
        openmeteo_data.get("temp"),
    )

    # Merge cloud cover
    weather.cloud = merge_weather_value(
        kma_data.get("cloud"),
        openmeteo_data.get("cloud"),
    )

    # Merge rain probability
    weather.rain_prob = merge_weather_value(
        kma_data.get("rain_prob"),
        openmeteo_data.get("rain_prob"),
    )

    # Merge rain amount
    weather.rain_amount = merge_weather_value(
        kma_data.get("rain_amount"),
        openmeteo_data.get("rain_amount"),
    )

    # Merge humidity
    weather.humidity = merge_weather_value(
        kma_data.get("humidity"),
        openmeteo_data.get("humidity"),
    )

    # Merge wind speed
    weather.wind_speed = merge_weather_value(
        kma_data.get("wind_speed"),
        openmeteo_data.get("wind_speed"),
    )

    # Add single-source data (Airkorea)
    if airkorea_data:
        weather.pm25 = airkorea_data.get("pm25")
        weather.pm10 = airkorea_data.get("pm10")

    # Add sunrise/sunset (usually from KMA or calculated)
    weather.sunrise = kma_data.get("sunrise") or openmeteo_data.get("sunrise")
    weather.sunset = kma_data.get("sunset") or openmeteo_data.get("sunset")

    # Add visibility (usually from KMA)
    weather.visibility = kma_data.get("visibility")

    return weather


def weather_data_to_dict(weather: WeatherData) -> dict:
    """
    Convert WeatherData object to dictionary for JSON serialization.

    Args:
        weather: WeatherData object

    Returns:
        dict: Dictionary representation
    """
    def value_to_dict(val: WeatherValue) -> dict:
        return {
            "kma": val.kma,
            "openmeteo": val.openmeteo,
            "avg": val.avg,
            "deviation_flag": val.deviation_flag,
        }

    return {
        "datetime": weather.datetime.isoformat(),
        "temp": value_to_dict(weather.temp),
        "cloud": value_to_dict(weather.cloud),
        "rain_prob": value_to_dict(weather.rain_prob),
        "rain_amount": value_to_dict(weather.rain_amount),
        "humidity": value_to_dict(weather.humidity),
        "wind_speed": value_to_dict(weather.wind_speed),
        "pm25": weather.pm25,
        "pm10": weather.pm10,
        "sunrise": weather.sunrise,
        "sunset": weather.sunset,
        "visibility": weather.visibility,
    }
