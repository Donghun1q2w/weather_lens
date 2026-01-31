"""Weather data models"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class WeatherValue:
    """Single weather measurement with multi-source support"""
    kma: Optional[float] = None  # 기상청 값
    openmeteo: Optional[float] = None  # Open-Meteo 값
    avg: Optional[float] = None  # 가중 평균값
    deviation_flag: bool = False  # 편차 경고 플래그

    def calculate_weighted_average(self, kma_weight: float = 0.6, threshold: float = 5.0) -> None:
        """가중 평균 계산 및 편차 플래그 설정"""
        if self.kma is not None and self.openmeteo is not None:
            openmeteo_weight = 1.0 - kma_weight
            self.avg = (self.kma * kma_weight) + (self.openmeteo * openmeteo_weight)
            self.deviation_flag = abs(self.kma - self.openmeteo) > threshold
        elif self.kma is not None:
            self.avg = self.kma
        elif self.openmeteo is not None:
            self.avg = self.openmeteo


@dataclass
class WeatherData:
    """날씨 데이터 (특정 시점)"""
    datetime: datetime
    temp: WeatherValue = field(default_factory=WeatherValue)
    humidity: WeatherValue = field(default_factory=WeatherValue)
    wind_speed: WeatherValue = field(default_factory=WeatherValue)
    cloud_cover: WeatherValue = field(default_factory=WeatherValue)
    rain_prob: WeatherValue = field(default_factory=WeatherValue)
    precipitation: WeatherValue = field(default_factory=WeatherValue)
    pm25: Optional[float] = None  # 에어코리아 단일 소스
    pm10: Optional[float] = None
    visibility: Optional[float] = None
    sunrise: Optional[str] = None
    sunset: Optional[str] = None

    def calculate_all_averages(self, kma_weight: float = 0.6, threshold: float = 5.0) -> None:
        """모든 필드의 가중 평균 계산"""
        for field_name in ['temp', 'humidity', 'wind_speed', 'cloud_cover', 'rain_prob', 'precipitation']:
            value: WeatherValue = getattr(self, field_name)
            value.calculate_weighted_average(kma_weight, threshold)


@dataclass
class ForecastData:
    """지역 예보 데이터"""
    region_code: str
    region_name: str
    coordinates: dict  # {"lat": float, "lng": float}
    updated_at: datetime
    forecast: list[WeatherData] = field(default_factory=list)
    ocean_station_id: Optional[str] = None

    def to_dict(self) -> dict:
        """JSON 직렬화용 dict 변환"""
        return {
            "region_code": self.region_code,
            "region_name": self.region_name,
            "coordinates": self.coordinates,
            "updated_at": self.updated_at.isoformat(),
            "forecast": [
                {
                    "datetime": w.datetime.isoformat(),
                    "temp": {
                        "kma": w.temp.kma,
                        "openmeteo": w.temp.openmeteo,
                        "avg": w.temp.avg,
                        "deviation_flag": w.temp.deviation_flag
                    },
                    "cloud": {
                        "kma": w.cloud_cover.kma,
                        "openmeteo": w.cloud_cover.openmeteo,
                        "avg": w.cloud_cover.avg
                    },
                    "rain_prob": {
                        "kma": w.rain_prob.kma,
                        "openmeteo": w.rain_prob.openmeteo,
                        "avg": w.rain_prob.avg
                    },
                    "pm25": w.pm25,
                    "sunrise": w.sunrise,
                    "sunset": w.sunset
                }
                for w in self.forecast
            ],
            "ocean_station_id": self.ocean_station_id
        }
