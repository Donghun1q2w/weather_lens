"""KMA (기상청) Forecast Collector - Multiple API Support"""
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple, Literal
import logging
from .base_collector import BaseCollector, CollectorError

logger = logging.getLogger(__name__)


class KMAForecastCollector(BaseCollector):
    """
    기상청 단기예보 API Collector

    지원 API 소스:
    - data.go.kr: 공공데이터포털 (VilageFcstInfoService)
    - apihub.kma.go.kr: 기상청 API 허브 (VilageFcstMsgService)
    """

    # API 소스별 기본 URL
    API_SOURCES = {
        "data.go.kr": "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst",
        "apihub.kma.go.kr": "https://apihub.kma.go.kr/api/typ02/openApi/VilageFcstMsgService/getLandFcst"
    }

    # 지역 코드 → API 허브 지역 ID 매핑
    REGION_TO_REGID = {
        # 서울
        "11": "11B10101",
        # 부산
        "26": "11H20201",
        # 대구
        "27": "11H10701",
        # 인천
        "28": "11B20201",
        # 광주
        "29": "11F20501",
        # 대전
        "30": "11C20401",
        # 울산
        "31": "11H20101",
        # 세종
        "36": "11C20404",
        # 경기
        "41": "11B20601",
        # 강원
        "42": "11D10301",
        # 충북
        "43": "11C10301",
        # 충남
        "44": "11C20101",
        # 전북
        "45": "11F10201",
        # 전남
        "46": "11F20401",
        # 경북
        "47": "11H10201",
        # 경남
        "48": "11H20301",
        # 제주
        "50": "11G00201"
    }

    # 날씨 코드 → 하늘 상태 매핑
    WEATHER_CODE_TO_SKY = {
        "DB01": 1,  # 맑음
        "DB03": 3,  # 구름많음
        "DB04": 4,  # 흐림
    }

    # 예보 항목 코드 (data.go.kr용)
    FORECAST_CATEGORIES = {
        "TMP": "기온(℃)",
        "REH": "습도(%)",
        "WSD": "풍속(m/s)",
        "POP": "강수확률(%)",
        "PCP": "1시간 강수량(mm)",
        "SKY": "하늘상태(코드값)"
    }

    def __init__(
        self,
        api_key: str,
        api_source: Literal["data.go.kr", "apihub.kma.go.kr"] = "apihub.kma.go.kr"
    ):
        """
        Initialize KMA Forecast Collector

        Args:
            api_key: 기상청 API 인증키
            api_source: API 소스 선택 ("data.go.kr" 또는 "apihub.kma.go.kr")
        """
        super().__init__(api_key)
        if not api_key:
            raise ValueError("KMA API key is required")

        self.api_source = api_source
        if api_source not in self.API_SOURCES:
            raise ValueError(f"Invalid API source: {api_source}. Must be one of {list(self.API_SOURCES.keys())}")

        self.base_url = self.API_SOURCES[api_source]
        logger.info(f"KMAForecastCollector initialized with source: {api_source}")

    async def collect(
        self,
        region_code: str,
        date_range: Optional[Tuple[datetime, datetime]] = None,
        nx: Optional[int] = None,
        ny: Optional[int] = None,
        reg_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Collect forecast data from KMA

        Args:
            region_code: 읍면동 코드
            date_range: (start_date, end_date) tuple
            nx: 격자 X 좌표 (data.go.kr용)
            ny: 격자 Y 좌표 (data.go.kr용)
            reg_id: 지역 ID (apihub용, 예: 11B10101)

        Returns:
            Dictionary with forecast data

        Raises:
            CollectorError: If collection fails
        """
        # Default to D-day ~ D+2
        if date_range is None:
            start_date = datetime.now()
            end_date = start_date + timedelta(days=2)
        else:
            start_date, end_date = date_range

        try:
            if self.api_source == "data.go.kr":
                if nx is None or ny is None:
                    raise CollectorError(f"nx, ny grid coordinates are required for data.go.kr API")
                return await self._collect_from_data_go_kr(region_code, start_date, end_date, nx, ny)
            elif self.api_source == "apihub.kma.go.kr":
                return await self._collect_from_apihub(region_code, start_date, end_date, reg_id)
            else:
                raise CollectorError(f"Unsupported API source: {self.api_source}")

        except Exception as e:
            logger.error(f"Failed to collect KMA data for {region_code}: {str(e)}")
            raise CollectorError(f"KMA collection failed: {str(e)}") from e

    async def _collect_from_apihub(
        self,
        region_code: str,
        start_date: datetime,
        end_date: datetime,
        reg_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Collect data from apihub.kma.go.kr (기상청 API 허브)
        동네예보 통보문 조회 API 사용

        Args:
            region_code: 읍면동 코드
            start_date: 시작 날짜
            end_date: 종료 날짜
            reg_id: 지역 ID (없으면 region_code에서 추출)

        Returns:
            Dictionary with forecast data
        """
        # reg_id가 없으면 region_code에서 추출
        if reg_id is None:
            sido_code = region_code[:2]
            reg_id = self.REGION_TO_REGID.get(sido_code, "11B10101")  # 기본값: 서울

        params = {
            "pageNo": 1,
            "numOfRows": 20,
            "dataType": "JSON",
            "regId": reg_id,
            "authKey": self.api_key
        }

        response = await self._make_request(self.base_url, params)

        # API 응답 확인
        header = response.get("response", {}).get("header", {})
        result_code = header.get("resultCode")

        if result_code == "03":
            # NO_DATA - 빈 결과 반환
            logger.warning(f"No data available for region {reg_id}")
            return {
                "source": "kma",
                "api_source": self.api_source,
                "region_code": region_code,
                "reg_id": reg_id,
                "collected_at": datetime.now().isoformat(),
                "forecast": []
            }

        if result_code != "00":
            error_msg = header.get("resultMsg", "Unknown error")
            raise CollectorError(f"KMA API Hub error: {error_msg} (code: {result_code})")

        items = response.get("response", {}).get("body", {}).get("items", {}).get("item", [])

        if not items:
            logger.warning(f"Empty forecast data for region {reg_id}")
            return {
                "source": "kma",
                "api_source": self.api_source,
                "region_code": region_code,
                "reg_id": reg_id,
                "collected_at": datetime.now().isoformat(),
                "forecast": []
            }

        # 단일 항목인 경우 리스트로 변환
        if isinstance(items, dict):
            items = [items]

        forecast_data = self._parse_apihub_data(items, start_date, end_date)

        return {
            "source": "kma",
            "api_source": self.api_source,
            "region_code": region_code,
            "reg_id": reg_id,
            "collected_at": datetime.now().isoformat(),
            "announce_time": items[0].get("announceTime") if items else None,
            "forecast": forecast_data
        }

    def _parse_apihub_data(
        self,
        items: list,
        start_date: datetime,
        end_date: datetime
    ) -> list:
        """
        Parse API Hub response data (VilageFcstMsgService/getLandFcst)

        응답 필드:
        - announceTime: 발표시각 (202601301700)
        - numEf: 예보 시점 (0=오늘밤, 1=내일아침, 2=내일낮, ...)
        - ta: 기온 (°C)
        - rnSt: 강수확률 (%)
        - rnYn: 강수유무 (0=없음, 1=비, 2=비/눈, 3=눈)
        - wf: 날씨 설명 (맑음, 구름많음, 흐림 등)
        - wfCd: 날씨 코드 (DB01=맑음, DB03=구름많음, DB04=흐림)
        - wd1, wd2: 풍향
        - wsIt: 풍속 등급

        Args:
            items: API 응답 아이템 리스트
            start_date: 필터 시작 날짜
            end_date: 필터 종료 날짜

        Returns:
            List of forecast dictionaries
        """
        result = []
        base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        for item in items:
            num_ef = item.get("numEf", 0)

            # numEf를 날짜/시간으로 변환
            # 0=오늘밤, 1=내일아침, 2=내일낮, 3=내일밤, 4=모레아침, ...
            day_offset = num_ef // 2
            is_morning = (num_ef % 2) == 1  # 홀수면 아침, 짝수면 밤/낮

            if num_ef == 0:
                # 오늘 밤
                forecast_dt = base_date + timedelta(hours=21)
            else:
                forecast_dt = base_date + timedelta(days=day_offset)
                if is_morning:
                    forecast_dt = forecast_dt.replace(hour=6)
                else:
                    forecast_dt = forecast_dt.replace(hour=15)

            # 온도 파싱
            temp_str = item.get("ta", "")
            temp = None
            if temp_str and temp_str != "":
                try:
                    temp = float(temp_str)
                except ValueError:
                    pass

            # 하늘 상태 코드 변환
            wf_cd = item.get("wfCd", "")
            sky = self.WEATHER_CODE_TO_SKY.get(wf_cd, 3)

            # 풍속 등급 → 대략적인 풍속 (m/s)
            ws_it = item.get("wsIt", "")
            wind_speed = None
            if ws_it:
                try:
                    ws_level = int(ws_it)
                    # 1=약함(~4m/s), 2=보통(4~9m/s), 3=강함(9~14m/s), 4=매우강함(14m/s~)
                    wind_speed_map = {1: 2.0, 2: 6.5, 3: 11.5, 4: 16.0}
                    wind_speed = wind_speed_map.get(ws_level, 5.0)
                except ValueError:
                    pass

            result.append({
                "datetime": forecast_dt.isoformat(),
                "period": num_ef,
                "period_name": self._get_period_name(num_ef),
                "temp": temp,
                "rain_prob": item.get("rnSt"),
                "rain_type": item.get("rnYn"),  # 0=없음, 1=비, 2=비/눈, 3=눈
                "weather": item.get("wf"),  # 날씨 설명 텍스트
                "weather_code": wf_cd,
                "sky": sky,
                "cloud_cover": self._sky_to_cloud_cover(sky),
                "wind_dir1": item.get("wd1"),
                "wind_dir2": item.get("wd2"),
                "wind_speed": wind_speed
            })

        return result

    def _get_period_name(self, num_ef: int) -> str:
        """numEf 값을 한글 시점명으로 변환"""
        period_names = [
            "오늘 밤",
            "내일 아침",
            "내일 낮",
            "내일 밤",
            "모레 아침",
            "모레 낮",
            "모레 밤",
            "글피 아침",
            "글피 낮"
        ]
        if 0 <= num_ef < len(period_names):
            return period_names[num_ef]
        return f"예보 {num_ef}"

    async def _collect_from_data_go_kr(
        self,
        region_code: str,
        start_date: datetime,
        end_date: datetime,
        nx: int,
        ny: int
    ) -> Dict[str, Any]:
        """
        Collect data from data.go.kr (공공데이터포털)

        Args:
            region_code: 읍면동 코드
            start_date: 시작 날짜
            end_date: 종료 날짜
            nx: 격자 X 좌표
            ny: 격자 Y 좌표

        Returns:
            Dictionary with forecast data
        """
        base_date, base_time = self._get_base_datetime(datetime.now())

        params = {
            "serviceKey": self.api_key,
            "numOfRows": 1000,
            "pageNo": 1,
            "dataType": "JSON",
            "base_date": base_date,
            "base_time": base_time,
            "nx": nx,
            "ny": ny
        }

        response = await self._make_request(self.base_url, params)

        if response.get("response", {}).get("header", {}).get("resultCode") != "00":
            error_msg = response.get("response", {}).get("header", {}).get("resultMsg", "Unknown error")
            raise CollectorError(f"KMA API error: {error_msg}")

        items = response.get("response", {}).get("body", {}).get("items", {}).get("item", [])

        if not items:
            raise CollectorError(f"No forecast data returned for region {region_code}")

        forecast_data = self._parse_forecast_data(items, start_date, end_date)

        return {
            "source": "kma",
            "api_source": self.api_source,
            "region_code": region_code,
            "collected_at": datetime.now().isoformat(),
            "base_date": base_date,
            "base_time": base_time,
            "forecast": forecast_data
        }

    def _get_base_datetime(self, current_time: datetime) -> Tuple[str, str]:
        """Get the latest base date/time for data.go.kr API request"""
        base_times = ["0210", "0510", "0810", "1110", "1410", "1710", "2010", "2310"]
        current_hhmm = current_time.strftime("%H%M")

        base_time = "2310"
        base_date = current_time

        for bt in base_times:
            if current_hhmm >= bt:
                base_time = bt
            else:
                break

        if current_hhmm < "0210":
            base_date = current_time - timedelta(days=1)

        return base_date.strftime("%Y%m%d"), base_time

    def _parse_forecast_data(
        self,
        items: list,
        start_date: datetime,
        end_date: datetime
    ) -> list:
        """Parse data.go.kr forecast items"""
        forecast_by_time = {}

        for item in items:
            fcst_date = item.get("fcstDate")
            fcst_time = item.get("fcstTime")
            category = item.get("category")
            fcst_value = item.get("fcstValue")

            if not all([fcst_date, fcst_time, category, fcst_value]):
                continue

            try:
                fcst_datetime = datetime.strptime(f"{fcst_date}{fcst_time}", "%Y%m%d%H%M")
            except ValueError:
                continue

            if not (start_date <= fcst_datetime <= end_date + timedelta(days=1)):
                continue

            key = fcst_datetime.isoformat()

            if key not in forecast_by_time:
                forecast_by_time[key] = {"datetime": key, "data": {}}

            if category in self.FORECAST_CATEGORIES:
                forecast_by_time[key]["data"][category] = self._convert_value(category, fcst_value)

        forecast_list = sorted(forecast_by_time.values(), key=lambda x: x["datetime"])

        result = []
        for item in forecast_list:
            data = item["data"]
            result.append({
                "datetime": item["datetime"],
                "temp": data.get("TMP"),
                "humidity": data.get("REH"),
                "wind_speed": data.get("WSD"),
                "rain_prob": data.get("POP"),
                "precipitation": data.get("PCP"),
                "sky": data.get("SKY"),
                "cloud_cover": self._sky_to_cloud_cover(data.get("SKY"))
            })

        return result

    def _convert_value(self, category: str, value: str) -> Any:
        """Convert string value to appropriate type"""
        try:
            if category in ["TMP", "WSD"]:
                return float(value)
            elif category in ["REH", "POP", "SKY"]:
                return int(value)
            elif category == "PCP":
                if "없음" in value or value == "0":
                    return 0.0
                elif "미만" in value:
                    return 0.5
                else:
                    parts = value.replace("mm", "").split("~")
                    if len(parts) == 2:
                        return (float(parts[0]) + float(parts[1])) / 2
                    return float(parts[0])
        except (ValueError, IndexError):
            return value
        return value

    def _sky_to_cloud_cover(self, sky_code: Optional[int]) -> Optional[int]:
        """Convert SKY code to cloud cover percentage"""
        if sky_code is None:
            return None
        sky_mapping = {1: 20, 3: 60, 4: 90}
        return sky_mapping.get(sky_code, 50)
