"""
네이버 지도 북마크 데이터를 사용자 컬렉션으로 임포트

출사리스트.json 파일을 읽어서:
1. user_collections 테이블에 컬렉션 생성
2. user_collection_spots 테이블에 북마크들을 추가
3. 주소 정보를 바탕으로 region_code 매칭
4. displayName/mcidName 기반으로 태그 자동 추론

사용법:
    python scripts/import_naver_spots.py
"""
import json
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import SQLITE_DB_PATH

# 네이버 지도 JSON 파일 경로
NAVER_JSON_PATH = PROJECT_ROOT / "출사리스트.json"


def find_region_code(conn, address):
    """
    주소 문자열에서 region_code 찾기

    예: "전남 순천시 별량면 무풍리 88-7" -> 순천시에 해당하는 region_code
    """
    if not address:
        return None

    cursor = conn.cursor()

    # 주소를 공백으로 분리
    parts = address.replace("광역시", "시").replace("특별시", "시").replace("특별자치도", "도").replace("특별자치시", "시").split()

    if len(parts) < 2:
        return None

    sido = parts[0]  # 예: "전남", "강원"
    sigungu = parts[1]  # 예: "순천시", "강릉시"

    # sido 정규화
    sido_map = {
        "전남": "전라남도",
        "전북": "전북특별자치도",
        "경남": "경상남도",
        "경북": "경상북도",
        "충남": "충청남도",
        "충북": "충청북도",
        "강원": "강원특별자치도",
        "제주": "제주특별자치도",
        "서울": "서울특별시",
        "부산": "부산광역시",
        "대구": "대구광역시",
        "인천": "인천광역시",
        "광주": "광주광역시",
        "대전": "대전광역시",
        "울산": "울산광역시",
        "세종": "세종특별자치시",
    }

    full_sido = sido_map.get(sido, sido)

    # regions 테이블에서 매칭 시도
    # 1차: sido + sigungu 정확히 매칭
    cursor.execute("""
        SELECT code FROM regions
        WHERE sido = ? AND sigungu = ?
        LIMIT 1
    """, (full_sido, sigungu))

    result = cursor.fetchone()
    if result:
        return result[0]

    # 2차: sido만 매칭 (시군구가 정확하지 않은 경우)
    cursor.execute("""
        SELECT code FROM regions
        WHERE sido = ?
        LIMIT 1
    """, (full_sido,))

    result = cursor.fetchone()
    return result[0] if result else None


def infer_tags(display_name, mcid_name, name):
    """
    displayName, mcidName, name을 분석해서 태그 추론
    """
    text = f"{display_name} {mcid_name} {name}".lower()

    tags = set()

    # 해변/바다 관련
    if any(keyword in text for keyword in ["해수욕장", "해변", "beach"]):
        tags.update(["해변", "바다"])

    # 폐선 관련
    elif "폐선" in text:
        tags.update(["폐선", "장노출"])

    # 칠면초/갯벌 관련
    elif any(keyword in text for keyword in ["칠면초", "갯골", "갯벌"]):
        tags.update(["갯벌", "일몰"])

    # 바위 관련
    elif "바위" in text:
        tags.update(["바위", "장노출"])

    # 매생이 (특수 케이스)
    elif "매생이" in text:
        tags.update(["갯벌", "일몰", "매생이"])

    # 산/산악
    elif any(keyword in text for keyword in ["산", "봉", "고지", "peak"]):
        tags.update(["산악", "일출"])

    # 기본값
    if not tags:
        tags.add("장노출")

    return list(tags)


def import_naver_bookmarks():
    """네이버 지도 북마크를 사용자 컬렉션으로 임포트"""

    # JSON 파일 읽기
    if not NAVER_JSON_PATH.exists():
        print(f"❌ 파일을 찾을 수 없습니다: {NAVER_JSON_PATH}")
        return

    with open(NAVER_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    folder = data.get("folder", {})
    bookmarks = data.get("bookmarkList", [])

    print(f"📂 컬렉션: {folder.get('name')}")
    print(f"📌 북마크 수: {len(bookmarks)}개")

    # DB 연결
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()

    # 1. user_collection 생성
    user_id = "default_user"
    collection_name = folder.get("name", "장노출")
    color_code = folder.get("colorCode", "1")
    icon_id = folder.get("iconId", "1")

    cursor.execute("""
        INSERT OR IGNORE INTO user_collections
        (user_id, name, description, color_code, icon_id, is_default)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, collection_name, "", color_code, icon_id, True))

    # collection_id 가져오기
    cursor.execute("""
        SELECT id FROM user_collections
        WHERE user_id = ? AND name = ?
    """, (user_id, collection_name))

    collection_id = cursor.fetchone()[0]
    print(f"✅ 컬렉션 생성/확인: ID={collection_id}")

    # 2. 북마크들을 user_collection_spots에 추가
    inserted = 0
    skipped = 0

    for bookmark in bookmarks:
        # name 결정: displayName이 있으면 사용, 없으면 address 사용
        display_name = bookmark.get("displayName", "").strip()
        name = display_name if display_name else bookmark.get("name", "")
        address = bookmark.get("address", "")

        if not name:
            print(f"  ⚠️ 이름 없음, 건너뜀: {bookmark.get('bookmarkId')}")
            skipped += 1
            continue

        # 좌표
        lat = bookmark.get("py")
        lon = bookmark.get("px")

        # region_code 찾기
        region_code = find_region_code(conn, address)

        # 태그 추론
        mcid_name = bookmark.get("mcidName", "")
        tags = infer_tags(display_name, mcid_name, name)

        # source_url
        source_url = bookmark.get("url", "")

        # memo (북마크의 memo 필드)
        memo = bookmark.get("memo", "")

        # 삽입
        try:
            cursor.execute("""
                INSERT INTO user_collection_spots
                (collection_id, photo_spot_id, custom_name, custom_lat, custom_lon,
                 region_code, memo, tags, source_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                collection_id,
                None,  # photo_spot_id는 NULL (사용자 커스텀 스팟)
                name,
                lat,
                lon,
                region_code,
                memo,
                ",".join(tags),
                source_url
            ))
            inserted += 1

            if inserted <= 5:  # 처음 5개만 자세히 출력
                print(f"  ✅ [{inserted}] {name}")
                print(f"      주소: {address}")
                print(f"      좌표: ({lat}, {lon})")
                print(f"      지역코드: {region_code}")
                print(f"      태그: {', '.join(tags)}")

        except Exception as e:
            print(f"  ❌ 실패: {name} - {e}")
            skipped += 1

    conn.commit()

    # 3. 요약 출력
    print("\n" + "=" * 60)
    print("📊 임포트 완료")
    print("=" * 60)
    print(f"✅ 추가된 스팟: {inserted}개")
    print(f"⚠️ 건너뛴 스팟: {skipped}개")

    # 태그별 통계
    cursor.execute("""
        SELECT tags, COUNT(*) as cnt
        FROM user_collection_spots
        WHERE collection_id = ?
        GROUP BY tags
        ORDER BY cnt DESC
    """, (collection_id,))

    print("\n태그별 분포:")
    for row in cursor.fetchall():
        tags = row[0]
        count = row[1]
        print(f"  {tags}: {count}개")

    conn.close()


def main():
    print("=" * 60)
    print("네이버 지도 북마크 임포트")
    print("=" * 60)

    import_naver_bookmarks()

    print("\n" + "=" * 60)
    print("✅ 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
