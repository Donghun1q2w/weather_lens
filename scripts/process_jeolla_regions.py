#!/usr/bin/env python3
"""
Process Jeolla regions (전남, 전북, 광주) data for Weather Lens
Worker 4 - Jeolla Regions
"""

import json
import csv
import sqlite3
import urllib.request
import urllib.parse
from typing import Dict, List, Tuple
import time

# Paths
CSV_PATH = "/Users/donghun/Documents/git_repository/weather_lens/docs/행정안전부_읍면동 하부행정기관 현황_20240731.csv"
DB_PATH = "/Users/donghun/Documents/git_repository/weather_lens/data/regions.db"
OUTPUT_PATH = "/Users/donghun/Documents/git_repository/weather_lens/.omc/w4_jeolla.json"

# Region mappings
SIDO_MAP = {
    "전남": "전라남도",
    "전북": "전북특별자치도",
    "광주": "광주광역시"
}

TARGET_SIDOS = ["전남", "전북", "광주"]

def load_csv_data() -> List[Dict]:
    """Load and filter CSV data for Jeolla regions"""
    regions = []

    with open(CSV_PATH, 'r', encoding='euc-kr') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header

        for row in reader:
            if len(row) < 4:
                continue

            sido = row[1].strip()
            if sido not in TARGET_SIDOS:
                continue

            sigungu = row[2].strip()
            emd_raw = row[3].strip()

            # Strip suffixes
            suffixes = [
                "행정복지센터", "주민센터", "읍사무소", "면사무소", "동사무소",
                "행정복지", "복지센터"
            ]
            for suffix in suffixes:
                if emd_raw.endswith(suffix):
                    emd_raw = emd_raw[:-len(suffix)]
                    break

            regions.append({
                "row_num": row[0],
                "sido": SIDO_MAP[sido],
                "sigungu": sigungu,
                "emd": emd_raw
            })

    return regions

def load_db_regions() -> Dict[str, Dict]:
    """Load existing regions from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT code, sido, sigungu, emd, lat, lon, elevation
        FROM regions
        WHERE sido IN ('전라남도', '전북특별자치도', '광주광역시')
    """)

    db_regions = {}
    for row in cursor.fetchall():
        code, sido, sigungu, emd, lat, lon, elevation = row
        key = f"{sido}|{sigungu}|{emd}"
        db_regions[key] = {
            "code": code,
            "lat": lat,
            "lon": lon,
            "elevation": elevation
        }

    conn.close()
    return db_regions

def load_sigungu_centers() -> Dict[str, Tuple[float, float, float]]:
    """Load sigungu center coordinates and average elevation"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT sigungu, AVG(lat), AVG(lon), AVG(elevation)
        FROM regions
        WHERE sido IN ('전라남도', '전북특별자치도', '광주광역시')
        GROUP BY sigungu
    """)

    centers = {}
    for row in cursor.fetchall():
        sigungu, avg_lat, avg_lon, avg_elevation = row
        centers[sigungu] = (avg_lat, avg_lon, avg_elevation or 0.0)

    conn.close()
    return centers

def fetch_elevations_batch(coords: List[Tuple[float, float]]) -> List[float]:
    """Fetch elevations from Open-Meteo API in batch"""
    if not coords:
        return []

    # Batch up to 50 at a time (reduced from 100)
    batch_size = 50
    all_elevations = []

    for i in range(0, len(coords), batch_size):
        batch = coords[i:i+batch_size]

        lats = ",".join(str(lat) for lat, lon in batch)
        lons = ",".join(str(lon) for lat, lon in batch)

        url = f"https://api.open-meteo.com/v1/elevation?latitude={lats}&longitude={lons}"

        # Retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(url) as response:
                    data = json.loads(response.read())
                    elevations = data.get("elevation", [])
                    all_elevations.extend(elevations)

                print(f"  Batch {i//batch_size + 1}/{(len(coords)-1)//batch_size + 1} complete")
                break  # Success

            except urllib.error.HTTPError as e:
                if e.code == 429:
                    wait_time = (attempt + 1) * 2  # Exponential backoff
                    print(f"  Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"  HTTP Error {e.code}: {e}")
                    all_elevations.extend([0.0] * len(batch))
                    break

            except Exception as e:
                print(f"  Error fetching elevations: {e}")
                all_elevations.extend([0.0] * len(batch))
                break
        else:
            # All retries failed
            print(f"  Failed after {max_retries} retries, using 0.0")
            all_elevations.extend([0.0] * len(batch))

        # Rate limiting between batches
        time.sleep(1)

    return all_elevations

def process_regions():
    """Main processing function"""
    print("Loading CSV data...")
    csv_regions = load_csv_data()
    print(f"Found {len(csv_regions)} Jeolla regions in CSV")

    print("Loading database regions...")
    db_regions = load_db_regions()
    print(f"Found {len(db_regions)} regions in database")

    print("Loading sigungu centers...")
    sigungu_centers = load_sigungu_centers()

    # Process each region
    enriched_data = []

    for idx, region in enumerate(csv_regions):
        key = f"{region['sido']}|{region['sigungu']}|{region['emd']}"

        if key in db_regions:
            # Use existing data
            db_data = db_regions[key]
            enriched_data.append({
                "sido": region["sido"],
                "sigungu": region["sigungu"],
                "emd": region["emd"],
                "lat": db_data["lat"],
                "lon": db_data["lon"],
                "elevation": db_data["elevation"],
                "source": f"csv_row_{region['row_num']}_db"
            })
        else:
            # Use sigungu center if available
            if region["sigungu"] in sigungu_centers:
                lat, lon, elevation = sigungu_centers[region["sigungu"]]
            else:
                # Default fallback (shouldn't happen)
                lat, lon, elevation = 35.0, 127.0, 0.0

            enriched_data.append({
                "sido": region["sido"],
                "sigungu": region["sigungu"],
                "emd": region["emd"],
                "lat": lat,
                "lon": lon,
                "elevation": elevation,
                "source": f"csv_row_{region['row_num']}_sigungu_avg"
            })

    # Create output JSON
    output = {
        "worker": "w4",
        "regions": ["전남", "전북", "광주"],
        "total_count": len(enriched_data),
        "data": enriched_data,
        "status": "complete"
    }

    print(f"Writing output to {OUTPUT_PATH}...")
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # Count sources
    db_count = sum(1 for r in enriched_data if "_db" in r["source"])
    sigungu_count = sum(1 for r in enriched_data if "_sigungu_avg" in r["source"])

    print(f"✓ Complete! Processed {len(enriched_data)} regions")
    print(f"  - Regions from DB: {db_count}")
    print(f"  - Regions using sigungu avg: {sigungu_count}")

if __name__ == "__main__":
    process_regions()
