"""
데이터베이스 초기화 스크립트

이 스크립트는 regions.db를 생성하고 기본 테이블을 만듭니다.
실제 지역 데이터는 별도로 삽입해야 합니다.

사용법:
    python scripts/init_database.py
"""
import sqlite3
from pathlib import Path
import sys

# 프로젝트 루트를 Python 경로에 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import DATA_DIR, SQLITE_DB_PATH, OCEAN_MAPPING_DB_PATH


def create_regions_database():
    """regions.db 생성 및 테이블 초기화"""

    # data 디렉토리가 없으면 생성
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print(f"데이터베이스 생성 중: {SQLITE_DB_PATH}")

    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()

    # regions 테이블 생성
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS regions (
            code TEXT PRIMARY KEY,          -- 읍면동 코드 (예: "1168010100")
            name TEXT NOT NULL,             -- 전체 지역명 (예: "서울특별시 강남구 역삼동")
            sido TEXT NOT NULL,             -- 시/도 (예: "서울특별시")
            sigungu TEXT NOT NULL,          -- 시/군/구 (예: "강남구")
            emd TEXT NOT NULL,              -- 읍/면/동 (예: "역삼동")
            lat REAL NOT NULL,              -- 위도
            lon REAL NOT NULL,              -- 경도
            nx INTEGER,                     -- 기상청 격자 X 좌표
            ny INTEGER,                     -- 기상청 격자 Y 좌표
            elevation REAL DEFAULT 0,       -- 해발고도 (m)
            is_coastal INTEGER DEFAULT 0,   -- 해안가 여부 (0 or 1)
            is_east_coast INTEGER DEFAULT 0,-- 동해안 여부 (0 or 1)
            ocean_station_id TEXT,          -- 연결된 해양관측소 ID
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 인덱스 생성 (검색 속도 향상)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_regions_sido ON regions(sido)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_regions_coastal ON regions(is_coastal)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_regions_elevation ON regions(elevation)")

    conn.commit()
    print("✅ regions 테이블 생성 완료")

    # 샘플 데이터 삽입 (테스트용)
    sample_regions = [
        ("1168010100", "서울특별시 강남구 역삼동", "서울특별시", "강남구", "역삼동",
         37.5007, 127.0365, 60, 127, 30, 0, 0, None),
        ("2644010100", "부산광역시 해운대구 우동", "부산광역시", "해운대구", "우동",
         35.1631, 129.1635, 99, 76, 5, 1, 0, "DT_0001"),
        ("4211010100", "강원특별자치도 강릉시 강문동", "강원특별자치도", "강릉시", "강문동",
         37.7943, 128.9089, 92, 131, 3, 1, 1, "DT_0002"),
        ("5011010100", "제주특별자치도 제주시 삼도1동", "제주특별자치도", "제주시", "삼도1동",
         33.5097, 126.5219, 52, 38, 20, 1, 0, "DT_0003"),
    ]

    cursor.executemany("""
        INSERT OR REPLACE INTO regions
        (code, name, sido, sigungu, emd, lat, lon, nx, ny, elevation, is_coastal, is_east_coast, ocean_station_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, sample_regions)

    conn.commit()
    print(f"✅ 샘플 데이터 {len(sample_regions)}개 삽입 완료")

    # 확인
    cursor.execute("SELECT COUNT(*) FROM regions")
    count = cursor.fetchone()[0]
    print(f"📊 현재 등록된 지역 수: {count}개")

    conn.close()
    return SQLITE_DB_PATH


def create_ocean_mapping_database():
    """ocean_mapping.db 생성 및 테이블 초기화"""

    print(f"\n데이터베이스 생성 중: {OCEAN_MAPPING_DB_PATH}")

    conn = sqlite3.connect(OCEAN_MAPPING_DB_PATH)
    cursor = conn.cursor()

    # ocean_stations 테이블 생성
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ocean_stations (
            station_id TEXT PRIMARY KEY,    -- 관측소 ID (예: "DT_0001")
            station_name TEXT NOT NULL,     -- 관측소 이름 (예: "부산")
            lat REAL NOT NULL,              -- 위도
            lon REAL NOT NULL,              -- 경도
            station_type TEXT,              -- 관측소 유형 (tide/wave/both)
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 샘플 해양관측소 데이터
    sample_stations = [
        ("DT_0001", "부산", 35.0962, 129.0360, "both"),
        ("DT_0002", "강릉", 37.7519, 128.8963, "both"),
        ("DT_0003", "제주", 33.5163, 126.5265, "both"),
        ("DT_0004", "인천", 37.4519, 126.5920, "tide"),
        ("DT_0005", "포항", 36.0322, 129.3650, "both"),
    ]

    cursor.executemany("""
        INSERT OR REPLACE INTO ocean_stations
        (station_id, station_name, lat, lon, station_type)
        VALUES (?, ?, ?, ?, ?)
    """, sample_stations)

    conn.commit()
    print(f"✅ 샘플 해양관측소 {len(sample_stations)}개 삽입 완료")

    conn.close()
    return OCEAN_MAPPING_DB_PATH


def main():
    """메인 실행 함수"""
    print("=" * 50)
    print("Weather Lens 데이터베이스 초기화")
    print("=" * 50)

    # 1. regions.db 생성
    regions_path = create_regions_database()

    # 2. ocean_mapping.db 생성
    ocean_path = create_ocean_mapping_database()

    print("\n" + "=" * 50)
    print("✅ 데이터베이스 초기화 완료!")
    print("=" * 50)
    print(f"\n생성된 파일:")
    print(f"  - {regions_path}")
    print(f"  - {ocean_path}")
    print(f"\n⚠️  현재는 샘플 데이터만 포함되어 있습니다.")
    print(f"    전체 3,500개 지역 데이터는 별도로 삽입해야 합니다.")
    print(f"\n다음 단계:")
    print(f"  1. 행정구역 데이터 다운로드 (data.go.kr)")
    print(f"  2. scripts/import_regions.py 실행하여 전체 데이터 삽입")


if __name__ == "__main__":
    main()
