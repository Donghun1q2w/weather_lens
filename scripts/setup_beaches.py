#!/usr/bin/env python3
"""
Setup script for beaches.

This script:
1. Creates the beaches table
2. Populates it with beach data from data/beaches.py
3. Maps each beach to the nearest 읍면동 region using haversine distance
4. Assigns marine_zone_code based on region location
"""
import sqlite3
import sys
from pathlib import Path
from math import radians, cos, sin, asin, sqrt

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data.beaches import BEACHES


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth.

    Args:
        lat1, lon1: Latitude and longitude of point 1
        lat2, lon2: Latitude and longitude of point 2

    Returns:
        Distance in kilometers
    """
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))

    # Earth radius in kilometers
    r = 6371
    return c * r


def create_beaches_table(db_path: Path) -> None:
    """Create beaches table."""
    print(f"Creating beaches table in {db_path}...")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Read SQL schema
    sql_path = project_root / "data" / "init_beaches.sql"
    with open(sql_path) as f:
        schema_sql = f.read()

    # Execute schema
    cursor.executescript(schema_sql)
    conn.commit()

    print("  Table created successfully")
    conn.close()


def populate_beaches(db_path: Path) -> None:
    """Populate beaches table with beach data."""
    print(f"Populating beaches table...")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Clear existing data
    cursor.execute("DELETE FROM beaches")

    # Insert beach data
    insert_count = 0
    for beach in BEACHES:
        cursor.execute("""
            INSERT INTO beaches (
                beach_num, name, nx, ny, lon, lat
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            beach["beach_num"],
            beach["name"],
            beach["nx"],
            beach["ny"],
            beach["lon"],
            beach["lat"],
        ))
        insert_count += 1

    conn.commit()
    print(f"  Inserted {insert_count} beaches")

    # Display summary statistics
    cursor.execute("SELECT COUNT(*) FROM beaches")
    total_beaches = cursor.fetchone()[0]

    cursor.execute("SELECT MIN(lat), MAX(lat), MIN(lon), MAX(lon) FROM beaches")
    min_lat, max_lat, min_lon, max_lon = cursor.fetchone()

    print(f"\n  Summary:")
    print(f"    Total beaches: {total_beaches}")
    print(f"    Latitude range: {min_lat:.4f} to {max_lat:.4f}")
    print(f"    Longitude range: {min_lon:.4f} to {max_lon:.4f}")

    conn.close()


def map_beaches_to_regions(db_path: Path, max_distance_km: float = 30.0) -> None:
    """
    Map each beach to the nearest 읍면동 region using haversine distance.

    Args:
        db_path: Path to regions.db
        max_distance_km: Maximum distance to assign region (default 30km)
    """
    print(f"\nMapping beaches to regions (max distance: {max_distance_km}km)...")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all beaches
    cursor.execute("""
        SELECT beach_num, name, lat, lon
        FROM beaches
    """)
    beaches = cursor.fetchall()

    print(f"  Processing {len(beaches)} beaches...")

    # Get all regions with preference for coastal regions
    cursor.execute("""
        SELECT code, name, lat, lon, is_coastal
        FROM regions
        WHERE lat IS NOT NULL AND lon IS NOT NULL
    """)
    regions = cursor.fetchall()

    print(f"  Comparing against {len(regions)} regions...")

    update_count = 0
    skipped_count = 0
    coastal_match_count = 0

    for beach_num, beach_name, beach_lat, beach_lon in beaches:
        # Find nearest region, preferring coastal regions
        nearest_region = None
        nearest_distance = float('inf')

        for region_code, region_name, region_lat, region_lon, is_coastal in regions:
            distance = haversine_distance(beach_lat, beach_lon, region_lat, region_lon)

            # Prefer coastal regions (give 50% bonus)
            if is_coastal:
                distance *= 0.5

            if distance < nearest_distance:
                nearest_distance = distance
                nearest_region = (region_code, is_coastal)

        # Restore actual distance if coastal bonus was applied
        actual_distance = nearest_distance
        if nearest_region and nearest_region[1]:  # is_coastal
            actual_distance = nearest_distance * 2

        if nearest_region and actual_distance <= max_distance_km:
            cursor.execute("""
                UPDATE beaches
                SET region_code = ?
                WHERE beach_num = ?
            """, (nearest_region[0], beach_num))
            update_count += 1
            if nearest_region[1]:  # is_coastal
                coastal_match_count += 1
        else:
            skipped_count += 1

    conn.commit()
    print(f"  Updated {update_count} beaches with region codes")
    print(f"  Matched to coastal regions: {coastal_match_count}")
    print(f"  Skipped {skipped_count} beaches (no region within {max_distance_km}km)")

    # Show sample mappings
    cursor.execute("""
        SELECT b.name, r.name, r.is_coastal
        FROM beaches b
        JOIN regions r ON b.region_code = r.code
        LIMIT 10
    """)
    print("\n  Sample beach-region mappings:")
    for beach_name, region_name, is_coastal in cursor.fetchall():
        coastal_marker = " (coastal)" if is_coastal else ""
        print(f"    {beach_name} → {region_name}{coastal_marker}")

    conn.close()


def assign_marine_zones(db_path: Path) -> None:
    """
    Assign marine_zone_code to beaches based on their region's marine zone.
    """
    print(f"\nAssigning marine zones to beaches...")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Update beaches with marine zone from their region
    cursor.execute("""
        UPDATE beaches
        SET marine_zone_code = (
            SELECT rmz.zone_code
            FROM region_marine_zone rmz
            WHERE rmz.region_code = beaches.region_code
        )
        WHERE region_code IS NOT NULL
    """)

    update_count = cursor.rowcount
    conn.commit()

    print(f"  Updated {update_count} beaches with marine zone codes")

    # Display summary by marine zone
    cursor.execute("""
        SELECT mz.name, mz.zone_code, COUNT(b.beach_num) as beach_count
        FROM beaches b
        LEFT JOIN marine_zones mz ON b.marine_zone_code = mz.zone_code
        WHERE b.marine_zone_code IS NOT NULL
        GROUP BY b.marine_zone_code, mz.name
        ORDER BY beach_count DESC
    """)
    print("\n  Summary by marine zone:")
    for zone_name, zone_code, count in cursor.fetchall():
        print(f"    {zone_name} ({zone_code}): {count} beaches")

    conn.close()


def main():
    """Main setup function."""
    db_path = project_root / "data" / "regions.db"

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)

    print("=" * 60)
    print("Beach Setup")
    print("=" * 60)

    # Step 1: Create table
    create_beaches_table(db_path)

    # Step 2: Populate beaches
    populate_beaches(db_path)

    # Step 3: Map beaches to regions
    map_beaches_to_regions(db_path)

    # Step 4: Assign marine zones
    assign_marine_zones(db_path)

    # Final summary
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM beaches")
    total_beaches = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM beaches WHERE region_code IS NOT NULL")
    mapped_beaches = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM beaches WHERE marine_zone_code IS NOT NULL")
    zoned_beaches = cursor.fetchone()[0]

    print("\n" + "=" * 60)
    print("Setup Summary")
    print("=" * 60)
    print(f"  Total beaches: {total_beaches}")
    print(f"  Mapped to regions: {mapped_beaches}")
    print(f"  Assigned marine zones: {zoned_beaches}")

    # Show final sample mappings with all data
    cursor.execute("""
        SELECT b.name, r.name, mz.name
        FROM beaches b
        LEFT JOIN regions r ON b.region_code = r.code
        LEFT JOIN marine_zones mz ON b.marine_zone_code = mz.zone_code
        WHERE b.region_code IS NOT NULL
        LIMIT 5
    """)
    print("\n  Sample complete mappings:")
    for beach_name, region_name, zone_name in cursor.fetchall():
        print(f"    {beach_name}")
        print(f"      → Region: {region_name}")
        print(f"      → Marine zone: {zone_name}")

    conn.close()

    print("\n" + "=" * 60)
    print("Setup completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
