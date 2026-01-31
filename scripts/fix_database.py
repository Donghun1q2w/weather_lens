#!/usr/bin/env python3
"""
Fix database issues found during validation.
Addresses:
1. Sequential-code records (codes starting with '0000')
2. Double-space naming issues
3. Duplicate EMD entries
4. Invalid (0,0) coordinates
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "regions.db"


def fix_sequential_codes(conn):
    """Remove records with sequential codes (0000*)."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM regions WHERE code LIKE '0000%'")
    count_before = cursor.fetchone()[0]

    print(f"[1/4] Removing {count_before} sequential-code records...")
    cursor.execute("DELETE FROM regions WHERE code LIKE '0000%'")
    conn.commit()
    print(f"      ✓ Deleted {count_before} records")


def fix_double_spaces(conn):
    """Fix double-space issues in sigungu names."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM regions WHERE sigungu LIKE '%  %'")
    count_before = cursor.fetchone()[0]

    print(f"[2/4] Fixing {count_before} records with double-space sigungu names...")
    cursor.execute("UPDATE regions SET sigungu = REPLACE(sigungu, '  ', ' ')")
    cursor.execute("UPDATE regions SET sigungu = TRIM(sigungu)")
    conn.commit()
    print(f"      ✓ Fixed double-space naming")


def fix_duplicates(conn):
    """Remove duplicate EMD entries, keeping the better record."""
    cursor = conn.cursor()

    # Find duplicates
    cursor.execute("""
        SELECT sido, sigungu, emd, GROUP_CONCAT(code) as codes
        FROM regions
        GROUP BY sido, sigungu, emd
        HAVING COUNT(*) > 1
    """)
    duplicates = cursor.fetchall()

    print(f"[3/4] Fixing {len(duplicates)} duplicate EMD entries...")

    deleted_count = 0
    for sido, sigungu, emd, codes in duplicates:
        codes_list = codes.split(',')

        # Get all records for this location
        cursor.execute("""
            SELECT code, lat, lon, nx, ny, elevation, is_coastal, is_east_coast
            FROM regions
            WHERE sido = ? AND sigungu = ? AND emd = ?
            ORDER BY
                CASE WHEN lat = 0.0 AND lon = 0.0 THEN 1 ELSE 0 END,  -- invalid coords last
                CASE WHEN code LIKE '0000%' THEN 1 ELSE 0 END,         -- sequential codes last
                LENGTH(code) DESC,                                     -- longer codes first
                code
        """, (sido, sigungu, emd))

        records = cursor.fetchall()

        # Keep the first (best) record, delete the rest
        keep_code = records[0][0]
        delete_codes = [r[0] for r in records[1:]]

        for code in delete_codes:
            cursor.execute("DELETE FROM regions WHERE code = ?", (code,))
            deleted_count += 1

    conn.commit()
    print(f"      ✓ Deleted {deleted_count} duplicate records")


def fix_invalid_coordinates(conn):
    """Fix records with invalid (0,0) coordinates."""
    cursor = conn.cursor()

    # Find records with invalid coordinates
    cursor.execute("""
        SELECT code, sido, sigungu, emd
        FROM regions
        WHERE lat = 0.0 AND lon = 0.0
    """)
    invalid_records = cursor.fetchall()

    print(f"[4/4] Fixing {len(invalid_records)} records with invalid coordinates...")

    fixed_count = 0
    for code, sido, sigungu, emd in invalid_records:
        # Try to find sigungu center from other records
        cursor.execute("""
            SELECT AVG(lat), AVG(lon)
            FROM regions
            WHERE sido = ? AND sigungu = ? AND lat != 0.0 AND lon != 0.0
        """, (sido, sigungu))

        result = cursor.fetchone()
        if result and result[0] is not None:
            avg_lat, avg_lon = result

            # Calculate nx, ny using the conversion formula
            # This is a simplified version - you might want to use the exact conversion
            nx = int((avg_lon - 126.0) / 0.01 + 1)
            ny = int((avg_lat - 33.0) / 0.01 + 1)

            cursor.execute("""
                UPDATE regions
                SET lat = ?, lon = ?, nx = ?, ny = ?
                WHERE code = ?
            """, (avg_lat, avg_lon, nx, ny, code))
            fixed_count += 1
        else:
            # If we can't find coordinates, delete the record
            cursor.execute("DELETE FROM regions WHERE code = ?", (code,))

    conn.commit()
    print(f"      ✓ Fixed {fixed_count} invalid coordinates, deleted {len(invalid_records) - fixed_count} unfixable records")


def verify_cleanup(conn):
    """Verify the cleanup was successful."""
    cursor = conn.cursor()

    print("\n=== VERIFICATION ===")

    # Check total count
    cursor.execute("SELECT COUNT(*) FROM regions")
    total = cursor.fetchone()[0]
    print(f"Total records: {total}")

    # Check for sequential codes
    cursor.execute("SELECT COUNT(*) FROM regions WHERE code LIKE '0000%'")
    seq_codes = cursor.fetchone()[0]
    print(f"Sequential codes: {seq_codes} {'✓' if seq_codes == 0 else '✗'}")

    # Check for double spaces
    cursor.execute("SELECT COUNT(*) FROM regions WHERE sigungu LIKE '%  %'")
    double_spaces = cursor.fetchone()[0]
    print(f"Double-space names: {double_spaces} {'✓' if double_spaces == 0 else '✗'}")

    # Check for duplicates
    cursor.execute("""
        SELECT COUNT(*) FROM (
            SELECT sido, sigungu, emd
            FROM regions
            GROUP BY sido, sigungu, emd
            HAVING COUNT(*) > 1
        )
    """)
    duplicates = cursor.fetchone()[0]
    print(f"Duplicate entries: {duplicates} {'✓' if duplicates == 0 else '✗'}")

    # Check for invalid coordinates
    cursor.execute("SELECT COUNT(*) FROM regions WHERE lat = 0.0 AND lon = 0.0")
    invalid_coords = cursor.fetchone()[0]
    print(f"Invalid coordinates: {invalid_coords} {'✓' if invalid_coords == 0 else '✗'}")

    success = (seq_codes == 0 and double_spaces == 0 and duplicates == 0 and invalid_coords == 0)
    print(f"\nCLEANUP STATUS: {'SUCCESS' if success else 'FAILED'}")

    return success


def main():
    """Main cleanup process."""
    print("=== DATABASE CLEANUP ===\n")

    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        sys.exit(1)

    # Connect to database
    conn = sqlite3.connect(DB_PATH)

    try:
        # Run all fixes
        fix_sequential_codes(conn)
        fix_double_spaces(conn)
        fix_duplicates(conn)
        fix_invalid_coordinates(conn)

        # Verify
        success = verify_cleanup(conn)

        return 0 if success else 1

    except Exception as e:
        print(f"Error during cleanup: {e}")
        conn.rollback()
        return 1

    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
