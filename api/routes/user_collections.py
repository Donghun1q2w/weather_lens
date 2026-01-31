"""사용자 출사포인트 컬렉션 API"""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import sqlite3

from config.settings import SQLITE_DB_PATH

router = APIRouter()


# ========== Pydantic Models ==========

class CollectionCreate(BaseModel):
    """컬렉션 생성 모델"""
    user_id: str
    name: str
    description: Optional[str] = None
    color_code: Optional[str] = "1"
    icon_id: Optional[str] = "1"


class CollectionUpdate(BaseModel):
    """컬렉션 수정 모델"""
    name: Optional[str] = None
    description: Optional[str] = None
    color_code: Optional[str] = None
    icon_id: Optional[str] = None


class CollectionSpotCreate(BaseModel):
    """컬렉션 스팟 생성 모델"""
    photo_spot_id: Optional[int] = None  # Link to global spot
    custom_name: Optional[str] = None  # For custom spots
    custom_lat: Optional[float] = None
    custom_lon: Optional[float] = None
    region_code: Optional[str] = None
    memo: Optional[str] = None
    tags: Optional[List[str]] = None
    source_url: Optional[str] = None


class CollectionSpotUpdate(BaseModel):
    """컬렉션 스팟 수정 모델"""
    custom_name: Optional[str] = None
    custom_lat: Optional[float] = None
    custom_lon: Optional[float] = None
    region_code: Optional[str] = None
    memo: Optional[str] = None
    tags: Optional[List[str]] = None
    source_url: Optional[str] = None


# ========== Helper Functions ==========

def get_db():
    """DB 연결"""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ========== Collection CRUD ==========

@router.get("/collections")
async def list_collections(
    user_id: str = Query(..., description="User ID to filter collections"),
    limit: int = Query(default=50, le=200),
    offset: int = 0,
) -> Dict[str, Any]:
    """
    사용자의 컬렉션 목록 조회

    Args:
        user_id: 사용자 ID (필수)
        limit: 최대 반환 개수
        offset: 오프셋
    """
    conn = get_db()
    cursor = conn.cursor()

    # 컬렉션 조회
    cursor.execute("""
        SELECT id, user_id, name, description, color_code, icon_id, created_at, updated_at
        FROM user_collections
        WHERE user_id = ?
        ORDER BY updated_at DESC
        LIMIT ? OFFSET ?
    """, (user_id, limit, offset))

    collections = []
    for row in cursor.fetchall():
        collection_id = row["id"]

        # 각 컬렉션의 스팟 개수
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM user_collection_spots
            WHERE collection_id = ?
        """, (collection_id,))
        spot_count = cursor.fetchone()["count"]

        collections.append({
            "id": collection_id,
            "user_id": row["user_id"],
            "name": row["name"],
            "description": row["description"],
            "color_code": row["color_code"],
            "icon_id": row["icon_id"],
            "spot_count": spot_count,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        })

    # 전체 개수
    cursor.execute("""
        SELECT COUNT(*) as total
        FROM user_collections
        WHERE user_id = ?
    """, (user_id,))
    total = cursor.fetchone()["total"]

    conn.close()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": collections,
    }


@router.post("/collections")
async def create_collection(collection: CollectionCreate) -> Dict[str, Any]:
    """
    새 컬렉션 생성

    Args:
        collection: 컬렉션 정보
    """
    conn = get_db()
    cursor = conn.cursor()

    # 컬렉션 삽입
    cursor.execute("""
        INSERT INTO user_collections (user_id, name, description, color_code, icon_id)
        VALUES (?, ?, ?, ?, ?)
    """, (
        collection.user_id,
        collection.name,
        collection.description,
        collection.color_code,
        collection.icon_id,
    ))

    collection_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return {
        "message": "Collection created",
        "id": collection_id,
        "name": collection.name,
    }


@router.get("/collections/{id}")
async def get_collection(id: int) -> Dict[str, Any]:
    """
    컬렉션 상세 조회 (스팟 포함)

    Args:
        id: 컬렉션 ID
    """
    conn = get_db()
    cursor = conn.cursor()

    # 컬렉션 정보
    cursor.execute("""
        SELECT id, user_id, name, description, color_code, icon_id, created_at, updated_at
        FROM user_collections
        WHERE id = ?
    """, (id,))

    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Collection not found")

    collection = {
        "id": row["id"],
        "user_id": row["user_id"],
        "name": row["name"],
        "description": row["description"],
        "color_code": row["color_code"],
        "icon_id": row["icon_id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }

    # 컬렉션의 스팟 목록
    cursor.execute("""
        SELECT
            ucs.id, ucs.photo_spot_id, ucs.custom_name, ucs.custom_lat, ucs.custom_lon,
            ucs.region_code, ucs.memo, ucs.tags, ucs.source_url, ucs.created_at,
            r.name as region_name, r.sido,
            ps.name as spot_name, ps.lat as spot_lat, ps.lon as spot_lon,
            ps.elevation, ps.description as spot_description
        FROM user_collection_spots ucs
        LEFT JOIN regions r ON ucs.region_code = r.code
        LEFT JOIN photo_spots ps ON ucs.photo_spot_id = ps.id
        WHERE ucs.collection_id = ?
        ORDER BY ucs.created_at DESC
    """, (id,))

    spots = []
    for spot_row in cursor.fetchall():
        spot_data = {
            "id": spot_row["id"],
            "photo_spot_id": spot_row["photo_spot_id"],
            "custom_name": spot_row["custom_name"],
            "custom_lat": spot_row["custom_lat"],
            "custom_lon": spot_row["custom_lon"],
            "region_code": spot_row["region_code"],
            "region_name": spot_row["region_name"],
            "sido": spot_row["sido"],
            "memo": spot_row["memo"],
            "tags": spot_row["tags"].split(",") if spot_row["tags"] else [],
            "source_url": spot_row["source_url"],
            "created_at": spot_row["created_at"],
        }

        # Global photo spot 정보 포함
        if spot_row["photo_spot_id"]:
            spot_data["global_spot"] = {
                "id": spot_row["photo_spot_id"],
                "name": spot_row["spot_name"],
                "lat": spot_row["spot_lat"],
                "lon": spot_row["spot_lon"],
                "elevation": spot_row["elevation"],
                "description": spot_row["spot_description"],
            }

        spots.append(spot_data)

    collection["spots"] = spots
    collection["spot_count"] = len(spots)

    conn.close()

    return collection


@router.put("/collections/{id}")
async def update_collection(id: int, collection: CollectionUpdate) -> Dict[str, Any]:
    """
    컬렉션 수정

    Args:
        id: 컬렉션 ID
        collection: 수정할 컬렉션 정보
    """
    conn = get_db()
    cursor = conn.cursor()

    # 존재 여부 확인
    cursor.execute("SELECT id FROM user_collections WHERE id = ?", (id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Collection not found")

    # 업데이트할 필드 구성
    updates = []
    params = []

    if collection.name is not None:
        updates.append("name = ?")
        params.append(collection.name)
    if collection.description is not None:
        updates.append("description = ?")
        params.append(collection.description)
    if collection.color_code is not None:
        updates.append("color_code = ?")
        params.append(collection.color_code)
    if collection.icon_id is not None:
        updates.append("icon_id = ?")
        params.append(collection.icon_id)

    if not updates:
        conn.close()
        return {"message": "No fields to update", "id": id}

    updates.append("updated_at = CURRENT_TIMESTAMP")
    params.append(id)

    cursor.execute(f"""
        UPDATE user_collections SET {", ".join(updates)} WHERE id = ?
    """, params)

    conn.commit()
    conn.close()

    return {"message": "Collection updated", "id": id}


@router.delete("/collections/{id}")
async def delete_collection(id: int) -> Dict[str, Any]:
    """
    컬렉션 삭제 (스팟도 함께 삭제됨)

    Args:
        id: 컬렉션 ID
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM user_collections WHERE id = ?", (id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Collection not found")

    name = row["name"]

    # 스팟 삭제 (CASCADE로 자동 삭제되지만 명시적으로 처리)
    cursor.execute("DELETE FROM user_collection_spots WHERE collection_id = ?", (id,))
    # 컬렉션 삭제
    cursor.execute("DELETE FROM user_collections WHERE id = ?", (id,))

    conn.commit()
    conn.close()

    return {"message": "Collection deleted", "id": id, "name": name}


# ========== Collection Spots CRUD ==========

@router.get("/collections/{id}/spots")
async def list_collection_spots(
    id: int,
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
) -> Dict[str, Any]:
    """
    컬렉션의 스팟 목록 조회

    Args:
        id: 컬렉션 ID
        tags: 태그 필터 (쉼표로 구분)
    """
    conn = get_db()
    cursor = conn.cursor()

    # 컬렉션 존재 확인
    cursor.execute("SELECT id, name FROM user_collections WHERE id = ?", (id,))
    collection = cursor.fetchone()
    if not collection:
        conn.close()
        raise HTTPException(status_code=404, detail="Collection not found")

    # 스팟 조회
    query = """
        SELECT
            ucs.id, ucs.photo_spot_id, ucs.custom_name, ucs.custom_lat, ucs.custom_lon,
            ucs.region_code, ucs.memo, ucs.tags, ucs.source_url, ucs.created_at,
            r.name as region_name, r.sido,
            ps.name as spot_name, ps.lat as spot_lat, ps.lon as spot_lon,
            ps.elevation, ps.description as spot_description
        FROM user_collection_spots ucs
        LEFT JOIN regions r ON ucs.region_code = r.code
        LEFT JOIN photo_spots ps ON ucs.photo_spot_id = ps.id
        WHERE ucs.collection_id = ?
    """
    params = [id]

    # 태그 필터
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        tag_conditions = " OR ".join(["ucs.tags LIKE ?" for _ in tag_list])
        query += f" AND ({tag_conditions})"
        params.extend([f"%{tag}%" for tag in tag_list])

    query += " ORDER BY ucs.created_at DESC"

    cursor.execute(query, params)

    spots = []
    for row in cursor.fetchall():
        spot_data = {
            "id": row["id"],
            "photo_spot_id": row["photo_spot_id"],
            "custom_name": row["custom_name"],
            "custom_lat": row["custom_lat"],
            "custom_lon": row["custom_lon"],
            "region_code": row["region_code"],
            "region_name": row["region_name"],
            "sido": row["sido"],
            "memo": row["memo"],
            "tags": row["tags"].split(",") if row["tags"] else [],
            "source_url": row["source_url"],
            "created_at": row["created_at"],
        }

        # Global photo spot 정보 포함
        if row["photo_spot_id"]:
            spot_data["global_spot"] = {
                "id": row["photo_spot_id"],
                "name": row["spot_name"],
                "lat": row["spot_lat"],
                "lon": row["spot_lon"],
                "elevation": row["elevation"],
                "description": row["spot_description"],
            }

        spots.append(spot_data)

    conn.close()

    return {
        "collection": {
            "id": collection["id"],
            "name": collection["name"],
        },
        "total": len(spots),
        "items": spots,
    }


@router.post("/collections/{id}/spots")
async def add_spot_to_collection(id: int, spot: CollectionSpotCreate) -> Dict[str, Any]:
    """
    컬렉션에 스팟 추가

    Args:
        id: 컬렉션 ID
        spot: 스팟 정보 (global photo_spot_id 또는 custom 정보)
    """
    conn = get_db()
    cursor = conn.cursor()

    # 컬렉션 존재 확인
    cursor.execute("SELECT id FROM user_collections WHERE id = ?", (id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Collection not found")

    # photo_spot_id가 있으면 유효성 검사
    if spot.photo_spot_id:
        cursor.execute("SELECT id FROM photo_spots WHERE id = ?", (spot.photo_spot_id,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail=f"Invalid photo_spot_id: {spot.photo_spot_id}")

    # region_code가 있으면 유효성 검사
    if spot.region_code:
        cursor.execute("SELECT code FROM regions WHERE code = ?", (spot.region_code,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail=f"Invalid region_code: {spot.region_code}")

    # Custom spot의 경우 custom_name 필수
    if not spot.photo_spot_id and not spot.custom_name:
        conn.close()
        raise HTTPException(status_code=400, detail="custom_name is required for custom spots")

    # 스팟 삽입
    cursor.execute("""
        INSERT INTO user_collection_spots (
            collection_id, photo_spot_id, custom_name, custom_lat, custom_lon,
            region_code, memo, tags, source_url
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        id,
        spot.photo_spot_id,
        spot.custom_name,
        spot.custom_lat,
        spot.custom_lon,
        spot.region_code,
        spot.memo,
        ",".join(spot.tags) if spot.tags else None,
        spot.source_url,
    ))

    spot_id = cursor.lastrowid

    # 컬렉션 updated_at 갱신
    cursor.execute("""
        UPDATE user_collections SET updated_at = CURRENT_TIMESTAMP WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    return {
        "message": "Spot added to collection",
        "id": spot_id,
        "collection_id": id,
    }


@router.put("/collections/{id}/spots/{spot_id}")
async def update_collection_spot(
    id: int,
    spot_id: int,
    spot: CollectionSpotUpdate,
) -> Dict[str, Any]:
    """
    컬렉션 스팟 수정

    Args:
        id: 컬렉션 ID
        spot_id: 스팟 ID
        spot: 수정할 스팟 정보
    """
    conn = get_db()
    cursor = conn.cursor()

    # 스팟 존재 확인 및 컬렉션 소속 확인
    cursor.execute("""
        SELECT id FROM user_collection_spots
        WHERE id = ? AND collection_id = ?
    """, (spot_id, id))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Spot not found in this collection")

    # region_code가 있으면 유효성 검사
    if spot.region_code:
        cursor.execute("SELECT code FROM regions WHERE code = ?", (spot.region_code,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail=f"Invalid region_code: {spot.region_code}")

    # 업데이트할 필드 구성
    updates = []
    params = []

    if spot.custom_name is not None:
        updates.append("custom_name = ?")
        params.append(spot.custom_name)
    if spot.custom_lat is not None:
        updates.append("custom_lat = ?")
        params.append(spot.custom_lat)
    if spot.custom_lon is not None:
        updates.append("custom_lon = ?")
        params.append(spot.custom_lon)
    if spot.region_code is not None:
        updates.append("region_code = ?")
        params.append(spot.region_code)
    if spot.memo is not None:
        updates.append("memo = ?")
        params.append(spot.memo)
    if spot.tags is not None:
        updates.append("tags = ?")
        params.append(",".join(spot.tags) if spot.tags else None)
    if spot.source_url is not None:
        updates.append("source_url = ?")
        params.append(spot.source_url)

    if not updates:
        conn.close()
        return {"message": "No fields to update", "id": spot_id}

    params.append(spot_id)

    cursor.execute(f"""
        UPDATE user_collection_spots SET {", ".join(updates)} WHERE id = ?
    """, params)

    # 컬렉션 updated_at 갱신
    cursor.execute("""
        UPDATE user_collections SET updated_at = CURRENT_TIMESTAMP WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    return {"message": "Spot updated", "id": spot_id}


@router.delete("/collections/{id}/spots/{spot_id}")
async def remove_spot_from_collection(id: int, spot_id: int) -> Dict[str, Any]:
    """
    컬렉션에서 스팟 제거

    Args:
        id: 컬렉션 ID
        spot_id: 스팟 ID
    """
    conn = get_db()
    cursor = conn.cursor()

    # 스팟 존재 확인 및 컬렉션 소속 확인
    cursor.execute("""
        SELECT custom_name FROM user_collection_spots
        WHERE id = ? AND collection_id = ?
    """, (spot_id, id))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Spot not found in this collection")

    custom_name = row["custom_name"]

    # 스팟 삭제
    cursor.execute("DELETE FROM user_collection_spots WHERE id = ?", (spot_id,))

    # 컬렉션 updated_at 갱신
    cursor.execute("""
        UPDATE user_collections SET updated_at = CURRENT_TIMESTAMP WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    return {
        "message": "Spot removed from collection",
        "id": spot_id,
        "custom_name": custom_name,
    }
