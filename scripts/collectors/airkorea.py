"""AirKorea (에어코리아) Air Quality Collector"""
from datetime import datetime
from typing import Any, Dict, Optional, Tuple
import logging
from .base_collector import BaseCollector, CollectorError

logger = logging.getLogger(__name__)


class AirKoreaCollector(BaseCollector):
    """
    에어코리아 대기질 API Collector

    API: 한국환경공단_에어코리아_대기오염정보
    - PM2.5, PM10 데이터 수집
    """

    BASE_URL = "http://apis.data.go.kr/B552584/ArpltnInforInqireSvc"

    # 측정소별 실시간 측정정보 조회
    REALTIME_ENDPOINT = f"{BASE_URL}/getMsrstnAcctoRltmMesureDnsty"

    # 통합대기환경지수 나쁨 이상 측정소 목록조회
    STATION_LIST_ENDPOINT = f"{BASE_URL}/getCtprvnRltmMesureDnsty"

    # 대기질 등급
    PM25_GRADES = {
        (0, 15): "좋음",
        (16, 35): "보통",
        (36, 75): "나쁨",
        (76, float('inf')): "매우나쁨"
    }

    PM10_GRADES = {
        (0, 30): "좋음",
        (31, 80): "보통",
        (81, 150): "나쁨",
        (151, float('inf')): "매우나쁨"
    }

    def __init__(self, api_key: str):
        """
        Initialize AirKorea Collector

        Args:
            api_key: 에어코리아 API 인증키
        """
        super().__init__(api_key)
        if not api_key:
            raise ValueError("AirKorea API key is required")

    async def collect(
        self,
        region_code: str,
        date_range: Optional[Tuple[datetime, datetime]] = None,
        station_name: Optional[str] = None,
        sido_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Collect air quality data from AirKorea

        Args:
            region_code: 읍면동 코드
            date_range: Not used for real-time data (kept for interface consistency)
            station_name: 측정소명 (e.g., "강남구", "종로구")
            sido_name: 시도명 (e.g., "서울", "부산") - used if station_name not provided

        Returns:
            Dictionary with air quality data

        Raises:
            CollectorError: If collection fails
        """
        try:
            # Use station-specific endpoint if station_name provided
            if station_name:
                data = await self._get_station_data(station_name)
            elif sido_name:
                # Get sido-level data and extract relevant station
                data = await self._get_sido_data(sido_name, region_code)
            else:
                raise CollectorError(f"Either station_name or sido_name is required for region {region_code}")

            return {
                "source": "airkorea",
                "region_code": region_code,
                "collected_at": datetime.now().isoformat(),
                "station_name": data.get("stationName"),
                "air_quality": {
                    "pm25": data.get("pm25Value"),
                    "pm25_grade": data.get("pm25Grade"),
                    "pm10": data.get("pm10Value"),
                    "pm10_grade": data.get("pm10Grade"),
                    "measured_at": data.get("dataTime")
                }
            }

        except Exception as e:
            logger.error(f"Failed to collect AirKorea data for {region_code}: {str(e)}")
            raise CollectorError(f"AirKorea collection failed: {str(e)}") from e

    async def _get_station_data(self, station_name: str) -> Dict[str, Any]:
        """
        Get air quality data for specific station

        Args:
            station_name: 측정소명

        Returns:
            Dictionary with PM2.5 and PM10 data
        """
        params = {
            "serviceKey": self.api_key,
            "returnType": "json",
            "numOfRows": 1,
            "pageNo": 1,
            "stationName": station_name,
            "dataTerm": "DAILY",
            "ver": "1.0"
        }

        response = await self._make_request(self.REALTIME_ENDPOINT, params)

        # Check response
        header = response.get("response", {}).get("header", {})
        if header.get("resultCode") != "00":
            error_msg = header.get("resultMsg", "Unknown error")
            raise CollectorError(f"AirKorea API error: {error_msg}")

        items = response.get("response", {}).get("body", {}).get("items", [])

        if not items:
            raise CollectorError(f"No air quality data for station {station_name}")

        item = items[0]

        return {
            "stationName": item.get("stationName"),
            "pm25Value": self._parse_value(item.get("pm25Value")),
            "pm25Grade": self._get_pm25_grade(self._parse_value(item.get("pm25Value"))),
            "pm10Value": self._parse_value(item.get("pm10Value")),
            "pm10Grade": self._get_pm10_grade(self._parse_value(item.get("pm10Value"))),
            "dataTime": item.get("dataTime")
        }

    async def _get_sido_data(self, sido_name: str, region_code: str) -> Dict[str, Any]:
        """
        Get air quality data for sido (시도)

        Args:
            sido_name: 시도명
            region_code: 읍면동 코드 (for logging)

        Returns:
            Dictionary with PM2.5 and PM10 data
        """
        params = {
            "serviceKey": self.api_key,
            "returnType": "json",
            "numOfRows": 100,
            "pageNo": 1,
            "sidoName": sido_name,
            "ver": "1.0"
        }

        response = await self._make_request(self.STATION_LIST_ENDPOINT, params)

        # Check response
        header = response.get("response", {}).get("header", {})
        if header.get("resultCode") != "00":
            error_msg = header.get("resultMsg", "Unknown error")
            raise CollectorError(f"AirKorea API error: {error_msg}")

        items = response.get("response", {}).get("body", {}).get("items", [])

        if not items:
            raise CollectorError(f"No air quality data for sido {sido_name}")

        # Use the first station (or aggregate if needed in future)
        item = items[0]

        return {
            "stationName": item.get("stationName"),
            "pm25Value": self._parse_value(item.get("pm25Value")),
            "pm25Grade": self._get_pm25_grade(self._parse_value(item.get("pm25Value"))),
            "pm10Value": self._parse_value(item.get("pm10Value")),
            "pm10Grade": self._get_pm10_grade(self._parse_value(item.get("pm10Value"))),
            "dataTime": item.get("dataTime")
        }

    def _parse_value(self, value: Any) -> Optional[float]:
        """
        Parse PM value from string

        Args:
            value: PM value (may be string, number, or "-")

        Returns:
            Float value or None
        """
        if value is None or value == "-" or value == "":
            return None

        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _get_pm25_grade(self, value: Optional[float]) -> Optional[str]:
        """
        Get PM2.5 grade based on value

        Args:
            value: PM2.5 concentration (μg/m³)

        Returns:
            Grade string (좋음/보통/나쁨/매우나쁨) or None
        """
        if value is None:
            return None

        for (low, high), grade in self.PM25_GRADES.items():
            if low <= value <= high:
                return grade

        return "매우나쁨"

    def _get_pm10_grade(self, value: Optional[float]) -> Optional[str]:
        """
        Get PM10 grade based on value

        Args:
            value: PM10 concentration (μg/m³)

        Returns:
            Grade string (좋음/보통/나쁨/매우나쁨) or None
        """
        if value is None:
            return None

        for (low, high), grade in self.PM10_GRADES.items():
            if low <= value <= high:
                return grade

        return "매우나쁨"
