"""Theme-specific Scorers for PhotoSpot Korea - 8 Photography Themes"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from scorers.base_scorer import BaseScorer


# Load weights configuration
WEIGHTS_PATH = Path(__file__).parent.parent / "config" / "weights.json"
with open(WEIGHTS_PATH, 'r', encoding='utf-8') as f:
    WEIGHTS = json.load(f)['themes']


class SunriseScorer(BaseScorer):
    """Scorer for sunrise photography (일출)

    Optimal conditions:
    - Cloud cover: 30-60%
    - Rain probability: <20%
    - PM2.5: Good (< 35)
    - East coast bonus: +10 points
    """

    def __init__(self):
        super().__init__(theme_id=1, theme_name="일출")
        self.config = WEIGHTS['sunrise']

    async def calculate_score(
        self,
        weather_data: dict,
        ocean_data: Optional[dict] = None
    ) -> float:
        score = 0.0

        # Cloud cover score (30-60% optimal)
        cloud = self._safe_get(weather_data, 'cloud.avg', 50)
        cloud_score = self._calculate_range_score(
            cloud,
            self.config['cloud_cover']['min'],
            self.config['cloud_cover']['max']
        )
        score += cloud_score * self.config['cloud_cover']['weight']

        # Rain probability score (<20% optimal)
        rain_prob = self._safe_get(weather_data, 'rain_prob.avg', 50)
        rain_score = self._normalize_score(
            rain_prob,
            0,
            self.config['rain_prob']['max'],
            reverse=True
        )
        score += rain_score * self.config['rain_prob']['weight']

        # PM2.5 score (<35 optimal)
        pm25 = self._safe_get(weather_data, 'pm25', 50)
        pm25_score = self._normalize_score(
            pm25,
            0,
            self.config['pm25']['max'],
            reverse=True
        )
        score += pm25_score * self.config['pm25']['weight']

        # Visibility score (>10km optimal)
        visibility = self._safe_get(weather_data, 'visibility', 5)
        visibility_score = self._normalize_score(
            visibility,
            self.config['visibility']['min'],
            30,
            reverse=False
        )
        score += visibility_score * self.config['visibility']['weight']

        # East coast bonus
        is_east_coast = self._safe_get(weather_data, 'is_east_coast', False)
        if is_east_coast:
            score += self.config['east_coast_bonus']

        return min(100.0, max(0.0, score))


class SunriseOmegaScorer(BaseScorer):
    """Scorer for omega sunrise (일출 오메가)

    Optimal conditions:
    - Clear horizon
    - Sea temp > Air temp + 5°C
    - Wind speed < 3 m/s
    - East coast required
    - High uncertainty (actual occurrence ~30%)
    """

    def __init__(self):
        super().__init__(theme_id=2, theme_name="일출 오메가")
        self.config = WEIGHTS['sunrise_omega']
        self.uncertainty_note = self.config['uncertainty_note']

    async def calculate_score(
        self,
        weather_data: dict,
        ocean_data: Optional[dict] = None
    ) -> float:
        # East coast is mandatory
        is_east_coast = self._safe_get(weather_data, 'is_east_coast', False)
        if not is_east_coast:
            return 0.0

        score = 0.0

        # Horizon clear (low cloud cover near horizon)
        cloud = self._safe_get(weather_data, 'cloud.avg', 50)
        horizon_score = self._normalize_score(cloud, 0, 20, reverse=True)
        score += horizon_score * self.config['horizon_clear']['weight']

        # Sea temperature difference
        if ocean_data:
            sea_temp = self._safe_get(ocean_data, 'sea_temp', None)
            air_temp = self._safe_get(weather_data, 'temp.avg', None)

            if sea_temp is not None and air_temp is not None:
                temp_diff = sea_temp - air_temp
                temp_diff_score = self._normalize_score(
                    temp_diff,
                    self.config['sea_temp_diff']['min'],
                    15,
                    reverse=False
                )
                score += temp_diff_score * self.config['sea_temp_diff']['weight']
        else:
            # No ocean data available, penalize heavily
            score += 0

        # Wind speed score (<3 m/s optimal)
        wind_speed = self._safe_get(weather_data, 'wind_speed.avg', 10)
        wind_score = self._normalize_score(
            wind_speed,
            0,
            self.config['wind_speed']['max'],
            reverse=True
        )
        score += wind_score * self.config['wind_speed']['weight']

        # Remaining weight distributed
        remaining_weight = 1.0 - (
            self.config['horizon_clear']['weight'] +
            self.config['sea_temp_diff']['weight'] +
            self.config['wind_speed']['weight']
        )

        # Visibility bonus
        visibility = self._safe_get(weather_data, 'visibility', 5)
        visibility_score = self._normalize_score(visibility, 15, 30, reverse=False)
        score += visibility_score * remaining_weight

        return min(100.0, max(0.0, score))


class SunsetScorer(BaseScorer):
    """Scorer for sunset photography (일몰)

    Optimal conditions:
    - Cloud cover: 40-70%
    - Rain probability: <20%
    - PM2.5: Moderate (<50)
    - West coast bonus: +10 points
    """

    def __init__(self):
        super().__init__(theme_id=3, theme_name="일몰")
        self.config = WEIGHTS['sunset']

    async def calculate_score(
        self,
        weather_data: dict,
        ocean_data: Optional[dict] = None
    ) -> float:
        score = 0.0

        # Cloud cover score (40-70% optimal)
        cloud = self._safe_get(weather_data, 'cloud.avg', 50)
        cloud_score = self._calculate_range_score(
            cloud,
            self.config['cloud_cover']['min'],
            self.config['cloud_cover']['max']
        )
        score += cloud_score * self.config['cloud_cover']['weight']

        # Rain probability score (<20% optimal)
        rain_prob = self._safe_get(weather_data, 'rain_prob.avg', 50)
        rain_score = self._normalize_score(
            rain_prob,
            0,
            self.config['rain_prob']['max'],
            reverse=True
        )
        score += rain_score * self.config['rain_prob']['weight']

        # PM2.5 score (<50 optimal)
        pm25 = self._safe_get(weather_data, 'pm25', 50)
        pm25_score = self._normalize_score(
            pm25,
            0,
            self.config['pm25']['max'],
            reverse=True
        )
        score += pm25_score * self.config['pm25']['weight']

        # Visibility score (>10km optimal)
        visibility = self._safe_get(weather_data, 'visibility', 5)
        visibility_score = self._normalize_score(
            visibility,
            self.config['visibility']['min'],
            30,
            reverse=False
        )
        score += visibility_score * self.config['visibility']['weight']

        # West coast bonus
        is_west_coast = self._safe_get(weather_data, 'is_west_coast', False)
        if is_west_coast:
            score += self.config['west_coast_bonus']

        return min(100.0, max(0.0, score))


class SunsetOmegaScorer(BaseScorer):
    """Scorer for omega sunset (일몰 오메가)

    Same conditions as sunrise omega, but for west coast
    """

    def __init__(self):
        super().__init__(theme_id=4, theme_name="일몰 오메가")
        self.config = WEIGHTS['sunset_omega']
        self.uncertainty_note = self.config['uncertainty_note']

    async def calculate_score(
        self,
        weather_data: dict,
        ocean_data: Optional[dict] = None
    ) -> float:
        # West coast is mandatory
        is_west_coast = self._safe_get(weather_data, 'is_west_coast', False)
        if not is_west_coast:
            return 0.0

        score = 0.0

        # Horizon clear (low cloud cover near horizon)
        cloud = self._safe_get(weather_data, 'cloud.avg', 50)
        horizon_score = self._normalize_score(cloud, 0, 20, reverse=True)
        score += horizon_score * self.config['horizon_clear']['weight']

        # Sea temperature difference
        if ocean_data:
            sea_temp = self._safe_get(ocean_data, 'sea_temp', None)
            air_temp = self._safe_get(weather_data, 'temp.avg', None)

            if sea_temp is not None and air_temp is not None:
                temp_diff = sea_temp - air_temp
                temp_diff_score = self._normalize_score(
                    temp_diff,
                    self.config['sea_temp_diff']['min'],
                    15,
                    reverse=False
                )
                score += temp_diff_score * self.config['sea_temp_diff']['weight']
        else:
            score += 0

        # Wind speed score (<3 m/s optimal)
        wind_speed = self._safe_get(weather_data, 'wind_speed.avg', 10)
        wind_score = self._normalize_score(
            wind_speed,
            0,
            self.config['wind_speed']['max'],
            reverse=True
        )
        score += wind_score * self.config['wind_speed']['weight']

        # Remaining weight
        remaining_weight = 1.0 - (
            self.config['horizon_clear']['weight'] +
            self.config['sea_temp_diff']['weight'] +
            self.config['wind_speed']['weight']
        )

        # Visibility bonus
        visibility = self._safe_get(weather_data, 'visibility', 5)
        visibility_score = self._normalize_score(visibility, 15, 30, reverse=False)
        score += visibility_score * remaining_weight

        return min(100.0, max(0.0, score))


class MilkyWayScorer(BaseScorer):
    """Scorer for Milky Way photography (은하수)

    Optimal conditions:
    - Moon phase: New moon ±3 days
    - Cloud cover: <20%
    - Light pollution: Low (<3)
    - Visibility: >15km
    """

    def __init__(self):
        super().__init__(theme_id=5, theme_name="은하수")
        self.config = WEIGHTS['milky_way']

    async def calculate_score(
        self,
        weather_data: dict,
        ocean_data: Optional[dict] = None
    ) -> float:
        score = 0.0

        # Moon phase score (new moon ±3 days)
        moon_age = self._safe_get(weather_data, 'moon_age', 15)  # Days since new moon
        moon_score = self._calculate_moon_phase_score(
            moon_age,
            self.config['moon_phase']['range_days']
        )
        score += moon_score * self.config['moon_phase']['weight']

        # Cloud cover score (<20% optimal)
        cloud = self._safe_get(weather_data, 'cloud.avg', 50)
        cloud_score = self._normalize_score(
            cloud,
            0,
            self.config['cloud_cover']['max'],
            reverse=True
        )
        score += cloud_score * self.config['cloud_cover']['weight']

        # Light pollution score (lower is better)
        light_pollution = self._safe_get(weather_data, 'light_pollution', 5)
        light_score = self._normalize_score(
            light_pollution,
            0,
            self.config['light_pollution']['max'],
            reverse=True
        )
        score += light_score * self.config['light_pollution']['weight']

        # Visibility score (>15km optimal)
        visibility = self._safe_get(weather_data, 'visibility', 5)
        visibility_score = self._normalize_score(
            visibility,
            self.config['visibility']['min'],
            30,
            reverse=False
        )
        score += visibility_score * self.config['visibility']['weight']

        return min(100.0, max(0.0, score))

    def _calculate_moon_phase_score(self, moon_age: float, range_days: int) -> float:
        """Calculate score based on moon phase

        Args:
            moon_age: Days since new moon (0-29.5)
            range_days: Acceptable range around new moon

        Returns:
            float: Score (0-100)
        """
        # Handle moon cycle wrap-around (0 and ~29.5 are both new moon)
        if moon_age > 15:
            moon_age = 29.5 - moon_age

        if moon_age <= range_days:
            return 100.0
        else:
            penalty = (moon_age - range_days) * 5
            return max(0.0, 100.0 - penalty)


class BioluminescenceScorer(BaseScorer):
    """Scorer for bioluminescence photography (야광충)

    Optimal conditions:
    - Sea temperature: 18-25°C
    - Moon phase: New moon ±5 days
    - Season: April-September
    - South/East coast bonus
    - High uncertainty
    """

    def __init__(self):
        super().__init__(theme_id=6, theme_name="야광충")
        self.config = WEIGHTS['bioluminescence']
        self.uncertainty_note = self.config['uncertainty_note']

    async def calculate_score(
        self,
        weather_data: dict,
        ocean_data: Optional[dict] = None
    ) -> float:
        score = 0.0

        # Season check (April-September)
        forecast_date = self._safe_get(weather_data, 'datetime', None)
        if forecast_date:
            month = datetime.fromisoformat(forecast_date.replace('Z', '+00:00')).month
            if month not in self.config['season']['months']:
                return 0.0  # Out of season
            season_score = 100.0
        else:
            season_score = 50.0  # Unknown season

        score += season_score * self.config['season']['weight']

        # Sea temperature (18-25°C optimal)
        if ocean_data:
            sea_temp = self._safe_get(ocean_data, 'sea_temp', None)
            if sea_temp is not None:
                temp_score = self._calculate_range_score(
                    sea_temp,
                    self.config['sea_temp']['min'],
                    self.config['sea_temp']['max']
                )
                score += temp_score * self.config['sea_temp']['weight']
        else:
            # No ocean data, heavily penalize
            score += 0

        # Moon phase score (new moon ±5 days)
        moon_age = self._safe_get(weather_data, 'moon_age', 15)
        moon_score = self._calculate_moon_phase_score(
            moon_age,
            self.config['moon_phase']['range_days']
        )
        score += moon_score * self.config['moon_phase']['weight']

        # South/East coast bonus
        is_south_coast = self._safe_get(weather_data, 'is_south_coast', False)
        is_east_coast = self._safe_get(weather_data, 'is_east_coast', False)
        if is_south_coast or is_east_coast:
            score += self.config['south_east_coast_bonus']

        return min(100.0, max(0.0, score))

    def _calculate_moon_phase_score(self, moon_age: float, range_days: int) -> float:
        """Calculate score based on moon phase"""
        if moon_age > 15:
            moon_age = 29.5 - moon_age

        if moon_age <= range_days:
            return 100.0
        else:
            penalty = (moon_age - range_days) * 4
            return max(0.0, 100.0 - penalty)


class SeaLongExposureScorer(BaseScorer):
    """Scorer for sea long exposure photography (바다 장노출)

    Optimal conditions:
    - Wave height: 0.3-1.0m
    - No storm warnings
    - Low tide timing: ±2 hours
    - Wind speed: <8 m/s
    """

    def __init__(self):
        super().__init__(theme_id=7, theme_name="바다 장노출")
        self.config = WEIGHTS['sea_long_exposure']

    async def calculate_score(
        self,
        weather_data: dict,
        ocean_data: Optional[dict] = None
    ) -> float:
        score = 0.0

        # Wave height (0.3-1.0m optimal)
        if ocean_data:
            wave_height = self._safe_get(ocean_data, 'wave_height', 2.0)
            wave_score = self._calculate_range_score(
                wave_height,
                self.config['wave_height']['min'],
                self.config['wave_height']['max']
            )
            score += wave_score * self.config['wave_height']['weight']

            # Storm warning check
            has_storm_warning = self._safe_get(ocean_data, 'storm_warning', False)
            storm_score = 0.0 if has_storm_warning else 100.0
            score += storm_score * self.config['no_storm_warning']['weight']

            # Tide timing (within 2 hours of low tide)
            tide_hours_diff = self._safe_get(ocean_data, 'hours_from_low_tide', 12)
            tide_score = self._normalize_score(
                abs(tide_hours_diff),
                0,
                self.config['tide_timing']['hours_from_low_tide'],
                reverse=True
            )
            score += tide_score * self.config['tide_timing']['weight']
        else:
            # No ocean data, cannot score properly
            return 0.0

        # Wind speed (<8 m/s optimal)
        wind_speed = self._safe_get(weather_data, 'wind_speed.avg', 10)
        wind_score = self._normalize_score(
            wind_speed,
            0,
            self.config['wind_speed']['max'],
            reverse=True
        )
        score += wind_score * self.config['wind_speed']['weight']

        return min(100.0, max(0.0, score))


class SeaOfCloudsScorer(BaseScorer):
    """Scorer for sea of clouds photography (운해)

    Optimal conditions:
    - Low-land humidity: >85%
    - Temperature inversion
    - Wind speed: <3 m/s
    - Elevation: >500m
    """

    def __init__(self):
        super().__init__(theme_id=8, theme_name="운해")
        self.config = WEIGHTS['sea_of_clouds']

    async def calculate_score(
        self,
        weather_data: dict,
        ocean_data: Optional[dict] = None
    ) -> float:
        # Elevation requirement
        elevation = self._safe_get(weather_data, 'elevation', 0)
        if elevation < self.config['elevation']['min']:
            return 0.0  # Below minimum elevation

        score = 0.0

        # Low-land humidity (>85% optimal)
        humidity = self._safe_get(weather_data, 'humidity.avg', 50)
        humidity_score = self._normalize_score(
            humidity,
            self.config['low_humidity']['min'],
            100,
            reverse=False
        )
        score += humidity_score * self.config['low_humidity']['weight']

        # Temperature inversion (check if available)
        has_temp_inversion = self._safe_get(weather_data, 'temp_inversion', False)
        inversion_score = 100.0 if has_temp_inversion else 30.0
        score += inversion_score * self.config['temp_inversion']['weight']

        # Wind speed (<3 m/s optimal)
        wind_speed = self._safe_get(weather_data, 'wind_speed.avg', 10)
        wind_score = self._normalize_score(
            wind_speed,
            0,
            self.config['wind_speed']['max'],
            reverse=True
        )
        score += wind_score * self.config['wind_speed']['weight']

        # Elevation bonus (higher is better)
        elevation_score = self._normalize_score(
            elevation,
            self.config['elevation']['min'],
            1500,
            reverse=False
        )
        score += elevation_score * self.config['elevation']['weight']

        return min(100.0, max(0.0, score))


class StarTrailScorer(BaseScorer):
    """Scorer for star trail photography (별궤적)

    Optimal conditions:
    - New moon ±5 days
    - Cloud cover: <15%
    - Low light pollution
    - Wind speed: <5 m/s (for stable tripod)
    """

    def __init__(self):
        super().__init__(theme_id=9, theme_name="별궤적")
        self.config = WEIGHTS['star_trail']

    async def calculate_score(
        self,
        weather_data: dict,
        ocean_data: Optional[dict] = None
    ) -> float:
        score = 0.0

        # Moon phase score (new moon ±5 days)
        moon_age = self._safe_get(weather_data, 'moon_age', 15)
        moon_score = self._calculate_moon_phase_score(moon_age, self.config['moon_phase']['range_days'])
        score += moon_score * self.config['moon_phase']['weight']

        # Cloud cover score (<15% optimal)
        cloud = self._safe_get(weather_data, 'cloud.avg', 50)
        cloud_score = self._normalize_score(cloud, 0, self.config['cloud_cover']['max'], reverse=True)
        score += cloud_score * self.config['cloud_cover']['weight']

        # Light pollution score
        light_pollution = self._safe_get(weather_data, 'light_pollution', 5)
        light_score = self._normalize_score(light_pollution, 0, self.config['light_pollution']['max'], reverse=True)
        score += light_score * self.config['light_pollution']['weight']

        # Wind speed score (<5 m/s for stable tripod)
        wind_speed = self._safe_get(weather_data, 'wind_speed', 10)
        wind_score = self._normalize_score(wind_speed, 0, self.config['wind_speed']['max'], reverse=True)
        score += wind_score * self.config['wind_speed']['weight']

        return min(100.0, max(0.0, score))

    def _calculate_moon_phase_score(self, moon_age: float, range_days: int) -> float:
        if moon_age > 15:
            moon_age = 29.5 - moon_age
        if moon_age <= range_days:
            return 100.0
        else:
            penalty = (moon_age - range_days) * 5
            return max(0.0, 100.0 - penalty)


class NightCityscapeScorer(BaseScorer):
    """Scorer for night cityscape photography (야경)

    Optimal conditions:
    - Cloud cover: <50%
    - Rain probability: <10%
    - Good visibility: >10km
    - Wind speed: <10 m/s
    """

    def __init__(self):
        super().__init__(theme_id=10, theme_name="야경")
        self.config = WEIGHTS['night_cityscape']

    async def calculate_score(
        self,
        weather_data: dict,
        ocean_data: Optional[dict] = None
    ) -> float:
        score = 0.0

        # Cloud cover score
        cloud = self._safe_get(weather_data, 'cloud.avg', 50)
        cloud_score = self._normalize_score(cloud, 0, self.config['cloud_cover']['max'], reverse=True)
        score += cloud_score * self.config['cloud_cover']['weight']

        # Rain probability
        rain_prob = self._safe_get(weather_data, 'rain_prob.avg', 50)
        rain_score = self._normalize_score(rain_prob, 0, self.config['rain_prob']['max'], reverse=True)
        score += rain_score * self.config['rain_prob']['weight']

        # Visibility
        visibility = self._safe_get(weather_data, 'visibility', 5)
        visibility_score = self._normalize_score(visibility, self.config['visibility']['min'], 30, reverse=False)
        score += visibility_score * self.config['visibility']['weight']

        # Wind speed
        wind_speed = self._safe_get(weather_data, 'wind_speed', 10)
        wind_score = self._normalize_score(wind_speed, 0, self.config['wind_speed']['max'], reverse=True)
        score += wind_score * self.config['wind_speed']['weight']

        return min(100.0, max(0.0, score))


class FogLandscapeScorer(BaseScorer):
    """Scorer for fog landscape photography (안개)

    Optimal conditions:
    - High humidity: >90%
    - Large day-night temperature difference
    - Very low wind: <2 m/s
    - Low rain probability
    """

    def __init__(self):
        super().__init__(theme_id=11, theme_name="안개")
        self.config = WEIGHTS['fog_landscape']

    async def calculate_score(
        self,
        weather_data: dict,
        ocean_data: Optional[dict] = None
    ) -> float:
        score = 0.0

        # Humidity score (>90% optimal)
        humidity = self._safe_get(weather_data, 'humidity', 50)
        humidity_score = self._normalize_score(humidity, self.config['humidity']['min'], 100, reverse=False)
        score += humidity_score * self.config['humidity']['weight']

        # Temperature difference (day-night)
        temp_diff = self._safe_get(weather_data, 'temp_diff_day_night', 5)
        temp_score = self._normalize_score(temp_diff, self.config['temp_diff_day_night']['min'], 15, reverse=False)
        score += temp_score * self.config['temp_diff_day_night']['weight']

        # Wind speed (<2 m/s)
        wind_speed = self._safe_get(weather_data, 'wind_speed', 10)
        wind_score = self._normalize_score(wind_speed, 0, self.config['wind_speed']['max'], reverse=True)
        score += wind_score * self.config['wind_speed']['weight']

        # Rain probability
        rain_prob = self._safe_get(weather_data, 'rain_prob.avg', 50)
        rain_score = self._normalize_score(rain_prob, 0, self.config['rain_prob']['max'], reverse=True)
        score += rain_score * self.config['rain_prob']['weight']

        return min(100.0, max(0.0, score))


class ReflectionScorer(BaseScorer):
    """Scorer for reflection photography (반영)

    Optimal conditions:
    - Very low wind: <2 m/s (calm water surface)
    - Low rain probability
    - Some clouds for interesting sky
    - Good visibility
    """

    def __init__(self):
        super().__init__(theme_id=12, theme_name="반영")
        self.config = WEIGHTS['reflection']

    async def calculate_score(
        self,
        weather_data: dict,
        ocean_data: Optional[dict] = None
    ) -> float:
        score = 0.0

        # Wind speed (most critical - <2 m/s for calm water)
        wind_speed = self._safe_get(weather_data, 'wind_speed', 10)
        wind_score = self._normalize_score(wind_speed, 0, self.config['wind_speed']['max'], reverse=True)
        score += wind_score * self.config['wind_speed']['weight']

        # Rain probability
        rain_prob = self._safe_get(weather_data, 'rain_prob.avg', 50)
        rain_score = self._normalize_score(rain_prob, 0, self.config['rain_prob']['max'], reverse=True)
        score += rain_score * self.config['rain_prob']['weight']

        # Cloud cover (some clouds for interesting sky)
        cloud = self._safe_get(weather_data, 'cloud.avg', 50)
        cloud_score = self._calculate_range_score(cloud, self.config['cloud_cover']['min'], self.config['cloud_cover']['max'])
        score += cloud_score * self.config['cloud_cover']['weight']

        # Visibility
        visibility = self._safe_get(weather_data, 'visibility', 5)
        visibility_score = self._normalize_score(visibility, self.config['visibility']['min'], 30, reverse=False)
        score += visibility_score * self.config['visibility']['weight']

        return min(100.0, max(0.0, score))


class GoldenHourScorer(BaseScorer):
    """Scorer for golden hour photography (골든아워)

    Optimal conditions:
    - Cloud cover: 20-50%
    - Low rain probability
    - Low PM2.5
    - Good visibility
    """

    def __init__(self):
        super().__init__(theme_id=13, theme_name="골든아워")
        self.config = WEIGHTS['golden_hour']

    async def calculate_score(
        self,
        weather_data: dict,
        ocean_data: Optional[dict] = None
    ) -> float:
        score = 0.0

        # Cloud cover (20-50% optimal for golden light)
        cloud = self._safe_get(weather_data, 'cloud.avg', 50)
        cloud_score = self._calculate_range_score(cloud, self.config['cloud_cover']['min'], self.config['cloud_cover']['max'])
        score += cloud_score * self.config['cloud_cover']['weight']

        # Rain probability
        rain_prob = self._safe_get(weather_data, 'rain_prob.avg', 50)
        rain_score = self._normalize_score(rain_prob, 0, self.config['rain_prob']['max'], reverse=True)
        score += rain_score * self.config['rain_prob']['weight']

        # PM2.5
        pm25 = self._safe_get(weather_data, 'pm25', 50)
        pm25_score = self._normalize_score(pm25, 0, self.config['pm25']['max'], reverse=True)
        score += pm25_score * self.config['pm25']['weight']

        # Visibility
        visibility = self._safe_get(weather_data, 'visibility', 5)
        visibility_score = self._normalize_score(visibility, self.config['visibility']['min'], 30, reverse=False)
        score += visibility_score * self.config['visibility']['weight']

        return min(100.0, max(0.0, score))


class BlueHourScorer(BaseScorer):
    """Scorer for blue hour photography (블루아워)

    Optimal conditions:
    - Cloud cover: <40%
    - Very low rain probability
    - Excellent visibility
    - Low PM2.5
    """

    def __init__(self):
        super().__init__(theme_id=14, theme_name="블루아워")
        self.config = WEIGHTS['blue_hour']

    async def calculate_score(
        self,
        weather_data: dict,
        ocean_data: Optional[dict] = None
    ) -> float:
        score = 0.0

        # Cloud cover
        cloud = self._safe_get(weather_data, 'cloud.avg', 50)
        cloud_score = self._normalize_score(cloud, 0, self.config['cloud_cover']['max'], reverse=True)
        score += cloud_score * self.config['cloud_cover']['weight']

        # Rain probability
        rain_prob = self._safe_get(weather_data, 'rain_prob.avg', 50)
        rain_score = self._normalize_score(rain_prob, 0, self.config['rain_prob']['max'], reverse=True)
        score += rain_score * self.config['rain_prob']['weight']

        # Visibility
        visibility = self._safe_get(weather_data, 'visibility', 5)
        visibility_score = self._normalize_score(visibility, self.config['visibility']['min'], 30, reverse=False)
        score += visibility_score * self.config['visibility']['weight']

        # PM2.5
        pm25 = self._safe_get(weather_data, 'pm25', 50)
        pm25_score = self._normalize_score(pm25, 0, self.config['pm25']['max'], reverse=True)
        score += pm25_score * self.config['pm25']['weight']

        return min(100.0, max(0.0, score))


class FrostRimeScorer(BaseScorer):
    """Scorer for frost/rime photography (상고대)

    Optimal conditions:
    - Temperature: <-5°C
    - High humidity: >85%
    - Low wind: <3 m/s
    - Low cloud cover
    - Winter season (Nov-Feb)
    """

    def __init__(self):
        super().__init__(theme_id=15, theme_name="상고대")
        self.config = WEIGHTS['frost_rime']

    async def calculate_score(
        self,
        weather_data: dict,
        ocean_data: Optional[dict] = None
    ) -> float:
        # Season check (November-February)
        forecast_date = self._safe_get(weather_data, 'datetime', None)
        if forecast_date:
            try:
                month = datetime.fromisoformat(forecast_date.replace('Z', '+00:00')).month
                if month not in self.config['season']['months']:
                    return 0.0  # Out of season
            except:
                pass

        score = 0.0

        # Temperature (< -5°C optimal)
        temp = self._safe_get(weather_data, 'temp.avg', 10)
        if temp > 0:
            return 0.0  # Must be below freezing
        temp_score = self._normalize_score(temp, self.config['temp']['max'], 5, reverse=True)
        score += temp_score * self.config['temp']['weight']

        # Humidity (>85% optimal)
        humidity = self._safe_get(weather_data, 'humidity', 50)
        humidity_score = self._normalize_score(humidity, self.config['humidity']['min'], 100, reverse=False)
        score += humidity_score * self.config['humidity']['weight']

        # Wind speed (<3 m/s)
        wind_speed = self._safe_get(weather_data, 'wind_speed', 10)
        wind_score = self._normalize_score(wind_speed, 0, self.config['wind_speed']['max'], reverse=True)
        score += wind_score * self.config['wind_speed']['weight']

        # Cloud cover (<30%)
        cloud = self._safe_get(weather_data, 'cloud.avg', 50)
        cloud_score = self._normalize_score(cloud, 0, self.config['cloud_cover']['max'], reverse=True)
        score += cloud_score * self.config['cloud_cover']['weight']

        # Mountain bonus
        elevation = self._safe_get(weather_data, 'elevation', 0)
        if elevation >= 500:
            score += 10

        return min(100.0, max(0.0, score))


class MoonriseScorer(BaseScorer):
    """Scorer for moonrise photography (월출)

    Optimal conditions:
    - Full moon ±2 days
    - Low cloud cover
    - Excellent visibility
    - Low PM2.5
    """

    def __init__(self):
        super().__init__(theme_id=16, theme_name="월출")
        self.config = WEIGHTS['moonrise']

    async def calculate_score(
        self,
        weather_data: dict,
        ocean_data: Optional[dict] = None
    ) -> float:
        score = 0.0

        # Moon phase score (full moon ±2 days)
        moon_age = self._safe_get(weather_data, 'moon_age', 15)
        moon_score = self._calculate_full_moon_score(moon_age, self.config['moon_phase']['range_days'])
        score += moon_score * self.config['moon_phase']['weight']

        # Cloud cover
        cloud = self._safe_get(weather_data, 'cloud.avg', 50)
        cloud_score = self._normalize_score(cloud, 0, self.config['cloud_cover']['max'], reverse=True)
        score += cloud_score * self.config['cloud_cover']['weight']

        # Visibility
        visibility = self._safe_get(weather_data, 'visibility', 5)
        visibility_score = self._normalize_score(visibility, self.config['visibility']['min'], 30, reverse=False)
        score += visibility_score * self.config['visibility']['weight']

        # PM2.5
        pm25 = self._safe_get(weather_data, 'pm25', 50)
        pm25_score = self._normalize_score(pm25, 0, self.config['pm25']['max'], reverse=True)
        score += pm25_score * self.config['pm25']['weight']

        return min(100.0, max(0.0, score))

    def _calculate_full_moon_score(self, moon_age: float, range_days: int) -> float:
        """Calculate score based on full moon phase (around day 15)"""
        full_moon_age = 14.75  # Full moon is around day 14-15
        diff = abs(moon_age - full_moon_age)
        if diff <= range_days:
            return 100.0
        else:
            penalty = (diff - range_days) * 8
            return max(0.0, 100.0 - penalty)


# Export all scorers
ALL_SCORERS = [
    SunriseScorer,
    SunriseOmegaScorer,
    SunsetScorer,
    SunsetOmegaScorer,
    MilkyWayScorer,
    BioluminescenceScorer,
    SeaLongExposureScorer,
    SeaOfCloudsScorer,
    StarTrailScorer,
    NightCityscapeScorer,
    FogLandscapeScorer,
    ReflectionScorer,
    GoldenHourScorer,
    BlueHourScorer,
    FrostRimeScorer,
    MoonriseScorer,
]


def get_scorer_by_theme_id(theme_id: int) -> Optional[BaseScorer]:
    """Get scorer instance by theme ID

    Args:
        theme_id: Theme ID (1-8)

    Returns:
        BaseScorer instance or None if not found
    """
    for scorer_class in ALL_SCORERS:
        scorer = scorer_class()
        if scorer.theme_id == theme_id:
            return scorer
    return None


def get_all_scorers() -> list[BaseScorer]:
    """Get all scorer instances

    Returns:
        List of all scorer instances
    """
    return [scorer_class() for scorer_class in ALL_SCORERS]
