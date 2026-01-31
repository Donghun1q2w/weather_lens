#!/usr/bin/env python3
"""
ULTRAPILOT Integration Script
Merge worker outputs, clean data, fetch elevations, and update database.
"""

import json
import math
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Tuple, Set
import requests
from collections import defaultdict

# Constants
BASE_DIR = Path("/Users/donghun/Documents/git_repository/weather_lens")
OMC_DIR = BASE_DIR / ".omc"
DB_PATH = BASE_DIR / "data" / "regions.db"
DOCS_DIR = BASE_DIR / "docs"

# Worker JSON files
WORKER_FILES = [
    OMC_DIR / "w1_seoul_gyeonggi.json",
    OMC_DIR / "w2_gyeongsang.json",
    OMC_DIR / "w3_chungcheong_gangwon.json",
    OMC_DIR / "w4_jeolla.json",
    OMC_DIR / "w5_incheon_jeju.json",
]

# Sido name normalization mapping
SIDO_NORMALIZATION = {
    "서울": "서울특별시",
    "부산": "부산광역시",
    "대구": "대구광역시",
    "인천": "인천광역시",
    "광주": "광주광역시",
    "대전": "대전광역시",
    "울산": "울산광역시",
    "세종": "세종특별자치시",
    "경기": "경기도",
    "강원": "강원특별자치도",
    "충북": "충청북도",
    "충남": "충청남도",
    "전북": "전북특별자치도",
    "전남": "전라남도",
    "경북": "경상북도",
    "경남": "경상남도",
    "제주": "제주특별자치도",
}

# EMD suffixes to remove
EMD_SUFFIXES = ["주민센터", "읍사무소", "면사무소", "행정복지센터", "(임시청사)"]

# East coast sigungu
EAST_COAST_SIGUNGU = {
    "강릉시", "동해시", "삼척시", "속초시", "양양군", "고성군", "울진군", "영덕군",
    "포항시남구", "포항시북구", "경주시", "울산중구", "울산동구", "울산북구", "울주군",
    "해운대구", "기장군"
}

# West coast sigungu
WEST_COAST_SIGUNGU = {
    "인천중구", "옹진군", "강화군", "태안군", "서산시", "당진시", "아산시", "보령시",
    "서천군", "군산시", "부안군", "김제시", "고창군", "영광군", "함평군", "무안군",
    "신안군", "목포시", "영암군", "해남군", "진도군", "완도군", "강진군", "장흥군",
    "보성군", "고흥군", "여수시"
}

# Sigungu codes from existing database
SIGUNGU_CODES = {
    ("서울특별시", "종로구"): "11110",
    ("서울특별시", "중구"): "11140",
    ("서울특별시", "용산구"): "11170",
    ("서울특별시", "성동구"): "11200",
    ("서울특별시", "광진구"): "11215",
    ("서울특별시", "동대문구"): "11230",
    ("서울특별시", "중랑구"): "11260",
    ("서울특별시", "성북구"): "11290",
    ("서울특별시", "강북구"): "11305",
    ("서울특별시", "도봉구"): "11320",
    ("서울특별시", "노원구"): "11350",
    ("서울특별시", "은평구"): "11380",
    ("서울특별시", "서대문구"): "11410",
    ("서울특별시", "마포구"): "11440",
    ("서울특별시", "양천구"): "11470",
    ("서울특별시", "강서구"): "11500",
    ("서울특별시", "구로구"): "11530",
    ("서울특별시", "금천구"): "11545",
    ("서울특별시", "영등포구"): "11560",
    ("서울특별시", "동작구"): "11590",
    ("서울특별시", "관악구"): "11620",
    ("서울특별시", "서초구"): "11650",
    ("서울특별시", "강남구"): "11680",
    ("서울특별시", "송파구"): "11710",
    ("서울특별시", "강동구"): "11740",
    ("부산광역시", "중구"): "26110",
    ("부산광역시", "서구"): "26140",
    ("부산광역시", "동구"): "26170",
    ("부산광역시", "영도구"): "26200",
    ("부산광역시", "부산진구"): "26230",
    ("부산광역시", "동래구"): "26260",
    ("부산광역시", "남구"): "26290",
    ("부산광역시", "북구"): "26320",
    ("부산광역시", "해운대구"): "26350",
    ("부산광역시", "사하구"): "26380",
    ("부산광역시", "금정구"): "26410",
    ("부산광역시", "강서구"): "26440",
    ("부산광역시", "연제구"): "26470",
    ("부산광역시", "수영구"): "26500",
    ("부산광역시", "사상구"): "26530",
    ("부산광역시", "기장군"): "26710",
    ("대구광역시", "중구"): "27110",
    ("대구광역시", "동구"): "27140",
    ("대구광역시", "서구"): "27170",
    ("대구광역시", "남구"): "27200",
    ("대구광역시", "북구"): "27230",
    ("대구광역시", "수성구"): "27260",
    ("대구광역시", "달서구"): "27290",
    ("대구광역시", "달성군"): "27710",
    ("인천광역시", "중구"): "28110",
    ("인천광역시", "동구"): "28140",
    ("인천광역시", "연수구"): "28177",
    ("인천광역시", "남동구"): "28185",
    ("인천광역시", "부평구"): "28200",
    ("인천광역시", "계양구"): "28237",
    ("인천광역시", "서구"): "28245",
    ("인천광역시", "미추홀구"): "28260",
    ("인천광역시", "강화군"): "28710",
    ("인천광역시", "옹진군"): "28720",
    ("광주광역시", "동구"): "29110",
    ("광주광역시", "서구"): "29140",
    ("광주광역시", "남구"): "29155",
    ("광주광역시", "북구"): "29170",
    ("광주광역시", "광산구"): "29200",
    ("대전광역시", "동구"): "30110",
    ("대전광역시", "중구"): "30140",
    ("대전광역시", "서구"): "30170",
    ("대전광역시", "유성구"): "30200",
    ("대전광역시", "대덕구"): "30230",
    ("울산광역시", "중구"): "31110",
    ("울산광역시", "남구"): "31140",
    ("울산광역시", "동구"): "31170",
    ("울산광역시", "북구"): "31200",
    ("울산광역시", "울주군"): "31710",
    ("세종특별자치시", "세종시"): "36110",
    ("경기도", "수원시장안구"): "41111",
    ("경기도", "수원시권선구"): "41113",
    ("경기도", "수원시팔달구"): "41115",
    ("경기도", "수원시영통구"): "41117",
    ("경기도", "성남시수정구"): "41131",
    ("경기도", "성남시중원구"): "41133",
    ("경기도", "성남시분당구"): "41135",
    ("경기도", "의정부시"): "41150",
    ("경기도", "안양시만안구"): "41170",
    ("경기도", "안양시동안구"): "41173",
    ("경기도", "부천시"): "41190",
    ("경기도", "광명시"): "41210",
    ("경기도", "평택시"): "41220",
    ("경기도", "동두천시"): "41250",
    ("경기도", "안산시상록구"): "41270",
    ("경기도", "안산시단원구"): "41273",
    ("경기도", "고양시덕양구"): "41280",
    ("경기도", "고양시일산동구"): "41283",
    ("경기도", "고양시일산서구"): "41285",
    ("경기도", "과천시"): "41290",
    ("경기도", "구리시"): "41310",
    ("경기도", "남양주시"): "41360",
    ("경기도", "오산시"): "41370",
    ("경기도", "시흥시"): "41390",
    ("경기도", "군포시"): "41410",
    ("경기도", "의왕시"): "41430",
    ("경기도", "하남시"): "41450",
    ("경기도", "용인시처인구"): "41460",
    ("경기도", "용인시기흥구"): "41463",
    ("경기도", "용인시수지구"): "41465",
    ("경기도", "파주시"): "41480",
    ("경기도", "이천시"): "41500",
    ("경기도", "안성시"): "41550",
    ("경기도", "김포시"): "41570",
    ("경기도", "화성시"): "41590",
    ("경기도", "광주시"): "41610",
    ("경기도", "양주시"): "41630",
    ("경기도", "포천시"): "41650",
    ("경기도", "여주시"): "41670",
    ("경기도", "연천군"): "41800",
    ("경기도", "가평군"): "41820",
    ("경기도", "양평군"): "41830",
    ("강원특별자치도", "춘천시"): "42110",
    ("강원특별자치도", "원주시"): "42130",
    ("강원특별자치도", "강릉시"): "42150",
    ("강원특별자치도", "동해시"): "42170",
    ("강원특별자치도", "태백시"): "42190",
    ("강원특별자치도", "속초시"): "42210",
    ("강원특별자치도", "삼척시"): "42230",
    ("강원특별자치도", "홍천군"): "42720",
    ("강원특별자치도", "횡성군"): "42730",
    ("강원특별자치도", "영월군"): "42750",
    ("강원특별자치도", "평창군"): "42760",
    ("강원특별자치도", "정선군"): "42770",
    ("강원특별자치도", "철원군"): "42780",
    ("강원특별자치도", "화천군"): "42790",
    ("강원특별자치도", "양구군"): "42800",
    ("강원특별자치도", "인제군"): "42810",
    ("강원특별자치도", "고성군"): "42820",
    ("강원특별자치도", "양양군"): "42830",
    ("충청북도", "청주시상당구"): "43110",
    ("충청북도", "청주시서원구"): "43112",
    ("충청북도", "청주시흥덕구"): "43113",
    ("충청북도", "청주시청원구"): "43114",
    ("충청북도", "충주시"): "43130",
    ("충청북도", "제천시"): "43150",
    ("충청북도", "보은군"): "43720",
    ("충청북도", "옥천군"): "43730",
    ("충청북도", "영동군"): "43740",
    ("충청북도", "증평군"): "43745",
    ("충청북도", "진천군"): "43750",
    ("충청북도", "괴산군"): "43760",
    ("충청북도", "음성군"): "43770",
    ("충청북도", "단양군"): "43800",
    ("충청남도", "천안시동남구"): "44130",
    ("충청남도", "천안시서북구"): "44133",
    ("충청남도", "공주시"): "44150",
    ("충청남도", "보령시"): "44180",
    ("충청남도", "아산시"): "44200",
    ("충청남도", "서산시"): "44210",
    ("충청남도", "논산시"): "44230",
    ("충청남도", "계룡시"): "44250",
    ("충청남도", "당진시"): "44270",
    ("충청남도", "금산군"): "44710",
    ("충청남도", "부여군"): "44760",
    ("충청남도", "서천군"): "44770",
    ("충청남도", "청양군"): "44790",
    ("충청남도", "홍성군"): "44800",
    ("충청남도", "예산군"): "44810",
    ("충청남도", "태안군"): "44825",
    ("전북특별자치도", "전주시완산구"): "45111",
    ("전북특별자치도", "전주시덕진구"): "45113",
    ("전북특별자치도", "군산시"): "45130",
    ("전북특별자치도", "익산시"): "45140",
    ("전북특별자치도", "정읍시"): "45180",
    ("전북특별자치도", "남원시"): "45190",
    ("전북특별자치도", "김제시"): "45210",
    ("전북특별자치도", "완주군"): "45710",
    ("전북특별자치도", "진안군"): "45720",
    ("전북특별자치도", "무주군"): "45730",
    ("전북특별자치도", "장수군"): "45740",
    ("전북특별자치도", "임실군"): "45750",
    ("전북특별자치도", "순창군"): "45770",
    ("전북특별자치도", "고창군"): "45790",
    ("전북특별자치도", "부안군"): "45800",
    ("전라남도", "목포시"): "46110",
    ("전라남도", "여수시"): "46130",
    ("전라남도", "순천시"): "46150",
    ("전라남도", "나주시"): "46170",
    ("전라남도", "광양시"): "46230",
    ("전라남도", "담양군"): "46710",
    ("전라남도", "곡성군"): "46720",
    ("전라남도", "구례군"): "46730",
    ("전라남도", "고흥군"): "46770",
    ("전라남도", "보성군"): "46780",
    ("전라남도", "화순군"): "46790",
    ("전라남도", "장흥군"): "46800",
    ("전라남도", "강진군"): "46810",
    ("전라남도", "해남군"): "46820",
    ("전라남도", "영암군"): "46830",
    ("전라남도", "무안군"): "46840",
    ("전라남도", "함평군"): "46860",
    ("전라남도", "영광군"): "46870",
    ("전라남도", "장성군"): "46880",
    ("전라남도", "완도군"): "46890",
    ("전라남도", "진도군"): "46900",
    ("전라남도", "신안군"): "46910",
    ("경상북도", "포항시남구"): "47111",
    ("경상북도", "포항시북구"): "47113",
    ("경상북도", "경주시"): "47130",
    ("경상북도", "김천시"): "47150",
    ("경상북도", "안동시"): "47170",
    ("경상북도", "구미시"): "47190",
    ("경상북도", "영주시"): "47210",
    ("경상북도", "영천시"): "47230",
    ("경상북도", "상주시"): "47250",
    ("경상북도", "문경시"): "47280",
    ("경상북도", "경산시"): "47290",
    ("경상북도", "군위군"): "47720",
    ("경상북도", "의성군"): "47730",
    ("경상북도", "청송군"): "47750",
    ("경상북도", "영양군"): "47760",
    ("경상북도", "영덕군"): "47770",
    ("경상북도", "청도군"): "47820",
    ("경상북도", "고령군"): "47830",
    ("경상북도", "성주군"): "47840",
    ("경상북도", "칠곡군"): "47850",
    ("경상북도", "예천군"): "47900",
    ("경상북도", "봉화군"): "47920",
    ("경상북도", "울진군"): "47930",
    ("경상북도", "울릉군"): "47940",
    ("경상남도", "창원시의창구"): "48121",
    ("경상남도", "창원시성산구"): "48123",
    ("경상남도", "창원시마산합포구"): "48125",
    ("경상남도", "창원시마산회원구"): "48127",
    ("경상남도", "창원시진해구"): "48129",
    ("경상남도", "진주시"): "48170",
    ("경상남도", "통영시"): "48220",
    ("경상남도", "사천시"): "48240",
    ("경상남도", "김해시"): "48250",
    ("경상남도", "밀양시"): "48270",
    ("경상남도", "거제시"): "48310",
    ("경상남도", "양산시"): "48330",
    ("경상남도", "창녕군"): "48370",
    ("경상남도", "의령군"): "48720",
    ("경상남도", "함안군"): "48730",
    ("경상남도", "고성군"): "48820",
    ("경상남도", "남해군"): "48840",
    ("경상남도", "하동군"): "48850",
    ("경상남도", "산청군"): "48860",
    ("경상남도", "함양군"): "48870",
    ("경상남도", "거창군"): "48880",
    ("경상남도", "합천군"): "48890",
    ("제주특별자치도", "제주시"): "50110",
    ("제주특별자치도", "서귀포시"): "50130",
}


def latlon_to_grid(lat: float, lon: float) -> Tuple[int, int]:
    """위경도를 기상청 격자 좌표로 변환 (Lambert Conformal Conic)"""
    RE, GRID = 6371.00877, 5.0
    SLAT1, SLAT2 = 30.0, 60.0
    OLON, OLAT = 126.0, 38.0
    XO, YO = 43, 136
    DEGRAD = math.pi / 180.0

    re = RE / GRID
    slat1, slat2 = SLAT1 * DEGRAD, SLAT2 * DEGRAD
    olon, olat = OLON * DEGRAD, OLAT * DEGRAD

    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(
        math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
    )
    sf = math.pow(math.tan(math.pi * 0.25 + slat1 * 0.5), sn) * math.cos(slat1) / sn
    ro = re * sf / math.pow(math.tan(math.pi * 0.25 + olat * 0.5), sn)
    ra = re * sf / math.pow(math.tan(math.pi * 0.25 + lat * DEGRAD * 0.5), sn)

    theta = lon * DEGRAD - olon
    if theta > math.pi:
        theta -= 2.0 * math.pi
    if theta < -math.pi:
        theta += 2.0 * math.pi
    theta *= sn

    return int(ra * math.sin(theta) + XO + 0.5), int(ro - ra * math.cos(theta) + YO + 0.5)


def clean_emd(emd: str) -> str:
    """Remove suffixes from emd name"""
    for suffix in EMD_SUFFIXES:
        emd = emd.replace(suffix, "")
    return emd.strip()


def normalize_sido(sido: str) -> str:
    """Normalize sido name"""
    sido = sido.strip()
    return SIDO_NORMALIZATION.get(sido, sido)


def get_sigungu_code(sido: str, sigungu: str) -> str:
    """Get sigungu code from mapping"""
    key = (sido, sigungu)
    if key in SIGUNGU_CODES:
        return SIGUNGU_CODES[key]
    print(f"WARNING: No sigungu code for ({sido}, {sigungu})")
    return "00000"


def is_coastal_region(sigungu: str) -> Tuple[bool, bool, bool]:
    """Determine if region is coastal, east coast, or west coast"""
    is_east = sigungu in EAST_COAST_SIGUNGU
    is_west = sigungu in WEST_COAST_SIGUNGU
    is_coastal = is_east or is_west
    return is_coastal, is_east, is_west


def fetch_elevations_batch(coords: List[Tuple[float, float]], batch_size: int = 100) -> List[float]:
    """Fetch elevations from Open-Meteo API in batches"""
    elevations = []
    total = len(coords)

    for i in range(0, total, batch_size):
        batch = coords[i:i + batch_size]
        lats = ",".join(str(lat) for lat, _ in batch)
        lons = ",".join(str(lon) for _, lon in batch)

        url = f"https://api.open-meteo.com/v1/elevation?latitude={lats}&longitude={lons}"

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                data = response.json()

                if "elevation" in data:
                    elevations.extend(data["elevation"])
                    print(f"Fetched elevations for batch {i // batch_size + 1}/{(total + batch_size - 1) // batch_size}")
                    break
                else:
                    print(f"WARNING: No elevation data in response for batch {i // batch_size + 1}")
                    elevations.extend([0.0] * len(batch))
                    break

            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"Retry {attempt + 1}/{max_retries} for batch {i // batch_size + 1}: {e}")
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    print(f"ERROR fetching batch {i // batch_size + 1}: {e}")
                    elevations.extend([0.0] * len(batch))

        # Rate limiting
        time.sleep(0.5)

    return elevations


def main():
    print("=" * 80)
    print("ULTRAPILOT INTEGRATION PHASE")
    print("=" * 80)

    # Step 1: Merge all worker JSON files
    print("\n[1/8] Merging worker outputs...")
    all_data = []
    for worker_file in WORKER_FILES:
        with open(worker_file, "r", encoding="utf-8") as f:
            worker_data = json.load(f)
            all_data.extend(worker_data["data"])
            print(f"  - {worker_file.name}: {len(worker_data['data'])} regions")

    print(f"\nTotal merged: {len(all_data)} regions")

    # Step 2: Clean up data
    print("\n[2/8] Cleaning and normalizing data...")
    cleaned_data = []
    for region in all_data:
        sido = normalize_sido(region["sido"])
        sigungu = region["sigungu"].strip()
        emd = clean_emd(region["emd"]).strip()

        cleaned_data.append({
            "sido": sido,
            "sigungu": sigungu,
            "emd": emd,
            "lat": region["lat"],
            "lon": region["lon"],
            "elevation": region.get("elevation", 0.0),
        })

    print(f"Cleaned {len(cleaned_data)} regions")

    # Step 3: Fetch missing elevations
    print("\n[3/8] Fetching missing elevations...")
    missing_coords = []
    missing_indices = []

    for i, region in enumerate(cleaned_data):
        if region["elevation"] == 0 or region["elevation"] is None:
            missing_coords.append((region["lat"], region["lon"]))
            missing_indices.append(i)

    print(f"Found {len(missing_coords)} regions with missing elevation")

    if missing_coords:
        print("Fetching from Open-Meteo API...")
        new_elevations = fetch_elevations_batch(missing_coords)

        for idx, elevation in zip(missing_indices, new_elevations):
            cleaned_data[idx]["elevation"] = elevation

        print(f"Updated {len(missing_indices)} elevations")

    # Step 4: Generate region codes
    print("\n[4/8] Generating region codes...")
    sigungu_counters = defaultdict(int)
    regions_with_codes = []

    for region in cleaned_data:
        sido = region["sido"]
        sigungu = region["sigungu"]

        sigungu_code = get_sigungu_code(sido, sigungu)
        sigungu_counters[sigungu_code] += 1
        emd_seq = sigungu_counters[sigungu_code]

        code = f"{sigungu_code}{emd_seq:05d}"

        regions_with_codes.append({
            **region,
            "code": code,
        })

    print(f"Generated codes for {len(regions_with_codes)} regions")

    # Step 5: Compute KMA grid coordinates
    print("\n[5/8] Computing KMA grid coordinates...")
    for region in regions_with_codes:
        nx, ny = latlon_to_grid(region["lat"], region["lon"])
        region["nx"] = nx
        region["ny"] = ny

    print(f"Computed grid coordinates for {len(regions_with_codes)} regions")

    # Step 6: Determine coastal flags
    print("\n[6/8] Determining coastal/east/west coast flags...")
    for region in regions_with_codes:
        is_coastal, is_east, is_west = is_coastal_region(region["sigungu"])
        region["is_coastal"] = 1 if is_coastal else 0
        region["is_east_coast"] = 1 if is_east else 0
        region["is_west_coast"] = 1 if is_west else 0

    coastal_count = sum(1 for r in regions_with_codes if r["is_coastal"])
    east_count = sum(1 for r in regions_with_codes if r["is_east_coast"])
    west_count = sum(1 for r in regions_with_codes if r["is_west_coast"])
    print(f"Coastal: {coastal_count}, East: {east_count}, West: {west_count}")

    # Step 7: Update SQLite database
    print("\n[7/8] Updating SQLite database...")

    # Backup database
    import shutil
    backup_path = str(DB_PATH) + ".backup"
    shutil.copy2(DB_PATH, backup_path)
    print(f"  - Backed up database to {backup_path}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    inserted = 0
    updated = 0

    for region in regions_with_codes:
        name = f"{region['sido']} {region['sigungu']} {region['emd']}"

        # Check if record exists
        cursor.execute("SELECT code, elevation FROM regions WHERE code = ?", (region["code"],))
        existing = cursor.fetchone()

        if existing:
            # Update elevation if changed
            if existing[1] != region["elevation"]:
                cursor.execute(
                    "UPDATE regions SET elevation = ?, nx = ?, ny = ?, is_coastal = ?, is_east_coast = ?, is_west_coast = ? WHERE code = ?",
                    (region["elevation"], region["nx"], region["ny"], region["is_coastal"], region["is_east_coast"], region["is_west_coast"], region["code"])
                )
                updated += 1
        else:
            # Insert new record
            cursor.execute(
                """INSERT INTO regions (code, name, sido, sigungu, emd, lat, lon, nx, ny, elevation, is_coastal, is_east_coast, is_west_coast)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    region["code"],
                    name,
                    region["sido"],
                    region["sigungu"],
                    region["emd"],
                    region["lat"],
                    region["lon"],
                    region["nx"],
                    region["ny"],
                    region["elevation"],
                    region["is_coastal"],
                    region["is_east_coast"],
                    region["is_west_coast"],
                )
            )
            inserted += 1

    conn.commit()
    conn.close()

    print(f"  - Inserted: {inserted}")
    print(f"  - Updated: {updated}")

    # Step 8: Generate REGIONS_FULL_LIST.md
    print("\n[8/8] Generating REGIONS_FULL_LIST.md...")

    # Sort regions
    sorted_regions = sorted(
        regions_with_codes,
        key=lambda r: (r["sido"], r["sigungu"], r["emd"])
    )

    # Generate markdown
    DOCS_DIR.mkdir(exist_ok=True)
    md_path = DOCS_DIR / "REGIONS_FULL_LIST.md"

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Weather Lens 전체 지역 목록\n\n")
        f.write(f"**총 지역 수: {len(sorted_regions):,}개**\n\n")
        f.write("---\n\n")

        current_sido = None
        current_sigungu = None

        for region in sorted_regions:
            # New sido section
            if region["sido"] != current_sido:
                current_sido = region["sido"]
                current_sigungu = None
                f.write(f"\n## {current_sido}\n\n")

            # New sigungu section
            if region["sigungu"] != current_sigungu:
                current_sigungu = region["sigungu"]
                f.write(f"\n### {current_sigungu}\n\n")
                f.write("| 코드 | 읍면동 | 위도 | 경도 | 격자(nx,ny) | 고도(m) | 해안 | 동해 | 서해 |\n")
                f.write("|------|--------|------|------|-------------|---------|------|------|------|\n")

            # Row
            coastal = "O" if region["is_coastal"] else "-"
            east = "O" if region["is_east_coast"] else "-"
            west = "O" if region["is_west_coast"] else "-"

            f.write(
                f"| {region['code']} | {region['emd']} | {region['lat']:.4f} | {region['lon']:.4f} | "
                f"({region['nx']},{region['ny']}) | {region['elevation']:.0f} | {coastal} | {east} | {west} |\n"
            )

    print(f"  - Generated {md_path}")
    print(f"  - Total regions: {len(sorted_regions):,}")

    # Summary
    print("\n" + "=" * 80)
    print("INTEGRATION COMPLETE")
    print("=" * 80)
    print(f"\nSummary:")
    print(f"  - Total regions processed: {len(sorted_regions):,}")
    print(f"  - Database records inserted: {inserted}")
    print(f"  - Database records updated: {updated}")
    print(f"  - Coastal regions: {coastal_count}")
    print(f"  - East coast regions: {east_count}")
    print(f"  - West coast regions: {west_count}")
    print(f"\nOutputs:")
    print(f"  - Database: {DB_PATH}")
    print(f"  - Database backup: {backup_path}")
    print(f"  - Markdown: {md_path}")
    print("\nINTEGRATION_COMPLETE")


if __name__ == "__main__":
    main()
