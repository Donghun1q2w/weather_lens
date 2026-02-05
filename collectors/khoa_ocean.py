"""KHOA (국립해양조사원 바다누리) Ocean Data Collector"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import logging
from .base_collector import BaseCollector, CollectorError

logger = logging.getLogger(__name__)


class KHOAOceanCollector(BaseCollector):
    """
    바다누리 해양 데이터 API Collector

    APIs:
    - 조석예보: 만조/간조 시각, 조위
    - 파고정보: 유의파고, 파주기
    - 해수온 관측: 표층 수온
    """

    # Base URLs for different ocean data services
    TIDE_URL = "https://apis.data.go.kr/1192136/tideFcstTime/GetTideFcstTimeApiService"
    WAVE_URL = "http://www.khoa.go.kr/api/oceangrid/obsWave/search.do"
    TEMP_URL = "http://www.khoa.go.kr/api/oceangrid/obsTemp/search.do"

    def __init__(self, api_key: str):
        """
        Initialize Ocean Collector

        Args:
            api_key: 공공데이터포털 API 인증키 (KMA_API_KEY or BEACH_API_KEY)
        """
        super().__init__(api_key)
        if not api_key:
            raise ValueError("API key is required (use KMA_API_KEY or BEACH_API_KEY)")

    async def collect(
        self,
        region_code: str,
        date_range: Optional[Tuple[datetime, datetime]] = None,
        ocean_station_id: Optional[str] = None,
        collect_tide: bool = True,
        collect_wave: bool = True,
        collect_temp: bool = True
    ) -> Dict[str, Any]:
        """
        Collect ocean data from KHOA

        Args:
            region_code: 읍면동 코드
            date_range: (start_date, end_date) tuple
            ocean_station_id: 해양 관측소 ID (e.g., "DT_0001")
            collect_tide: Collect tide data
            collect_wave: Collect wave data
            collect_temp: Collect water temperature data

        Returns:
            Dictionary with ocean data

        Raises:
            CollectorError: If collection fails
        """
        if not ocean_station_id:
            raise CollectorError(f"Ocean station ID is required for region {region_code}")

        # Default to D-day ~ D+2
        if date_range is None:
            start_date = datetime.now()
            end_date = start_date + timedelta(days=2)
        else:
            start_date, end_date = date_range

        result = {
            "source": "khoa",
            "region_code": region_code,
            "ocean_station_id": ocean_station_id,
            "collected_at": datetime.now().isoformat(),
            "data": {}
        }

        try:
            # Collect tide forecast data (조석예보)
            if collect_tide:
                try:
                    tide_data = await self._collect_tide_data(ocean_station_id, start_date, end_date)
                    result["data"]["tide"] = tide_data
                except Exception as e:
                    logger.warning(f"Failed to collect tide data: {str(e)}")
                    result["data"]["tide"] = None

            # Collect wave data (파고정보)
            if collect_wave:
                try:
                    wave_data = await self._collect_wave_data(ocean_station_id)
                    result["data"]["wave"] = wave_data
                except Exception as e:
                    logger.warning(f"Failed to collect wave data: {str(e)}")
                    result["data"]["wave"] = None

            # Collect water temperature data (해수온)
            if collect_temp:
                try:
                    temp_data = await self._collect_temp_data(ocean_station_id)
                    result["data"]["water_temp"] = temp_data
                except Exception as e:
                    logger.warning(f"Failed to collect water temp data: {str(e)}")
                    result["data"]["water_temp"] = None

            return result

        except Exception as e:
            logger.error(f"Failed to collect KHOA data for {region_code}: {str(e)}")
            raise CollectorError(f"KHOA collection failed: {str(e)}") from e

    async def _collect_tide_data(
        self,
        station_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Collect tide forecast data (조석예보) from data.go.kr

        Args:
            station_id: Ocean station ID (e.g., "DT_0018")
            start_date: Start date
            end_date: End date

        Returns:
            Dictionary with tide data including high/low tide events
        """
        params = {
            "serviceKey": self.api_key,
            "obsCode": station_id,
            "reqDate": start_date.strftime("%Y%m%d"),
            "min": 60,  # 1-hour intervals
            "type": "json",
            "numOfRows": 300,  # Max to get full day
            "pageNo": 1
        }

        response = await self._make_request(self.TIDE_URL, params)

        # Parse response - data.go.kr format
        # Response structure: {"header": {...}, "body": {...}}
        header = response.get("header", {})
        body = response.get("body", {})

        result_code = header.get("resultCode")
        if result_code != "00":
            result_msg = header.get("resultMsg", "Unknown error")
            raise CollectorError(f"Tide API error: {result_msg}")

        items = body.get("items", {})
        if isinstance(items, dict):
            items = items.get("item", [])
        if not items:
            return {"station_name": None, "forecasts": []}

        # Handle single item case (API returns dict instead of list)
        if isinstance(items, dict):
            items = [items]

        # Extract station info
        station_name = items[0].get("obsvtrNm") if items else None

        # Parse time-series to find high/low tides
        parsed_tides = self._extract_high_low_tides(items)

        return {
            "station_name": station_name,
            "forecasts": parsed_tides,
            "time_series": [
                {
                    "datetime": item.get("predcDt"),
                    "height": float(item.get("tdlvHgt", 0))
                }
                for item in items
            ]
        }

    def _extract_high_low_tides(self, items: List[Dict]) -> List[Dict]:
        """
        Extract high/low tide events from time-series data

        Looks for local maxima (high tide) and local minima (low tide)

        Note: Using min=60 (1-hour intervals) means tide times are approximate
        (±30 minutes from actual peak/trough).

        Args:
            items: List of time-series data points with predcDt and tdlvHgt

        Returns:
            List of high/low tide events with datetime, type, and height
        """
        if len(items) < 3:
            return []

        tides = []
        heights = [(item.get("predcDt"), float(item.get("tdlvHgt", 0))) for item in items]

        for i in range(1, len(heights) - 1):
            prev_h = heights[i - 1][1]
            curr_h = heights[i][1]
            next_h = heights[i + 1][1]

            # Local maximum = high tide (고조)
            if curr_h > prev_h and curr_h > next_h:
                tides.append({
                    "datetime": heights[i][0],
                    "type": "고조",
                    "height": curr_h
                })
            # Local minimum = low tide (저조)
            elif curr_h < prev_h and curr_h < next_h:
                tides.append({
                    "datetime": heights[i][0],
                    "type": "저조",
                    "height": curr_h
                })

        return tides

    async def _collect_wave_data(self, station_id: str) -> Dict[str, Any]:
        """
        Collect wave observation data (파고정보)

        Args:
            station_id: Ocean station ID

        Returns:
            Dictionary with wave data
        """
        params = {
            "ServiceKey": self.api_key,
            "ObsCode": station_id,
            "ResultType": "json"
        }

        response = await self._make_request(self.WAVE_URL, params)

        # Parse wave data
        result = response.get("result", {})

        if result.get("code") != 200:
            raise CollectorError(f"KHOA wave API error: {result.get('message')}")

        data = result.get("data", {})

        # Get latest observation
        if isinstance(data, list) and len(data) > 0:
            latest = data[0]
        elif isinstance(data, dict):
            latest = data
        else:
            raise CollectorError("Invalid wave data format")

        return {
            "station_name": latest.get("obs_post_name"),
            "observed_at": latest.get("record_time"),
            "significant_wave_height": self._parse_float(latest.get("wave_height")),  # 유의파고 (m)
            "wave_period": self._parse_float(latest.get("wave_per")),  # 파주기 (초)
            "max_wave_height": self._parse_float(latest.get("wave_height_max"))  # 최대파고 (m)
        }

    async def _collect_temp_data(self, station_id: str) -> Dict[str, Any]:
        """
        Collect water temperature observation data (해수온)

        Args:
            station_id: Ocean station ID

        Returns:
            Dictionary with water temperature data
        """
        params = {
            "ServiceKey": self.api_key,
            "ObsCode": station_id,
            "ResultType": "json"
        }

        response = await self._make_request(self.TEMP_URL, params)

        # Parse temperature data
        result = response.get("result", {})

        if result.get("code") != 200:
            raise CollectorError(f"KHOA temp API error: {result.get('message')}")

        data = result.get("data", {})

        # Get latest observation
        if isinstance(data, list) and len(data) > 0:
            latest = data[0]
        elif isinstance(data, dict):
            latest = data
        else:
            raise CollectorError("Invalid temperature data format")

        return {
            "station_name": latest.get("obs_post_name"),
            "observed_at": latest.get("record_time"),
            "surface_temp": self._parse_float(latest.get("water_temp")),  # 표층 수온 (℃)
            "depth_1m_temp": self._parse_float(latest.get("water_temp_1")),  # 1m 수온
            "depth_5m_temp": self._parse_float(latest.get("water_temp_5"))  # 5m 수온
        }

    def _parse_float(self, value: Any) -> Optional[float]:
        """
        Safely parse float value

        Args:
            value: Value to parse

        Returns:
            Float value or None
        """
        if value is None or value == "" or value == "-":
            return None

        try:
            return float(value)
        except (ValueError, TypeError):
            return None
