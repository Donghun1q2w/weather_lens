#!/usr/bin/env python3
"""
Verification script for ocean stations implementation.

Checks:
1. Python module loads correctly
2. Station data is complete
3. Marine zone coverage is correct
4. Database schema is valid
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def verify_module():
    """Verify ocean_stations module loads and data is correct."""
    print("=" * 60)
    print("Verifying ocean_stations module...")
    print("=" * 60)

    try:
        from data.ocean_stations import (
            OCEAN_STATIONS,
            get_stations_by_zone,
            get_station_by_id,
            get_tide_stations,
            get_wave_stations,
        )
    except ImportError as e:
        print(f"FAIL: Module import failed - {e}")
        return False

    # Check total count
    total = len(OCEAN_STATIONS)
    print(f"\nTotal stations: {total}")

    # Check by type
    tide_count = len(get_tide_stations())
    wave_count = len(get_wave_stations())
    print(f"  Tide stations: {tide_count}")
    print(f"  Wave stations: {wave_count}")

    # Check by marine zone
    print("\nStations by marine zone:")
    zone_counts = {}
    for station in OCEAN_STATIONS:
        zone = station["marine_zone_code"]
        zone_counts[zone] = zone_counts.get(zone, 0) + 1

    for zone in sorted(zone_counts.keys()):
        count = zone_counts[zone]
        print(f"  {zone}: {count} stations")

    # Verify key stations
    print("\nVerifying key stations:")
    test_stations = [
        ("DT_0063", "제주"),
        ("DT_0028", "성산포"),
        ("DT_0001", "인천"),
        ("TW_0069", "제주 외해"),
    ]

    all_ok = True
    for station_id, expected_name in test_stations:
        station = get_station_by_id(station_id)
        if station:
            if station["station_name"] == expected_name:
                print(f"  ✓ {station_id}: {station['station_name']}")
            else:
                print(f"  ✗ {station_id}: Expected '{expected_name}', got '{station['station_name']}'")
                all_ok = False
        else:
            print(f"  ✗ {station_id}: Not found")
            all_ok = False

    # Check data completeness
    print("\nData completeness checks:")
    issues = []

    for station in OCEAN_STATIONS:
        # Check required fields
        if not station.get("station_id"):
            issues.append(f"Missing station_id")
        if not station.get("station_name"):
            issues.append(f"Missing name for {station.get('station_id')}")
        if not station.get("station_type"):
            issues.append(f"Missing type for {station.get('station_id')}")
        if not station.get("marine_zone_code"):
            issues.append(f"Missing marine_zone for {station.get('station_id')}")

        # Check coordinates
        lat = station.get("lat", 0)
        lon = station.get("lon", 0)
        if not (33 <= lat <= 39):  # Korea latitude range
            issues.append(f"Invalid lat {lat} for {station.get('station_id')}")
        if not (124 <= lon <= 132):  # Korea longitude range
            issues.append(f"Invalid lon {lon} for {station.get('station_id')}")

        # Check data provision flags
        provides_data = station.get("provides_tide", 0) + \
                       station.get("provides_wave", 0) + \
                       station.get("provides_temp", 0)
        if provides_data == 0:
            issues.append(f"Station {station.get('station_id')} provides no data")

    if issues:
        print(f"  ✗ Found {len(issues)} issues:")
        for issue in issues[:10]:  # Show first 10
            print(f"    - {issue}")
        all_ok = False
    else:
        print("  ✓ All stations have complete data")

    if all_ok:
        print("\n✓ Module verification PASSED")
    else:
        print("\n✗ Module verification FAILED")

    return all_ok


def verify_sql_schema():
    """Verify SQL schema file."""
    print("\n" + "=" * 60)
    print("Verifying SQL schema...")
    print("=" * 60)

    sql_path = project_root / "data" / "init_ocean_stations.sql"

    if not sql_path.exists():
        print(f"✗ SQL file not found: {sql_path}")
        return False

    with open(sql_path) as f:
        sql_content = f.read()

    # Check for required elements
    checks = [
        ("CREATE TABLE", "Table creation statement"),
        ("ocean_stations", "Table name"),
        ("station_id TEXT PRIMARY KEY", "Primary key"),
        ("marine_zone_code", "Marine zone foreign key"),
        ("INDEX", "Indexes"),
    ]

    all_ok = True
    for pattern, description in checks:
        if pattern in sql_content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ Missing: {description}")
            all_ok = False

    if all_ok:
        print("\n✓ SQL schema verification PASSED")
    else:
        print("\n✗ SQL schema verification FAILED")

    return all_ok


def main():
    """Run all verifications."""
    print("Ocean Stations Implementation Verification\n")

    results = []
    results.append(("Module", verify_module()))
    results.append(("SQL Schema", verify_sql_schema()))

    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{name:20s}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 All verifications passed!")
        return 0
    else:
        print("\n❌ Some verifications failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
