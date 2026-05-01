"""Region data models"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Region:
    """읍면동 지역 정보"""
    region_code: str  # 법정동코드 10자리
    sido: str  # 시/도
    sigungu: str  # 시/군/구
    emd: str  # 읍/면/동
    lat: float  # 위도
    lng: float  # 경도
    is_coastal: bool = False  # 해안 지역 여부 (해안선 30km 이내)
    elevation: int = 0  # 해발 고도 (미터)
    coast_type: Optional[str] = None  # 'east', 'west', 'south' or None

    @property
    def full_name(self) -> str:
        """전체 지역명"""
        return f"{self.sido} {self.sigungu} {self.emd}"

    @property
    def is_east_coast(self) -> bool:
        return self.coast_type == 'east'

    @property
    def is_west_coast(self) -> bool:
        return self.coast_type == 'west'

    @property
    def is_south_coast(self) -> bool:
        return self.coast_type == 'south'


@dataclass
class RegionScore:
    """지역별 테마 점수"""
    region_code: str
    region_name: str
    theme_id: int
    theme_name: str
    score: float  # 0~100
    weather_summary: str  # 날씨 요약 (LLM 프롬프트용)
    factors: dict = field(default_factory=dict)  # 점수 계산에 사용된 요소들
    penalty_applied: float = 0.0  # 적용된 페널티 점수
    uncertainty_note: Optional[str] = None  # 불확실성 표기 (오메가/야광충)
    coordinates: Optional[dict] = None  # {"lat": float, "lng": float}
    forecast_datetime: Optional[str] = None  # 예보 시간

    @property
    def final_score(self) -> float:
        """페널티 적용 후 최종 점수"""
        return max(0, self.score - self.penalty_applied)

    def to_dict(self) -> dict:
        return {
            "region_code": self.region_code,
            "region_name": self.region_name,
            "theme_id": self.theme_id,
            "theme_name": self.theme_name,
            "score": self.score,
            "final_score": self.final_score,
            "weather_summary": self.weather_summary,
            "factors": self.factors,
            "penalty_applied": self.penalty_applied,
            "uncertainty_note": self.uncertainty_note,
            "coordinates": self.coordinates,
            "forecast_datetime": self.forecast_datetime
        }
