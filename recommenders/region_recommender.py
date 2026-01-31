"""RegionRecommender - 시도별/전국 테마 추천 시스템"""
from typing import List, Dict, Optional
from dataclasses import dataclass
from pathlib import Path
import json
from collections import defaultdict
import logging

from config.settings import CACHE_DIR, NATIONAL_TOP, REGIONS_PER_SIDO_TOP, THEME_IDS

logger = logging.getLogger(__name__)


@dataclass
class RegionScore:
    """지역 점수 데이터 클래스"""
    region_code: str
    region_name: str
    sido: str
    sigungu: str
    emd: str
    score: float
    lat: float
    lng: float
    weather_summary: Dict
    forecast_datetime: str
    theme_id: int

    def to_dict(self) -> Dict:
        return {
            "region_code": self.region_code,
            "region_name": self.region_name,
            "sido": self.sido,
            "sigungu": self.sigungu,
            "emd": self.emd,
            "score": self.score,
            "lat": self.lat,
            "lng": self.lng,
            "weather_summary": self.weather_summary,
            "forecast_datetime": self.forecast_datetime,
            "theme_id": self.theme_id,
        }


class RegionRecommender:
    """지역 추천 시스템

    전국 읍/면/동 캐시 JSON을 로드하여 테마별 점수 기반 추천을 제공합니다.

    처리 흐름:
    1. 전국 읍/면/동 캐시 JSON 로드 (약 3,500개)
    2. 각 지역별 8개 테마 점수 계산 (0~100점)
    3. 시/도 단위 그룹핑 후 테마별 TOP 1 추출
    4. 전국 테마별 TOP 10 리스트 생성
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        """초기화

        Args:
            cache_dir: JSON 캐시 디렉토리 경로 (기본값: settings.CACHE_DIR)
        """
        self.cache_dir = cache_dir or CACHE_DIR
        self.scores_cache: Dict[int, List[RegionScore]] = {}

    async def _load_region_scores(self, theme_id: int) -> List[RegionScore]:
        """특정 테마의 모든 지역 점수 로드

        Args:
            theme_id: 테마 ID (1~8)

        Returns:
            전체 지역의 점수 리스트

        Note:
            실제 구현에서는 scorers 모듈을 통해 점수를 계산하거나
            캐시된 점수 파일을 로드합니다.
            현재는 구조 정의를 위한 스켈레톤입니다.
        """
        # TODO: scorers 모듈 연동 후 실제 점수 계산 로직 추가
        # 현재는 빈 리스트 반환
        logger.info(f"Loading scores for theme_id={theme_id}")

        # 캐시 확인
        if theme_id in self.scores_cache:
            return self.scores_cache[theme_id]

        # 실제 구현에서는 여기서 JSON 파일들을 읽고 점수를 계산
        scores = []
        # scores = await self._calculate_scores_from_cache(theme_id)

        self.scores_cache[theme_id] = scores
        return scores

    async def get_sido_top(self, theme_id: int, sido: str) -> List[RegionScore]:
        """시/도별 테마 TOP 1 추출

        Args:
            theme_id: 테마 ID (1~8)
            sido: 시/도 이름 (예: "서울특별시", "경기도")

        Returns:
            해당 시/도의 TOP 1 지역 점수 (리스트 형태)
        """
        all_scores = await self._load_region_scores(theme_id)

        # 해당 시/도 필터링
        sido_scores = [s for s in all_scores if s.sido == sido]

        if not sido_scores:
            logger.warning(f"No scores found for sido={sido}, theme_id={theme_id}")
            return []

        # 점수 내림차순 정렬 후 TOP N
        sido_scores.sort(key=lambda x: x.score, reverse=True)
        return sido_scores[:REGIONS_PER_SIDO_TOP]

    async def get_national_top(
        self,
        theme_id: int,
        limit: Optional[int] = None
    ) -> List[RegionScore]:
        """전국 테마별 TOP 10 추출

        Args:
            theme_id: 테마 ID (1~8)
            limit: 반환할 개수 (기본값: settings.NATIONAL_TOP)

        Returns:
            전국 TOP N 지역 점수 리스트
        """
        limit = limit or NATIONAL_TOP
        all_scores = await self._load_region_scores(theme_id)

        if not all_scores:
            logger.warning(f"No scores found for theme_id={theme_id}")
            return []

        # 점수 내림차순 정렬 후 TOP N
        all_scores.sort(key=lambda x: x.score, reverse=True)
        return all_scores[:limit]

    async def get_all_recommendations(self) -> Dict[int, List[RegionScore]]:
        """8개 테마 전체 추천 결과

        Returns:
            테마 ID를 키로 하는 전국 TOP N 딕셔너리
            {theme_id: [RegionScore, ...], ...}
        """
        recommendations = {}

        for theme_id in THEME_IDS.keys():
            theme_name = THEME_IDS[theme_id]
            logger.info(f"Generating recommendations for theme: {theme_name} (ID: {theme_id})")

            top_regions = await self.get_national_top(theme_id)
            recommendations[theme_id] = top_regions

        return recommendations

    async def get_sido_summary(self, theme_id: int) -> Dict[str, List[RegionScore]]:
        """전국 모든 시/도별 테마 TOP 1 추출

        Args:
            theme_id: 테마 ID (1~8)

        Returns:
            시/도를 키로 하는 TOP 1 딕셔너리
            {sido: [RegionScore], ...}
        """
        all_scores = await self._load_region_scores(theme_id)

        # 시/도별 그룹핑
        sido_groups: Dict[str, List[RegionScore]] = defaultdict(list)
        for score in all_scores:
            sido_groups[score.sido].append(score)

        # 각 시/도별 TOP 1 추출
        sido_summary = {}
        for sido, scores in sido_groups.items():
            scores.sort(key=lambda x: x.score, reverse=True)
            sido_summary[sido] = scores[:REGIONS_PER_SIDO_TOP]

        return sido_summary

    def clear_cache(self):
        """메모리 캐시 초기화"""
        self.scores_cache.clear()
        logger.info("Scores cache cleared")

    async def cache_theme_scores(self, theme_id: int, scores: List[Dict]) -> None:
        """테마별 점수 캐시 저장

        Args:
            theme_id: 테마 ID (1~8)
            scores: 점수 딕셔너리 리스트
        """
        # Convert dicts to RegionScore objects
        region_scores = []
        for score_dict in scores:
            try:
                region_score = RegionScore(
                    region_code=score_dict.get("region_code", ""),
                    region_name=score_dict.get("region_name", ""),
                    sido=score_dict.get("sido", self._extract_sido(score_dict.get("region_name", ""))),
                    sigungu=score_dict.get("sigungu", ""),
                    emd=score_dict.get("emd", ""),
                    score=score_dict.get("score", 0.0),
                    lat=score_dict.get("lat", 0.0),
                    lng=score_dict.get("lng", 0.0),
                    weather_summary=score_dict.get("factors", {}),
                    forecast_datetime=score_dict.get("forecast_datetime", ""),
                    theme_id=theme_id,
                )
                region_scores.append(region_score)
            except Exception as e:
                logger.warning(f"Failed to create RegionScore: {e}")
                continue

        self.scores_cache[theme_id] = region_scores
        logger.info(f"Cached {len(region_scores)} scores for theme_id={theme_id}")

        # Optionally persist to disk
        await self._persist_scores(theme_id, region_scores)

    def _extract_sido(self, region_name: str) -> str:
        """지역명에서 시/도 추출"""
        if not region_name:
            return ""
        parts = region_name.split()
        return parts[0] if parts else ""

    async def _persist_scores(self, theme_id: int, scores: List[RegionScore]) -> None:
        """점수를 JSON 파일로 저장"""
        from datetime import datetime
        import aiofiles

        scores_dir = self.cache_dir / "scores"
        scores_dir.mkdir(parents=True, exist_ok=True)

        today = datetime.now().strftime("%Y-%m-%d")
        filename = scores_dir / f"{today}_theme_{theme_id}.json"

        scores_data = [s.to_dict() for s in scores]

        try:
            async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(scores_data, ensure_ascii=False, indent=2))
            logger.info(f"Persisted scores to {filename}")
        except Exception as e:
            logger.error(f"Failed to persist scores: {e}")
