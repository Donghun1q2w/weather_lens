"""Theme-specific Scorers for PhotoSpot Korea - 16 Photography Themes (Daily Scoring)"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from scripts.scorers.base_scorer import BaseScorer


# Load weights configuration
WEIGHTS_PATH = Path(__file__).parent.parent / "config" / "weights.json"
with open(WEIGHTS_PATH, 'r', encoding='utf-8') as f:
    WEIGHTS = json.load(f)['themes']


# =============================================================================
# Helper: extract hour from timeslot
# =============================================================================

def _slot_hour(slot: dict) -> Optional[int]:
    """Extract hour from a timeslot's datetime string."""
    dt_str = slot.get("datetime", "")
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).hour
    except (ValueError, AttributeError):
        return None


def _parse_time_str(time_str: str) -> Optional[tuple]:
    """Parse 'HH:MM' string to (hour, minute) tuple."""
    if not time_str:
        return None
    try:
        parts = time_str.split(":")
        return (int(parts[0]), int(parts[1]))
    except (ValueError, IndexError):
        return None


# =============================================================================
# Group A: Sun-time-based scorers
# =============================================================================

class SunriseScorer(BaseScorer):
    """일출 - Sunrise photography scorer (daily)"""

    def __init__(self):
        super().__init__(theme_id=1, theme_name="일출")
        self.config = WEIGHTS['sunrise']
        self.relevant_hours = [6, 9]
        self.time_selection = "closest"

    async def calculate_score(self, weather_data: dict, ocean_data: Optional[dict] = None) -> float:
        cloud = self._safe_get(weather_data, 'cloud.avg', 50)
        rain_prob = self._safe_get(weather_data, 'rain_prob.avg', 50)
        score = max(0, 100 - abs(cloud - 45) - rain_prob)
        return min(100.0, max(0.0, float(score)))

    async def calculate_daily_score(self, day_weather: list, date: str,
                                     location_meta: dict, marine_data: dict = None,
                                     astronomy: dict = None) -> dict:
        # Determine sunrise time from marine/astronomy data
        sunrise_hour, sunrise_min = 7, 0  # default
        if marine_data and marine_data.get("sun_info"):
            t = _parse_time_str(marine_data["sun_info"].get("sunrise"))
            if t:
                sunrise_hour, sunrise_min = t
        elif astronomy and astronomy.get("sunrise"):
            t = _parse_time_str(astronomy["sunrise"])
            if t:
                sunrise_hour, sunrise_min = t

        slot = self._find_closest_timeslot(day_weather, sunrise_hour, sunrise_min)
        if not slot:
            return {"score": 0, "factors": {"error": "no timeslot"}, "time_used": "N/A"}

        cloud = self._get_weather_value(slot, "cloud_cover", 50)
        rain = self._get_weather_value(slot, "rain_probability", 50)
        vis = self._get_weather_value(slot, "visibility", 10)
        humidity = self._get_weather_value(slot, "humidity", 50)

        # Cloud: 30-60% optimal for colorful sunrise
        cloud_score = self._calculate_range_score(cloud, 30, 60)
        rain_score = self._normalize_score(rain, 0, self.config['rain_prob']['max'], reverse=True)
        vis_score = self._normalize_score(vis, self.config['visibility']['min'], 30)

        score = (cloud_score * self.config['cloud_cover']['weight'] +
                 rain_score * self.config['rain_prob']['weight'] +
                 vis_score * self.config['visibility']['weight'])

        # Remaining weight for humidity (lower is better for clarity)
        remaining_weight = 1.0 - (self.config['cloud_cover']['weight'] +
                                   self.config['rain_prob']['weight'] +
                                   self.config['visibility']['weight'])
        humidity_score = self._normalize_score(humidity, 30, 90, reverse=True)
        score += humidity_score * remaining_weight

        # East coast bonus
        if location_meta.get("is_east_coast"):
            score += self.config.get('east_coast_bonus', 10)

        time_used = f"{sunrise_hour:02d}:{sunrise_min:02d}"
        return {
            "score": round(min(100.0, max(0.0, score)), 1),
            "factors": {
                "cloud_cover": round(cloud, 1),
                "rain_probability": round(rain, 1),
                "visibility_km": round(vis, 1),
                "east_coast": location_meta.get("is_east_coast", False),
            },
            "time_used": time_used,
        }


class SunriseOmegaScorer(BaseScorer):
    """일출 오메가 - Omega sunrise scorer (daily)"""

    def __init__(self):
        super().__init__(theme_id=2, theme_name="일출 오메가")
        self.config = WEIGHTS['sunrise_omega']
        self.relevant_hours = [6, 9]
        self.time_selection = "closest"

    async def calculate_score(self, weather_data: dict, ocean_data: Optional[dict] = None) -> float:
        is_east = self._safe_get(weather_data, 'is_east_coast', False)
        if not is_east:
            return 0.0
        cloud = self._safe_get(weather_data, 'cloud.avg', 50)
        return min(100.0, max(0.0, 100 - cloud * 1.5))

    async def calculate_daily_score(self, day_weather: list, date: str,
                                     location_meta: dict, marine_data: dict = None,
                                     astronomy: dict = None) -> dict:
        if not location_meta.get("is_east_coast"):
            return {"score": 0, "factors": {"reason": "east_coast_required"}, "time_used": "N/A"}

        sunrise_hour, sunrise_min = 7, 0
        if marine_data and marine_data.get("sun_info"):
            t = _parse_time_str(marine_data["sun_info"].get("sunrise"))
            if t:
                sunrise_hour, sunrise_min = t

        slot = self._find_closest_timeslot(day_weather, sunrise_hour, sunrise_min)
        if not slot:
            return {"score": 0, "factors": {"error": "no timeslot"}, "time_used": "N/A"}

        cloud = self._get_weather_value(slot, "cloud_cover", 50)
        wind = self._get_weather_value(slot, "wind_speed", 10)
        vis = self._get_weather_value(slot, "visibility", 10)

        # Horizon clear (low cloud)
        horizon_score = self._normalize_score(cloud, 0, 20, reverse=True)
        # Wind (<3 m/s for mirage effect)
        wind_score = self._normalize_score(wind, 0, self.config['wind_speed']['max'], reverse=True)
        # Visibility
        vis_score = self._normalize_score(vis, 15, 30)

        score = (horizon_score * self.config['horizon_clear']['weight'] +
                 wind_score * self.config['wind_speed']['weight'] +
                 vis_score * 0.2)

        # Sea temp diff (requires marine data)
        sea_temp_diff_score = 0
        if marine_data and marine_data.get("sea_temperature"):
            sea_temp = marine_data["sea_temperature"].get("temperature")
            air_temp = self._get_weather_value(slot, "temperature")
            if sea_temp is not None and air_temp is not None:
                try:
                    temp_diff = float(sea_temp) - air_temp
                    sea_temp_diff_score = self._normalize_score(
                        temp_diff, self.config['sea_temp_diff']['min'], 15)
                except (TypeError, ValueError):
                    pass
        score += sea_temp_diff_score * self.config['sea_temp_diff']['weight']

        time_used = f"{sunrise_hour:02d}:{sunrise_min:02d}"
        return {
            "score": round(min(100.0, max(0.0, score)), 1),
            "factors": {
                "cloud_cover": round(cloud, 1),
                "wind_speed": round(wind, 1),
                "visibility_km": round(vis, 1),
                "uncertainty": "조건 충족 시에도 실제 발생률 ~30%",
            },
            "time_used": time_used,
        }


class SunsetScorer(BaseScorer):
    """일몰 - Sunset photography scorer (daily)"""

    def __init__(self):
        super().__init__(theme_id=3, theme_name="일몰")
        self.config = WEIGHTS['sunset']
        self.relevant_hours = [15, 18]
        self.time_selection = "closest"

    async def calculate_score(self, weather_data: dict, ocean_data: Optional[dict] = None) -> float:
        cloud = self._safe_get(weather_data, 'cloud.avg', 50)
        rain_prob = self._safe_get(weather_data, 'rain_prob.avg', 50)
        score = max(0, 100 - abs(cloud - 55) - rain_prob)
        return min(100.0, max(0.0, float(score)))

    async def calculate_daily_score(self, day_weather: list, date: str,
                                     location_meta: dict, marine_data: dict = None,
                                     astronomy: dict = None) -> dict:
        sunset_hour, sunset_min = 18, 0
        if marine_data and marine_data.get("sun_info"):
            t = _parse_time_str(marine_data["sun_info"].get("sunset"))
            if t:
                sunset_hour, sunset_min = t
        elif astronomy and astronomy.get("sunset"):
            t = _parse_time_str(astronomy["sunset"])
            if t:
                sunset_hour, sunset_min = t

        slot = self._find_closest_timeslot(day_weather, sunset_hour, sunset_min)
        if not slot:
            return {"score": 0, "factors": {"error": "no timeslot"}, "time_used": "N/A"}

        cloud = self._get_weather_value(slot, "cloud_cover", 50)
        rain = self._get_weather_value(slot, "rain_probability", 50)
        vis = self._get_weather_value(slot, "visibility", 10)
        humidity = self._get_weather_value(slot, "humidity", 50)

        cloud_score = self._calculate_range_score(cloud, 40, 70)
        rain_score = self._normalize_score(rain, 0, self.config['rain_prob']['max'], reverse=True)
        vis_score = self._normalize_score(vis, self.config['visibility']['min'], 30)

        score = (cloud_score * self.config['cloud_cover']['weight'] +
                 rain_score * self.config['rain_prob']['weight'] +
                 vis_score * self.config['visibility']['weight'])

        remaining_weight = 1.0 - (self.config['cloud_cover']['weight'] +
                                   self.config['rain_prob']['weight'] +
                                   self.config['visibility']['weight'])
        humidity_score = self._normalize_score(humidity, 30, 90, reverse=True)
        score += humidity_score * remaining_weight

        if location_meta.get("is_west_coast"):
            score += self.config.get('west_coast_bonus', 10)

        time_used = f"{sunset_hour:02d}:{sunset_min:02d}"
        return {
            "score": round(min(100.0, max(0.0, score)), 1),
            "factors": {
                "cloud_cover": round(cloud, 1),
                "rain_probability": round(rain, 1),
                "visibility_km": round(vis, 1),
                "west_coast": location_meta.get("is_west_coast", False),
            },
            "time_used": time_used,
        }


class SunsetOmegaScorer(BaseScorer):
    """일몰 오메가 - Omega sunset scorer (daily)"""

    def __init__(self):
        super().__init__(theme_id=4, theme_name="일몰 오메가")
        self.config = WEIGHTS['sunset_omega']
        self.relevant_hours = [15, 18]
        self.time_selection = "closest"

    async def calculate_score(self, weather_data: dict, ocean_data: Optional[dict] = None) -> float:
        is_west = self._safe_get(weather_data, 'is_west_coast', False)
        if not is_west:
            return 0.0
        cloud = self._safe_get(weather_data, 'cloud.avg', 50)
        return min(100.0, max(0.0, 100 - cloud * 1.5))

    async def calculate_daily_score(self, day_weather: list, date: str,
                                     location_meta: dict, marine_data: dict = None,
                                     astronomy: dict = None) -> dict:
        if not location_meta.get("is_west_coast"):
            return {"score": 0, "factors": {"reason": "west_coast_required"}, "time_used": "N/A"}

        sunset_hour, sunset_min = 18, 0
        if marine_data and marine_data.get("sun_info"):
            t = _parse_time_str(marine_data["sun_info"].get("sunset"))
            if t:
                sunset_hour, sunset_min = t

        slot = self._find_closest_timeslot(day_weather, sunset_hour, sunset_min)
        if not slot:
            return {"score": 0, "factors": {"error": "no timeslot"}, "time_used": "N/A"}

        cloud = self._get_weather_value(slot, "cloud_cover", 50)
        wind = self._get_weather_value(slot, "wind_speed", 10)
        vis = self._get_weather_value(slot, "visibility", 10)

        horizon_score = self._normalize_score(cloud, 0, 20, reverse=True)
        wind_score = self._normalize_score(wind, 0, self.config['wind_speed']['max'], reverse=True)
        vis_score = self._normalize_score(vis, 15, 30)

        score = (horizon_score * self.config['horizon_clear']['weight'] +
                 wind_score * self.config['wind_speed']['weight'] +
                 vis_score * 0.2)

        sea_temp_diff_score = 0
        if marine_data and marine_data.get("sea_temperature"):
            sea_temp = marine_data["sea_temperature"].get("temperature")
            air_temp = self._get_weather_value(slot, "temperature")
            if sea_temp is not None and air_temp is not None:
                try:
                    temp_diff = float(sea_temp) - air_temp
                    sea_temp_diff_score = self._normalize_score(
                        temp_diff, self.config['sea_temp_diff']['min'], 15)
                except (TypeError, ValueError):
                    pass
        score += sea_temp_diff_score * self.config['sea_temp_diff']['weight']

        time_used = f"{sunset_hour:02d}:{sunset_min:02d}"
        return {
            "score": round(min(100.0, max(0.0, score)), 1),
            "factors": {
                "cloud_cover": round(cloud, 1),
                "wind_speed": round(wind, 1),
                "visibility_km": round(vis, 1),
                "uncertainty": "조건 충족 시에도 실제 발생률 ~30%",
            },
            "time_used": time_used,
        }


class GoldenHourScorer(BaseScorer):
    """골든아워 - Golden hour scorer (daily, best of sunrise/sunset)"""

    def __init__(self):
        super().__init__(theme_id=13, theme_name="골든아워")
        self.config = WEIGHTS['golden_hour']
        self.relevant_hours = [6, 9, 15, 18]
        self.time_selection = "closest"

    async def calculate_score(self, weather_data: dict, ocean_data: Optional[dict] = None) -> float:
        cloud = self._safe_get(weather_data, 'cloud.avg', 50)
        rain = self._safe_get(weather_data, 'rain_prob.avg', 50)
        return min(100.0, max(0.0, 100 - abs(cloud - 35) - rain))

    async def calculate_daily_score(self, day_weather: list, date: str,
                                     location_meta: dict, marine_data: dict = None,
                                     astronomy: dict = None) -> dict:
        # Golden hour = sunrise ±1h and sunset ±1h, pick best
        sunrise_hour, sunset_hour = 7, 18
        if marine_data and marine_data.get("sun_info"):
            t = _parse_time_str(marine_data["sun_info"].get("sunrise"))
            if t:
                sunrise_hour = t[0]
            t = _parse_time_str(marine_data["sun_info"].get("sunset"))
            if t:
                sunset_hour = t[0]

        sunrise_slot = self._find_closest_timeslot(day_weather, sunrise_hour)
        sunset_slot = self._find_closest_timeslot(day_weather, sunset_hour)

        best_score = 0
        best_factors = {}
        best_time = "N/A"

        for slot, label in [(sunrise_slot, "sunrise"), (sunset_slot, "sunset")]:
            if not slot:
                continue
            cloud = self._get_weather_value(slot, "cloud_cover", 50)
            rain = self._get_weather_value(slot, "rain_probability", 50)
            vis = self._get_weather_value(slot, "visibility", 10)

            cloud_s = self._calculate_range_score(cloud, 20, 50)
            rain_s = self._normalize_score(rain, 0, self.config['rain_prob']['max'], reverse=True)
            vis_s = self._normalize_score(vis, self.config['visibility']['min'], 30)

            s = (cloud_s * self.config['cloud_cover']['weight'] +
                 rain_s * self.config['rain_prob']['weight'] +
                 vis_s * self.config['visibility']['weight'])

            # Use remaining weight for pm25 proxy (humidity as stand-in)
            remaining = 1.0 - (self.config['cloud_cover']['weight'] +
                               self.config['rain_prob']['weight'] +
                               self.config['visibility']['weight'])
            humidity = self._get_weather_value(slot, "humidity", 50)
            s += self._normalize_score(humidity, 30, 80, reverse=True) * remaining

            if s > best_score:
                best_score = s
                h = _slot_hour(slot)
                best_time = f"{h:02d}:00" if h is not None else label
                best_factors = {
                    "cloud_cover": round(cloud, 1),
                    "rain_probability": round(rain, 1),
                    "period": label,
                }

        return {
            "score": round(min(100.0, max(0.0, best_score)), 1),
            "factors": best_factors,
            "time_used": best_time,
        }


class BlueHourScorer(BaseScorer):
    """블루아워 - Blue hour scorer (daily, sunrise-30min & sunset+30min)"""

    def __init__(self):
        super().__init__(theme_id=14, theme_name="블루아워")
        self.config = WEIGHTS['blue_hour']
        self.relevant_hours = [6, 18, 21]
        self.time_selection = "closest"

    async def calculate_score(self, weather_data: dict, ocean_data: Optional[dict] = None) -> float:
        cloud = self._safe_get(weather_data, 'cloud.avg', 50)
        rain = self._safe_get(weather_data, 'rain_prob.avg', 50)
        return min(100.0, max(0.0, 100 - cloud - rain))

    async def calculate_daily_score(self, day_weather: list, date: str,
                                     location_meta: dict, marine_data: dict = None,
                                     astronomy: dict = None) -> dict:
        sunrise_hour, sunset_hour = 7, 18
        if marine_data and marine_data.get("sun_info"):
            t = _parse_time_str(marine_data["sun_info"].get("sunrise"))
            if t:
                sunrise_hour = t[0]
            t = _parse_time_str(marine_data["sun_info"].get("sunset"))
            if t:
                sunset_hour = t[0]

        # Blue hour: ~30min before sunrise, ~30min after sunset
        morning_slot = self._find_closest_timeslot(day_weather, sunrise_hour - 1 if sunrise_hour > 0 else 0)
        evening_slot = self._find_closest_timeslot(day_weather, sunset_hour + 1 if sunset_hour < 23 else 23)

        best_score = 0
        best_factors = {}
        best_time = "N/A"

        for slot, label in [(morning_slot, "morning"), (evening_slot, "evening")]:
            if not slot:
                continue
            cloud = self._get_weather_value(slot, "cloud_cover", 50)
            rain = self._get_weather_value(slot, "rain_probability", 50)
            vis = self._get_weather_value(slot, "visibility", 10)

            cloud_s = self._normalize_score(cloud, 0, self.config['cloud_cover']['max'], reverse=True)
            rain_s = self._normalize_score(rain, 0, self.config['rain_prob']['max'], reverse=True)
            vis_s = self._normalize_score(vis, self.config['visibility']['min'], 30)

            s = (cloud_s * self.config['cloud_cover']['weight'] +
                 rain_s * self.config['rain_prob']['weight'] +
                 vis_s * self.config['visibility']['weight'])

            remaining = 1.0 - (self.config['cloud_cover']['weight'] +
                               self.config['rain_prob']['weight'] +
                               self.config['visibility']['weight'])
            humidity = self._get_weather_value(slot, "humidity", 50)
            s += self._normalize_score(humidity, 30, 80, reverse=True) * remaining

            if s > best_score:
                best_score = s
                h = _slot_hour(slot)
                best_time = f"{h:02d}:00" if h is not None else label
                best_factors = {
                    "cloud_cover": round(cloud, 1),
                    "rain_probability": round(rain, 1),
                    "period": label,
                }

        return {
            "score": round(min(100.0, max(0.0, best_score)), 1),
            "factors": best_factors,
            "time_used": best_time,
        }


class MoonriseScorer(BaseScorer):
    """월출 - Moonrise scorer (daily)"""

    def __init__(self):
        super().__init__(theme_id=16, theme_name="월출")
        self.config = WEIGHTS['moonrise']
        self.relevant_hours = [18, 21]
        self.time_selection = "closest"

    async def calculate_score(self, weather_data: dict, ocean_data: Optional[dict] = None) -> float:
        moon_age = self._safe_get(weather_data, 'moon_age', 15)
        cloud = self._safe_get(weather_data, 'cloud.avg', 50)
        full_moon_diff = abs(moon_age - 14.75)
        score = max(0, 100 - full_moon_diff * 8 - cloud)
        return min(100.0, max(0.0, float(score)))

    async def calculate_daily_score(self, day_weather: list, date: str,
                                     location_meta: dict, marine_data: dict = None,
                                     astronomy: dict = None) -> dict:
        # Moon phase check: need full moon ±2 days
        moon_age = 15.0  # default (not great)
        illumination = 50.0
        if marine_data and marine_data.get("moon_info"):
            moon_age = marine_data["moon_info"].get("moon_age", 15)
            illumination = marine_data["moon_info"].get("illumination", 50)
        elif astronomy and astronomy.get("moon_phase"):
            moon_age = astronomy["moon_phase"].get("moon_age", 15)
            illumination = astronomy["moon_phase"].get("illumination", 50)

        # Full moon score
        full_moon_age = 14.75
        diff = abs(moon_age - full_moon_age)
        range_days = self.config['moon_phase']['range_days']
        if diff <= range_days:
            moon_score = 100.0
        else:
            moon_score = max(0.0, 100.0 - (diff - range_days) * 8)

        # Determine moonrise time
        moonrise_hour = 18  # default
        if marine_data and marine_data.get("moon_info"):
            t = _parse_time_str(marine_data["moon_info"].get("moonrise"))
            if t:
                moonrise_hour = t[0]

        slot = self._find_closest_timeslot(day_weather, moonrise_hour)
        if not slot:
            return {"score": 0, "factors": {"error": "no timeslot"}, "time_used": "N/A"}

        cloud = self._get_weather_value(slot, "cloud_cover", 50)
        vis = self._get_weather_value(slot, "visibility", 10)

        cloud_score = self._normalize_score(cloud, 0, self.config['cloud_cover']['max'], reverse=True)
        vis_score = self._normalize_score(vis, self.config['visibility']['min'], 30)

        score = (moon_score * self.config['moon_phase']['weight'] +
                 cloud_score * self.config['cloud_cover']['weight'] +
                 vis_score * self.config['visibility']['weight'])

        # Remaining weight
        remaining = 1.0 - (self.config['moon_phase']['weight'] +
                           self.config['cloud_cover']['weight'] +
                           self.config['visibility']['weight'])
        humidity = self._get_weather_value(slot, "humidity", 50)
        score += self._normalize_score(humidity, 30, 80, reverse=True) * remaining

        return {
            "score": round(min(100.0, max(0.0, score)), 1),
            "factors": {
                "moon_age": round(moon_age, 1),
                "illumination": round(illumination, 1),
                "cloud_cover": round(cloud, 1),
                "visibility_km": round(vis, 1),
            },
            "time_used": f"{moonrise_hour:02d}:00",
        }


# =============================================================================
# Group B: Night-based scorers (21:00-03:00)
# =============================================================================

class MilkyWayScorer(BaseScorer):
    """은하수 - Milky Way scorer (daily, night-based with dark window logic)"""

    def __init__(self):
        super().__init__(theme_id=5, theme_name="은하수")
        self.config = WEIGHTS['milky_way']
        self.relevant_hours = [21, 0, 3]
        self.time_selection = "worst_case"

    async def calculate_score(self, weather_data: dict, ocean_data: Optional[dict] = None) -> float:
        cloud = self._safe_get(weather_data, 'cloud.avg', 50)
        return min(100.0, max(0.0, 100 - cloud * 2))

    async def calculate_daily_score(self, day_weather: list, date: str,
                                     location_meta: dict, marine_data: dict = None,
                                     astronomy: dict = None) -> dict:
        """
        MilkyWay daily scoring with weighted components:
        - dark_window_score    * 0.35
        - night_cloud_score    * 0.25
        - galactic_alt_score   * 0.15
        - light_pollution      * 0.15
        - night_visibility     * 0.10
        + wave_height_bonus (coastal only, 0-10 additive)

        HARD GATE: dark_window_hours < 2.0 => score = 0
        """
        # Night timeslots: 21, 00, 03 from day_weather
        night_slots = self._get_timeslots_in_range(day_weather, 21, 3)

        # --- Dark window score ---
        dark_hours = 0
        if astronomy and astronomy.get("dark_window"):
            dw = astronomy["dark_window"]
            if dw.get("available"):
                dark_hours = dw.get("duration_hours", 0)

        # HARD GATE
        if dark_hours < 2.0:
            return {
                "score": 0,
                "factors": {
                    "dark_window_hours": round(dark_hours, 1),
                    "gate": "dark_window < 2h",
                },
                "time_used": "21:00-03:00",
            }

        # dark_window_score: clamp((hours - 2) / 6 * 100, 0, 100)
        dark_window_score = min(100, max(0, (dark_hours - 2) / 6 * 100))

        # --- Night cloud score (worst-case) ---
        worst_cloud = self._worst_case_field(night_slots, "cloud_cover", mode="max")
        if worst_cloud is None:
            worst_cloud = 50
        night_cloud_score = self._normalize_score(worst_cloud, 0, 80, reverse=True)

        # --- Galactic altitude score ---
        galactic_alt = 0
        if astronomy and astronomy.get("core_altitude") is not None:
            galactic_alt = astronomy["core_altitude"]
        galactic_alt_score = self._normalize_score(galactic_alt, 0, 45)

        # --- Light pollution score (static per site, default 40pts) ---
        light_pollution_score = 40.0  # default for unknown bortle
        if location_meta.get("bortle"):
            bortle = location_meta["bortle"]
            # Bortle 1=best, 9=worst
            light_pollution_score = self._normalize_score(bortle, 1, 9, reverse=True)

        # --- Night visibility score (min visibility, convert m->km done by _get_weather_value) ---
        min_vis = self._worst_case_field(night_slots, "visibility", mode="min")
        if min_vis is None:
            min_vis = 10
        night_vis_score = self._normalize_score(min_vis, 5, 20)

        # Weighted sum
        score = (dark_window_score * 0.35 +
                 night_cloud_score * 0.25 +
                 galactic_alt_score * 0.15 +
                 light_pollution_score * 0.15 +
                 night_vis_score * 0.10)

        # --- Wave height bonus (coastal only, 0-10 additive) ---
        wave_bonus = 0
        if location_meta.get("is_coastal") and marine_data:
            wh_data = marine_data.get("wave_height")
            if wh_data and wh_data.get("height") is not None:
                try:
                    wh = float(wh_data["height"])
                    if wh < 0.5:
                        wave_bonus = 0
                    elif wh < 1.0:
                        wave_bonus = 2
                    elif wh < 1.5:
                        wave_bonus = 5
                    elif wh < 2.5:
                        wave_bonus = 8
                    else:
                        wave_bonus = 10
                except (TypeError, ValueError):
                    pass

        score += wave_bonus

        # Season check (informational, not gating)
        season_quality = "off"
        if astronomy and astronomy.get("season_quality"):
            season_quality = astronomy["season_quality"]

        return {
            "score": round(min(100.0, max(0.0, score)), 1),
            "factors": {
                "dark_window_hours": round(dark_hours, 1),
                "dark_window_score": round(dark_window_score, 1),
                "worst_cloud": round(worst_cloud, 1),
                "galactic_altitude": round(galactic_alt, 1),
                "min_visibility_km": round(min_vis, 1),
                "wave_height_bonus": wave_bonus,
                "season": season_quality,
            },
            "time_used": "21:00-03:00",
        }


class StarTrailScorer(BaseScorer):
    """별궤적 - Star trail scorer (daily, night-based)"""

    def __init__(self):
        super().__init__(theme_id=9, theme_name="별궤적")
        self.config = WEIGHTS['star_trail']
        self.relevant_hours = [21, 0, 3]
        self.time_selection = "worst_case"

    async def calculate_score(self, weather_data: dict, ocean_data: Optional[dict] = None) -> float:
        cloud = self._safe_get(weather_data, 'cloud.avg', 50)
        wind = self._safe_get(weather_data, 'wind_speed.avg', 10)
        return min(100.0, max(0.0, 100 - cloud * 2 - wind * 5))

    async def calculate_daily_score(self, day_weather: list, date: str,
                                     location_meta: dict, marine_data: dict = None,
                                     astronomy: dict = None) -> dict:
        night_slots = self._get_timeslots_in_range(day_weather, 21, 3)

        # Moon phase (new moon ±5 days)
        moon_age = 15.0
        if marine_data and marine_data.get("moon_info"):
            moon_age = marine_data["moon_info"].get("moon_age", 15)
        elif astronomy and astronomy.get("moon_phase"):
            moon_age = astronomy["moon_phase"].get("moon_age", 15)

        if moon_age > 15:
            moon_age_adj = 29.5 - moon_age
        else:
            moon_age_adj = moon_age
        range_days = self.config['moon_phase']['range_days']
        if moon_age_adj <= range_days:
            moon_score = 100.0
        else:
            moon_score = max(0.0, 100 - (moon_age_adj - range_days) * 5)

        # Worst-case cloud
        worst_cloud = self._worst_case_field(night_slots, "cloud_cover", mode="max")
        if worst_cloud is None:
            worst_cloud = 50
        cloud_score = self._normalize_score(worst_cloud, 0, self.config['cloud_cover']['max'], reverse=True)

        # Light pollution
        light_score = 40.0
        if location_meta.get("bortle"):
            light_score = self._normalize_score(location_meta["bortle"], 1, 9, reverse=True)

        # Wind (needs stability for 4h+ exposure)
        worst_wind = self._worst_case_field(night_slots, "wind_speed", mode="max")
        if worst_wind is None:
            worst_wind = 5
        wind_score = self._normalize_score(worst_wind, 0, self.config['wind_speed']['max'], reverse=True)

        score = (moon_score * self.config['moon_phase']['weight'] +
                 cloud_score * self.config['cloud_cover']['weight'] +
                 light_score * self.config['light_pollution']['weight'] +
                 wind_score * self.config['wind_speed']['weight'])

        return {
            "score": round(min(100.0, max(0.0, score)), 1),
            "factors": {
                "moon_age": round(moon_age, 1),
                "worst_cloud": round(worst_cloud, 1),
                "worst_wind": round(worst_wind, 1),
            },
            "time_used": "21:00-03:00",
        }


class BioluminescenceScorer(BaseScorer):
    """야광충 - Bioluminescence scorer (daily, night-based)"""

    def __init__(self):
        super().__init__(theme_id=6, theme_name="야광충")
        self.config = WEIGHTS['bioluminescence']
        self.relevant_hours = [21, 0, 3]
        self.time_selection = "worst_case"

    async def calculate_score(self, weather_data: dict, ocean_data: Optional[dict] = None) -> float:
        return 0.0  # Requires specific conditions

    async def calculate_daily_score(self, day_weather: list, date: str,
                                     location_meta: dict, marine_data: dict = None,
                                     astronomy: dict = None) -> dict:
        # GATE: 서해/남해 해안만 (야광충은 서·남해 연안에서 발생하는 현상 — 내륙·동해 제외)
        is_west = location_meta.get("is_west_coast")
        is_south = (location_meta.get("is_south_coast") or
                    (location_meta.get("is_coastal") and
                     not location_meta.get("is_east_coast") and
                     not location_meta.get("is_west_coast")))
        if not (is_west or is_south):
            return {"score": 0, "factors": {"reason": "서해/남해 해안 아님"}, "time_used": "N/A"}

        # Season check (April-September)
        try:
            month = datetime.fromisoformat(date).month
        except (ValueError, TypeError):
            month = datetime.now().month
        if month not in self.config['season']['months']:
            return {"score": 0, "factors": {"reason": "off_season"}, "time_used": "N/A"}

        night_slots = self._get_timeslots_in_range(day_weather, 21, 3)

        # Season score
        season_score = 100.0

        # Sea temperature (18-25°C)
        sea_temp_score = 0
        sea_temp_val = None
        if marine_data and marine_data.get("sea_temperature"):
            sea_temp_val = marine_data["sea_temperature"].get("temperature")
            if sea_temp_val is not None:
                try:
                    sea_temp_score = self._calculate_range_score(
                        float(sea_temp_val), self.config['sea_temp']['min'], self.config['sea_temp']['max'])
                except (TypeError, ValueError):
                    pass

        # Moon phase (new moon ±5 days)
        moon_age = 15.0
        if marine_data and marine_data.get("moon_info"):
            moon_age = marine_data["moon_info"].get("moon_age", 15)
        elif astronomy and astronomy.get("moon_phase"):
            moon_age = astronomy["moon_phase"].get("moon_age", 15)

        if moon_age > 15:
            moon_age_adj = 29.5 - moon_age
        else:
            moon_age_adj = moon_age
        range_days = self.config['moon_phase']['range_days']
        if moon_age_adj <= range_days:
            moon_score = 100.0
        else:
            moon_score = max(0.0, 100 - (moon_age_adj - range_days) * 4)

        # Worst-case cloud at night
        worst_cloud = self._worst_case_field(night_slots, "cloud_cover", mode="max")
        if worst_cloud is None:
            worst_cloud = 50
        cloud_score = self._normalize_score(worst_cloud, 0, 50, reverse=True)

        score = (season_score * self.config['season']['weight'] +
                 sea_temp_score * self.config['sea_temp']['weight'] +
                 moon_score * self.config['moon_phase']['weight'])

        # Remaining weight for cloud
        remaining = 1.0 - (self.config['season']['weight'] +
                           self.config['sea_temp']['weight'] +
                           self.config['moon_phase']['weight'])
        score += cloud_score * remaining

        # Coast bonus (서·남해 연안) — 게이트를 통과했으므로 항상 적용
        score += self.config.get('south_east_coast_bonus', 10)

        return {
            "score": round(min(100.0, max(0.0, score)), 1),
            "factors": {
                "sea_temperature": sea_temp_val,
                "moon_age": round(moon_age, 1),
                "worst_cloud": round(worst_cloud, 1),
                "uncertainty": "관측 이력 + 수온 기반 가능성, 보장 아님",
            },
            "time_used": "21:00-03:00",
        }


class NightCityscapeScorer(BaseScorer):
    """야경 - Night cityscape scorer (daily, 18:00-21:00)"""

    def __init__(self):
        super().__init__(theme_id=10, theme_name="야경")
        self.config = WEIGHTS['night_cityscape']
        self.relevant_hours = [18, 21]
        self.time_selection = "range"

    async def calculate_score(self, weather_data: dict, ocean_data: Optional[dict] = None) -> float:
        cloud = self._safe_get(weather_data, 'cloud.avg', 50)
        rain = self._safe_get(weather_data, 'rain_prob.avg', 50)
        return min(100.0, max(0.0, 100 - cloud - rain))

    async def calculate_daily_score(self, day_weather: list, date: str,
                                     location_meta: dict, marine_data: dict = None,
                                     astronomy: dict = None) -> dict:
        evening_slots = self._get_timeslots_in_range(day_weather, 18, 21)
        if not evening_slots:
            return {"score": 0, "factors": {"error": "no evening slots"}, "time_used": "N/A"}

        # Average values across evening slots
        avg_cloud = self._avg_field(evening_slots, "cloud_cover") or 50
        avg_rain = self._avg_field(evening_slots, "rain_probability") or 50
        avg_vis = self._avg_field(evening_slots, "visibility") or 10
        avg_wind = self._avg_field(evening_slots, "wind_speed") or 5

        cloud_score = self._normalize_score(avg_cloud, 0, self.config['cloud_cover']['max'], reverse=True)
        rain_score = self._normalize_score(avg_rain, 0, self.config['rain_prob']['max'], reverse=True)
        vis_score = self._normalize_score(avg_vis, self.config['visibility']['min'], 30)
        wind_score = self._normalize_score(avg_wind, 0, self.config['wind_speed']['max'], reverse=True)

        score = (cloud_score * self.config['cloud_cover']['weight'] +
                 rain_score * self.config['rain_prob']['weight'] +
                 vis_score * self.config['visibility']['weight'] +
                 wind_score * self.config['wind_speed']['weight'])

        return {
            "score": round(min(100.0, max(0.0, score)), 1),
            "factors": {
                "avg_cloud": round(avg_cloud, 1),
                "avg_rain": round(avg_rain, 1),
                "avg_visibility_km": round(avg_vis, 1),
            },
            "time_used": "18:00-21:00",
        }


# =============================================================================
# Group C: Dawn-based scorers (03:00-06:00)
# =============================================================================

class FogLandscapeScorer(BaseScorer):
    """안개 - Fog landscape scorer (daily, dawn 03:00-06:00)"""

    def __init__(self):
        super().__init__(theme_id=11, theme_name="안개")
        self.config = WEIGHTS['fog_landscape']
        self.relevant_hours = [3, 6]
        self.time_selection = "range"

    async def calculate_score(self, weather_data: dict, ocean_data: Optional[dict] = None) -> float:
        humidity = self._safe_get(weather_data, 'humidity.avg', 50)
        wind = self._safe_get(weather_data, 'wind_speed.avg', 10)
        return min(100.0, max(0.0, humidity - wind * 5))

    async def calculate_daily_score(self, day_weather: list, date: str,
                                     location_meta: dict, marine_data: dict = None,
                                     astronomy: dict = None) -> dict:
        dawn_slots = self._get_timeslots_in_range(day_weather, 3, 6)
        if not dawn_slots:
            return {"score": 0, "factors": {"error": "no dawn slots"}, "time_used": "N/A"}

        avg_humidity = self._avg_field(dawn_slots, "humidity") or 50
        min_wind = self._worst_case_field(dawn_slots, "wind_speed", mode="min") or 5
        avg_rain = self._avg_field(dawn_slots, "rain_probability") or 50

        humidity_score = self._normalize_score(avg_humidity, self.config['humidity']['min'], 100)
        wind_score = self._normalize_score(min_wind, 0, self.config['wind_speed']['max'], reverse=True)
        rain_score = self._normalize_score(avg_rain, 0, self.config['rain_prob']['max'], reverse=True)

        # Temperature difference approximation (use range of day if available)
        temp_diff_score = 50  # default middle score
        temps = [self._get_weather_value(s, "temperature") for s in day_weather]
        temps = [t for t in temps if t is not None]
        if len(temps) >= 2:
            temp_diff = max(temps) - min(temps)
            temp_diff_score = self._normalize_score(
                temp_diff, self.config['temp_diff_day_night']['min'], 15)

        score = (humidity_score * self.config['humidity']['weight'] +
                 temp_diff_score * self.config['temp_diff_day_night']['weight'] +
                 wind_score * self.config['wind_speed']['weight'] +
                 rain_score * self.config['rain_prob']['weight'])

        return {
            "score": round(min(100.0, max(0.0, score)), 1),
            "factors": {
                "avg_humidity": round(avg_humidity, 1),
                "min_wind": round(min_wind, 1),
                "avg_rain": round(avg_rain, 1),
            },
            "time_used": "03:00-06:00",
        }


class SeaOfCloudsScorer(BaseScorer):
    """운해 - Sea of clouds scorer (daily, dawn 03:00-06:00)"""

    def __init__(self):
        super().__init__(theme_id=8, theme_name="운해")
        self.config = WEIGHTS['sea_of_clouds']
        self.relevant_hours = [3, 6]
        self.time_selection = "range"

    async def calculate_score(self, weather_data: dict, ocean_data: Optional[dict] = None) -> float:
        humidity = self._safe_get(weather_data, 'humidity.avg', 50)
        elevation = self._safe_get(weather_data, 'elevation', 0)
        if elevation < 500:
            return 0.0
        return min(100.0, max(0.0, humidity - 30))

    async def calculate_daily_score(self, day_weather: list, date: str,
                                     location_meta: dict, marine_data: dict = None,
                                     astronomy: dict = None) -> dict:
        elevation = location_meta.get("elevation", 0)
        if elevation < self.config['elevation']['min']:
            return {"score": 0, "factors": {"reason": f"elevation {elevation}m < {self.config['elevation']['min']}m"}, "time_used": "N/A"}

        dawn_slots = self._get_timeslots_in_range(day_weather, 3, 6)
        if not dawn_slots:
            return {"score": 0, "factors": {"error": "no dawn slots"}, "time_used": "N/A"}

        avg_humidity = self._avg_field(dawn_slots, "humidity") or 50
        avg_wind = self._avg_field(dawn_slots, "wind_speed") or 5

        humidity_score = self._normalize_score(avg_humidity, self.config['low_humidity']['min'], 100)
        wind_score = self._normalize_score(avg_wind, 0, self.config['wind_speed']['max'], reverse=True)
        elevation_score = self._normalize_score(elevation, self.config['elevation']['min'], 1500)

        # Temperature inversion proxy: high humidity + low wind = likely inversion
        inversion_score = min(100, humidity_score * 0.5 + wind_score * 0.5)

        score = (humidity_score * self.config['low_humidity']['weight'] +
                 inversion_score * self.config['temp_inversion']['weight'] +
                 wind_score * self.config['wind_speed']['weight'] +
                 elevation_score * self.config['elevation']['weight'])

        return {
            "score": round(min(100.0, max(0.0, score)), 1),
            "factors": {
                "avg_humidity": round(avg_humidity, 1),
                "avg_wind": round(avg_wind, 1),
                "elevation": elevation,
            },
            "time_used": "03:00-06:00",
        }


class FrostRimeScorer(BaseScorer):
    """상고대 - Frost/Rime scorer (daily, dawn 03:00-06:00)"""

    def __init__(self):
        super().__init__(theme_id=15, theme_name="상고대")
        self.config = WEIGHTS['frost_rime']
        self.relevant_hours = [3, 6]
        self.time_selection = "range"

    async def calculate_score(self, weather_data: dict, ocean_data: Optional[dict] = None) -> float:
        temp = self._safe_get(weather_data, 'temp.avg', 10)
        if temp > 0:
            return 0.0
        humidity = self._safe_get(weather_data, 'humidity.avg', 50)
        return min(100.0, max(0.0, humidity + abs(temp) * 5))

    async def calculate_daily_score(self, day_weather: list, date: str,
                                     location_meta: dict, marine_data: dict = None,
                                     astronomy: dict = None) -> dict:
        # Season check (Nov-Feb)
        try:
            month = datetime.fromisoformat(date).month
        except (ValueError, TypeError):
            month = datetime.now().month
        if month not in self.config['season']['months']:
            return {"score": 0, "factors": {"reason": "off_season"}, "time_used": "N/A"}

        dawn_slots = self._get_timeslots_in_range(day_weather, 3, 6)
        if not dawn_slots:
            return {"score": 0, "factors": {"error": "no dawn slots"}, "time_used": "N/A"}

        min_temp = self._worst_case_field(dawn_slots, "temperature", mode="min")
        if min_temp is None:
            min_temp = 5
        if min_temp > 0:
            return {"score": 0, "factors": {"reason": f"temp {min_temp}°C > 0°C"}, "time_used": "03:00-06:00"}

        avg_humidity = self._avg_field(dawn_slots, "humidity") or 50
        avg_wind = self._avg_field(dawn_slots, "wind_speed") or 5
        avg_cloud = self._avg_field(dawn_slots, "cloud_cover") or 50

        temp_score = self._normalize_score(min_temp, self.config['temp']['max'], 5, reverse=True)
        humidity_score = self._normalize_score(avg_humidity, self.config['humidity']['min'], 100)
        wind_score = self._normalize_score(avg_wind, 0, self.config['wind_speed']['max'], reverse=True)
        cloud_score = self._normalize_score(avg_cloud, 0, self.config['cloud_cover']['max'], reverse=True)

        score = (temp_score * self.config['temp']['weight'] +
                 humidity_score * self.config['humidity']['weight'] +
                 wind_score * self.config['wind_speed']['weight'] +
                 cloud_score * self.config['cloud_cover']['weight'])

        # Mountain bonus
        elevation = location_meta.get("elevation", 0)
        if elevation >= 500:
            score += 10

        return {
            "score": round(min(100.0, max(0.0, score)), 1),
            "factors": {
                "min_temp": round(min_temp, 1),
                "avg_humidity": round(avg_humidity, 1),
                "avg_wind": round(avg_wind, 1),
                "elevation": elevation,
            },
            "time_used": "03:00-06:00",
        }


# =============================================================================
# Group D: Daytime/tide-based scorers
# =============================================================================

class SeaLongExposureEastScorer(BaseScorer):
    """바다 장노출(동해) - Sea long exposure scorer for East Coast (daily, wave-based)"""

    def __init__(self):
        super().__init__(theme_id=7, theme_name="바다 장노출(동해)")
        self.config = WEIGHTS['sea_long_exposure_east']
        self.relevant_hours = [6, 9, 12, 15, 18]
        self.time_selection = "closest"

    async def calculate_score(self, weather_data: dict, ocean_data: Optional[dict] = None) -> float:
        if not ocean_data:
            return 0.0
        wh = ocean_data.get('wave_height', {})
        wave = float(wh.get('height', 0)) if isinstance(wh, dict) else float(wh if wh else 0)
        if wave < 2.0:
            return 0.0
        return min(100.0, max(0.0, (wave - 2) / 2 * 100))

    async def calculate_daily_score(self, day_weather: list, date: str,
                                     location_meta: dict, marine_data: dict = None,
                                     astronomy: dict = None) -> dict:
        # GATE: East coast check
        if not location_meta.get("is_east_coast"):
            return {"score": 0, "factors": {"reason": "동해 아님"}, "time_used": "N/A"}

        # GATE: Marine data and wave height check
        if not marine_data or not marine_data.get("wave_height"):
            return {"score": 0, "factors": {"reason": "no wave data"}, "time_used": "N/A"}

        wave_height_data = marine_data["wave_height"].get("height")
        if wave_height_data is None:
            return {"score": 0, "factors": {"reason": "no wave data"}, "time_used": "N/A"}

        try:
            wave_height = float(wave_height_data)
        except (TypeError, ValueError):
            return {"score": 0, "factors": {"reason": "invalid wave data"}, "time_used": "N/A"}

        # HARD GATE: wave < 2m → score 0 (scoring only within 2~4m range)
        if wave_height < 2.0:
            return {"score": 0, "factors": {"wave_height": round(wave_height, 2), "reason": "파고 2m 미만"}, "time_used": "N/A"}

        # Wave score: linear from 2m=0pts to 4m=100pts
        wave_score = min(100, max(0, (wave_height - 2) / 2 * 100))

        # Find closest timeslot to midday (12)
        slot = self._find_closest_timeslot(day_weather, 12)
        if not slot:
            return {"score": 0, "factors": {"error": "no timeslot"}, "time_used": "N/A"}

        wind_speed = self._get_weather_value(slot, "wind_speed", 5)
        rain_probability = self._get_weather_value(slot, "rain_probability", 50)

        # Wind score
        wind_score = self._normalize_score(wind_speed, 0, self.config['wind_speed']['max'], reverse=True)

        # Storm score
        storm_score = 0 if marine_data.get("storm_warning") else 100

        # Rain score
        rain_score = self._normalize_score(rain_probability, 0, self.config['rain_prob']['max'], reverse=True)

        # Final score: wave*0.45 + wind*0.25 + storm*0.20 + rain*0.10
        score = (wave_score * 0.45 +
                 wind_score * 0.25 +
                 storm_score * 0.20 +
                 rain_score * 0.10)

        return {
            "score": round(min(100.0, max(0.0, score)), 1),
            "factors": {
                "wave_height": round(wave_height, 2),
                "wind_speed": round(wind_speed, 1),
                "storm_warning": bool(marine_data.get("storm_warning")),
            },
            "time_used": "12:00",
        }


class SeaLongExposureWestScorer(BaseScorer):
    """바다 장노출(서해) - Sea long exposure scorer for West Coast (daily, tide-based)"""

    def __init__(self):
        super().__init__(theme_id=17, theme_name="바다 장노출(서해)")
        self.config = WEIGHTS['sea_long_exposure_west']
        self.relevant_hours = [6, 9, 12, 15, 18]
        self.time_selection = "closest"

    async def calculate_score(self, weather_data: dict, ocean_data: Optional[dict] = None) -> float:
        return 50.0

    async def calculate_daily_score(self, day_weather: list, date: str,
                                     location_meta: dict, marine_data: dict = None,
                                     astronomy: dict = None) -> dict:
        # GATE: West coast check
        if not location_meta.get("is_west_coast"):
            return {"score": 0, "factors": {"reason": "서해 아님"}, "time_used": "N/A"}

        # GATE: Tide data check
        if not marine_data or not marine_data.get("tide_info"):
            return {"score": 0, "factors": {"reason": "no tide data"}, "time_used": "N/A"}

        tide_info = marine_data["tide_info"]
        if not tide_info.get("forecasts"):
            return {"score": 0, "factors": {"reason": "no tide forecasts"}, "time_used": "N/A"}

        # Calculate tidal range from forecasts
        forecasts = tide_info["forecasts"]
        heights = []
        for f in forecasts:
            h = f.get("tph_level") or f.get("height")
            if h is not None:
                try:
                    heights.append(float(h))
                except (TypeError, ValueError):
                    continue

        if not heights:
            return {"score": 0, "factors": {"reason": "no valid tide heights"}, "time_used": "N/A"}

        tidal_range = max(heights) - min(heights)
        high_tide_cm = max(heights)
        low_tide_cm = min(heights)

        # Find low tide time
        low_tide_hour = 12  # default
        for forecast in forecasts:
            tide_type = forecast.get("hl_code") or forecast.get("type", "")
            if tide_type == "저조" or tide_type == "low":
                tide_time = forecast.get("tph_time") or forecast.get("time", "")
                t = _parse_time_str(tide_time)
                if t:
                    low_tide_hour = t[0]
                    break

        # Tidal range score: linear from 300cm=0pts to 650cm=100pts
        tidal_score = min(100, max(0, (tidal_range - 300) / 350 * 100))

        # Find closest timeslot to low tide hour
        slot = self._find_closest_timeslot(day_weather, low_tide_hour)
        if not slot:
            return {"score": 0, "factors": {"error": "no timeslot"}, "time_used": "N/A"}

        wind_speed = self._get_weather_value(slot, "wind_speed", 5)
        rain_probability = self._get_weather_value(slot, "rain_probability", 50)

        # Wind score
        wind_score = self._normalize_score(wind_speed, 0, self.config['wind_speed']['max'], reverse=True)

        # Storm score
        storm_score = 0 if marine_data.get("storm_warning") else 100

        # Rain score
        rain_score = self._normalize_score(rain_probability, 0, self.config['rain_prob']['max'], reverse=True)

        # Final score: tidal*0.45 + wind*0.20 + storm*0.20 + rain*0.15
        score = (tidal_score * 0.45 +
                 wind_score * 0.20 +
                 storm_score * 0.20 +
                 rain_score * 0.15)

        return {
            "score": round(min(100.0, max(0.0, score)), 1),
            "factors": {
                "tidal_range_cm": round(tidal_range, 1),
                "high_tide_cm": round(high_tide_cm, 1),
                "low_tide_cm": round(low_tide_cm, 1),
                "wind_speed": round(wind_speed, 1),
            },
            "time_used": f"{low_tide_hour:02d}:00",
        }


class SeaLongExposureSouthScorer(BaseScorer):
    """바다 장노출(남해) - Sea long exposure scorer for South Coast (daily, tide-based)"""

    def __init__(self):
        super().__init__(theme_id=18, theme_name="바다 장노출(남해)")
        self.config = WEIGHTS['sea_long_exposure_south']
        self.relevant_hours = [6, 9, 12, 15, 18]
        self.time_selection = "closest"

    async def calculate_score(self, weather_data: dict, ocean_data: Optional[dict] = None) -> float:
        return 50.0

    async def calculate_daily_score(self, day_weather: list, date: str,
                                     location_meta: dict, marine_data: dict = None,
                                     astronomy: dict = None) -> dict:
        # GATE: South coast check
        is_south = (location_meta.get("is_south_coast") or
                    (location_meta.get("is_coastal") and
                     not location_meta.get("is_east_coast") and
                     not location_meta.get("is_west_coast")))

        if not is_south:
            return {"score": 0, "factors": {"reason": "남해 아님"}, "time_used": "N/A"}

        # GATE: Tide data check
        if not marine_data or not marine_data.get("tide_info"):
            return {"score": 0, "factors": {"reason": "no tide data"}, "time_used": "N/A"}

        tide_info = marine_data["tide_info"]
        if not tide_info.get("forecasts"):
            return {"score": 0, "factors": {"reason": "no tide forecasts"}, "time_used": "N/A"}

        # Calculate tidal range from forecasts
        forecasts = tide_info["forecasts"]
        heights = []
        for f in forecasts:
            h = f.get("tph_level") or f.get("height")
            if h is not None:
                try:
                    heights.append(float(h))
                except (TypeError, ValueError):
                    continue

        if not heights:
            return {"score": 0, "factors": {"reason": "no valid tide heights"}, "time_used": "N/A"}

        tidal_range = max(heights) - min(heights)
        high_tide_cm = max(heights)
        low_tide_cm = min(heights)

        # Find low tide time
        low_tide_hour = 12  # default
        for forecast in forecasts:
            tide_type = forecast.get("hl_code") or forecast.get("type", "")
            if tide_type == "저조" or tide_type == "low":
                tide_time = forecast.get("tph_time") or forecast.get("time", "")
                t = _parse_time_str(tide_time)
                if t:
                    low_tide_hour = t[0]
                    break

        # Tidal range score: linear from 100cm=0pts to 300cm=100pts
        tidal_score = min(100, max(0, (tidal_range - 100) / 200 * 100))

        # Find closest timeslot to low tide hour
        slot = self._find_closest_timeslot(day_weather, low_tide_hour)
        if not slot:
            return {"score": 0, "factors": {"error": "no timeslot"}, "time_used": "N/A"}

        wind_speed = self._get_weather_value(slot, "wind_speed", 5)
        rain_probability = self._get_weather_value(slot, "rain_probability", 50)

        # Wind score
        wind_score = self._normalize_score(wind_speed, 0, self.config['wind_speed']['max'], reverse=True)

        # Storm score
        storm_score = 0 if marine_data.get("storm_warning") else 100

        # Rain score
        rain_score = self._normalize_score(rain_probability, 0, self.config['rain_prob']['max'], reverse=True)

        # Final score: tidal*0.45 + wind*0.20 + storm*0.20 + rain*0.15
        score = (tidal_score * 0.45 +
                 wind_score * 0.20 +
                 storm_score * 0.20 +
                 rain_score * 0.15)

        return {
            "score": round(min(100.0, max(0.0, score)), 1),
            "factors": {
                "tidal_range_cm": round(tidal_range, 1),
                "high_tide_cm": round(high_tide_cm, 1),
                "low_tide_cm": round(low_tide_cm, 1),
                "wind_speed": round(wind_speed, 1),
            },
            "time_used": f"{low_tide_hour:02d}:00",
        }


class ReflectionScorer(BaseScorer):
    """반영 - Reflection scorer (daily, sunrise & sunset hours)"""

    def __init__(self):
        super().__init__(theme_id=12, theme_name="반영")
        self.config = WEIGHTS['reflection']
        self.relevant_hours = [6, 9, 15, 18]
        self.time_selection = "closest"

    async def calculate_score(self, weather_data: dict, ocean_data: Optional[dict] = None) -> float:
        wind = self._safe_get(weather_data, 'wind_speed.avg', 10)
        return min(100.0, max(0.0, 100 - wind * 20))

    async def calculate_daily_score(self, day_weather: list, date: str,
                                     location_meta: dict, marine_data: dict = None,
                                     astronomy: dict = None) -> dict:
        sunrise_hour, sunset_hour = 7, 18
        if marine_data and marine_data.get("sun_info"):
            t = _parse_time_str(marine_data["sun_info"].get("sunrise"))
            if t:
                sunrise_hour = t[0]
            t = _parse_time_str(marine_data["sun_info"].get("sunset"))
            if t:
                sunset_hour = t[0]

        sunrise_slot = self._find_closest_timeslot(day_weather, sunrise_hour)
        sunset_slot = self._find_closest_timeslot(day_weather, sunset_hour)

        best_score = 0
        best_factors = {}
        best_time = "N/A"

        for slot, label in [(sunrise_slot, "sunrise"), (sunset_slot, "sunset")]:
            if not slot:
                continue
            wind = self._get_weather_value(slot, "wind_speed", 10)
            rain = self._get_weather_value(slot, "rain_probability", 50)
            cloud = self._get_weather_value(slot, "cloud_cover", 50)
            vis = self._get_weather_value(slot, "visibility", 10)

            # Wind is critical for reflection (calm water)
            wind_s = self._normalize_score(wind, 0, self.config['wind_speed']['max'], reverse=True)
            rain_s = self._normalize_score(rain, 0, self.config['rain_prob']['max'], reverse=True)
            cloud_s = self._calculate_range_score(cloud, self.config['cloud_cover']['min'], self.config['cloud_cover']['max'])
            vis_s = self._normalize_score(vis, self.config['visibility']['min'], 30)

            s = (wind_s * self.config['wind_speed']['weight'] +
                 rain_s * self.config['rain_prob']['weight'] +
                 cloud_s * self.config['cloud_cover']['weight'] +
                 vis_s * self.config['visibility']['weight'])

            if s > best_score:
                best_score = s
                h = _slot_hour(slot)
                best_time = f"{h:02d}:00" if h is not None else label
                best_factors = {
                    "wind_speed": round(wind, 1),
                    "cloud_cover": round(cloud, 1),
                    "period": label,
                }

        return {
            "score": round(min(100.0, max(0.0, best_score)), 1),
            "factors": best_factors,
            "time_used": best_time,
        }


# =============================================================================
# Exports
# =============================================================================

ALL_SCORERS = [
    SunriseScorer,
    SunriseOmegaScorer,
    SunsetScorer,
    SunsetOmegaScorer,
    MilkyWayScorer,
    BioluminescenceScorer,
    SeaLongExposureEastScorer,
    SeaLongExposureWestScorer,
    SeaLongExposureSouthScorer,
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
    """Get scorer instance by theme ID"""
    for scorer_class in ALL_SCORERS:
        scorer = scorer_class()
        if scorer.theme_id == theme_id:
            return scorer
    return None


def get_all_scorers() -> list:
    """Get all scorer instances"""
    return [scorer_class() for scorer_class in ALL_SCORERS]
