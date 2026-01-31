"""네이버 지도 북마크 JSON 임포트 헬퍼"""
import json
import sqlite3
from typing import Dict, List, Optional, Tuple
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "regions.db"

# 시도 축약형 매핑
SIDO_VARIATIONS = {
    "전라남도": "전남",
    "전라북도": "전북",
    "경상남도": "경남",
    "경상북도": "경북",
    "충청남도": "충남",
    "충청북도": "충북",
}

# 역방향 매핑도 추가
for full, short in list(SIDO_VARIATIONS.items()):
    SIDO_VARIATIONS[short] = full


def find_region_by_address(address: str) -> Optional[str]:
    """
    Parse Korean address to extract 시도/시군구/읍면동 and find matching region code.

    Args:
        address: Korean address string

    Returns:
        region_code or None if not found
    """
    if not address:
        return None

    # Parse address components (split by space)
    parts = address.strip().split()
    if len(parts) < 2:
        return None

    sido = parts[0]
    sigungu = parts[1] if len(parts) > 1 else ""
    eupmyeondong = parts[2] if len(parts) > 2 else ""

    # Handle 특별자치도 suffix
    sido = sido.replace("특별자치도", "도")

    # Try to connect to database
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Try exact match first
        cursor.execute("""
            SELECT region_code FROM regions
            WHERE sido = ? AND sigungu = ? AND eupmyeondong = ?
        """, (sido, sigungu, eupmyeondong))

        result = cursor.fetchone()
        if result:
            conn.close()
            return result[0]

        # Try with variations (full name <-> short name)
        if sido in SIDO_VARIATIONS:
            alt_sido = SIDO_VARIATIONS[sido]
            cursor.execute("""
                SELECT region_code FROM regions
                WHERE sido = ? AND sigungu = ? AND eupmyeondong = ?
            """, (alt_sido, sigungu, eupmyeondong))

            result = cursor.fetchone()
            if result:
                conn.close()
                return result[0]

        # Try without eupmyeondong
        if eupmyeondong:
            cursor.execute("""
                SELECT region_code FROM regions
                WHERE sido = ? AND sigungu = ?
                LIMIT 1
            """, (sido, sigungu))

            result = cursor.fetchone()
            if result:
                conn.close()
                return result[0]

            # Try with variation
            if sido in SIDO_VARIATIONS:
                alt_sido = SIDO_VARIATIONS[sido]
                cursor.execute("""
                    SELECT region_code FROM regions
                    WHERE sido = ? AND sigungu = ?
                    LIMIT 1
                """, (alt_sido, sigungu))

                result = cursor.fetchone()
                if result:
                    conn.close()
                    return result[0]

        conn.close()
        return None

    except Exception as e:
        print(f"Error finding region: {e}")
        return None


def infer_tags_from_name(name: str, mcid_name: str = "") -> List[str]:
    """
    Analyze name and return relevant tags based on keywords.

    Args:
        name: Spot name
        mcid_name: Optional category/mcid name

    Returns:
        List of inferred tags
    """
    tags = set()
    combined = (name + " " + mcid_name).lower()

    # Keywords mapping
    if any(kw in combined for kw in ["해수욕장", "해변", "바다"]):
        tags.update(["해변", "바다", "장노출"])

    if "폐선" in combined:
        tags.update(["폐선", "장노출", "피사체"])

    if any(kw in combined for kw in ["칠면초", "갯골", "갯벌"]):
        tags.update(["갯벌", "일몰", "장노출"])

    if "바위" in combined:
        tags.update(["바위", "장노출"])

    if "등대" in combined:
        tags.update(["등대", "일출", "일몰"])

    if any(kw in combined for kw in ["항구", "포구", "선착장"]):
        tags.update(["항구", "어촌", "장노출"])

    if any(kw in combined for kw in ["산", "봉", "고지"]):
        tags.update(["산", "운해", "일출"])

    if any(kw in combined for kw in ["일출", "해돋이"]):
        tags.update(["일출", "골든아워"])

    if any(kw in combined for kw in ["일몰", "석양"]):
        tags.update(["일몰", "골든아워"])

    # Default if no tags matched
    if not tags:
        tags.add("출사지")

    return sorted(list(tags))


def parse_naver_bookmark(bookmark: Dict) -> Dict:
    """
    Extract and normalize bookmark data from Naver Map bookmark JSON.

    Args:
        bookmark: Naver bookmark dictionary

    Returns:
        Normalized spot data dict with keys: name, lat, lon, address, tags, memo, source_url
    """
    name = bookmark.get("name", "").strip()

    # Extract coordinates
    x = bookmark.get("x")  # longitude
    y = bookmark.get("y")  # latitude
    lon = float(x) if x else None
    lat = float(y) if y else None

    # Extract address
    address = bookmark.get("address", "").strip()

    # Extract memo
    memo = bookmark.get("memo", "").strip()

    # Extract mcid_name for better tag inference
    mcid_name = bookmark.get("mcid_name", "").strip()

    # Infer tags
    tags = infer_tags_from_name(name, mcid_name)

    # Build source URL if available
    source_url = ""
    if "id" in bookmark:
        source_url = f"https://map.naver.com/p/entry/place/{bookmark['id']}"

    return {
        "name": name,
        "lat": lat,
        "lon": lon,
        "address": address,
        "tags": tags,
        "memo": memo,
        "source_url": source_url,
    }


def get_or_create_collection(user_id: str, name: str, conn: sqlite3.Connection) -> int:
    """
    Get existing collection or create new one.

    Args:
        user_id: User identifier
        name: Collection name
        conn: Database connection

    Returns:
        collection_id
    """
    cursor = conn.cursor()

    # Try to find existing collection
    cursor.execute("""
        SELECT collection_id FROM user_collections
        WHERE user_id = ? AND name = ?
    """, (user_id, name))

    result = cursor.fetchone()
    if result:
        return result[0]

    # Create new collection
    cursor.execute("""
        INSERT INTO user_collections (user_id, name, created_at)
        VALUES (?, ?, datetime('now'))
    """, (user_id, name))

    conn.commit()
    return cursor.lastrowid


def add_spot_to_collection(collection_id: int, spot_data: Dict, conn: sqlite3.Connection) -> int:
    """
    Insert spot into user_collection_spots.

    Args:
        collection_id: Collection ID
        spot_data: Spot data dictionary (from parse_naver_bookmark)
        conn: Database connection

    Returns:
        spot_id
    """
    cursor = conn.cursor()

    # Find region code
    region_code = None
    if spot_data.get("address"):
        region_code = find_region_by_address(spot_data["address"])

    # Convert tags list to JSON string
    tags_json = json.dumps(spot_data["tags"], ensure_ascii=False)

    # Insert spot
    cursor.execute("""
        INSERT INTO user_collection_spots
        (collection_id, name, latitude, longitude, region_code, address,
         tags, memo, source_url, added_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """, (
        collection_id,
        spot_data["name"],
        spot_data["lat"],
        spot_data["lon"],
        region_code,
        spot_data["address"],
        tags_json,
        spot_data["memo"],
        spot_data["source_url"],
    ))

    conn.commit()
    return cursor.lastrowid


if __name__ == "__main__":
    # Simple test demonstration
    print("=== Import JSON Helper Test ===\n")

    # Test 1: Address parsing
    test_addresses = [
        "전라남도 순천시 해룡면",
        "전남 여수시 화정면",
        "경상북도 포항시 북구",
        "제주특별자치도 서귀포시 대정읍",
    ]

    print("1. Address parsing test:")
    for addr in test_addresses:
        region_code = find_region_by_address(addr)
        print(f"  {addr} -> {region_code}")

    # Test 2: Tag inference
    test_names = [
        ("송도해수욕장", ""),
        ("폐선 출사지", ""),
        ("순천만 갯벌", ""),
        ("호미곶 등대", ""),
        ("일출봉", ""),
    ]

    print("\n2. Tag inference test:")
    for name, mcid in test_names:
        tags = infer_tags_from_name(name, mcid)
        print(f"  {name} -> {tags}")

    # Test 3: Bookmark parsing
    sample_bookmark = {
        "name": "송도해수욕장",
        "x": "129.2156",
        "y": "35.0783",
        "address": "부산광역시 서구 암남동",
        "memo": "일몰 촬영 좋음",
        "id": "12345678",
        "mcid_name": "관광명소",
    }

    print("\n3. Bookmark parsing test:")
    parsed = parse_naver_bookmark(sample_bookmark)
    for key, value in parsed.items():
        print(f"  {key}: {value}")

    print("\n=== Test Complete ===")
