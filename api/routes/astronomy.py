"""천문 정보 API - 은하수, 월령, 무월광 시간대"""
from fastapi import APIRouter, Query
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from utils.astronomy import (
    get_moon_phase,
    get_moon_times,
    get_astronomical_twilight,
    get_milky_way_visibility,
    get_monthly_milky_way_calendar,
    calculate_milky_way_score,
)

router = APIRouter()


@router.get("/astronomy/moon")
async def get_moon_info(
    date: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
) -> Dict[str, Any]:
    """
    월령 및 월출/월몰 정보

    Args:
        date: 날짜 (YYYY-MM-DD, 기본: 오늘)
        lat: 위도 (기본: 서울)
        lon: 경도 (기본: 서울)

    Returns:
        월령, 조도, 월출/월몰 시간
    """
    if date:
        target_date = datetime.strptime(date, "%Y-%m-%d")
    else:
        target_date = datetime.now()

    phase = get_moon_phase(target_date)
    times = get_moon_times(target_date, lat, lon)

    return {
        "date": target_date.strftime("%Y-%m-%d"),
        "phase": phase,
        "times": times,
    }


@router.get("/astronomy/milky-way")
async def get_milky_way_info(
    date: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
) -> Dict[str, Any]:
    """
    은하수 촬영 조건 조회

    Args:
        date: 날짜 (YYYY-MM-DD, 기본: 오늘)
        lat: 위도 (기본: 서울)
        lon: 경도 (기본: 서울)

    Returns:
        시즌, 무월광 시간대, 추천 메시지
    """
    if date:
        target_date = datetime.strptime(date, "%Y-%m-%d")
    else:
        target_date = datetime.now()

    visibility = get_milky_way_visibility(target_date, lat, lon)
    score = calculate_milky_way_score(visibility)

    return {
        "date": visibility["date"],
        "score": score,
        "season": {
            "ok": visibility["season_ok"],
            "quality": visibility["season_quality"],
            "months": "3월~10월 (최적: 5월~8월)",
        },
        "moon": {
            "age": visibility["moon_phase"]["moon_age"],
            "illumination": visibility["moon_phase"]["illumination"],
            "phase_name": visibility["moon_phase"]["phase_name"],
            "is_dark": visibility["moon_phase"]["is_dark_moon"],
            "rise": visibility["moon_times"].get("moonrise"),
            "set": visibility["moon_times"].get("moonset"),
        },
        "dark_window": visibility["dark_window"],
        "galactic_center_altitude": visibility["core_altitude"],
        "recommendation": visibility["recommendation"],
    }


@router.get("/astronomy/milky-way/calendar")
async def get_milky_way_calendar(
    year: int = Query(default=None),
    month: int = Query(ge=1, le=12, default=None),
) -> Dict[str, Any]:
    """
    월간 은하수 촬영 캘린더

    Args:
        year: 연도 (기본: 올해)
        month: 월 (1-12, 기본: 이번 달)

    Returns:
        일별 은하수 촬영 조건 및 점수
    """
    now = datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month

    calendar = get_monthly_milky_way_calendar(year, month)

    # 추천일 (점수 70점 이상)
    best_days = [d for d in calendar if d["score"] >= 70]

    # 시즌 체크
    season_ok = month in [3, 4, 5, 6, 7, 8, 9, 10]

    return {
        "year": year,
        "month": month,
        "season_ok": season_ok,
        "season_note": "은하수 시즌: 3월~10월" if season_ok else "비시즌 (11월~2월)",
        "best_days": [d["date"] for d in best_days],
        "calendar": calendar,
    }


@router.get("/astronomy/milky-way/next-best")
async def get_next_best_milky_way_days(
    days: int = Query(default=30, ge=7, le=90),
) -> Dict[str, Any]:
    """
    향후 N일 내 은하수 촬영 최적일 조회

    Args:
        days: 조회 기간 (기본: 30일, 최대: 90일)

    Returns:
        촬영 추천일 목록
    """
    results = []
    today = datetime.now()

    for i in range(days):
        target_date = today + timedelta(days=i)
        visibility = get_milky_way_visibility(target_date)
        score = calculate_milky_way_score(visibility)

        if score >= 50:  # 50점 이상만
            results.append({
                "date": target_date.strftime("%Y-%m-%d"),
                "weekday": target_date.strftime("%a"),
                "score": score,
                "moon_age": visibility["moon_phase"]["moon_age"],
                "illumination": visibility["moon_phase"]["illumination"],
                "dark_window": visibility["dark_window"],
                "recommendation": visibility["recommendation"],
            })

    # 점수순 정렬
    results.sort(key=lambda x: x["score"], reverse=True)

    return {
        "period": f"{today.strftime('%Y-%m-%d')} ~ {(today + timedelta(days=days)).strftime('%Y-%m-%d')}",
        "total_good_days": len(results),
        "best_days": results[:10],  # TOP 10
    }


@router.get("/astronomy/dark-window")
async def get_dark_window(
    date: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
) -> Dict[str, Any]:
    """
    무월광 촬영 시간대 조회 (별궤적, 은하수 공통)

    Args:
        date: 날짜 (YYYY-MM-DD)
        lat: 위도
        lon: 경도

    Returns:
        천문박명 시간, 월출/월몰, 무월광 시간대
    """
    if date:
        target_date = datetime.strptime(date, "%Y-%m-%d")
    else:
        target_date = datetime.now()

    phase = get_moon_phase(target_date)
    times = get_moon_times(target_date, lat, lon)
    twilight = get_astronomical_twilight(target_date, lat, lon)

    from utils.astronomy import calculate_dark_window
    dark_window = calculate_dark_window(twilight, times, phase)

    return {
        "date": target_date.strftime("%Y-%m-%d"),
        "astronomical_twilight": {
            "evening_end": twilight.get("evening_twilight"),
            "morning_start": twilight.get("morning_twilight"),
            "dark_hours": twilight.get("dark_hours"),
        },
        "moon": {
            "age": phase["moon_age"],
            "illumination": phase["illumination"],
            "is_dark": phase["is_dark_moon"],
            "rise": times.get("moonrise"),
            "set": times.get("moonset"),
        },
        "dark_window": dark_window,
        "suitable_for": ["은하수", "별궤적", "유성우"] if dark_window.get("available") else [],
    }
