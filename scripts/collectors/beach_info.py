"""KMA Beach Info Service Collector - 기상청 전국해수욕장 날씨 조회서비스"""
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple, Literal
import logging
from .base_collector import BaseCollector, CollectorError

logger = logging.getLogger(__name__)


class BeachInfoCollector(BaseCollector):
    """
    기상청 전국해수욕장 날씨 조회서비스 API Collector

    6개 API 엔드포인트 지원:
    1. getUltraSrtFcstBeach - 초단기예보 (매 30분)
    2. getVilageFcstBeach - 단기예보 (하루 8회: 02,05,08,11,14,17,20,23시)
    3. getWhBuoyBeach - 파고조회
    4. getTideInfoBeach - 조석조회 (6~8월만 제공)
    5. getSunInfoBeach - 일출일몰조회 (6~8월만 제공)
    6. getTwBuoyBeach - 수온조회
    """

    BASE_URL = "http://apis.data.go.kr/1360000/BeachInfoservice"

    # 하늘 상태 코드 (SKY)
    SKY_CODE = {
        1: "맑음",
        3: "구름많음",
        4: "흐림"
    }

    # 강수 형태 코드 (PTY)
    PTY_CODE = {
        0: "없음",
        1: "비",
        2: "비/눈",
        3: "눈",
        4: "소나기"
    }

    # 조석 타입 (tiType)
    TIDE_TYPE = {
        "ET": "간조",
        "FT": "만조"
    }

    def __init__(self, api_key: str):
        """
        Initialize Beach Info Service Collector

        Args:
            api_key: 공공데이터포털 API 인증키
        """
        super().__init__(api_key)
        if not api_key:
            raise ValueError("Beach Info API key is required")

        logger.info("BeachInfoCollector initialized")

    async def collect(
        self,
        beach_num: str,
        date_range: Optional[Tuple[datetime, datetime]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Collect comprehensive beach weather data

        Args:
            beach_num: 해수욕장 번호 (예: 1, 2, 3, ...)
            date_range: (start_date, end_date) tuple
            **kwargs: Additional parameters

        Returns:
            Dictionary with all beach weather data

        Raises:
            CollectorError: If collection fails
        """
        if date_range is None:
            base_date = datetime.now()
        else:
            base_date = date_range[0]

        try:
            # 모든 데이터 수집
            ultra_srt = await self.get_ultra_short_forecast(beach_num, base_date)
            village = await self.get_village_forecast(beach_num, base_date)
            wave_height = await self.get_wave_height(beach_num, base_date)
            sea_temp = await self.get_sea_temperature(beach_num, base_date)

            # 6~8월만 제공되는 데이터
            tide_info = None
            sun_info = None
            if 6 <= base_date.month <= 8:
                tide_info = await self.get_tide_info(beach_num, base_date)
                sun_info = await self.get_sun_info(beach_num, base_date)

            return {
                "source": "kma_beach_info",
                "beach_num": beach_num,
                "collected_at": datetime.now().isoformat(),
                "base_date": base_date.isoformat(),
                "ultra_short_forecast": ultra_srt,
                "village_forecast": village,
                "wave_height": wave_height,
                "sea_temperature": sea_temp,
                "tide_info": tide_info,
                "sun_info": sun_info
            }

        except Exception as e:
            logger.error(f"Failed to collect beach info for beach {beach_num}: {str(e)}")
            raise CollectorError(f"Beach info collection failed: {str(e)}") from e

    async def get_ultra_short_forecast(
        self,
        beach_num: str,
        base_datetime: datetime,
        num_of_rows: int = 1000
    ) -> Dict[str, Any]:
        """
        초단기예보 조회 (매 30분 갱신)

        제공 카테고리:
        - TMP: 기온 (°C)
        - PTY: 강수형태 (0=없음, 1=비, 2=비/눈, 3=눈, 4=소나기)
        - SKY: 하늘상태 (1=맑음, 3=구름많음, 4=흐림)
        - REH: 습도 (%)
        - VEC: 풍향 (deg)
        - WSD: 풍속 (m/s)
        - UUU: 동서바람성분 (m/s)
        - VVV: 남북바람성분 (m/s)

        Args:
            beach_num: 해수욕장 번호
            base_datetime: 기준 날짜/시간
            num_of_rows: 조회 행 수

        Returns:
            Dictionary with ultra short forecast data
        """
        # 발표 시각 계산 (매 시각 30분 발표)
        base_time = base_datetime.replace(minute=30, second=0, microsecond=0)
        if base_datetime.minute < 30:
            base_time -= timedelta(hours=1)

        params = {
            "serviceKey": self.api_key,
            "numOfRows": num_of_rows,
            "pageNo": 1,
            "dataType": "JSON",
            "base_date": base_time.strftime("%Y%m%d"),
            "base_time": base_time.strftime("%H%M"),
            "beach_num": beach_num
        }

        url = f"{self.BASE_URL}/getUltraSrtFcstBeach"
        response = await self._make_request(url, params)

        # 응답 파싱
        header = response.get("response", {}).get("header", {})
        result_code = header.get("resultCode")

        if result_code == "03":
            # NO_DATA
            logger.warning(f"No ultra short forecast data for beach {beach_num}")
            return {"items": []}

        if result_code != "00":
            error_msg = header.get("resultMsg", "Unknown error")
            raise CollectorError(f"Ultra short forecast API error: {error_msg}")

        items = response.get("response", {}).get("body", {}).get("items", {}).get("item", [])

        if isinstance(items, dict):
            items = [items]

        return {
            "base_date": params["base_date"],
            "base_time": params["base_time"],
            "items": self._parse_forecast_items(items)
        }

    async def get_village_forecast(
        self,
        beach_num: str,
        base_datetime: datetime,
        num_of_rows: int = 1000
    ) -> Dict[str, Any]:
        """
        단기예보 조회 (하루 8회: 02,05,08,11,14,17,20,23시)

        제공 카테고리:
        - TMP: 1시간 기온 (°C)
        - TMN: 일 최저기온 (°C)
        - TMX: 일 최고기온 (°C)
        - POP: 강수확률 (%)
        - PTY: 강수형태
        - PCP: 1시간 강수량 (mm)
        - REH: 습도 (%)
        - SNO: 1시간 신적설 (cm)
        - SKY: 하늘상태
        - UUU: 동서바람성분 (m/s)
        - VVV: 남북바람성분 (m/s)
        - WAV: 파고 (m)
        - VEC: 풍향 (deg)
        - WSD: 풍속 (m/s)

        Args:
            beach_num: 해수욕장 번호
            base_datetime: 기준 날짜/시간
            num_of_rows: 조회 행 수

        Returns:
            Dictionary with village forecast data
        """
        # 발표 시각 결정 (02, 05, 08, 11, 14, 17, 20, 23시)
        base_hours = [2, 5, 8, 11, 14, 17, 20, 23]
        current_hour = base_datetime.hour

        # 가장 최근 발표 시각 찾기
        base_hour = max([h for h in base_hours if h <= current_hour], default=23)
        base_time = base_datetime.replace(hour=base_hour, minute=0, second=0, microsecond=0)

        if base_hour == 23 and current_hour < 23:
            # 어제 23시 발표
            base_time -= timedelta(days=1)

        params = {
            "serviceKey": self.api_key,
            "numOfRows": num_of_rows,
            "pageNo": 1,
            "dataType": "JSON",
            "base_date": base_time.strftime("%Y%m%d"),
            "base_time": base_time.strftime("%H%M"),
            "beach_num": beach_num
        }

        url = f"{self.BASE_URL}/getVilageFcstBeach"
        response = await self._make_request(url, params)

        # 응답 파싱
        header = response.get("response", {}).get("header", {})
        result_code = header.get("resultCode")

        if result_code == "03":
            # NO_DATA
            logger.warning(f"No village forecast data for beach {beach_num}")
            return {"items": []}

        if result_code != "00":
            error_msg = header.get("resultMsg", "Unknown error")
            raise CollectorError(f"Village forecast API error: {error_msg}")

        items = response.get("response", {}).get("body", {}).get("items", {}).get("item", [])

        if isinstance(items, dict):
            items = [items]

        return {
            "base_date": params["base_date"],
            "base_time": params["base_time"],
            "items": self._parse_forecast_items(items)
        }

    async def get_wave_height(
        self,
        beach_num: str,
        search_time: datetime,
        num_of_rows: int = 10
    ) -> Dict[str, Any]:
        """
        파고 조회 (wave height)

        응답 필드:
        - beachnum: 해수욕장 번호
        - tm: 관측 시각 (yyyymmddhhmm)
        - wh: 파고 (미터)

        Args:
            beach_num: 해수욕장 번호
            search_time: 조회 시각
            num_of_rows: 조회 행 수

        Returns:
            Dictionary with wave height data
        """
        params = {
            "serviceKey": self.api_key,
            "numOfRows": num_of_rows,
            "pageNo": 1,
            "dataType": "JSON",
            "beach_num": beach_num,
            "searchTime": search_time.strftime("%Y%m%d%H%M")
        }

        url = f"{self.BASE_URL}/getWhBuoyBeach"
        response = await self._make_request(url, params)

        # 응답 파싱
        header = response.get("response", {}).get("header", {})
        result_code = header.get("resultCode")

        if result_code == "03":
            # NO_DATA
            logger.warning(f"No wave height data for beach {beach_num}")
            return {"items": []}

        if result_code != "00":
            error_msg = header.get("resultMsg", "Unknown error")
            raise CollectorError(f"Wave height API error: {error_msg}")

        items = response.get("response", {}).get("body", {}).get("items", {}).get("item", [])

        if isinstance(items, dict):
            items = [items]

        return {
            "search_time": params["searchTime"],
            "items": self._parse_wave_height_items(items)
        }

    async def get_tide_info(
        self,
        beach_num: str,
        base_date: datetime,
        num_of_rows: int = 100
    ) -> Dict[str, Any]:
        """
        조석 조회 (6~8월만 제공)

        응답 필드:
        - beachNum: 해수욕장 번호
        - baseDate: 기준일자 (yyyymmdd)
        - tiStnld: 조석 관측소명
        - tiTime: 조석 시각 (hhmm)
        - tiType: 조석 타입 (ET=간조, FT=만조)
        - tilevel: 조위 (cm)

        Args:
            beach_num: 해수욕장 번호
            base_date: 기준 날짜
            num_of_rows: 조회 행 수

        Returns:
            Dictionary with tide info data
        """
        params = {
            "serviceKey": self.api_key,
            "numOfRows": num_of_rows,
            "pageNo": 1,
            "dataType": "JSON",
            "base_date": base_date.strftime("%Y%m%d"),
            "beach_num": beach_num
        }

        url = f"{self.BASE_URL}/getTideInfoBeach"
        response = await self._make_request(url, params)

        # 응답 파싱
        header = response.get("response", {}).get("header", {})
        result_code = header.get("resultCode")

        if result_code == "03":
            # NO_DATA
            logger.warning(f"No tide info for beach {beach_num} (available only June-August)")
            return {"items": []}

        if result_code != "00":
            error_msg = header.get("resultMsg", "Unknown error")
            raise CollectorError(f"Tide info API error: {error_msg}")

        items = response.get("response", {}).get("body", {}).get("items", {}).get("item", [])

        if isinstance(items, dict):
            items = [items]

        return {
            "base_date": params["base_date"],
            "items": self._parse_tide_items(items)
        }

    async def get_sun_info(
        self,
        beach_num: str,
        base_date: datetime,
        num_of_rows: int = 10
    ) -> Dict[str, Any]:
        """
        일출일몰 조회 (6~8월만 제공)

        응답 필드:
        - beachNum: 해수욕장 번호
        - baseDate: 기준일자 (yyyymmdd)
        - sunrise: 일출시각 (hhmm)
        - sunset: 일몰시각 (hhmm)

        Args:
            beach_num: 해수욕장 번호
            base_date: 기준 날짜
            num_of_rows: 조회 행 수

        Returns:
            Dictionary with sunrise/sunset data
        """
        params = {
            "serviceKey": self.api_key,
            "numOfRows": num_of_rows,
            "pageNo": 1,
            "dataType": "JSON",
            "Base_date": base_date.strftime("%Y%m%d"),
            "beach_num": beach_num
        }

        url = f"{self.BASE_URL}/getSunInfoBeach"
        response = await self._make_request(url, params)

        # 응답 파싱
        header = response.get("response", {}).get("header", {})
        result_code = header.get("resultCode")

        if result_code == "03":
            # NO_DATA
            logger.warning(f"No sun info for beach {beach_num} (available only June-August)")
            return {"items": []}

        if result_code != "00":
            error_msg = header.get("resultMsg", "Unknown error")
            raise CollectorError(f"Sun info API error: {error_msg}")

        items = response.get("response", {}).get("body", {}).get("items", {}).get("item", [])

        if isinstance(items, dict):
            items = [items]

        return {
            "base_date": params["Base_date"],
            "items": self._parse_sun_items(items)
        }

    async def get_sea_temperature(
        self,
        beach_num: str,
        search_time: datetime,
        num_of_rows: int = 10
    ) -> Dict[str, Any]:
        """
        수온 조회 (sea temperature)

        응답 필드:
        - beachNum: 해수욕장 번호
        - tm: 관측 시각 (yyyymmddhhmm)
        - tw: 수온 (°C)

        Args:
            beach_num: 해수욕장 번호
            search_time: 조회 시각
            num_of_rows: 조회 행 수

        Returns:
            Dictionary with sea temperature data
        """
        params = {
            "serviceKey": self.api_key,
            "numOfRows": num_of_rows,
            "pageNo": 1,
            "dataType": "JSON",
            "beach_num": beach_num,
            "searchTime": search_time.strftime("%Y%m%d%H%M")
        }

        url = f"{self.BASE_URL}/getTwBuoyBeach"
        response = await self._make_request(url, params)

        # 응답 파싱
        header = response.get("response", {}).get("header", {})
        result_code = header.get("resultCode")

        if result_code == "03":
            # NO_DATA
            logger.warning(f"No sea temperature data for beach {beach_num}")
            return {"items": []}

        if result_code != "00":
            error_msg = header.get("resultMsg", "Unknown error")
            raise CollectorError(f"Sea temperature API error: {error_msg}")

        items = response.get("response", {}).get("body", {}).get("items", {}).get("item", [])

        if isinstance(items, dict):
            items = [items]

        return {
            "search_time": params["searchTime"],
            "items": self._parse_sea_temp_items(items)
        }

    def _parse_forecast_items(self, items: list) -> list:
        """
        예보 데이터 아이템 파싱 (초단기예보, 단기예보)

        Args:
            items: API 응답 아이템 리스트

        Returns:
            List of parsed forecast items
        """
        result = []

        # fcstDate + fcstTime 기준으로 그룹화
        forecast_map = {}

        for item in items:
            fcst_date = item.get("fcstDate")
            fcst_time = item.get("fcstTime")
            category = item.get("category")
            fcst_value = item.get("fcstValue")

            if not fcst_date or not fcst_time:
                continue

            key = f"{fcst_date}_{fcst_time}"

            if key not in forecast_map:
                forecast_map[key] = {
                    "fcst_date": fcst_date,
                    "fcst_time": fcst_time,
                    "datetime": None
                }

            # 카테고리별 값 저장
            if category == "TMP":
                forecast_map[key]["temperature"] = self._safe_float(fcst_value)
            elif category == "TMN":
                forecast_map[key]["temp_min"] = self._safe_float(fcst_value)
            elif category == "TMX":
                forecast_map[key]["temp_max"] = self._safe_float(fcst_value)
            elif category == "POP":
                forecast_map[key]["precipitation_prob"] = self._safe_int(fcst_value)
            elif category == "PTY":
                pty_code = self._safe_int(fcst_value)
                forecast_map[key]["precipitation_type"] = pty_code
                forecast_map[key]["precipitation_type_desc"] = self.PTY_CODE.get(pty_code, "알 수 없음")
            elif category == "PCP":
                forecast_map[key]["precipitation"] = fcst_value
            elif category == "REH":
                forecast_map[key]["humidity"] = self._safe_int(fcst_value)
            elif category == "SNO":
                forecast_map[key]["snow"] = fcst_value
            elif category == "SKY":
                sky_code = self._safe_int(fcst_value)
                forecast_map[key]["sky"] = sky_code
                forecast_map[key]["sky_desc"] = self.SKY_CODE.get(sky_code, "알 수 없음")
            elif category == "VEC":
                forecast_map[key]["wind_direction"] = self._safe_float(fcst_value)
            elif category == "WSD":
                forecast_map[key]["wind_speed"] = self._safe_float(fcst_value)
            elif category == "UUU":
                forecast_map[key]["wind_ew"] = self._safe_float(fcst_value)
            elif category == "VVV":
                forecast_map[key]["wind_ns"] = self._safe_float(fcst_value)
            elif category == "WAV":
                forecast_map[key]["wave_height"] = self._safe_float(fcst_value)

        # datetime 생성 및 리스트로 변환
        for key, data in forecast_map.items():
            try:
                dt = datetime.strptime(
                    f"{data['fcst_date']}{data['fcst_time']}",
                    "%Y%m%d%H%M"
                )
                data["datetime"] = dt.isoformat()
            except ValueError:
                pass

            result.append(data)

        # 시간순 정렬
        result.sort(key=lambda x: x.get("datetime", ""))

        return result

    def _parse_wave_height_items(self, items: list) -> list:
        """
        파고 데이터 아이템 파싱

        Args:
            items: API 응답 아이템 리스트

        Returns:
            List of parsed wave height items
        """
        result = []

        for item in items:
            tm = item.get("tm", "")
            wh = item.get("wh")

            parsed_item = {
                "beach_num": item.get("beachnum"),
                "time": tm,
                "wave_height": self._safe_float(wh)
            }

            # datetime 생성
            if tm and len(tm) >= 12:
                try:
                    dt = datetime.strptime(tm, "%Y%m%d%H%M")
                    parsed_item["datetime"] = dt.isoformat()
                except ValueError:
                    pass

            result.append(parsed_item)

        return result

    def _parse_tide_items(self, items: list) -> list:
        """
        조석 데이터 아이템 파싱

        Args:
            items: API 응답 아이템 리스트

        Returns:
            List of parsed tide items
        """
        result = []

        for item in items:
            ti_type = item.get("tiType", "")

            parsed_item = {
                "beach_num": item.get("beachNum"),
                "base_date": item.get("baseDate"),
                "station": item.get("tiStnld"),
                "time": item.get("tiTime"),
                "type": ti_type,
                "type_desc": self.TIDE_TYPE.get(ti_type, "알 수 없음"),
                "level": self._safe_float(item.get("tilevel"))
            }

            result.append(parsed_item)

        return result

    def _parse_sun_items(self, items: list) -> list:
        """
        일출일몰 데이터 아이템 파싱

        Args:
            items: API 응답 아이템 리스트

        Returns:
            List of parsed sun items
        """
        result = []

        for item in items:
            parsed_item = {
                "beach_num": item.get("beachNum"),
                "base_date": item.get("baseDate"),
                "sunrise": item.get("sunrise"),
                "sunset": item.get("sunset")
            }

            result.append(parsed_item)

        return result

    def _parse_sea_temp_items(self, items: list) -> list:
        """
        수온 데이터 아이템 파싱

        Args:
            items: API 응답 아이템 리스트

        Returns:
            List of parsed sea temperature items
        """
        result = []

        for item in items:
            tm = item.get("tm", "")
            tw = item.get("tw")

            parsed_item = {
                "beach_num": item.get("beachNum"),
                "time": tm,
                "temperature": self._safe_float(tw)
            }

            # datetime 생성
            if tm and len(tm) >= 12:
                try:
                    dt = datetime.strptime(tm, "%Y%m%d%H%M")
                    parsed_item["datetime"] = dt.isoformat()
                except ValueError:
                    pass

            result.append(parsed_item)

        return result

    def _safe_int(self, value: Any) -> Optional[int]:
        """안전하게 정수 변환"""
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    def _safe_float(self, value: Any) -> Optional[float]:
        """안전하게 실수 변환"""
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
