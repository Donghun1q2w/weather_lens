#!/usr/bin/env python3
"""
Mark regions adjacent to the South Sea (남해).

CRITICAL DISTINCTION:
- 남해 (South Sea) = The body of water between Korea's southern coast and Japan/Tsushima
- 남해군 = Namhae County in 경상남도 (a LAND region adjacent to the South Sea)
"""

import sqlite3
from pathlib import Path

DB_PATH = "/Users/donghun/Documents/git_repository/weather_lens/data/regions.db"

# South Sea adjacent sigungu (entire sigungu is coastal)
SOUTH_SEA_SIGUNGU_FULL = [
    # 경상남도 - Full coastal
    ("경상남도", "남해군"),      # 남해군 - island county in the South Sea
    ("경상남도", "통영시"),      # 통영시 - all coastal
    ("경상남도", "거제시"),      # 거제시 - island city
    ("경상남도", "고성군"),      # 고성군 - south coast
    ("경상남도", "사천시"),      # 사천시 - south coast
    ("경상남도", "하동군"),      # 하동군 - 섬진강 estuary

    # 부산광역시
    ("부산광역시", "영도구"),    # Yeongdo island
    ("부산광역시", "서구"),      # Songdo area
    ("부산광역시", "사하구"),    # Dadaepo area
    ("부산광역시", "강서구"),    # Gadeokdo island
    ("부산광역시", "중구"),      # Coastal areas

    # 전라남도 - South coast
    ("전라남도", "여수시"),      # Dolsan, southern areas
    ("전라남도", "고흥군"),      # Southern coast
    ("전라남도", "완도군"),      # Wando islands
    ("전라남도", "장흥군"),      # Southern coast
    ("전라남도", "강진군"),      # Southern coast
    ("전라남도", "보성군"),      # Beolgyo area
]

# Partial sigungu (only certain gu/emd are coastal)
SOUTH_SEA_SIGUNGU_PARTIAL = [
    ("경상남도", "창원시", "마산합포구"),  # Coastal parts
    ("경상남도", "창원시", "진해구"),      # Southern coast
    ("전라남도", "해남군"),                 # Southern areas only
    ("전라남도", "진도군"),                 # Southern parts
]

# Additional Busan areas (partial)
BUSAN_PARTIAL = [
    ("부산광역시", "동구"),      # Some coastal areas
    ("부산광역시", "남구"),      # Some coastal areas
]


def mark_south_coast():
    """Mark all regions adjacent to the South Sea."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    total_marked = 0

    # Mark full sigungu
    print("Marking full sigungu...")
    for sido, sigungu in SOUTH_SEA_SIGUNGU_FULL:
        cursor.execute(
            "UPDATE regions SET is_south_coast = 1 WHERE sido = ? AND sigungu = ?",
            (sido, sigungu)
        )
        count = cursor.rowcount
        total_marked += count
        print(f"  {sido} {sigungu}: {count} regions")

    # Mark partial sigungu (창원시 specific gu)
    # Note: In the database, 창원시 gu are stored as part of sigungu name
    print("\nMarking partial sigungu (창원시)...")
    for sido, sigungu in [
        ("경상남도", "창원시마산합포구"),
        ("경상남도", "창원시진해구"),
    ]:
        cursor.execute(
            "UPDATE regions SET is_south_coast = 1 WHERE sido = ? AND sigungu = ?",
            (sido, sigungu)
        )
        count = cursor.rowcount
        total_marked += count
        print(f"  {sido} {sigungu}: {count} regions")

    # Mark 해남군 southern areas (conservative approach - mark all for now)
    print("\nMarking 해남군...")
    cursor.execute(
        "UPDATE regions SET is_south_coast = 1 WHERE sido = ? AND sigungu = ?",
        ("전라남도", "해남군")
    )
    count = cursor.rowcount
    total_marked += count
    print(f"  전라남도 해남군: {count} regions")

    # Mark 진도군 southern areas (conservative approach - mark all for now)
    print("\nMarking 진도군...")
    cursor.execute(
        "UPDATE regions SET is_south_coast = 1 WHERE sido = ? AND sigungu = ?",
        ("전라남도", "진도군")
    )
    count = cursor.rowcount
    total_marked += count
    print(f"  전라남도 진도군: {count} regions")

    # Mark Busan partial areas
    print("\nMarking Busan partial areas...")
    for sido, sigungu in BUSAN_PARTIAL:
        cursor.execute(
            "UPDATE regions SET is_south_coast = 1 WHERE sido = ? AND sigungu = ?",
            (sido, sigungu)
        )
        count = cursor.rowcount
        total_marked += count
        print(f"  {sido} {sigungu}: {count} regions")

    conn.commit()

    # Verify results
    print("\n" + "="*60)
    print("VERIFICATION - Regions marked as South Sea adjacent:")
    print("="*60)

    cursor.execute("""
        SELECT sido, sigungu, COUNT(*) as cnt
        FROM regions
        WHERE is_south_coast = 1
        GROUP BY sido, sigungu
        ORDER BY sido, sigungu
    """)

    results = cursor.fetchall()
    sido_totals = {}

    for sido, sigungu, count in results:
        print(f"{sido:15s} {sigungu:20s} {count:5d} regions")
        sido_totals[sido] = sido_totals.get(sido, 0) + count

    print("\n" + "="*60)
    print("Summary by Sido:")
    print("="*60)
    for sido, count in sorted(sido_totals.items()):
        print(f"{sido:15s} {count:5d} regions")

    print("\n" + "="*60)
    print(f"TOTAL: {total_marked} regions marked as South Sea adjacent")
    print("="*60)

    conn.close()

    return total_marked


if __name__ == "__main__":
    mark_south_coast()
