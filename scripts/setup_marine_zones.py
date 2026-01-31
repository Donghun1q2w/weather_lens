"""
Marine Zone Mapping Setup Script

Creates marine zone tables and populates mappings between
coastal regions and KMA marine forecast zones (해상예보구역).

Usage:
    python scripts/setup_marine_zones.py
"""
import sqlite3
import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import SQLITE_DB_PATH
from data.marine_zones import MARINE_ZONES, get_marine_zone


def create_marine_zone_tables():
    """Create marine zone tables in the database"""

    print(f"데이터베이스: {SQLITE_DB_PATH}")

    if not SQLITE_DB_PATH.exists():
        print(f"❌ 데이터베이스가 존재하지 않습니다: {SQLITE_DB_PATH}")
        print("먼저 scripts/init_database.py를 실행하세요.")
        return False

    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()

    # Create marine_zones table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS marine_zones (
            zone_code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            name_en TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create region_marine_zone mapping table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS region_marine_zone (
            region_code TEXT PRIMARY KEY,
            zone_code TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (region_code) REFERENCES regions(code),
            FOREIGN KEY (zone_code) REFERENCES marine_zones(zone_code)
        )
    """)

    # Create indexes for faster lookups
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_region_marine_zone ON region_marine_zone(zone_code)")

    conn.commit()
    print("✅ 테이블 생성 완료")

    return conn


def populate_marine_zones(conn):
    """Populate the marine_zones table with zone definitions"""

    cursor = conn.cursor()

    # Insert all marine zones
    zone_data = [
        (code, info["name"], info["name_en"])
        for code, info in MARINE_ZONES.items()
    ]

    cursor.executemany("""
        INSERT OR REPLACE INTO marine_zones (zone_code, name, name_en)
        VALUES (?, ?, ?)
    """, zone_data)

    conn.commit()
    print(f"✅ 해상예보구역 {len(zone_data)}개 삽입 완료")

    return True


def populate_region_mappings(conn):
    """Populate region to marine zone mappings based on regions table"""

    cursor = conn.cursor()

    # Fetch all coastal regions
    cursor.execute("""
        SELECT code, sido, is_coastal, is_west_coast, is_east_coast
        FROM regions
        WHERE is_coastal = 1
    """)

    coastal_regions = cursor.fetchall()

    if not coastal_regions:
        print("⚠️  해안 지역이 없습니다. 먼저 지역 데이터를 임포트하세요.")
        return False

    print(f"📊 해안 지역 {len(coastal_regions)}개 처리 중...")

    # Create mappings
    mappings = []
    skipped = 0

    for code, sido, is_coastal, is_west_coast, is_east_coast in coastal_regions:
        zone_code = get_marine_zone(
            sido=sido,
            is_coastal=bool(is_coastal),
            is_west_coast=bool(is_west_coast),
            is_east_coast=bool(is_east_coast)
        )

        if zone_code:
            mappings.append((code, zone_code))
        else:
            skipped += 1
            print(f"⚠️  매핑 실패: {sido} (code: {code})")

    # Insert mappings
    if mappings:
        cursor.executemany("""
            INSERT OR REPLACE INTO region_marine_zone (region_code, zone_code)
            VALUES (?, ?)
        """, mappings)

        conn.commit()
        print(f"✅ 지역-해상구역 매핑 {len(mappings)}개 생성 완료")

    if skipped > 0:
        print(f"⚠️  매핑 생성 실패: {skipped}개")

    return True


def verify_mappings(conn):
    """Verify the created mappings"""

    cursor = conn.cursor()

    print("\n" + "=" * 60)
    print("📊 매핑 결과 요약")
    print("=" * 60)

    # Count mappings per zone
    cursor.execute("""
        SELECT mz.name, mz.zone_code, COUNT(rmz.region_code) as region_count
        FROM marine_zones mz
        LEFT JOIN region_marine_zone rmz ON mz.zone_code = rmz.zone_code
        GROUP BY mz.zone_code, mz.name
        ORDER BY mz.zone_code
    """)

    results = cursor.fetchall()

    for name, zone_code, count in results:
        print(f"  {name} ({zone_code}): {count}개 지역")

    # Total counts
    cursor.execute("SELECT COUNT(*) FROM marine_zones")
    total_zones = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM region_marine_zone")
    total_mappings = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM regions WHERE is_coastal = 1")
    total_coastal = cursor.fetchone()[0]

    print("\n" + "=" * 60)
    print(f"해상예보구역: {total_zones}개")
    print(f"해안 지역: {total_coastal}개")
    print(f"매핑 생성: {total_mappings}개")
    print("=" * 60)

    return True


def main():
    """Main execution function"""

    print("=" * 60)
    print("Marine Zone Mapping Setup")
    print("=" * 60)

    # Create tables
    conn = create_marine_zone_tables()
    if not conn:
        return

    try:
        # Populate marine zones
        if not populate_marine_zones(conn):
            print("❌ 해상예보구역 데이터 삽입 실패")
            return

        # Populate region mappings
        if not populate_region_mappings(conn):
            print("⚠️  지역 매핑 생성 중 문제 발생")
            # Continue to verify even if some mappings failed

        # Verify results
        verify_mappings(conn)

        print("\n" + "=" * 60)
        print("✅ Marine Zone Mapping Setup 완료!")
        print("=" * 60)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
