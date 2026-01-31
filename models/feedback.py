"""Feedback data models"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Feedback:
    """사용자 피드백 데이터"""
    id: Optional[int] = None
    region_code: str = ""
    theme_id: int = 0
    score_success: bool = False  # 촬영 성공 여부
    actual_weather: dict = field(default_factory=dict)  # 실제 기상 (구름, 시정 등)
    rating: int = 0  # 1~5점
    comment: Optional[str] = None  # 자유 의견
    photo_url: Optional[str] = None  # 증빙 사진 URL
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "region_code": self.region_code,
            "theme_id": self.theme_id,
            "score_success": self.score_success,
            "actual_weather": self.actual_weather,
            "rating": self.rating,
            "comment": self.comment,
            "photo_url": self.photo_url,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class ScorePenalty:
    """점수 페널티 데이터"""
    region_code: str
    theme_id: int
    penalty_score: int = 0  # 페널티 점수 (음수)
    expires_at: Optional[datetime] = None  # 만료 시각
    reason: str = ""  # 페널티 사유

    @property
    def is_active(self) -> bool:
        """페널티 활성 여부"""
        if self.expires_at is None:
            return False
        return datetime.now() < self.expires_at

    def to_dict(self) -> dict:
        return {
            "region_code": self.region_code,
            "theme_id": self.theme_id,
            "penalty_score": self.penalty_score,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "reason": self.reason,
            "is_active": self.is_active
        }
