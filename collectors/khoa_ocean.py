"""공공데이터포털 조석/해양 데이터 Collector

조석예보(고, 저조) API: https://apis.data.go.kr/1192136/tideFcstHghLw/GetTideFcstHghLwApiService
파고정보 API: http://www.khoa.go.kr/api/oceangrid/obsWave/search.do
해수온 API: http://www.khoa.go.kr/api/oceangrid/obsTemp/search.do
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import logging
from .base_collector import BaseCollector, CollectorError

logger = logging.getLogger(__name__)

# 고/저조 구분 코드
TIDE_TYPE_MAP = {
    "1": "고조",   # 1st high tide
    "2": "저조",   # 1st low tide
    "3": "고조",   # 2nd high tide
    "4": "저조",   # 2nd low tide
}


class KHOAOceanCollector(BaseCollector):
    """
    해양 데이터 Collector

    APIs:
    - 조석예보(고, 저조): 만조/간조 시각, 조위 (공공데이터포털)
    - 파고정보: 유의파고, 파주기 (KHOA)
    - 해수온 관측: 표층 수온 (KHOA)
    """

    # 조석예보(고, 저조) - 공공데이터포털
    TIDE_URL = "https://apis.data.go.kr/1192136/tideFcstHghLw/GetTideFcstHghLwApiService"
    # 파고/수온 - KHOA 바다누리
    WAVE_URL = "https://www.khoa.go.kr/api/oceangrid/obsWave/search.do"
    TEMP_URL = "https://www.khoa.go.kr/api/oceangrid/obsTemp/search.do"

    def __init__(self, api_key: str):
        """
        Initialize Ocean Collector

        Args:
            api_key: 공공데이터포털 API 인증키
        """
        super().__init__(api_key)
        if not api_key:
            raise ValueError("API key is required")

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
        Collect ocean data

        Args:
            region_code: 읍면동 코드
            date_range: (start_date, end_date) tuple
            ocean_station_id: 해양 관측소 ID (e.g., "DT_0001")
            collect_tide: Collect tide data
            collect_wave: Collect wave data
            collect_temp: Collect water temperature data

        Returns:
            Dictionary with ocean data
        """
        if not ocean_station_id:
            raise CollectorError(f"Ocean station ID is required for region {region_code}")

        if date_range is None:
            start_date = datetime.now()
            end_date = start_date + timedelta(days=2)
        else:
            start_date, end_date = date_range

        result = {
            "source": "data.go.kr",
            "region_code": region_code,
            "ocean_station_id": ocean_station_id,
            "collected_at": datetime.now().isoformat(),
            "data": {}
        }

        try:
            if collect_tide:
                try:
                    tide_data = await self.collect_tide(ocean_station_id, start_date)
                    result["data"]["tide"] = tide_data
                except Exception as e:
                    logger.warning(f"Failed to collect tide data: {e}")
                    result["data"]["tide"] = None

            if collect_wave:
                try:
                    wave_data = await self._collect_wave_data(ocean_station_id)
                    result["data"]["wave"] = wave_data
                except Exception as e:
                    logger.warning(f"Failed to collect wave data: {e}")
                    result["data"]["wave"] = None

            if collect_temp:
                try:
                    temp_data = await self._collect_temp_data(ocean_station_id)
                    result["data"]["water_temp"] = temp_data
                except Exception as e:
                    logger.warning(f"Failed to collect water temp data: {e}")
                    result["data"]["water_temp"] = None

            return result

        except Exception as e:
            logger.error(f"Failed to collect ocean data for {region_code}: {e}")
            raise CollectorError(f"Ocean collection failed: {e}") from e

    async def collect_tide(
        self,
        station_id: str,
        req_date: Optional[datetime] = None,
        num_of_rows: int = 20
    ) -> Dict[str, Any]:
        """
        조석예보(고, 저조) 데이터 수집

        공공데이터포털 API를 통해 고조/저조 시각과 조위를 직접 조회.
        하루 4건 (고조 2회, 저조 2회)의 정확한 데이터 제공.

        Args:
            station_id: 예보지점 코드 (e.g., "DT_0018")
            req_date: 요청 일자 (기본: 오늘)
            num_of_rows: 조회 건수 (기본: 20, 약 5일치)

        Returns:
            Dictionary with station info and tide forecasts
        """
        if req_date is None:
            req_date = datetime.now()

        params = {
            "serviceKey": self.api_key,
            "obsCode": station_id,
            "reqDate": req_date.strftime("%Y%m%d"),
            "type": "json",
            "numOfRows": num_of_rows,
            "pageNo": 1
        }

        response = await self._make_request(self.TIDE_URL, params)

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

        if isinstance(items, dict):
            items = [items]

        station_name = items[0].get("obsvtrNm") if items else None

        forecasts = []
        for item in items:
            extr_se = str(item.get("extrSe", ""))
            tide_type = TIDE_TYPE_MAP.get(extr_se)
            if not tide_type:
                continue

            forecasts.append({
                "datetime": item.get("predcDt"),
                "type": tide_type,
                "height": float(item.get("predcTdlvVl", 0)),
            })

        return {
            "station_name": station_name,
            "forecasts": forecasts,
        }

    async def _collect_wave_data(self, station_id: str) -> Dict[str, Any]:
        """
        Collect wave observation data (파고정보)
        """
        params = {
            "ServiceKey": self.api_key,
            "ObsCode": station_id,
            "ResultType": "json"
        }

        response = await self._make_request(self.WAVE_URL, params)

        result = response.get("result", {})
        if result.get("code") != 200:
            raise CollectorError(f"KHOA wave API error: {result.get('message')}")

        data = result.get("data", {})
        if isinstance(data, list) and len(data) > 0:
            latest = data[0]
        elif isinstance(data, dict):
            latest = data
        else:
            raise CollectorError("Invalid wave data format")

        return {
            "station_name": latest.get("obs_post_name"),
            "observed_at": latest.get("record_time"),
            "significant_wave_height": self._parse_float(latest.get("wave_height")),
            "wave_period": self._parse_float(latest.get("wave_per")),
            "max_wave_height": self._parse_float(latest.get("wave_height_max"))
        }

    async def _collect_temp_data(self, station_id: str) -> Dict[str, Any]:
        """
        Collect water temperature observation data (해수온)
        """
        params = {
            "ServiceKey": self.api_key,
            "ObsCode": station_id,
            "ResultType": "json"
        }

        response = await self._make_request(self.TEMP_URL, params)

        result = response.get("result", {})
        if result.get("code") != 200:
            raise CollectorError(f"KHOA temp API error: {result.get('message')}")

        data = result.get("data", {})
        if isinstance(data, list) and len(data) > 0:
            latest = data[0]
        elif isinstance(data, dict):
            latest = data
        else:
            raise CollectorError("Invalid temperature data format")

        return {
            "station_name": latest.get("obs_post_name"),
            "observed_at": latest.get("record_time"),
            "surface_temp": self._parse_float(latest.get("water_temp")),
            "depth_1m_temp": self._parse_float(latest.get("water_temp_1")),
            "depth_5m_temp": self._parse_float(latest.get("water_temp_5"))
        }

    def _parse_float(self, value: Any) -> Optional[float]:
        """Safely parse float value"""
        if value is None or value == "" or value == "-":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
