"""Marine/ocean data endpoints"""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import datetime
import sqlite3

from config.settings import SQLITE_DB_PATH

router = APIRouter()


def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class MarineZone(BaseModel):
    zone_code: str
    name: str
    name_en: str


class MarineForecast(BaseModel):
    zone_code: str
    zone_name: str
    forecast_time: str
    wave_height: Optional[float] = None  # meters
    wave_level: Optional[int] = None  # 1-5 scale
    sky: Optional[int] = None  # 1=맑음, 3=구름많음, 4=흐림
    weather: Optional[str] = None


class MarineConditions(BaseModel):
    zones: List[dict]
    updated_at: str


@router.get("/marine/zones")
async def get_marine_zones(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """
    Get list of marine zones.

    Args:
        limit: Maximum number of zones (default: 100, max: 500)
        offset: Offset for pagination

    Returns:
        List of marine zones with metadata
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get total count
    cursor.execute("SELECT COUNT(*) FROM marine_zones")
    total = cursor.fetchone()[0]

    # Get marine zones
    cursor.execute("""
        SELECT zone_code, name, name_en
        FROM marine_zones
        ORDER BY zone_code
        LIMIT ? OFFSET ?
    """, (limit, offset))

    zones = []
    for row in cursor.fetchall():
        zones.append({
            "zone_code": row["zone_code"],
            "name": row["name"],
            "name_en": row["name_en"],
        })

    conn.close()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "zones": zones,
    }


@router.get("/marine/zones/{zone_code}")
async def get_marine_zone_detail(zone_code: str) -> Dict[str, Any]:
    """
    Get detailed information for a specific marine zone.

    Args:
        zone_code: Marine zone code

    Returns:
        Marine zone details
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT zone_code, name, name_en
        FROM marine_zones
        WHERE zone_code = ?
    """, (zone_code,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Marine zone not found")

    return {
        "zone_code": row["zone_code"],
        "name": row["name"],
        "name_en": row["name_en"],
    }


@router.get("/marine/{region_code}/forecast")
async def get_marine_forecast(region_code: str) -> Dict[str, Any]:
    """
    Get marine forecast for a coastal region.

    Args:
        region_code: 10-digit region code (읍면동 코드) for coastal region

    Returns:
        Marine forecast data for associated zones
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Verify region exists and get associated marine zones
    cursor.execute("""
        SELECT r.code, r.name, mz.zone_code, mz.name as zone_name, mz.name_en
        FROM regions r
        LEFT JOIN region_marine_zone rmz ON r.code = rmz.region_code
        LEFT JOIN marine_zones mz ON rmz.zone_code = mz.zone_code
        WHERE r.code = ?
    """, (region_code,))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail="Region not found")

    # Check if region has marine zones
    if rows[0]["zone_code"] is None:
        return {
            "region_code": region_code,
            "region_name": rows[0]["name"],
            "forecasts": [],
            "note": "No marine zones associated with this region",
        }

    # Build forecast response
    forecasts = []
    for row in rows:
        if row["zone_code"]:
            forecasts.append({
                "zone_code": row["zone_code"],
                "zone_name": row["zone_name"],
                "zone_name_en": row["name_en"],
                "forecast_time": None,
                "wave_height": None,
                "wave_level": None,
                "sky": None,
                "weather": None,
                "note": "Forecast data will be populated by ingestion pipeline",
            })

    return {
        "region_code": region_code,
        "region_name": rows[0]["name"],
        "forecasts": forecasts,
        "updated_at": None,
    }


@router.get("/marine/conditions")
async def get_marine_conditions(
    limit: int = Query(50, ge=1, le=200),
) -> Dict[str, Any]:
    """
    Get current marine conditions overview.

    Args:
        limit: Maximum number of zones to include (default: 50, max: 200)

    Returns:
        Current conditions for marine zones
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get marine zones
    cursor.execute("""
        SELECT zone_code, name, name_en
        FROM marine_zones
        ORDER BY zone_code
        LIMIT ?
    """, (limit,))

    zones = []
    for row in cursor.fetchall():
        zones.append({
            "zone_code": row["zone_code"],
            "name": row["name"],
            "name_en": row["name_en"],
            "wave_height": None,
            "wave_level": None,
            "sky": None,
            "weather": None,
            "note": "Conditions will be populated by ingestion pipeline",
        })

    conn.close()

    return {
        "zones": zones,
        "updated_at": datetime.now().isoformat(),
        "note": "Real-time marine conditions will be populated by data ingestion",
    }
