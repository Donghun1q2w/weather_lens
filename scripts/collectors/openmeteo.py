"""Open-Meteo API Collector - No API key required"""
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple
import logging
from .base_collector import BaseCollector, CollectorError

logger = logging.getLogger(__name__)


class OpenMeteoCollector(BaseCollector):
    """
    Open-Meteo Weather API Collector

    API: Open-Meteo Free Weather API
    - No API key required
    - 10,000 requests/day free tier
    - Hourly forecast data
    """

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self):
        """Initialize Open-Meteo Collector (no API key needed)"""
        super().__init__(api_key=None)

    async def collect(
        self,
        region_code: str,
        date_range: Optional[Tuple[datetime, datetime]] = None,
        lat: Optional[float] = None,
        lng: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Collect forecast data from Open-Meteo

        Args:
            region_code: 읍면동 코드
            date_range: (start_date, end_date) tuple
            lat: Latitude (required)
            lng: Longitude (required)

        Returns:
            Dictionary with forecast data

        Raises:
            CollectorError: If collection fails
        """
        if lat is None or lng is None:
            raise CollectorError(f"Latitude and longitude are required for region {region_code}")

        # Default to D-day ~ D+2
        if date_range is None:
            start_date = datetime.now()
            end_date = start_date + timedelta(days=2)
        else:
            start_date, end_date = date_range

        try:
            params = {
                "latitude": lat,
                "longitude": lng,
                "hourly": ",".join([
                    "temperature_2m",
                    "relative_humidity_2m",
                    "precipitation_probability",
                    "precipitation",
                    "cloud_cover",
                    "wind_speed_10m"
                ]),
                "timezone": "Asia/Seoul",
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d")
            }

            response = await self._make_request(self.BASE_URL, params)

            if "hourly" not in response:
                raise CollectorError(f"Invalid response format from Open-Meteo for region {region_code}")

            forecast_data = self._parse_forecast_data(response["hourly"])

            return {
                "source": "open_meteo",
                "region_code": region_code,
                "collected_at": datetime.now().isoformat(),
                "coordinates": {
                    "lat": lat,
                    "lng": lng
                },
                "forecast": forecast_data
            }

        except Exception as e:
            logger.error(f"Failed to collect Open-Meteo data for {region_code}: {str(e)}")
            raise CollectorError(f"Open-Meteo collection failed: {str(e)}") from e

    def _parse_forecast_data(self, hourly_data: Dict[str, Any]) -> list:
        """
        Parse hourly forecast data into structured format

        Args:
            hourly_data: Hourly data from API response

        Returns:
            List of forecast dictionaries by datetime
        """
        times = hourly_data.get("time", [])
        temps = hourly_data.get("temperature_2m", [])
        humidity = hourly_data.get("relative_humidity_2m", [])
        rain_prob = hourly_data.get("precipitation_probability", [])
        precipitation = hourly_data.get("precipitation", [])
        cloud_cover = hourly_data.get("cloud_cover", [])
        wind_speed = hourly_data.get("wind_speed_10m", [])

        forecast = []

        for i, time_str in enumerate(times):
            try:
                # Parse datetime
                dt = datetime.fromisoformat(time_str)

                forecast.append({
                    "datetime": dt.isoformat(),
                    "temp": self._get_value(temps, i),
                    "humidity": self._get_value(humidity, i),
                    "rain_prob": self._get_value(rain_prob, i),
                    "precipitation": self._get_value(precipitation, i),
                    "cloud_cover": self._get_value(cloud_cover, i),
                    "wind_speed": self._get_value(wind_speed, i)
                })

            except (ValueError, IndexError) as e:
                logger.warning(f"Failed to parse forecast entry at index {i}: {str(e)}")
                continue

        return forecast

    def _get_value(self, data_list: list, index: int) -> Optional[float]:
        """
        Safely get value from list at index

        Args:
            data_list: Data list
            index: Index to retrieve

        Returns:
            Value at index or None if not available
        """
        try:
            value = data_list[index]
            return float(value) if value is not None else None
        except (IndexError, ValueError, TypeError):
            return None
