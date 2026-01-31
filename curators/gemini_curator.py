"""GeminiCurator - Gemini 1.5 Flash를 활용한 추천 문구 생성"""
from typing import Optional
import logging
import asyncio
from datetime import datetime

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from config.settings import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_DAILY_LIMIT, THEME_IDS

logger = logging.getLogger(__name__)


class GeminiCurator:
    """Gemini 1.5 Flash 기반 큐레이션 문구 생성기

    무료 할당량: 1,500 요청/일
    최적화 전략:
    - TOP N만 호출 (테마별 TOP 10 x 8테마 = 80 호출/일)
    - 실제 사용량: ~100 호출/일 (여유 확보)

    Note:
        Gemini API는 google-generativeai 라이브러리 사용
        비동기 처리로 동시 호출 성능 최적화
    """

    def __init__(self, api_key: Optional[str] = None):
        """초기화

        Args:
            api_key: Gemini API 키 (기본값: settings.GEMINI_API_KEY)
        """
        self.api_key = api_key or GEMINI_API_KEY
        self.model_name = GEMINI_MODEL
        self.daily_limit = GEMINI_DAILY_LIMIT
        self.call_count = 0
        self.last_reset = datetime.now().date()

        if not self.api_key:
            logger.warning("Gemini API key not configured")
            self.model = None
        elif genai is None:
            logger.error("google-generativeai library not installed")
            self.model = None
        else:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            logger.info(f"Gemini curator initialized with model: {self.model_name}")

    def _check_rate_limit(self) -> bool:
        """일일 호출 제한 확인

        Returns:
            호출 가능 여부 (True: 가능, False: 제한 초과)
        """
        # 날짜 변경 시 카운터 리셋
        today = datetime.now().date()
        if today != self.last_reset:
            self.call_count = 0
            self.last_reset = today
            logger.info("Daily API call counter reset")

        if self.call_count >= self.daily_limit:
            logger.warning(
                f"Daily API limit reached: {self.call_count}/{self.daily_limit}"
            )
            return False

        return True

    def _build_prompt(
        self,
        region_name: str,
        theme_name: str,
        score: float,
        weather_summary: dict
    ) -> str:
        """큐레이션 프롬프트 생성

        Args:
            region_name: 지역명 (예: "서울특별시 강남구 역삼동")
            theme_name: 테마명 (예: "일출", "은하수")
            score: 점수 (0~100)
            weather_summary: 날씨 요약 정보

        Returns:
            Gemini에 전달할 프롬프트
        """
        prompt = f"""당신은 풍경사진 출사지 큐레이터입니다.

지역: {region_name}
테마: {theme_name}
점수: {score:.1f}점

날씨 조건:
- 기온: {weather_summary.get('temp', 'N/A')}°C
- 구름량: {weather_summary.get('cloud', 'N/A')}%
- 강수확률: {weather_summary.get('rain_prob', 'N/A')}%
- 미세먼지(PM2.5): {weather_summary.get('pm25', 'N/A')}

이 장소가 {theme_name} 촬영에 왜 좋은지 2-3문장으로 설명해주세요.
날씨 조건과 촬영 테마를 연결하여 구체적이고 매력적으로 작성하세요.
단, 과장하지 말고 실제 조건에 기반한 현실적인 추천을 해주세요.
"""

        # 오메가/야광충 테마는 불확실성 경고 추가
        if "오메가" in theme_name or "야광충" in theme_name:
            prompt += "\n주의: 이 테마는 불확실성이 높으므로 '가능성'이라는 표현을 사용하고, 보장할 수 없음을 언급하세요."

        return prompt

    async def generate_curation(
        self,
        region_name: str,
        theme_name: str,
        score: float,
        weather_summary: dict
    ) -> Optional[str]:
        """자연어 추천 문구 생성

        Args:
            region_name: 지역명
            theme_name: 테마명
            score: 점수
            weather_summary: 날씨 요약 정보

        Returns:
            생성된 추천 문구 (실패 시 None)
        """
        if self.model is None:
            logger.error("Gemini model not initialized")
            return None

        if not self._check_rate_limit():
            logger.error("API rate limit exceeded")
            return None

        try:
            prompt = self._build_prompt(region_name, theme_name, score, weather_summary)

            # 비동기 호출
            response = await asyncio.to_thread(
                self.model.generate_content, prompt
            )

            self.call_count += 1
            logger.info(
                f"Gemini API call successful ({self.call_count}/{self.daily_limit}): "
                f"{region_name} - {theme_name}"
            )

            return response.text.strip()

        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            return None

    async def generate_batch_curations(
        self,
        regions_data: list
    ) -> dict:
        """배치 큐레이션 문구 생성

        Args:
            regions_data: 지역 정보 리스트
                [{region_name, theme_name, score, weather_summary}, ...]

        Returns:
            지역별 큐레이션 결과
            {region_code: curation_text, ...}
        """
        tasks = []
        region_codes = []

        for data in regions_data:
            task = self.generate_curation(
                region_name=data["region_name"],
                theme_name=data["theme_name"],
                score=data["score"],
                weather_summary=data["weather_summary"]
            )
            tasks.append(task)
            region_codes.append(data.get("region_code", ""))

        # 동시 실행
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 결과 매핑
        curations = {}
        for region_code, result in zip(region_codes, results):
            if isinstance(result, Exception):
                logger.error(f"Curation failed for {region_code}: {result}")
                curations[region_code] = None
            else:
                curations[region_code] = result

        return curations

    def get_usage_stats(self) -> dict:
        """API 사용량 통계 조회

        Returns:
            사용량 정보 딕셔너리
        """
        return {
            "call_count": self.call_count,
            "daily_limit": self.daily_limit,
            "remaining": self.daily_limit - self.call_count,
            "last_reset": self.last_reset.isoformat(),
        }
