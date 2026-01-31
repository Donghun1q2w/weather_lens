"""Map-related endpoints"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from typing import Optional
from pathlib import Path
import json

from config.settings import BOUNDARIES_DIR

router = APIRouter()


@router.get("/map/boundaries")
async def get_map_boundaries(
    level: str = Query("sido", description="Boundary level: sido, sigungu, or emd"),
    region_code: Optional[str] = Query(None, description="Filter by region code"),
) -> JSONResponse:
    """
    Get GeoJSON boundaries for map visualization.

    Args:
        level: Boundary level (sido/sigungu/emd)
        region_code: Optional filter by region code

    Returns:
        GeoJSON FeatureCollection
    """
    # TODO: Implement after boundaries data is prepared
    # For now, return empty FeatureCollection

    return JSONResponse(
        content={
            "type": "FeatureCollection",
            "features": [],
            "metadata": {
                "level": level,
                "region_code": region_code,
                "note": "Boundary data not yet loaded",
            },
        }
    )
