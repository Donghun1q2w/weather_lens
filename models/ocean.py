"""Ocean data models"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class TideData:
    """조석 데이터 (만조/간조)"""
    datetime: datetime
    tide_type: str  # 'high' or 'low'
    height: float  # 조위 (cm)


@dataclass
class WaveData:
    """파고 데이터"""
    datetime: datetime
    significant_height: float  # 유의파고 (m)
    period: float  # 파주기 (초)


@dataclass
class OceanData:
    """해양 관측 데이터"""
    station_id: str
    station_name: str
    region_code: Optional[str] = None  # 매핑된 읍면동 코드
    distance_km: float = 0.0  # 읍면동 중심까지 거리

    # 조석 데이터
    tides: List[TideData] = field(default_factory=list)

    # 파고 데이터
    waves: List[WaveData] = field(default_factory=list)

    # 수온 데이터
    sea_temp: Optional[float] = None  # 표층 수온 (°C)
    sea_temp_datetime: Optional[datetime] = None

    # 특보 상태
    storm_warning: bool = False  # 풍랑특보 여부

    def get_next_low_tide(self, after: datetime) -> Optional[TideData]:
        """다음 간조 시각 조회"""
        for tide in sorted(self.tides, key=lambda t: t.datetime):
            if tide.tide_type == 'low' and tide.datetime > after:
                return tide
        return None

    def get_next_high_tide(self, after: datetime) -> Optional[TideData]:
        """다음 만조 시각 조회"""
        for tide in sorted(self.tides, key=lambda t: t.datetime):
            if tide.tide_type == 'high' and tide.datetime > after:
                return tide
        return None

    def get_current_wave(self) -> Optional[WaveData]:
        """현재 파고 데이터"""
        if not self.waves:
            return None
        now = datetime.now()
        # 현재 시각에 가장 가까운 데이터
        return min(self.waves, key=lambda w: abs((w.datetime - now).total_seconds()))

    def to_dict(self) -> dict:
        return {
            "station_id": self.station_id,
            "station_name": self.station_name,
            "region_code": self.region_code,
            "distance_km": self.distance_km,
            "tides": [
                {
                    "datetime": t.datetime.isoformat(),
                    "tide_type": t.tide_type,
                    "height": t.height
                }
                for t in self.tides
            ],
            "waves": [
                {
                    "datetime": w.datetime.isoformat(),
                    "significant_height": w.significant_height,
                    "period": w.period
                }
                for w in self.waves
            ],
            "sea_temp": self.sea_temp,
            "sea_temp_datetime": self.sea_temp_datetime.isoformat() if self.sea_temp_datetime else None,
            "storm_warning": self.storm_warning
        }


@dataclass
class OceanRegionMapping:
    """해양 관측소-읍면동 매핑"""
    region_code: str
    region_name: str
    ocean_station_id: str
    ocean_station_name: str
    distance_km: float
    is_coastal: bool = False  # 해안선 30km 이내
