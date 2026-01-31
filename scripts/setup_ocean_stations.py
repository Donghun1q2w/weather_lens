#!/usr/bin/env python3
"""
Setup script for ocean observation stations.

This script:
1. Creates the ocean_stations table
2. Populates it with initial station data
3. Optionally updates regions table with nearest ocean_station_id
"""
import sqlite3
import sys
from pathlib import Path
from math import radians, cos, sin, asin, sqrt

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data.ocean_stations import OCEAN_STATIONS


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


def create_ocean_stations_table(db_path: Path) -> None:
    """Create ocean_stations table."""
    print(f"Creating ocean_stations table in {db_path}...")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Read SQL schema
    sql_path = project_root / "data" / "init_ocean_stations.sql"
    with open(sql_path) as f:
        schema_sql = f.read()

    # Execute schema
    cursor.executescript(schema_sql)
    conn.commit()

    print("  Table created successfully")
    conn.close()


def populate_ocean_stations(db_path: Path) -> None:
    """Populate ocean_stations table with initial data."""
    print(f"Populating ocean_stations table...")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Clear existing data
    cursor.execute("DELETE FROM ocean_stations")

    # Insert station data
    insert_count = 0
    for station in OCEAN_STATIONS:
        cursor.execute("""
            INSERT INTO ocean_stations (
                station_id, station_name, station_type,
                lat, lon,
                provides_tide, provides_wave, provides_temp,
                marine_zone_code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            station["station_id"],
            station["station_name"],
            station["station_type"],
            station["lat"],
            station["lon"],
            station["provides_tide"],
            station["provides_wave"],
            station["provides_temp"],
            station["marine_zone_code"],
        ))
        insert_count += 1

    conn.commit()
    print(f"  Inserted {insert_count} ocean stations")

    # Display summary by type
    cursor.execute("""
        SELECT station_type, COUNT(*)
        FROM ocean_stations
        GROUP BY station_type
    """)
    print("\n  Summary by station type:")
    for station_type, count in cursor.fetchall():
        print(f"    {station_type}: {count} stations")

    # Display summary by marine zone
    cursor.execute("""
        SELECT mz.name, COUNT(os.station_id)
        FROM ocean_stations os
        LEFT JOIN marine_zones mz ON os.marine_zone_code = mz.zone_code
        GROUP BY os.marine_zone_code
        ORDER BY os.marine_zone_code
    """)
    print("\n  Summary by marine zone:")
    for zone_name, count in cursor.fetchall():
        print(f"    {zone_name}: {count} stations")

    conn.close()


def update_regions_with_nearest_station(db_path: Path, max_distance_km: float = 50.0) -> None:
    """
    Update regions table with nearest ocean station ID for coastal regions.

    Args:
        db_path: Path to regions.db
        max_distance_km: Maximum distance to assign station (default 50km)
    """
    print(f"\nUpdating regions with nearest ocean stations (max distance: {max_distance_km}km)...")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all coastal regions
    cursor.execute("""
        SELECT code, name, lat, lon, zone_code
        FROM regions r
        LEFT JOIN region_marine_zone rmz ON r.code = rmz.region_code
        WHERE r.is_coastal = 1
    """)
    coastal_regions = cursor.fetchall()

    print(f"  Processing {len(coastal_regions)} coastal regions...")

    # Get all ocean stations
    cursor.execute("""
        SELECT station_id, lat, lon, marine_zone_code
        FROM ocean_stations
    """)
    stations = cursor.fetchall()

    update_count = 0
    skipped_count = 0

    for region_code, region_name, region_lat, region_lon, region_zone in coastal_regions:
        # Find nearest station, preferring same marine zone
        nearest_station = None
        nearest_distance = float('inf')

        for station_id, station_lat, station_lon, station_zone in stations:
            distance = haversine_distance(region_lat, region_lon, station_lat, station_lon)

            # Prefer stations in same marine zone
            if station_zone == region_zone:
                distance *= 0.5  # Give 50% bonus to same-zone stations

            if distance < nearest_distance and distance <= max_distance_km:
                nearest_distance = distance
                nearest_station = station_id

        if nearest_station:
            cursor.execute("""
                UPDATE regions
                SET ocean_station_id = ?
                WHERE code = ?
            """, (nearest_station, region_code))
            update_count += 1
        else:
            skipped_count += 1

    conn.commit()
    print(f"  Updated {update_count} regions with ocean station IDs")
    print(f"  Skipped {skipped_count} regions (no station within {max_distance_km}km)")

    # Show sample mappings
    cursor.execute("""
        SELECT r.name, os.station_name, os.station_type
        FROM regions r
        JOIN ocean_stations os ON r.ocean_station_id = os.station_id
        WHERE r.is_coastal = 1
        LIMIT 10
    """)
    print("\n  Sample region-station mappings:")
    for region_name, station_name, station_type in cursor.fetchall():
        print(f"    {region_name} → {station_name} ({station_type})")

    conn.close()


def main():
    """Main setup function."""
    db_path = project_root / "data" / "regions.db"

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)

    print("=" * 60)
    print("Ocean Stations Setup")
    print("=" * 60)

    # Step 1: Create table
    create_ocean_stations_table(db_path)

    # Step 2: Populate stations
    populate_ocean_stations(db_path)

    # Step 3: Update regions (optional)
    response = input("\nUpdate regions with nearest ocean stations? (y/n): ")
    if response.lower() == 'y':
        update_regions_with_nearest_station(db_path)

    print("\n" + "=" * 60)
    print("Setup completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
