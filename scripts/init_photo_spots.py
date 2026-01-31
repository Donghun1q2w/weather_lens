"""
출사포인트 테이블 초기화 및 기본 데이터 입력

출사포인트 = 촬영 명소 별명 + 실제 지역(읍면동) 연동
"""
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import SQLITE_DB_PATH

# 기본 출사포인트 데이터 (유명 촬영지)
DEFAULT_PHOTO_SPOTS = [
    # ===== 동해안 일출 명소 =====
    {
        "name": "정동진",
        "region_code": "42150",  # 강릉시
        "lat": 37.6899,
        "lon": 129.0344,
        "themes": [1, 2, 13],  # 일출, 일출오메가, 골든아워
        "description": "대한민국 대표 일출 명소, 모래시계 공원",
        "tags": ["일출", "동해", "해돋이"],
    },
    {
        "name": "주문진 방파제",
        "region_code": "42150",  # 강릉시
        "lat": 37.8987,
        "lon": 128.8218,
        "themes": [1, 2, 7],  # 일출, 일출오메가, 바다장노출
        "description": "BTS 앨범 재킷 촬영지, 방파제 일출",
        "tags": ["일출", "방파제", "BTS"],
    },
    {
        "name": "속초 영금정",
        "region_code": "42230",  # 속초시
        "lat": 38.2070,
        "lon": 128.5918,
        "themes": [1, 2],
        "description": "기암괴석과 일출, 영금정 해맞이",
        "tags": ["일출", "기암", "속초"],
    },
    {
        "name": "울산 간절곶",
        "region_code": "31710",  # 울주군
        "lat": 35.3620,
        "lon": 129.3611,
        "themes": [1, 2],
        "description": "한반도 가장 먼저 해뜨는 곳",
        "tags": ["일출", "간절곶", "새해"],
    },
    {
        "name": "포항 호미곶",
        "region_code": "47111",  # 포항시
        "lat": 36.0769,
        "lon": 129.5681,
        "themes": [1, 2],
        "description": "상생의 손, 한반도 최동단",
        "tags": ["일출", "호미곶", "상생의손"],
    },
    {
        "name": "부산 해운대",
        "region_code": "26350",  # 해운대구
        "lat": 35.1587,
        "lon": 129.1604,
        "themes": [1, 10, 14],  # 일출, 야경, 블루아워
        "description": "해운대 해수욕장 일출, 마린시티 야경",
        "tags": ["일출", "야경", "해운대"],
    },

    # ===== 서해안 일몰 명소 =====
    {
        "name": "인천 을왕리",
        "region_code": "28110",  # 중구
        "lat": 37.4469,
        "lon": 126.3769,
        "themes": [3, 4, 13],  # 일몰, 일몰오메가, 골든아워
        "description": "영종도 을왕리 해수욕장 일몰",
        "tags": ["일몰", "을왕리", "영종도"],
    },
    {
        "name": "강화 동막해변",
        "region_code": "28710",  # 강화군
        "lat": 37.5833,
        "lon": 126.4500,
        "themes": [3, 4],
        "description": "갯벌과 낙조, 강화도 대표 일몰",
        "tags": ["일몰", "갯벌", "강화도"],
    },
    {
        "name": "태안 꽃지해변",
        "region_code": "44825",  # 태안군
        "lat": 36.5167,
        "lon": 126.3333,
        "themes": [3, 4, 7],
        "description": "할미할아비 바위 낙조, 태안 대표 일몰",
        "tags": ["일몰", "꽃지", "할미바위"],
    },
    {
        "name": "무안 도리포",
        "region_code": "46840",  # 무안군
        "lat": 34.9833,
        "lon": 126.3667,
        "themes": [3, 4],
        "description": "노을이 아름다운 서해안 낙조",
        "tags": ["일몰", "노을", "서해"],
    },

    # ===== 제주 =====
    {
        "name": "성산일출봉",
        "region_code": "50130",  # 서귀포시
        "lat": 33.4590,
        "lon": 126.9426,
        "themes": [1, 2, 13],
        "description": "유네스코 세계자연유산, 제주 대표 일출",
        "tags": ["일출", "성산", "유네스코"],
    },
    {
        "name": "1100고지 습지",
        "region_code": "50130",  # 서귀포시
        "lat": 33.3625,
        "lon": 126.5347,
        "themes": [8, 5, 15],  # 운해, 은하수, 상고대
        "description": "한라산 1100고지, 운해와 상고대 명소",
        "tags": ["운해", "상고대", "한라산"],
        "elevation": 1100,
    },
    {
        "name": "영실",
        "region_code": "50130",
        "lat": 33.3472,
        "lon": 126.4958,
        "themes": [8, 15],
        "description": "한라산 영실, 오백나한 운해",
        "tags": ["운해", "영실", "한라산"],
        "elevation": 1280,
    },
    {
        "name": "섭지코지",
        "region_code": "50130",
        "lat": 33.4239,
        "lon": 126.9306,
        "themes": [1, 3, 13],
        "description": "제주 동쪽 해안 절경, 유채꽃밭",
        "tags": ["일출", "유채꽃", "제주"],
    },
    {
        "name": "협재해변",
        "region_code": "50110",  # 제주시
        "lat": 33.3939,
        "lon": 126.2397,
        "themes": [3, 4],
        "description": "에메랄드빛 바다와 일몰",
        "tags": ["일몰", "협재", "에메랄드"],
    },

    # ===== 산악/운해 =====
    {
        "name": "대관령 양떼목장",
        "region_code": "42760",  # 평창군
        "lat": 37.6833,
        "lon": 128.7500,
        "themes": [8, 1, 15],
        "description": "대관령 운해, 목장 풍경",
        "tags": ["운해", "대관령", "목장"],
        "elevation": 850,
    },
    {
        "name": "태백 매봉산",
        "region_code": "42190",  # 태백시
        "lat": 37.1500,
        "lon": 128.9833,
        "themes": [8, 5, 9],  # 운해, 은하수, 별궤적
        "description": "바람의 언덕, 풍력발전기와 운해",
        "tags": ["운해", "풍력발전기", "태백"],
        "elevation": 1303,
    },
    {
        "name": "지리산 노고단",
        "region_code": "46730",  # 구례군
        "lat": 35.2833,
        "lon": 127.5167,
        "themes": [8, 5, 1],
        "description": "지리산 운해, 일출 명소",
        "tags": ["운해", "지리산", "노고단"],
        "elevation": 1507,
    },
    {
        "name": "소백산 비로봉",
        "region_code": "43800",  # 단양군
        "lat": 36.9500,
        "lon": 128.4833,
        "themes": [8, 15, 5],
        "description": "철쭉과 운해, 겨울 상고대",
        "tags": ["운해", "상고대", "소백산"],
        "elevation": 1439,
    },

    # ===== 은하수/별 =====
    {
        "name": "영양 반딧불이 천문대",
        "region_code": "47760",  # 영양군
        "lat": 36.6500,
        "lon": 129.1167,
        "themes": [5, 9],  # 은하수, 별궤적
        "description": "국내 유일 국제밤하늘보호공원, 최고 은하수 촬영지",
        "tags": ["은하수", "별", "천문대"],
    },
    {
        "name": "보성 봇재",
        "region_code": "46780",  # 보성군
        "lat": 34.8000,
        "lon": 127.0500,
        "themes": [5, 9, 11],  # 은하수, 별궤적, 안개
        "description": "남부 은하수 명소, 차밭과 별",
        "tags": ["은하수", "보성", "차밭"],
    },
    {
        "name": "고성 당항포",
        "region_code": "48820",  # 고성군
        "lat": 34.9833,
        "lon": 128.3667,
        "themes": [5, 9],
        "description": "남해안 은하수, 당항포 관광지",
        "tags": ["은하수", "당항포", "남해"],
    },

    # ===== 야경 =====
    {
        "name": "남산타워",
        "region_code": "11170",  # 용산구
        "lat": 37.5512,
        "lon": 126.9882,
        "themes": [10, 14],  # 야경, 블루아워
        "description": "서울 대표 야경 촬영지",
        "tags": ["야경", "서울", "남산"],
    },
    {
        "name": "북악스카이웨이",
        "region_code": "11290",  # 성북구
        "lat": 37.6000,
        "lon": 126.9833,
        "themes": [10, 14],
        "description": "서울 전경, 팔각정 야경",
        "tags": ["야경", "서울", "전경"],
    },
    {
        "name": "부산 황령산",
        "region_code": "26290",  # 남구
        "lat": 35.1333,
        "lon": 129.0833,
        "themes": [10, 14],
        "description": "부산 시내 전경, 광안대교 야경",
        "tags": ["야경", "부산", "광안대교"],
    },

    # ===== 안개/반영 =====
    {
        "name": "충주호 탄금호",
        "region_code": "43130",  # 충주시
        "lat": 36.9667,
        "lon": 127.9333,
        "themes": [11, 12],  # 안개, 반영
        "description": "물안개와 반영, 일출",
        "tags": ["안개", "반영", "충주호"],
    },
    {
        "name": "청평호",
        "region_code": "41830",  # 가평군
        "lat": 37.7333,
        "lon": 127.4333,
        "themes": [11, 12],
        "description": "물안개 명소, 잔잔한 호수 반영",
        "tags": ["안개", "반영", "청평호"],
    },

    # ===== 야광충/바다 =====
    {
        "name": "진도 세방낙조",
        "region_code": "46900",  # 진도군
        "lat": 34.4833,
        "lon": 126.2500,
        "themes": [3, 6],  # 일몰, 야광충
        "description": "세방낙조 전망대, 여름 야광충",
        "tags": ["일몰", "야광충", "진도"],
    },
    {
        "name": "통영 동피랑",
        "region_code": "48220",  # 통영시
        "lat": 34.8500,
        "lon": 128.4333,
        "themes": [10, 6],
        "description": "벽화마을 야경, 여름 야광충",
        "tags": ["야경", "벽화마을", "통영"],
    },
]


def init_photo_spots_table():
    """출사포인트 테이블 생성"""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()

    # 출사포인트 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS photo_spots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            region_code TEXT,
            lat REAL,
            lon REAL,
            elevation INTEGER DEFAULT 0,
            description TEXT,
            tags TEXT,
            created_by TEXT DEFAULT 'system',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
    """)

    # 출사포인트-테마 연결 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS photo_spot_themes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            spot_id INTEGER NOT NULL,
            theme_id INTEGER NOT NULL,
            FOREIGN KEY (spot_id) REFERENCES photo_spots(id),
            UNIQUE(spot_id, theme_id)
        )
    """)

    # 인덱스
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_photo_spots_region ON photo_spots(region_code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_photo_spot_themes_spot ON photo_spot_themes(spot_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_photo_spot_themes_theme ON photo_spot_themes(theme_id)")

    conn.commit()
    conn.close()
    print("✅ 테이블 생성 완료")


def insert_default_spots():
    """기본 출사포인트 데이터 입력"""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()

    inserted = 0
    for spot in DEFAULT_PHOTO_SPOTS:
        try:
            # 출사포인트 입력
            cursor.execute("""
                INSERT OR IGNORE INTO photo_spots
                (name, region_code, lat, lon, elevation, description, tags, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'system')
            """, (
                spot["name"],
                spot["region_code"],
                spot["lat"],
                spot["lon"],
                spot.get("elevation", 0),
                spot.get("description", ""),
                ",".join(spot.get("tags", [])),
            ))

            if cursor.rowcount > 0:
                inserted += 1
                spot_id = cursor.lastrowid

                # 테마 연결
                for theme_id in spot.get("themes", []):
                    cursor.execute("""
                        INSERT OR IGNORE INTO photo_spot_themes (spot_id, theme_id)
                        VALUES (?, ?)
                    """, (spot_id, theme_id))

        except Exception as e:
            print(f"  ⚠️ {spot['name']}: {e}")

    conn.commit()

    # 통계
    cursor.execute("SELECT COUNT(*) FROM photo_spots")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM photo_spot_themes")
    themes = cursor.fetchone()[0]

    conn.close()

    print(f"✅ {inserted}개 추가 (총 {total}개 출사포인트, {themes}개 테마 연결)")


def show_stats():
    """통계 출력"""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()

    print("\n" + "=" * 60)
    print("📸 출사포인트 현황")
    print("=" * 60)

    # 테마별 출사포인트 수
    cursor.execute("""
        SELECT pst.theme_id, COUNT(*) as cnt
        FROM photo_spot_themes pst
        GROUP BY pst.theme_id
        ORDER BY pst.theme_id
    """)

    from config.settings import THEME_IDS
    print("\n테마별 출사포인트:")
    for row in cursor.fetchall():
        theme_name = THEME_IDS.get(row[0], f"테마{row[0]}")
        print(f"  [{row[0]:2d}] {theme_name:<12}: {row[1]}개")

    # 지역별
    cursor.execute("""
        SELECT SUBSTR(region_code, 1, 2) as sido, COUNT(*) as cnt
        FROM photo_spots
        GROUP BY sido
        ORDER BY cnt DESC
        LIMIT 10
    """)

    print("\n지역별 출사포인트 (TOP 10):")
    sido_names = {
        "11": "서울", "26": "부산", "27": "대구", "28": "인천",
        "29": "광주", "30": "대전", "31": "울산", "36": "세종",
        "41": "경기", "42": "강원", "43": "충북", "44": "충남",
        "45": "전북", "46": "전남", "47": "경북", "48": "경남", "50": "제주",
    }
    for row in cursor.fetchall():
        sido_name = sido_names.get(row[0], row[0])
        print(f"  {sido_name}: {row[1]}개")

    conn.close()


def main():
    print("=" * 60)
    print("출사포인트 테이블 초기화")
    print("=" * 60)

    init_photo_spots_table()
    insert_default_spots()
    show_stats()

    print("\n" + "=" * 60)
    print("✅ 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
