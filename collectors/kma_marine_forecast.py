"""KMA (기상청) Marine Forecast Collector - 해상예보 수집기"""
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple, Literal
import logging
from .base_collector import BaseCollector, CollectorError

logger = logging.getLogger(__name__)


class KMAMarineForecastCollector(BaseCollector):
    """
    기상청 해상예보 API Collector

    지원 API 소스:
    - data.go.kr: 공공데이터포털 (VilageFcstMsgService)
    - apihub.kma.go.kr: 기상청 API 허브 (VilageFcstMsgService/getWthrMarFcst)
    """

    # API 소스별 기본 URL
    API_SOURCES = {
        "data.go.kr": "http://apis.data.go.kr/1360000/VilageFcstMsgService/getWthrMarFcst",
        "apihub.kma.go.kr": "https://apihub.kma.go.kr/api/typ02/openApi/VilageFcstMsgService/getWthrMarFcst"
    }

    # 해상예보구역 코드
    MARINE_ZONE_CODES = {
        "12A10000": "서해북부",
        "12A20000": "서해중부",
        "12A30000": "서해남부",
        "12B10000": "남해서부",
        "12B20000": "남해동부",
        "12C10000": "동해남부",
        "12C20000": "동해중부",
        "12C30000": "동해북부",
        "12D10000": "제주도"
    }

    # 하늘 상태 코드 매핑 (육상예보와 동일)
    WEATHER_CODE_TO_SKY = {
        "DB01": 1,  # 맑음
        "DB03": 3,  # 구름많음
        "DB04": 4,  # 흐림
    }

    # SKY 코드 직접 매핑 (1=맑음, 3=구름많음, 4=흐림)
    SKY_CODE_MAPPING = {
        1: 1,  # 맑음
        3: 3,  # 구름많음
        4: 4   # 흐림
    }

    # 파고(WAV) 등급 → 수치 변환 (미터)
    WAVE_HEIGHT_MAPPING = {
        1: 0.25,   # 0~0.5m
        2: 0.75,   # 0.5~1.0m
        3: 1.5,    # 1.0~2.0m
        4: 2.5,    # 2.0~3.0m
        5: 3.5     # 3.0m 이상
    }

    # 파고 범위 설명
    WAVE_HEIGHT_DESCRIPTION = {
        1: "0~0.5m",
        2: "0.5~1.0m",
        3: "1.0~2.0m",
        4: "2.0~3.0m",
        5: "3.0m 이상"
    }

    def __init__(
        self,
        api_key: str,
        api_source: Literal["data.go.kr", "apihub.kma.go.kr"] = "apihub.kma.go.kr"
    ):
        """
        Initialize KMA Marine Forecast Collector

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
        logger.info(f"KMAMarineForecastCollector initialized with source: {api_source}")

    async def collect(
        self,
        marine_zone_code: str,
        date_range: Optional[Tuple[datetime, datetime]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Collect marine forecast data from KMA

        Args:
            marine_zone_code: 해상예보구역 코드 (예: 12A10000)
            date_range: (start_date, end_date) tuple (현재는 사용되지 않음)
            **kwargs: Additional parameters

        Returns:
            Dictionary with marine forecast data

        Raises:
            CollectorError: If collection fails
        """
        # 해상예보구역 코드 검증
        if marine_zone_code not in self.MARINE_ZONE_CODES:
            raise CollectorError(
                f"Invalid marine zone code: {marine_zone_code}. "
                f"Valid codes: {list(self.MARINE_ZONE_CODES.keys())}"
            )

        # Default to D-day ~ D+2
        if date_range is None:
            start_date = datetime.now()
            end_date = start_date + timedelta(days=2)
        else:
            start_date, end_date = date_range

        try:
            if self.api_source == "data.go.kr":
                return await self._collect_from_data_go_kr(
                    marine_zone_code, start_date, end_date
                )
            elif self.api_source == "apihub.kma.go.kr":
                return await self._collect_from_apihub(
                    marine_zone_code, start_date, end_date
                )
            else:
                raise CollectorError(f"Unsupported API source: {self.api_source}")

        except Exception as e:
            logger.error(f"Failed to collect KMA marine data for {marine_zone_code}: {str(e)}")
            raise CollectorError(f"KMA marine collection failed: {str(e)}") from e

    async def _collect_from_apihub(
        self,
        marine_zone_code: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Collect data from apihub.kma.go.kr (기상청 API 허브)
        해상예보 통보문 조회 API 사용

        Args:
            marine_zone_code: 해상예보구역 코드
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            Dictionary with marine forecast data
        """
        params = {
            "pageNo": 1,
            "numOfRows": 20,
            "dataType": "JSON",
            "regId": marine_zone_code,
            "authKey": self.api_key
        }

        response = await self._make_request(self.base_url, params)

        # API 응답 확인
        header = response.get("response", {}).get("header", {})
        result_code = header.get("resultCode")

        if result_code == "03":
            # NO_DATA - 빈 결과 반환
            logger.warning(f"No data available for marine zone {marine_zone_code}")
            return {
                "source": "kma_marine",
                "api_source": self.api_source,
                "marine_zone_code": marine_zone_code,
                "zone_name": self.MARINE_ZONE_CODES[marine_zone_code],
                "collected_at": datetime.now().isoformat(),
                "forecast": []
            }

        if result_code != "00":
            error_msg = header.get("resultMsg", "Unknown error")
            raise CollectorError(f"KMA API Hub error: {error_msg} (code: {result_code})")

        items = response.get("response", {}).get("body", {}).get("items", {}).get("item", [])

        if not items:
            logger.warning(f"Empty forecast data for marine zone {marine_zone_code}")
            return {
                "source": "kma_marine",
                "api_source": self.api_source,
                "marine_zone_code": marine_zone_code,
                "zone_name": self.MARINE_ZONE_CODES[marine_zone_code],
                "collected_at": datetime.now().isoformat(),
                "forecast": []
            }

        # 단일 항목인 경우 리스트로 변환
        if isinstance(items, dict):
            items = [items]

        forecast_data = self._parse_apihub_data(items, start_date, end_date)

        return {
            "source": "kma_marine",
            "api_source": self.api_source,
            "marine_zone_code": marine_zone_code,
            "zone_name": self.MARINE_ZONE_CODES[marine_zone_code],
            "collected_at": datetime.now().isoformat(),
            "announce_time": items[0].get("announceTime") if items else None,
            "forecast": forecast_data
        }

    async def _collect_from_data_go_kr(
        self,
        marine_zone_code: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Collect data from data.go.kr (공공데이터포털)

        Args:
            marine_zone_code: 해상예보구역 코드
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            Dictionary with marine forecast data
        """
        params = {
            "serviceKey": self.api_key,
            "numOfRows": 20,
            "pageNo": 1,
            "dataType": "JSON",
            "regId": marine_zone_code
        }

        response = await self._make_request(self.base_url, params)

        # API 응답 확인
        header = response.get("response", {}).get("header", {})
        result_code = header.get("resultCode")

        if result_code != "00":
            error_msg = header.get("resultMsg", "Unknown error")
            raise CollectorError(f"KMA API error: {error_msg}")

        items = response.get("response", {}).get("body", {}).get("items", {}).get("item", [])

        if not items:
            logger.warning(f"Empty forecast data for marine zone {marine_zone_code}")
            return {
                "source": "kma_marine",
                "api_source": self.api_source,
                "marine_zone_code": marine_zone_code,
                "zone_name": self.MARINE_ZONE_CODES[marine_zone_code],
                "collected_at": datetime.now().isoformat(),
                "forecast": []
            }

        # 단일 항목인 경우 리스트로 변환
        if isinstance(items, dict):
            items = [items]

        forecast_data = self._parse_apihub_data(items, start_date, end_date)

        return {
            "source": "kma_marine",
            "api_source": self.api_source,
            "marine_zone_code": marine_zone_code,
            "zone_name": self.MARINE_ZONE_CODES[marine_zone_code],
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
        Parse API Hub response data (VilageFcstMsgService/getWthrMarFcst)

        해상예보 응답 필드:
        - announceTime: 발표시각 (202601301700)
        - numEf: 예보 시점 (0=오늘밤, 1=내일아침, 2=내일낮, ...)
        - wf: 날씨 설명 (맑음, 구름많음, 흐림 등)
        - wfCd: 날씨 코드 (DB01=맑음, DB03=구름많음, DB04=흐림)
        - wav: 파고 등급 (1~5)
        - wd1, wd2: 풍향
        - ws: 풍속 (m/s)

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

            # 하늘 상태 코드 변환
            wf_cd = item.get("wfCd", "")
            sky = self.WEATHER_CODE_TO_SKY.get(wf_cd, 3)

            # 파고(WAV) 파싱
            wav_str = item.get("wav", "")
            wave_height = None
            wave_height_level = None
            wave_height_desc = None

            if wav_str and wav_str != "":
                try:
                    wav_level = int(wav_str)
                    if 1 <= wav_level <= 5:
                        wave_height_level = wav_level
                        wave_height = self.WAVE_HEIGHT_MAPPING.get(wav_level)
                        wave_height_desc = self.WAVE_HEIGHT_DESCRIPTION.get(wav_level)
                except ValueError:
                    pass

            # 풍속 파싱
            ws_str = item.get("ws", "")
            wind_speed = None
            if ws_str and ws_str != "":
                try:
                    wind_speed = float(ws_str)
                except ValueError:
                    pass

            result.append({
                "datetime": forecast_dt.isoformat(),
                "period": num_ef,
                "period_name": self._get_period_name(num_ef),
                "weather": item.get("wf"),  # 날씨 설명 텍스트
                "weather_code": wf_cd,
                "sky": sky,
                "cloud_cover": self._sky_to_cloud_cover(sky),
                "wave_height": wave_height,  # 파고 수치 (m)
                "wave_height_level": wave_height_level,  # 파고 등급 (1~5)
                "wave_height_desc": wave_height_desc,  # 파고 범위 설명
                "wind_dir1": item.get("wd1"),  # 풍향 1
                "wind_dir2": item.get("wd2"),  # 풍향 2
                "wind_speed": wind_speed  # 풍속 (m/s)
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

    def _sky_to_cloud_cover(self, sky_code: Optional[int]) -> Optional[int]:
        """Convert SKY code to cloud cover percentage"""
        if sky_code is None:
            return None
        sky_mapping = {1: 20, 3: 60, 4: 90}
        return sky_mapping.get(sky_code, 50)
