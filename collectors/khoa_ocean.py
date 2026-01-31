"""KHOA (국립해양조사원 바다누리) Ocean Data Collector"""
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple
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
    TIDE_URL = "http://www.khoa.go.kr/api/oceangrid/tidalBu/search.do"
    WAVE_URL = "http://www.khoa.go.kr/api/oceangrid/obsWave/search.do"
    TEMP_URL = "http://www.khoa.go.kr/api/oceangrid/obsTemp/search.do"

    def __init__(self, api_key: str):
        """
        Initialize KHOA Ocean Collector

        Args:
            api_key: 바다누리 API 인증키
        """
        super().__init__(api_key)
        if not api_key:
            raise ValueError("KHOA API key is required")

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
        Collect tide forecast data (조석예보)

        Args:
            station_id: Ocean station ID
            start_date: Start date
            end_date: End date

        Returns:
            Dictionary with tide data
        """
        params = {
            "ServiceKey": self.api_key,
            "ObsCode": station_id,
            "Date": start_date.strftime("%Y%m%d"),
            "ResultType": "json"
        }

        response = await self._make_request(self.TIDE_URL, params)

        # Parse tide data
        result = response.get("result", {})

        if result.get("code") != 200:
            raise CollectorError(f"KHOA tide API error: {result.get('message')}")

        data = result.get("data", {})
        tide_list = data.get("data", [])

        parsed_tides = []
        for tide in tide_list:
            try:
                parsed_tides.append({
                    "datetime": tide.get("tph_time"),  # 만조/간조 시각
                    "type": tide.get("tph_lev"),  # "고조" or "저조"
                    "height": float(tide.get("tph_height", 0)),  # 조위 (cm)
                })
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse tide entry: {str(e)}")
                continue

        return {
            "station_name": data.get("obs_post_name"),
            "forecasts": parsed_tides
        }

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
