"""Theme-related endpoints"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timedelta
import json

from config.settings import THEME_IDS, BASE_DIR

router = APIRouter()


@router.get("/themes")
async def get_themes() -> List[Dict[str, Any]]:
    """
    Get list of all available photography themes.

    Returns:
        List of themes with metadata (16 themes)
    """
    themes = []
    for theme_id, theme_name in THEME_IDS.items():
        themes.append({
            "id": theme_id,
            "name": theme_name,
            "category": _get_theme_category(theme_id),
        })

    return themes


@router.get("/themes/{theme_id}/top")
async def get_theme_top_regions(
    theme_id: int,
    limit: int = 10,
    date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get top N regions for a specific theme with 3-day forecast scores.

    Args:
        theme_id: Theme ID (1-16)
        limit: Number of top regions to return (default: 10)
        date: Base date (YYYY-MM-DD format, default: today)

    Returns:
        Theme info and ranked regions with 3-day scores (D-day, D+1, D+2)
    """
    if theme_id not in THEME_IDS:
        raise HTTPException(status_code=404, detail="Theme not found")

    # Parse base date
    if date:
        try:
            base_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        base_date = datetime.now()

    # Generate 3 dates
    dates = [
        base_date,
        base_date + timedelta(days=1),
        base_date + timedelta(days=2),
    ]
    date_labels = ["오늘", "내일", "모레"]
    date_strs = [d.strftime("%Y-%m-%d") for d in dates]

    # TODO: Read from database/cache once scoring is implemented
    # For now, return placeholder structure with 3-day format
    return {
        "theme_id": theme_id,
        "theme_name": THEME_IDS[theme_id],
        "category": _get_theme_category(theme_id),
        "forecast_dates": [
            {"date": date_strs[i], "label": date_labels[i]} for i in range(3)
        ],
        "top_regions": [],  # Will contain 3-day scores per region
        "updated_at": None,
        "note": "3일 예보 점수 (오늘/내일/모레)",
    }


@router.get("/themes/{theme_id}/regions/{region_code}")
async def get_region_theme_score(
    theme_id: int,
    region_code: str
) -> Dict[str, Any]:
    """
    Get 3-day forecast scores for a specific region and theme.

    Args:
        theme_id: Theme ID (1-16)
        region_code: Region code (읍면동 코드)

    Returns:
        3-day scores with details
    """
    if theme_id not in THEME_IDS:
        raise HTTPException(status_code=404, detail="Theme not found")

    base_date = datetime.now()
    dates = [
        base_date,
        base_date + timedelta(days=1),
        base_date + timedelta(days=2),
    ]
    date_labels = ["오늘", "내일", "모레"]
    date_strs = [d.strftime("%Y-%m-%d") for d in dates]

    # TODO: Implement actual scoring lookup
    return {
        "theme_id": theme_id,
        "theme_name": THEME_IDS[theme_id],
        "region_code": region_code,
        "scores": [
            {
                "date": date_strs[i],
                "label": date_labels[i],
                "score": 0,  # Will be calculated
                "factors": {},  # Detailed scoring factors
            }
            for i in range(3)
        ],
        "recommendation": None,  # Gemini-generated recommendation
    }


@router.get("/themes/rankings")
async def get_all_theme_rankings(limit: int = 5) -> Dict[str, Any]:
    """
    Get top regions for all themes with 3-day forecast.

    Args:
        limit: Number of top regions per theme (default: 5)

    Returns:
        All themes with their top regions and 3-day scores
    """
    base_date = datetime.now()
    dates = [
        base_date,
        base_date + timedelta(days=1),
        base_date + timedelta(days=2),
    ]
    date_labels = ["오늘", "내일", "모레"]
    date_strs = [d.strftime("%Y-%m-%d") for d in dates]

    rankings = {}
    for theme_id, theme_name in THEME_IDS.items():
        rankings[str(theme_id)] = {
            "theme_name": theme_name,
            "category": _get_theme_category(theme_id),
            "top_regions": [],  # Will contain 3-day scores
        }

    return {
        "forecast_dates": [
            {"date": date_strs[i], "label": date_labels[i]} for i in range(3)
        ],
        "rankings": rankings,
        "updated_at": None,
    }


def _get_theme_category(theme_id: int) -> str:
    """Get theme category for grouping"""
    categories = {
        1: "해/달",      # 일출
        2: "해/달",      # 일출 오메가
        3: "해/달",      # 일몰
        4: "해/달",      # 일몰 오메가
        5: "천체",       # 은하수
        6: "자연현상",   # 야광충
        7: "바다",       # 바다 장노출
        8: "자연현상",   # 운해
        9: "천체",       # 별궤적
        10: "도시",      # 야경
        11: "자연현상",  # 안개
        12: "풍경",      # 반영
        13: "빛",        # 골든아워
        14: "빛",        # 블루아워
        15: "겨울",      # 상고대
        16: "해/달",     # 월출
    }
    return categories.get(theme_id, "기타")
