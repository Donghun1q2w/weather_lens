"""Region-related endpoints"""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import json
import sqlite3

from config.settings import CACHE_DIR, SQLITE_DB_PATH

router = APIRouter()


def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/regions")
async def get_regions(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    sido: Optional[str] = None,
    is_coastal: Optional[bool] = None,
    is_east_coast: Optional[bool] = None,
    is_west_coast: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Get list of regions with filtering.

    Args:
        limit: Maximum number of regions (default: 100, max: 1000)
        offset: Offset for pagination
        sido: Filter by 시도 name
        is_coastal: Filter coastal regions
        is_east_coast: Filter east coast regions
        is_west_coast: Filter west coast regions

    Returns:
        List of regions with metadata
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Build query
    where_clauses = []
    params = []

    if sido:
        where_clauses.append("sido LIKE ?")
        params.append(f"%{sido}%")
    if is_coastal is not None:
        where_clauses.append("is_coastal = ?")
        params.append(1 if is_coastal else 0)
    if is_east_coast is not None:
        where_clauses.append("is_east_coast = ?")
        params.append(1 if is_east_coast else 0)
    if is_west_coast is not None:
        where_clauses.append("is_west_coast = ?")
        params.append(1 if is_west_coast else 0)

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    # Get total count
    cursor.execute(f"SELECT COUNT(*) FROM regions WHERE {where_sql}", params)
    total = cursor.fetchone()[0]

    # Get regions
    cursor.execute(f"""
        SELECT code, name, sido, sigungu, emd, lat, lon, nx, ny,
               elevation, is_coastal, is_east_coast, is_west_coast
        FROM regions
        WHERE {where_sql}
        ORDER BY sido, sigungu, emd
        LIMIT ? OFFSET ?
    """, params + [limit, offset])

    regions = []
    for row in cursor.fetchall():
        regions.append({
            "code": row["code"],
            "name": row["name"],
            "sido": row["sido"],
            "sigungu": row["sigungu"],
            "emd": row["emd"],
            "lat": row["lat"],
            "lon": row["lon"],
            "nx": row["nx"],
            "ny": row["ny"],
            "elevation": row["elevation"],
            "is_coastal": bool(row["is_coastal"]),
            "is_east_coast": bool(row["is_east_coast"]),
            "is_west_coast": bool(row["is_west_coast"]),
        })

    conn.close()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "regions": regions,
    }


@router.get("/regions/stats")
async def get_region_stats() -> Dict[str, Any]:
    """
    Get region statistics.

    Returns:
        Statistics by 시도 and region type
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Total count
    cursor.execute("SELECT COUNT(*) FROM regions")
    total = cursor.fetchone()[0]

    # By 시도
    cursor.execute("""
        SELECT sido, COUNT(*) as count
        FROM regions
        GROUP BY sido
        ORDER BY count DESC
    """)
    by_sido = {row["sido"]: row["count"] for row in cursor.fetchall()}

    # By type
    cursor.execute("SELECT COUNT(*) FROM regions WHERE is_coastal = 1")
    coastal = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM regions WHERE is_east_coast = 1")
    east_coast = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM regions WHERE is_west_coast = 1")
    west_coast = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM regions WHERE elevation >= 500")
    mountain = cursor.fetchone()[0]

    conn.close()

    return {
        "total": total,
        "by_sido": by_sido,
        "by_type": {
            "coastal": coastal,
            "east_coast": east_coast,
            "west_coast": west_coast,
            "mountain_500m": mountain,
        }
    }


@router.get("/regions/{region_code}")
async def get_region_detail(region_code: str) -> Dict[str, Any]:
    """
    Get detailed information for a specific region.

    Args:
        region_code: 10-digit region code (읍면동 코드)

    Returns:
        Region metadata and current scores
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT code, name, sido, sigungu, emd, lat, lon, nx, ny,
               elevation, is_coastal, is_east_coast, is_west_coast
        FROM regions
        WHERE code = ?
    """, (region_code,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Region not found")

    return {
        "code": row["code"],
        "name": row["name"],
        "sido": row["sido"],
        "sigungu": row["sigungu"],
        "emd": row["emd"],
        "coordinates": {
            "lat": row["lat"],
            "lon": row["lon"],
            "nx": row["nx"],
            "ny": row["ny"],
        },
        "elevation": row["elevation"],
        "is_coastal": bool(row["is_coastal"]),
        "is_east_coast": bool(row["is_east_coast"]),
        "is_west_coast": bool(row["is_west_coast"]),
        "scores": {},  # Will be populated when scoring is implemented
    }


@router.get("/regions/{region_code}/forecast")
async def get_region_forecast(region_code: str) -> Dict[str, Any]:
    """
    Get weather forecast for a specific region.

    Args:
        region_code: 10-digit region code (읍면동 코드)

    Returns:
        Weather forecast data (D-day ~ D+2)
    """
    # Try to read from cache
    today = datetime.now().strftime("%Y-%m-%d")
    cache_dir = CACHE_DIR / today

    # Look for JSON file matching region code
    if cache_dir.exists():
        for cache_file in cache_dir.glob("*.json"):
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("region_code") == region_code:
                    return data

    # If not found in cache
    return {
        "region_code": region_code,
        "forecast": [],
        "updated_at": None,
        "note": "No forecast data available yet",
    }
