"""
천문 계산 유틸리티

은하수 촬영을 위한 무월광 시간대, 월령, 은하수 가시성 계산
"""
import ephem
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import math


# 한국 기준 관측 위치 (서울)
DEFAULT_LAT = "37.5665"
DEFAULT_LON = "126.9780"


def get_observer(lat: float = None, lon: float = None, date: datetime = None) -> ephem.Observer:
    """관측자 객체 생성"""
    observer = ephem.Observer()
    observer.lat = str(lat) if lat else DEFAULT_LAT
    observer.lon = str(lon) if lon else DEFAULT_LON
    observer.elevation = 0

    if date:
        observer.date = ephem.Date(date)
    else:
        observer.date = ephem.Date(datetime.utcnow())

    return observer


def get_moon_phase(date: datetime = None) -> Dict:
    """
    월령(Moon Phase) 계산

    Returns:
        moon_age: 음력 날짜 (0-29.5, 0/29.5 = 삭, 14.75 = 보름)
        illumination: 조도 (0-100%)
        phase_name: 단계 이름
        is_dark_moon: 무월광 여부 (촬영 적합)
    """
    if date is None:
        date = datetime.now()

    moon = ephem.Moon()
    observer = get_observer(date=date)
    moon.compute(observer)

    # 월령 계산 (신월로부터 경과일)
    prev_new = ephem.previous_new_moon(observer.date)
    moon_age = observer.date - prev_new

    # 조도 (0-100%)
    illumination = moon.phase

    # 단계 이름
    if moon_age < 1.85:
        phase_name = "삭 (신월)"
    elif moon_age < 7.38:
        phase_name = "초승달"
    elif moon_age < 11.07:
        phase_name = "상현달"
    elif moon_age < 14.76:
        phase_name = "상현망간"
    elif moon_age < 18.45:
        phase_name = "보름달"
    elif moon_age < 22.14:
        phase_name = "하현망간"
    elif moon_age < 25.83:
        phase_name = "하현달"
    else:
        phase_name = "그믐달"

    # 무월광 판정 (조도 25% 미만)
    is_dark_moon = illumination < 25

    return {
        "moon_age": round(float(moon_age), 1),
        "illumination": round(float(illumination), 1),
        "phase_name": phase_name,
        "is_dark_moon": is_dark_moon,
    }


def get_moon_times(date: datetime = None, lat: float = None, lon: float = None) -> Dict:
    """
    월출/월몰 시간 계산

    Returns:
        moonrise: 월출 시간 (KST)
        moonset: 월몰 시간 (KST)
        moon_up_duration: 달이 떠있는 시간 (hours)
    """
    if date is None:
        date = datetime.now()

    observer = get_observer(lat, lon, date)
    moon = ephem.Moon()

    try:
        # UTC로 계산 후 KST로 변환 (+9시간)
        moonrise_utc = observer.next_rising(moon)
        moonset_utc = observer.next_setting(moon)

        moonrise_kst = ephem.Date(moonrise_utc).datetime() + timedelta(hours=9)
        moonset_kst = ephem.Date(moonset_utc).datetime() + timedelta(hours=9)

        # 달이 떠있는 시간
        if moonset_utc > moonrise_utc:
            moon_up = (moonset_utc - moonrise_utc) * 24
        else:
            moon_up = 24 - (moonrise_utc - moonset_utc) * 24

        return {
            "moonrise": moonrise_kst.strftime("%H:%M"),
            "moonset": moonset_kst.strftime("%H:%M"),
            "moonrise_datetime": moonrise_kst,
            "moonset_datetime": moonset_kst,
            "moon_up_hours": round(float(moon_up), 1),
        }
    except (ephem.AlwaysUpError, ephem.NeverUpError):
        return {
            "moonrise": None,
            "moonset": None,
            "moon_up_hours": None,
            "note": "극지방 또는 계산 불가"
        }


def get_sunrise_sunset(date: datetime = None, lat: float = None, lon: float = None) -> Dict:
    """
    일출/일몰 시간 계산 (ephem 기반, 연중 가능)

    Args:
        date: 계산할 날짜 (기본: 오늘)
        lat: 위도
        lon: 경도

    Returns:
        {
            "sunrise": "HH:MM" (KST),
            "sunset": "HH:MM" (KST),
            "sunrise_datetime": datetime,
            "sunset_datetime": datetime
        }
    """
    if date is None:
        date = datetime.now()

    observer = get_observer(lat, lon, date)
    sun = ephem.Sun()

    try:
        # UTC로 계산 후 KST로 변환 (+9시간)
        sunrise_utc = observer.next_rising(sun)
        sunset_utc = observer.next_setting(sun)

        sunrise_kst = ephem.Date(sunrise_utc).datetime() + timedelta(hours=9)
        sunset_kst = ephem.Date(sunset_utc).datetime() + timedelta(hours=9)

        return {
            "sunrise": sunrise_kst.strftime("%H:%M"),
            "sunset": sunset_kst.strftime("%H:%M"),
            "sunrise_datetime": sunrise_kst,
            "sunset_datetime": sunset_kst,
        }
    except (ephem.AlwaysUpError, ephem.NeverUpError):
        return {
            "sunrise": None,
            "sunset": None,
            "sunrise_datetime": None,
            "sunset_datetime": None,
            "note": "극지방 또는 계산 불가"
        }


def get_astronomical_twilight(date: datetime = None, lat: float = None, lon: float = None) -> Dict:
    """
    천문박명 시간 계산 (태양이 지평선 아래 18도)
    은하수 촬영 가능 시간 = 천문박명 이후

    Returns:
        evening_twilight: 저녁 천문박명 종료 시간 (완전한 어둠 시작)
        morning_twilight: 새벽 천문박명 시작 시간 (완전한 어둠 종료)
        dark_hours: 완전한 어둠 시간
    """
    if date is None:
        date = datetime.now()

    observer = get_observer(lat, lon, date)
    observer.horizon = '-18'  # 천문박명 (18도)

    sun = ephem.Sun()

    try:
        # 저녁 천문박명 종료 (해가 -18도 아래로)
        evening_twilight_utc = observer.next_setting(sun, use_center=True)

        # 새벽 천문박명 시작 (해가 -18도 위로)
        morning_twilight_utc = observer.next_rising(sun, use_center=True)

        evening_kst = ephem.Date(evening_twilight_utc).datetime() + timedelta(hours=9)
        morning_kst = ephem.Date(morning_twilight_utc).datetime() + timedelta(hours=9)

        # 완전한 어둠 시간
        dark_hours = (morning_twilight_utc - evening_twilight_utc) * 24

        return {
            "evening_twilight": evening_kst.strftime("%H:%M"),
            "morning_twilight": morning_kst.strftime("%H:%M"),
            "evening_datetime": evening_kst,
            "morning_datetime": morning_kst,
            "dark_hours": round(float(dark_hours), 1),
        }
    except Exception:
        return {
            "evening_twilight": None,
            "morning_twilight": None,
            "dark_hours": None,
        }


def get_milky_way_visibility(date: datetime = None, lat: float = None, lon: float = None) -> Dict:
    """
    은하수 가시성 계산

    은하수 중심부 (궁수자리 방향) 관측 조건:
    - 시즌: 3월~10월 (한국 기준)
    - 최적: 5월~8월
    - 방향: 남쪽 하늘

    Returns:
        season_ok: 시즌 내 여부
        season_quality: 시즌 품질 (optimal/good/marginal/off)
        core_altitude: 은하수 중심부 고도
        best_time: 최적 관측 시간
        dark_window: 무월광 + 천문박명 시간대
    """
    if date is None:
        date = datetime.now()

    month = date.month

    # 시즌 판정
    if month in [5, 6, 7, 8]:
        season_quality = "optimal"
        season_ok = True
    elif month in [4, 9]:
        season_quality = "good"
        season_ok = True
    elif month in [3, 10]:
        season_quality = "marginal"
        season_ok = True
    else:
        season_quality = "off"
        season_ok = False

    # 천문박명 시간
    twilight = get_astronomical_twilight(date, lat, lon)

    # 월령 정보
    moon_phase = get_moon_phase(date)

    # 월출/월몰 시간
    moon_times = get_moon_times(date, lat, lon)

    # 무월광 시간대 계산
    dark_window = calculate_dark_window(twilight, moon_times, moon_phase)

    # 은하수 중심부 고도 계산 (궁수자리 좌표: RA 18h, Dec -29°)
    observer = get_observer(lat, lon, date)
    galactic_center = ephem.FixedBody()
    galactic_center._ra = ephem.hours("18:00:00")
    galactic_center._dec = ephem.degrees("-29:00:00")

    # 자정 기준 고도
    midnight = date.replace(hour=15, minute=0, second=0)  # UTC 15시 = KST 0시
    observer.date = ephem.Date(midnight)
    galactic_center.compute(observer)

    core_altitude = float(galactic_center.alt) * 180 / math.pi

    return {
        "date": date.strftime("%Y-%m-%d"),
        "season_ok": season_ok,
        "season_quality": season_quality,
        "moon_phase": moon_phase,
        "moon_times": moon_times,
        "twilight": twilight,
        "dark_window": dark_window,
        "core_altitude": round(core_altitude, 1),
        "recommendation": get_milky_way_recommendation(season_ok, moon_phase, dark_window, core_altitude),
    }


def calculate_dark_window(twilight: Dict, moon_times: Dict, moon_phase: Dict) -> Dict:
    """
    무월광 촬영 가능 시간대 계산 (time-interval subtraction)

    dark_period = [evening_twilight, morning_twilight]
    if moon is bright (illumination >= 25%):
        moon_up_period = [moonrise, moonset] clipped to dark_period
        dark_window = dark_period - moon_up_period

    Handles all cases: moon up all night, moon down all night,
    moonrise during dark, moonset during dark, both during dark.
    """
    evening = twilight.get("evening_datetime")
    morning = twilight.get("morning_datetime")
    moonrise = moon_times.get("moonrise_datetime")
    moonset = moon_times.get("moonset_datetime")
    is_dark_moon = moon_phase.get("is_dark_moon", False)
    illumination = moon_phase.get("illumination", 0)

    if not evening or not morning:
        return {"available": False, "reason": "박명 시간 계산 불가"}

    total_dark_hours = twilight.get("dark_hours", 0)

    # 무월광이면 (조도 25% 미만) 전체 어둠 시간이 촬영 가능
    if is_dark_moon:
        return {
            "available": True,
            "start": evening.strftime("%H:%M"),
            "end": morning.strftime("%H:%M"),
            "duration_hours": total_dark_hours,
            "condition": "무월광 (전체 어둠 시간 촬영 가능)",
        }

    # 달이 밝은 경우: 달이 떠있는 시간을 dark_period에서 빼기
    # moonrise/moonset이 없으면 달이 항상 떠있거나 항상 져있는 경우
    if moonrise is None and moonset is None:
        # moon_up_hours로 판단
        moon_up_hours = moon_times.get("moon_up_hours")
        if moon_up_hours is None:
            # 계산 불가 - 밝은 달이므로 보수적으로 불가 판정
            return {
                "available": False,
                "reason": f"월광 영향 (조도 {illumination}%)",
            }
        # AlwaysUp/NeverUp은 get_moon_times에서 None 반환
        return {
            "available": False,
            "reason": f"월광 영향 (조도 {illumination}%, 월출몰 계산 불가)",
        }

    # 달이 떠있는 구간 계산 (dark period 내에서)
    # moonrise < moonset: 달이 moonrise에 뜨고 moonset에 짐
    # moonrise > moonset: 달이 이미 떠있다가 moonset에 지고, moonrise에 다시 뜸

    dark_segments = []  # (start, end) tuples of moonless dark periods

    if moonrise and moonset:
        if moonrise < moonset:
            # 달이 moonrise~moonset 동안 떠있음
            # dark window = [evening, moonrise] + [moonset, morning]
            moon_up_start = max(moonrise, evening)
            moon_up_end = min(moonset, morning)

            if moon_up_start >= morning or moon_up_end <= evening:
                # 달이 떠있는 시간이 dark period 밖
                dark_segments.append((evening, morning))
            else:
                # dark period 앞부분 (evening ~ moon_up_start)
                if moon_up_start > evening:
                    dark_segments.append((evening, moon_up_start))
                # dark period 뒷부분 (moon_up_end ~ morning)
                if moon_up_end < morning:
                    dark_segments.append((moon_up_end, morning))
        else:
            # moonrise > moonset: 달이 이미 떠있다가 moonset에 지고 moonrise에 다시 뜸
            # moon UP = [evening, moonset] + [moonrise, morning]
            # dark window = [moonset, moonrise] clipped to dark period
            clip_start = max(moonset, evening)
            clip_end = min(moonrise, morning)
            if clip_start < clip_end:
                dark_segments.append((clip_start, clip_end))

    elif moonrise and not moonset:
        # 달이 moonrise에 뜬 후 dark period 내에서 지지 않음
        # dark window = [evening, moonrise]
        clip_rise = max(moonrise, evening)
        if clip_rise > evening and clip_rise <= morning:
            dark_segments.append((evening, clip_rise))
        elif moonrise > morning:
            # 월출이 dark period 이후 → 전체가 dark
            dark_segments.append((evening, morning))

    elif moonset and not moonrise:
        # 달이 이미 떠있다가 moonset에 짐, 이후 뜨지 않음
        # dark window = [moonset, morning]
        clip_set = min(moonset, morning)
        if clip_set < morning and clip_set >= evening:
            dark_segments.append((clip_set, morning))
        elif moonset < evening:
            # 월몰이 dark period 이전 → 전체가 dark
            dark_segments.append((evening, morning))

    if not dark_segments:
        return {
            "available": False,
            "reason": f"월광 영향 (조도 {illumination}%)",
        }

    # 가장 긴 dark segment를 주 창으로 사용
    best_seg = max(dark_segments, key=lambda s: (s[1] - s[0]).total_seconds())
    duration = round((best_seg[1] - best_seg[0]).total_seconds() / 3600, 1)

    # 전체 dark 시간 합산
    total_duration = round(sum(
        (seg[1] - seg[0]).total_seconds() / 3600 for seg in dark_segments
    ), 1)

    if duration < 0.5:
        return {
            "available": False,
            "reason": f"무월광 시간 부족 ({duration}시간, 조도 {illumination}%)",
        }

    # 조건 문자열 생성
    if len(dark_segments) == 1:
        condition = f"{best_seg[0].strftime('%H:%M')}~{best_seg[1].strftime('%H:%M')} 촬영 가능"
    else:
        parts = [f"{s[0].strftime('%H:%M')}~{s[1].strftime('%H:%M')}" for s in dark_segments]
        condition = f"촬영 가능 구간: {', '.join(parts)}"

    return {
        "available": True,
        "start": best_seg[0].strftime("%H:%M"),
        "end": best_seg[1].strftime("%H:%M"),
        "duration_hours": total_duration,
        "segments": [
            {"start": s[0].strftime("%H:%M"), "end": s[1].strftime("%H:%M"),
             "hours": round((s[1] - s[0]).total_seconds() / 3600, 1)}
            for s in dark_segments
        ],
        "condition": condition,
    }


def get_milky_way_recommendation(season_ok: bool, moon_phase: Dict, dark_window: Dict, altitude: float) -> str:
    """은하수 촬영 추천 메시지 생성"""

    if not season_ok:
        return "❌ 비시즌 (11월~2월) - 은하수 중심부 관측 불가"

    if not dark_window.get("available"):
        return f"⚠️ {dark_window.get('reason', '무월광 시간 없음')}"

    if altitude < 10:
        return "⚠️ 은하수 중심부 고도 낮음 - 남쪽 지평선이 트인 장소 필요"

    duration = dark_window.get("duration_hours", 0)
    if duration < 2:
        return f"⚠️ 무월광 시간 짧음 ({duration}시간)"

    if moon_phase.get("is_dark_moon"):
        return f"🌌 최적 조건! 무월광 {duration}시간 ({dark_window.get('start')}~{dark_window.get('end')})"
    else:
        return f"✅ 촬영 가능 ({dark_window.get('condition')})"


def get_monthly_milky_way_calendar(year: int, month: int) -> List[Dict]:
    """
    월간 은하수 촬영 캘린더 생성

    Returns:
        해당 월의 일별 은하수 촬영 조건
    """
    import calendar

    _, days_in_month = calendar.monthrange(year, month)

    calendar_data = []
    for day in range(1, days_in_month + 1):
        date = datetime(year, month, day)
        visibility = get_milky_way_visibility(date)

        calendar_data.append({
            "date": date.strftime("%Y-%m-%d"),
            "day": day,
            "weekday": date.strftime("%a"),
            "moon_age": visibility["moon_phase"]["moon_age"],
            "illumination": visibility["moon_phase"]["illumination"],
            "phase_name": visibility["moon_phase"]["phase_name"],
            "is_dark_moon": visibility["moon_phase"]["is_dark_moon"],
            "dark_window": visibility["dark_window"],
            "score": calculate_milky_way_score(visibility),
        })

    return calendar_data


def calculate_milky_way_score(visibility: Dict) -> int:
    """은하수 촬영 점수 계산 (0-100)"""

    score = 0

    # 시즌 점수 (40점)
    season_scores = {"optimal": 40, "good": 30, "marginal": 15, "off": 0}
    score += season_scores.get(visibility.get("season_quality", "off"), 0)

    # 무월광 점수 (40점)
    dark_window = visibility.get("dark_window", {})
    if dark_window.get("available"):
        duration = dark_window.get("duration_hours", 0)
        if duration >= 6:
            score += 40
        elif duration >= 4:
            score += 30
        elif duration >= 2:
            score += 20
        else:
            score += 10

    # 은하수 고도 점수 (20점)
    altitude = visibility.get("core_altitude", 0)
    if altitude >= 30:
        score += 20
    elif altitude >= 20:
        score += 15
    elif altitude >= 10:
        score += 10

    return min(100, score)


# 테스트
if __name__ == "__main__":
    print("=" * 60)
    print("은하수 촬영 조건 테스트")
    print("=" * 60)

    # 오늘 조건
    today = datetime.now()
    result = get_milky_way_visibility(today)

    print(f"\n📅 {result['date']}")
    print(f"\n🌙 월령 정보:")
    print(f"   음력: {result['moon_phase']['moon_age']}일")
    print(f"   조도: {result['moon_phase']['illumination']}%")
    print(f"   상태: {result['moon_phase']['phase_name']}")
    print(f"   무월광: {'예' if result['moon_phase']['is_dark_moon'] else '아니오'}")

    print(f"\n🌅 월출/월몰:")
    print(f"   월출: {result['moon_times'].get('moonrise', '-')}")
    print(f"   월몰: {result['moon_times'].get('moonset', '-')}")

    print(f"\n🌌 은하수 조건:")
    print(f"   시즌: {result['season_quality']}")
    print(f"   중심부 고도: {result['core_altitude']}°")

    print(f"\n⏰ 무월광 시간대:")
    dw = result['dark_window']
    if dw.get('available'):
        print(f"   {dw['start']} ~ {dw['end']} ({dw['duration_hours']}시간)")
        print(f"   조건: {dw.get('condition', '-')}")
    else:
        print(f"   ❌ {dw.get('reason', '불가')}")

    print(f"\n💡 추천: {result['recommendation']}")
