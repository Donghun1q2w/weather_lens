"""출사포인트 API - CRUD 및 테마 연동"""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import sqlite3

from config.settings import SQLITE_DB_PATH

router = APIRouter()


class PhotoSpotCreate(BaseModel):
    """출사포인트 생성 모델"""
    name: str
    region_code: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    elevation: Optional[int] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    theme_ids: Optional[List[int]] = None  # 연결할 테마 ID 목록


class PhotoSpotUpdate(BaseModel):
    """출사포인트 수정 모델"""
    name: Optional[str] = None
    region_code: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    elevation: Optional[int] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    theme_ids: Optional[List[int]] = None


def get_db():
    """DB 연결"""
    return sqlite3.connect(SQLITE_DB_PATH)


@router.get("/photo-spots")
async def list_photo_spots(
    theme_id: Optional[int] = None,
    region_code: Optional[str] = None,
    sido: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
) -> Dict[str, Any]:
    """
    출사포인트 목록 조회

    Args:
        theme_id: 특정 테마에 연결된 포인트만 조회
        region_code: 특정 지역코드 필터
        sido: 시도명 필터 (예: 강원, 제주)
        search: 이름/설명/태그 검색
        limit: 최대 반환 개수
        offset: 오프셋
    """
    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT DISTINCT
            ps.id, ps.name, ps.region_code, ps.lat, ps.lon,
            ps.elevation, ps.description, ps.tags, ps.created_at,
            r.name as region_name, r.sido
        FROM photo_spots ps
        LEFT JOIN regions r ON ps.region_code = r.code
    """

    conditions = []
    params = []

    if theme_id:
        query += " JOIN photo_spot_themes pst ON ps.id = pst.spot_id"
        conditions.append("pst.theme_id = ?")
        params.append(theme_id)

    if region_code:
        conditions.append("ps.region_code = ?")
        params.append(region_code)

    if sido:
        conditions.append("r.sido LIKE ?")
        params.append(f"%{sido}%")

    if search:
        conditions.append("(ps.name LIKE ? OR ps.description LIKE ? OR ps.tags LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY ps.id LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()

    # 전체 개수
    count_query = "SELECT COUNT(DISTINCT ps.id) FROM photo_spots ps"
    if theme_id:
        count_query += " JOIN photo_spot_themes pst ON ps.id = pst.spot_id"
    if region_code or sido or search:
        count_query += " LEFT JOIN regions r ON ps.region_code = r.code"
    if conditions:
        count_query += " WHERE " + " AND ".join(conditions)

    cursor.execute(count_query, params[:-2])  # limit, offset 제외
    total = cursor.fetchone()[0]

    spots = []
    for row in rows:
        spot_id = row[0]

        # 테마 목록 조회
        cursor.execute("""
            SELECT t.id, t.name
            FROM themes t
            JOIN photo_spot_themes pst ON t.id = pst.theme_id
            WHERE pst.spot_id = ?
        """, (spot_id,))
        themes = [{"id": t[0], "name": t[1]} for t in cursor.fetchall()]

        spots.append({
            "id": spot_id,
            "name": row[1],
            "region_code": row[2],
            "region_name": row[9],
            "sido": row[10],
            "lat": row[3],
            "lon": row[4],
            "elevation": row[5],
            "description": row[6],
            "tags": row[7].split(",") if row[7] else [],
            "themes": themes,
            "created_at": row[8],
        })

    conn.close()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": spots,
    }


@router.get("/photo-spots/{spot_id}")
async def get_photo_spot(spot_id: int) -> Dict[str, Any]:
    """출사포인트 상세 조회"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            ps.id, ps.name, ps.region_code, ps.lat, ps.lon,
            ps.elevation, ps.description, ps.tags, ps.created_at,
            r.name as region_name, r.sido, r.nx, r.ny
        FROM photo_spots ps
        LEFT JOIN regions r ON ps.region_code = r.code
        WHERE ps.id = ?
    """, (spot_id,))

    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Photo spot not found")

    # 테마 목록 조회
    cursor.execute("""
        SELECT t.id, t.name, t.description
        FROM themes t
        JOIN photo_spot_themes pst ON t.id = pst.theme_id
        WHERE pst.spot_id = ?
    """, (spot_id,))
    themes = [{"id": t[0], "name": t[1], "description": t[2]} for t in cursor.fetchall()]

    conn.close()

    return {
        "id": row[0],
        "name": row[1],
        "region_code": row[2],
        "region_name": row[9],
        "sido": row[10],
        "lat": row[3],
        "lon": row[4],
        "elevation": row[5],
        "description": row[6],
        "tags": row[7].split(",") if row[7] else [],
        "themes": themes,
        "grid": {"nx": row[11], "ny": row[12]} if row[11] else None,
        "created_at": row[8],
    }


@router.post("/photo-spots")
async def create_photo_spot(spot: PhotoSpotCreate) -> Dict[str, Any]:
    """
    새 출사포인트 생성 (사용자 정의)

    Args:
        spot: 출사포인트 정보
    """
    conn = get_db()
    cursor = conn.cursor()

    # 지역코드 유효성 검사
    cursor.execute("SELECT code, name FROM regions WHERE code = ?", (spot.region_code,))
    region = cursor.fetchone()
    if not region:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Invalid region_code: {spot.region_code}")

    # 중복 이름 체크
    cursor.execute("SELECT id FROM photo_spots WHERE name = ?", (spot.name,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail=f"Photo spot already exists: {spot.name}")

    # 출사포인트 삽입
    cursor.execute("""
        INSERT INTO photo_spots (name, region_code, lat, lon, elevation, description, tags)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        spot.name,
        spot.region_code,
        spot.lat,
        spot.lon,
        spot.elevation,
        spot.description,
        ",".join(spot.tags) if spot.tags else None,
    ))

    spot_id = cursor.lastrowid

    # 테마 연결
    if spot.theme_ids:
        for theme_id in spot.theme_ids:
            cursor.execute("""
                INSERT OR IGNORE INTO photo_spot_themes (spot_id, theme_id)
                VALUES (?, ?)
            """, (spot_id, theme_id))

    conn.commit()
    conn.close()

    return {
        "message": "Photo spot created",
        "id": spot_id,
        "name": spot.name,
        "region": region[1],
    }


@router.put("/photo-spots/{spot_id}")
async def update_photo_spot(spot_id: int, spot: PhotoSpotUpdate) -> Dict[str, Any]:
    """출사포인트 수정"""
    conn = get_db()
    cursor = conn.cursor()

    # 존재 여부 확인
    cursor.execute("SELECT id FROM photo_spots WHERE id = ?", (spot_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Photo spot not found")

    # 지역코드 유효성 검사 (변경 시)
    if spot.region_code:
        cursor.execute("SELECT code FROM regions WHERE code = ?", (spot.region_code,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail=f"Invalid region_code: {spot.region_code}")

    # 업데이트할 필드 구성
    updates = []
    params = []

    if spot.name is not None:
        updates.append("name = ?")
        params.append(spot.name)
    if spot.region_code is not None:
        updates.append("region_code = ?")
        params.append(spot.region_code)
    if spot.lat is not None:
        updates.append("lat = ?")
        params.append(spot.lat)
    if spot.lon is not None:
        updates.append("lon = ?")
        params.append(spot.lon)
    if spot.elevation is not None:
        updates.append("elevation = ?")
        params.append(spot.elevation)
    if spot.description is not None:
        updates.append("description = ?")
        params.append(spot.description)
    if spot.tags is not None:
        updates.append("tags = ?")
        params.append(",".join(spot.tags) if spot.tags else None)

    if updates:
        params.append(spot_id)
        cursor.execute(f"""
            UPDATE photo_spots SET {", ".join(updates)} WHERE id = ?
        """, params)

    # 테마 업데이트
    if spot.theme_ids is not None:
        cursor.execute("DELETE FROM photo_spot_themes WHERE spot_id = ?", (spot_id,))
        for theme_id in spot.theme_ids:
            cursor.execute("""
                INSERT OR IGNORE INTO photo_spot_themes (spot_id, theme_id)
                VALUES (?, ?)
            """, (spot_id, theme_id))

    conn.commit()
    conn.close()

    return {"message": "Photo spot updated", "id": spot_id}


@router.delete("/photo-spots/{spot_id}")
async def delete_photo_spot(spot_id: int) -> Dict[str, Any]:
    """출사포인트 삭제"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM photo_spots WHERE id = ?", (spot_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Photo spot not found")

    name = row[0]

    # 테마 연결 삭제
    cursor.execute("DELETE FROM photo_spot_themes WHERE spot_id = ?", (spot_id,))
    # 출사포인트 삭제
    cursor.execute("DELETE FROM photo_spots WHERE id = ?", (spot_id,))

    conn.commit()
    conn.close()

    return {"message": "Photo spot deleted", "id": spot_id, "name": name}


@router.get("/photo-spots/by-theme/{theme_id}")
async def get_spots_by_theme(
    theme_id: int,
    limit: int = Query(default=20, le=100),
) -> Dict[str, Any]:
    """특정 테마에 적합한 출사포인트 목록"""
    conn = get_db()
    cursor = conn.cursor()

    # 테마 정보
    cursor.execute("SELECT id, name FROM themes WHERE id = ?", (theme_id,))
    theme = cursor.fetchone()
    if not theme:
        conn.close()
        raise HTTPException(status_code=404, detail="Theme not found")

    # 해당 테마의 출사포인트
    cursor.execute("""
        SELECT
            ps.id, ps.name, ps.region_code, ps.lat, ps.lon,
            ps.elevation, ps.description, ps.tags,
            r.name as region_name, r.sido
        FROM photo_spots ps
        JOIN photo_spot_themes pst ON ps.id = pst.spot_id
        LEFT JOIN regions r ON ps.region_code = r.code
        WHERE pst.theme_id = ?
        ORDER BY ps.name
        LIMIT ?
    """, (theme_id, limit))

    spots = []
    for row in cursor.fetchall():
        spots.append({
            "id": row[0],
            "name": row[1],
            "region_code": row[2],
            "region_name": row[8],
            "sido": row[9],
            "lat": row[3],
            "lon": row[4],
            "elevation": row[5],
            "description": row[6],
            "tags": row[7].split(",") if row[7] else [],
        })

    conn.close()

    return {
        "theme": {"id": theme[0], "name": theme[1]},
        "total": len(spots),
        "spots": spots,
    }


@router.post("/photo-spots/{spot_id}/themes/{theme_id}")
async def add_theme_to_spot(spot_id: int, theme_id: int) -> Dict[str, Any]:
    """출사포인트에 테마 추가"""
    conn = get_db()
    cursor = conn.cursor()

    # 출사포인트 확인
    cursor.execute("SELECT name FROM photo_spots WHERE id = ?", (spot_id,))
    spot = cursor.fetchone()
    if not spot:
        conn.close()
        raise HTTPException(status_code=404, detail="Photo spot not found")

    # 테마 확인
    cursor.execute("SELECT name FROM themes WHERE id = ?", (theme_id,))
    theme = cursor.fetchone()
    if not theme:
        conn.close()
        raise HTTPException(status_code=404, detail="Theme not found")

    cursor.execute("""
        INSERT OR IGNORE INTO photo_spot_themes (spot_id, theme_id)
        VALUES (?, ?)
    """, (spot_id, theme_id))

    conn.commit()
    conn.close()

    return {
        "message": "Theme added to photo spot",
        "spot": spot[0],
        "theme": theme[0],
    }


@router.delete("/photo-spots/{spot_id}/themes/{theme_id}")
async def remove_theme_from_spot(spot_id: int, theme_id: int) -> Dict[str, Any]:
    """출사포인트에서 테마 제거"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM photo_spot_themes
        WHERE spot_id = ? AND theme_id = ?
    """, (spot_id, theme_id))

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Theme association not found")

    conn.commit()
    conn.close()

    return {"message": "Theme removed from photo spot"}


@router.get("/photo-spots/search/nearby")
async def search_nearby_spots(
    lat: float,
    lon: float,
    radius_km: float = Query(default=50, le=200),
    theme_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    좌표 기준 주변 출사포인트 검색

    Args:
        lat: 위도
        lon: 경도
        radius_km: 검색 반경 (km)
        theme_id: 특정 테마 필터
    """
    conn = get_db()
    cursor = conn.cursor()

    # SQLite에서 간단한 거리 계산 (Haversine 근사)
    # 1도 ≈ 111km
    lat_range = radius_km / 111.0
    lon_range = radius_km / (111.0 * abs(cos(radians(lat))))

    query = """
        SELECT
            ps.id, ps.name, ps.region_code, ps.lat, ps.lon,
            ps.elevation, ps.description, ps.tags,
            r.name as region_name, r.sido
        FROM photo_spots ps
        LEFT JOIN regions r ON ps.region_code = r.code
    """

    conditions = [
        "ps.lat IS NOT NULL",
        "ps.lon IS NOT NULL",
        f"ps.lat BETWEEN {lat - lat_range} AND {lat + lat_range}",
        f"ps.lon BETWEEN {lon - lon_range} AND {lon + lon_range}",
    ]
    params = []

    if theme_id:
        query += " JOIN photo_spot_themes pst ON ps.id = pst.spot_id"
        conditions.append("pst.theme_id = ?")
        params.append(theme_id)

    query += " WHERE " + " AND ".join(conditions)

    cursor.execute(query, params)

    from math import radians, cos, sin, sqrt, atan2

    def haversine(lat1, lon1, lat2, lon2):
        R = 6371  # 지구 반경 (km)
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return R * c

    spots = []
    for row in cursor.fetchall():
        if row[3] and row[4]:  # lat, lon 존재
            distance = haversine(lat, lon, row[3], row[4])
            if distance <= radius_km:
                spots.append({
                    "id": row[0],
                    "name": row[1],
                    "region_code": row[2],
                    "region_name": row[8],
                    "sido": row[9],
                    "lat": row[3],
                    "lon": row[4],
                    "elevation": row[5],
                    "description": row[6],
                    "tags": row[7].split(",") if row[7] else [],
                    "distance_km": round(distance, 1),
                })

    # 거리순 정렬
    spots.sort(key=lambda x: x["distance_km"])

    conn.close()

    return {
        "center": {"lat": lat, "lon": lon},
        "radius_km": radius_km,
        "total": len(spots),
        "spots": spots,
    }


# 상단에 필요한 import 추가
from math import radians, cos
