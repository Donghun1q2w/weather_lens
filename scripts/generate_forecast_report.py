#!/usr/bin/env python3
"""
통합 예보 리포트 생성 스크립트

전체 프로세스:
1. 날씨 데이터 수집 (Bulk API)
2. 3시간 간격 필터링 (2일치)
3. 지역-해수욕장 매칭
4. 점수 계산
5. 파일 출력 (JSON)
"""

import argparse
import asyncio
import json
import logging
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

# 프로젝트 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

RESULT_DIR = PROJECT_ROOT / "result"
RESULT_DIR.mkdir(exist_ok=True)

# 데이터베이스 경로
DB_PATH = PROJECT_ROOT / "data" / "regions.db"

# Open-Meteo API
OPENMETEO_URL = "https://api.open-meteo.com/v1/forecast"

# Import collectors
from collectors.beach_info import BeachInfoCollector
from collectors.khoa_ocean import KHOAOceanCollector
from config.settings import BEACH_API_KEY, KMA_API_KEY
from utils.astronomy import get_sunrise_sunset
from utils.ocean_mapping import find_nearest_tide_station, find_nearest_temp_station

# API key fallback: BEACH_API_KEY가 없으면 KMA_API_KEY 사용
BEACH_API_KEY_TO_USE = BEACH_API_KEY or KMA_API_KEY


# ============================================================================
# STEP 1: 날씨 데이터 수집 (Bulk API)
# ============================================================================

def fetch_all_weather_data(regions: List[Dict], batch_size: int = 100) -> Dict[str, Dict]:
    """
    Bulk API를 사용하여 모든 지역의 72시간 날씨 데이터 수집

    Args:
        regions: 지역 목록 (code, lat, lon 포함)
        batch_size: 배치당 좌표 수 (기본 100)

    Returns:
        Dict[region_code, weather_data]: 지역 코드별 날씨 데이터
    """
    print("\n[1/5] 날씨 데이터 수집 중 (Bulk API)...")
    results = {}
    total = len(regions)
    valid_regions = [(r, i) for i, r in enumerate(regions) if r.get("lat") and r.get("lon")]

    print(f"  총 {len(valid_regions)}개 지역, {(len(valid_regions) + batch_size - 1) // batch_size}개 배치")

    max_retries = 5

    for batch_start in range(0, len(valid_regions), batch_size):
        batch = valid_regions[batch_start:batch_start + batch_size]
        batch_num = batch_start // batch_size + 1
        total_batches = (len(valid_regions) + batch_size - 1) // batch_size

        lats = ",".join(str(r["lat"]) for r, _ in batch)
        lons = ",".join(str(r["lon"]) for r, _ in batch)

        for attempt in range(max_retries):
            print(f"\r  배치 {batch_num}/{total_batches} ({len(batch)}개 좌표)...", end="", flush=True)

            try:
                params = {
                    "latitude": lats,
                    "longitude": lons,
                    "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,cloud_cover,wind_speed_10m,visibility",
                    "timezone": "Asia/Seoul",
                    "forecast_days": 3,
                }

                response = requests.get(OPENMETEO_URL, params=params, timeout=60)
                response.raise_for_status()
                data = response.json()

                # 단일/다중 응답 처리
                if isinstance(data, list):
                    responses = data
                else:
                    responses = [data]

                # 각 지역별 결과 처리
                for idx, (region, _) in enumerate(batch):
                    if idx >= len(responses):
                        continue

                    location_data = responses[idx]
                    if "hourly" not in location_data:
                        continue

                    hourly = location_data["hourly"]
                    times = hourly.get("time", [])

                    hourly_data = []
                    for i in range(len(times)):
                        hourly_data.append({
                            "datetime": times[i],
                            "temperature": hourly["temperature_2m"][i] if i < len(hourly["temperature_2m"]) else None,
                            "humidity": hourly["relative_humidity_2m"][i] if i < len(hourly["relative_humidity_2m"]) else None,
                            "rain_probability": hourly["precipitation_probability"][i] if i < len(hourly["precipitation_probability"]) else None,
                            "cloud_cover": hourly["cloud_cover"][i] if i < len(hourly["cloud_cover"]) else None,
                            "wind_speed": hourly["wind_speed_10m"][i] if i < len(hourly["wind_speed_10m"]) else None,
                            "visibility": hourly.get("visibility", [None] * len(times))[i] if "visibility" in hourly else None,
                        })

                    results[region["code"]] = {"hourly": hourly_data}

                time.sleep(3)  # API Rate Limit 방지
                break  # 성공 시 재시도 루프 탈출

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    wait_time = 5 * (2 ** attempt)  # 5, 10, 20, 40, 80초
                    print(f"\n  Rate Limit 초과, {wait_time}초 대기 후 재시도 ({attempt + 1}/{max_retries})...")
                    time.sleep(wait_time)
                else:
                    print(f"\n  배치 {batch_num} 오류: {e}")
                    break  # 429 외 HTTP 오류는 재시도 안함
            except Exception as e:
                print(f"\n  배치 {batch_num} 오류: {e}")
                break  # 일반 오류는 재시도 안함

    print(f"\r  Bulk API 완료: {len(results)}/{len(valid_regions)} 성공              ")
    return results


# ============================================================================
# STEP 2: 3시간 간격 필터링
# ============================================================================

def filter_3hour_intervals(weather_data: Dict[str, Dict], days: int = 2) -> Dict[str, List]:
    """
    72시간 데이터에서 3시간 간격만 필터링 (00, 03, 06, 09, 12, 15, 18, 21시)

    Args:
        weather_data: fetch_all_weather_data 결과
        days: 예보 일수 (기본 2일)

    Returns:
        Dict[region_code, filtered_hourly_data]
    """
    print("\n[2/5] 3시간 간격 필터링 중...")
    filtered = {}

    target_hours = {0, 3, 6, 9, 12, 15, 18, 21}
    max_datetime = datetime.now() + timedelta(days=days)

    for region_code, data in weather_data.items():
        hourly = data.get("hourly", [])
        filtered_hourly = []

        for hour_data in hourly:
            dt_str = hour_data.get("datetime")
            if not dt_str:
                continue

            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))

            # 3시간 간격 체크 및 날짜 제한
            if dt.hour in target_hours and dt <= max_datetime:
                filtered_hourly.append(hour_data)

        filtered[region_code] = filtered_hourly

    print(f"  필터링 완료: {len(filtered)}개 지역")
    return filtered


# ============================================================================
# STEP 3: 지역-해수욕장 매칭 (Placeholder)
# ============================================================================

def get_merged_forecast_data(
    region_data: Dict[str, List],
    regions: List[Dict],
    beach_data: Optional[Dict[str, List]] = None,
    beaches: Optional[List[Dict]] = None,
    beach_marine_data: Optional[Dict[str, Dict]] = None
) -> Dict:
    """
    지역 예보와 해수욕장 예보 매칭

    Args:
        region_data: 지역별 예보 데이터 (Dict[region_code, hourly_data])
        regions: 지역 정보 리스트
        beach_data: 해수욕장별 예보 데이터 (Dict[beach_code, hourly_data], 선택)
        beaches: 해수욕장 정보 리스트 (선택)
        beach_marine_data: 해수욕장별 해양 데이터 (Dict[beach_code, marine_data], 선택)

    Returns:
        병합된 예보 데이터
        {
            region_code: {
                "region": {"name": str, "weather": List[hourly_data]},
                "beaches": [{
                    "beach_num": int,
                    "name": str,
                    "weather": List[hourly_data],
                    "marine": {
                        "wave_height": {...},
                        "sea_temperature": {...},
                        "tide_info": [...],
                        "sun_info": {...}
                    }
                }]
            }
        }
    """
    print("\n[3/5] 지역-해수욕장 매칭 중...")

    # 지역 정보 딕셔너리 생성 (빠른 조회)
    region_info = {r["code"]: r for r in regions}

    # 병합된 데이터 구조 초기화
    merged = {}

    for region_code, hourly_data in region_data.items():
        region = region_info.get(region_code, {})
        merged[region_code] = {
            "region": {
                "name": region.get("name", "알 수 없음"),
                "weather": hourly_data
            },
            "beaches": []
        }

    # 해수욕장 데이터가 있으면 매칭
    if beach_data and beaches:
        print(f"  해수욕장 데이터: {len(beach_data)}개")

        for beach in beaches:
            region_code = beach.get("region_code")
            beach_code = beach.get("code")

            if not region_code or not beach_code:
                continue

            if region_code in merged and beach_code in beach_data:
                beach_entry = {
                    "beach_num": beach["beach_num"],
                    "name": beach["name"],
                    "weather": beach_data[beach_code]
                }

                # 해양 데이터 추가 (있는 경우)
                if beach_marine_data and beach_code in beach_marine_data:
                    beach_entry["marine"] = beach_marine_data[beach_code]

                merged[region_code]["beaches"].append(beach_entry)

        total_beaches = sum(len(data["beaches"]) for data in merged.values())
        beaches_with_marine = sum(1 for data in merged.values() for b in data["beaches"] if b.get("marine"))
        print(f"  매칭된 해수욕장: {total_beaches}개")
        if beach_marine_data:
            print(f"  해양 데이터 포함: {beaches_with_marine}개 해수욕장")

    print(f"  병합 완료: {len(merged)}개 지역")
    return merged


# ============================================================================
# STEP 4: 점수 계산 (Placeholder)
# ============================================================================

def batch_calculate_scores(merged_data: Dict) -> Dict:
    """
    테마별 점수 계산

    Args:
        merged_data: 병합된 예보 데이터 (region + beaches 구조)

    Returns:
        점수가 포함된 데이터
    """
    print("\n[4/5] 테마별 점수 계산 중...")

    scores_data = {}

    for region_code, data in merged_data.items():
        # 지역 날씨에 대한 점수 계산
        region_scores = []
        region_weather = data.get("region", {}).get("weather", [])

        for hour_data in region_weather:
            # 간단한 점수 계산 (예시)
            cloud = hour_data.get("cloud_cover", 50) or 50
            rain_prob = hour_data.get("rain_probability", 50) or 50
            wind = hour_data.get("wind_speed", 5) or 5

            # 테마별 점수 (간단한 알고리즘)
            scores = {
                "sunrise": max(0, 100 - abs(cloud - 45) - rain_prob),
                "sunset": max(0, 100 - abs(cloud - 55) - rain_prob),
                "milky_way": max(0, 100 - cloud * 2 - rain_prob),
                "star_trail": max(0, 100 - cloud * 2 - wind * 5),
            }

            region_scores.append({
                "datetime": hour_data["datetime"],
                "weather": hour_data,
                "scores": scores,
            })

        # 해수욕장별 점수 계산
        beaches_scores = []
        for beach in data.get("beaches", []):
            beach_hourly_scores = []

            for hour_data in beach.get("weather", []):
                cloud = hour_data.get("cloud_cover", 50) or 50
                rain_prob = hour_data.get("rain_probability", 50) or 50
                wind = hour_data.get("wind_speed", 5) or 5

                scores = {
                    "sunrise": max(0, 100 - abs(cloud - 45) - rain_prob),
                    "sunset": max(0, 100 - abs(cloud - 55) - rain_prob),
                    "milky_way": max(0, 100 - cloud * 2 - rain_prob),
                    "star_trail": max(0, 100 - cloud * 2 - wind * 5),
                }

                beach_hourly_scores.append({
                    "datetime": hour_data["datetime"],
                    "weather": hour_data,
                    "scores": scores,
                })

            beaches_scores.append({
                "beach_num": beach["beach_num"],
                "name": beach["name"],
                "scores": beach_hourly_scores
            })

        scores_data[region_code] = {
            "region": {
                "name": data.get("region", {}).get("name", "알 수 없음"),
                "scores": region_scores
            },
            "beaches": beaches_scores
        }

    total_beaches = sum(len(d["beaches"]) for d in scores_data.values())
    print(f"  점수 계산 완료: {len(scores_data)}개 지역, {total_beaches}개 해수욕장")
    return scores_data


# ============================================================================
# STEP 5: 파일 출력
# ============================================================================

def save_forecast_json(merged_data: Dict, filename: str):
    """통합 예보 데이터를 JSON 파일로 저장"""
    timestamp = datetime.now()
    timestamped_filename = f"forecast_merged_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
    filepath = RESULT_DIR / timestamped_filename

    output = {
        "generated_at": timestamp.isoformat(),
        "forecast_range": {
            "start": timestamp.strftime('%Y-%m-%d'),
            "end": (timestamp + timedelta(days=2)).strftime('%Y-%m-%d'),
        },
        "total_regions": len(merged_data),
        "data": merged_data,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n  저장: {filepath}")
    return filepath


def save_scores_json(scores_data: Dict, filename: str):
    """점수 데이터를 JSON 파일로 저장"""
    timestamp = datetime.now()
    timestamped_filename = f"forecast_scores_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
    filepath = RESULT_DIR / timestamped_filename

    output = {
        "generated_at": timestamp.isoformat(),
        "total_regions": len(scores_data),
        "data": scores_data,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"  저장: {filepath}")
    return filepath


# ============================================================================
# 데이터베이스 로더
# ============================================================================

def load_regions_from_db() -> List[Dict]:
    """데이터베이스에서 지역 목록 로드"""
    print("\n지역 데이터 로드 중...")

    if not DB_PATH.exists():
        print(f"  경고: 데이터베이스를 찾을 수 없습니다: {DB_PATH}")
        return []

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT code, name, sido, sigungu, emd, lat, lon, nx, ny, elevation,
               is_coastal, is_east_coast, is_west_coast
        FROM regions
        ORDER BY sido, sigungu, emd
    """)

    regions = []
    for row in cursor.fetchall():
        regions.append({
            "code": row[0],
            "name": row[1],
            "sido": row[2],
            "sigungu": row[3],
            "emd": row[4],
            "lat": row[5],
            "lon": row[6],
            "nx": row[7],
            "ny": row[8],
            "elevation": row[9] or 0,
            "is_coastal": bool(row[10]),
            "is_east_coast": bool(row[11]),
            "is_west_coast": bool(row[12]),
        })

    conn.close()

    print(f"  로드 완료: {len(regions)}개 지역")
    return regions


def load_beaches_from_db() -> List[Dict]:
    """데이터베이스에서 해수욕장 목록 로드"""
    print("\n해수욕장 데이터 로드 중...")

    if not DB_PATH.exists():
        print(f"  경고: 데이터베이스를 찾을 수 없습니다: {DB_PATH}")
        return []

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT beach_num, name, lat, lon, region_code
        FROM beaches
        WHERE lat IS NOT NULL AND lon IS NOT NULL
    """)

    beaches = []
    for row in cursor.fetchall():
        beaches.append({
            "code": f"beach_{row[0]}",
            "beach_num": row[0],
            "name": row[1],
            "lat": row[2],
            "lon": row[3],
            "region_code": row[4],
        })

    conn.close()

    print(f"  로드 완료: {len(beaches)}개 해수욕장")
    return beaches


# ============================================================================
# Marine Data Collection for Beaches
# ============================================================================

async def fetch_beach_marine_data(
    beaches: List[Dict],
    api_key: str
) -> Dict[str, Dict]:
    """
    BeachInfoCollector를 사용하여 해양 데이터 수집

    수집 항목:
    - wave_height: 파고 (BeachInfo, 연중)
    - sea_temperature: 수온 (BeachInfo, 연중)
    - tide_info: 조석 (공공데이터포털 조석예보 고/저조 API, 연중)
    - sun_info: 일출일몰 (astronomy.py, 연중)

    Args:
        beaches: 해수욕장 목록 (beach_num, lat, lon 포함)
        api_key: Beach/Data.go.kr API 키 (파고/수온/조석 모두 사용)

    Returns:
        Dict[beach_code, marine_data]: 해수욕장 코드별 해양 데이터
    """
    if not api_key:
        print("  경고: BEACH_API_KEY 없음 - 해양 데이터 수집 건너뜀")
        return {}

    print("\n해수욕장 해양 데이터 수집 중...")
    results = {}
    success_count = 0

    now = datetime.now()
    search_time = now
    base_date = now

    # Ocean collector (조석용) - 루프 밖에서 초기화
    ocean_collector = None
    if api_key:  # Use same BEACH_API_KEY for tide data
        try:
            ocean_collector = KHOAOceanCollector(api_key)
            await ocean_collector.__aenter__()
        except Exception as e:
            print(f"  경고: 조석 API 초기화 실패 - {str(e)}")
            ocean_collector = None

    try:
        async with BeachInfoCollector(api_key) as collector:
            total = len(beaches)
            batch_size = 10  # API rate limit 관리

            for batch_start in range(0, total, batch_size):
                batch = beaches[batch_start:batch_start + batch_size]
                batch_num = batch_start // batch_size + 1
                total_batches = (total + batch_size - 1) // batch_size

                print(f"\r  배치 {batch_num}/{total_batches} ({len(batch)}개 해수욕장)...", end="", flush=True)

                # 배치 내 모든 해수욕장 데이터 수집
                for beach in batch:
                    beach_num = str(beach["beach_num"])
                    beach_code = beach["code"]

                    marine_data = {
                        "wave_height": None,
                        "sea_temperature": None,
                        "tide_info": None,
                        "sun_info": None
                    }

                    try:
                        # 파고 수집
                        wave_data = await collector.get_wave_height(beach_num, search_time)
                        if wave_data and wave_data.get("items"):
                            items = wave_data["items"]
                            if items:
                                latest = items[0]
                                marine_data["wave_height"] = {
                                    "height": latest.get("wave_height"),
                                    "datetime": latest.get("datetime")
                                }

                        # 수온 수집
                        temp_data = await collector.get_sea_temperature(beach_num, search_time)
                        if temp_data and temp_data.get("items"):
                            items = temp_data["items"]
                            if items:
                                latest = items[0]
                                marine_data["sea_temperature"] = {
                                    "temperature": latest.get("temperature"),
                                    "datetime": latest.get("datetime")
                                }

                        # 조석 정보 - 공공데이터포털 조석예보(고, 저조) API (연중 가능)
                        if ocean_collector and beach.get("lat") and beach.get("lon"):
                            try:
                                station, distance = find_nearest_tide_station(
                                    beach["lat"], beach["lon"]
                                )
                                if station and distance < 100:  # 100km 이내
                                    tide_result = await ocean_collector.collect_tide(
                                        station["station_id"],
                                        base_date,
                                        num_of_rows=8  # 당일+익일 (하루 4건)
                                    )
                                    if tide_result and tide_result.get("forecasts"):
                                        marine_data["tide_info"] = {
                                            "source": "data.go.kr",
                                            "station": station["station_name"],
                                            "distance_km": round(distance, 1),
                                            "forecasts": tide_result["forecasts"][:4]  # 당일 4개
                                        }
                            except Exception as e:
                                logger.warning(f"Tide API failed for beach {beach_code}: {e}")

                        # 일출일몰 - astronomy.py 사용 (연중 가능)
                        if beach.get("lat") and beach.get("lon"):
                            try:
                                sun_result = get_sunrise_sunset(
                                    base_date,
                                    beach["lat"],
                                    beach["lon"]
                                )
                                if sun_result.get("sunrise") and sun_result.get("sunset"):
                                    marine_data["sun_info"] = {
                                        "source": "astronomy",
                                        "sunrise": sun_result["sunrise"],
                                        "sunset": sun_result["sunset"]
                                    }
                            except Exception:
                                pass  # 계산 실패 시 무시

                        # 어떤 데이터라도 있으면 성공으로 간주
                        if any([
                            marine_data["wave_height"],
                            marine_data["sea_temperature"],
                            marine_data["tide_info"],
                            marine_data["sun_info"]
                        ]):
                            success_count += 1

                        results[beach_code] = marine_data

                    except Exception as e:
                        # 에러 발생 시 해당 해수욕장은 빈 marine_data로 설정
                        results[beach_code] = marine_data

                # 배치 간 delay (API rate limit 관리)
                await asyncio.sleep(1.5)

        print(f"\r  해양 데이터 수집 완료: {success_count}/{total} 성공                    ")
    except Exception as e:
        print(f"\n  오류: 해양 데이터 수집 실패 - {str(e)}")
    finally:
        # Ocean collector 정리
        if ocean_collector:
            try:
                await ocean_collector.__aexit__(None, None, None)
            except Exception:
                pass

    return results


# ============================================================================
# 메인 함수
# ============================================================================

def main(days: int = 2, output_dir: Optional[Path] = None, sample_size: Optional[int] = None):
    """
    통합 예보 리포트 생성 메인 프로세스

    Args:
        days: 예보 일수 (기본 2)
        output_dir: 출력 디렉토리 (기본 result/)
        sample_size: 샘플 크기 (테스트용, None이면 전체)
    """
    print("=" * 80)
    print("통합 예보 리포트 생성 스크립트")
    print("=" * 80)
    print(f"시작 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"예보 일수: {days}일")
    if sample_size:
        print(f"샘플 모드: {sample_size}개 지역")
    print("=" * 80)

    # 출력 디렉토리 설정
    if output_dir:
        global RESULT_DIR
        RESULT_DIR = output_dir
        RESULT_DIR.mkdir(exist_ok=True)

    # 지역 데이터 로드
    regions = load_regions_from_db()

    if not regions:
        print("\n오류: 지역 데이터를 로드할 수 없습니다.")
        return

    # 해수욕장 데이터 로드
    beaches = load_beaches_from_db()

    # 샘플 모드
    if sample_size and sample_size < len(regions):
        import random
        regions = random.sample(regions, sample_size)
        print(f"\n샘플 {sample_size}개 지역 선택됨")

    # 1. 날씨 데이터 수집 (Bulk API)
    weather_data = fetch_all_weather_data(regions, batch_size=100)

    if not weather_data:
        print("\n오류: 날씨 데이터 수집 실패")
        return

    # 해수욕장 날씨 데이터 수집
    beach_weather_data = {}
    if beaches:
        beach_weather_data = fetch_all_weather_data(beaches, batch_size=100)

    # 해수욕장 해양 데이터 수집 (비동기)
    beach_marine_data = {}
    if beaches and BEACH_API_KEY_TO_USE:
        beach_marine_data = asyncio.run(
            fetch_beach_marine_data(beaches, BEACH_API_KEY_TO_USE)
        )

    # 2. 3시간 간격 필터링
    filtered_data = filter_3hour_intervals(weather_data, days=days)
    filtered_beach_data = filter_3hour_intervals(beach_weather_data, days=days) if beach_weather_data else {}

    # 3. 지역-해수욕장 매칭 (해양 데이터 포함)
    merged_data = get_merged_forecast_data(
        filtered_data,
        regions,
        filtered_beach_data if filtered_beach_data else None,
        beaches if beaches else None,
        beach_marine_data if beach_marine_data else None
    )

    # 4. 점수 계산
    scores_data = batch_calculate_scores(merged_data)

    # 5. 파일 출력
    print("\n[5/5] 파일 저장 중...")
    forecast_file = save_forecast_json(merged_data, "forecast_merged.json")
    scores_file = save_scores_json(scores_data, "forecast_scores.json")

    # 완료 메시지
    total_beaches = sum(len(d.get("beaches", [])) for d in merged_data.values())
    beaches_with_marine = sum(1 for d in merged_data.values() for b in d.get("beaches", []) if b.get("marine"))
    print("\n" + "=" * 80)
    print("완료!")
    print("=" * 80)
    print(f"\n출력 파일:")
    print(f"  1. 통합 예보: {forecast_file}")
    print(f"  2. 점수 데이터: {scores_file}")
    print(f"\n처리 지역: {len(merged_data)}개")
    print(f"처리 해수욕장: {total_beaches}개")
    print(f"해양 데이터 포함: {beaches_with_marine}개 해수욕장")
    print(f"완료 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)


# ============================================================================
# CLI 인터페이스
# ============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="통합 예보 리포트 생성 스크립트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 전체 지역, 2일치 예보
  python generate_forecast_report.py

  # 3일치 예보
  python generate_forecast_report.py --days 3

  # 테스트 모드 (10개 지역만)
  python generate_forecast_report.py --sample 10

  # 출력 디렉토리 지정
  python generate_forecast_report.py --output-dir /path/to/output
        """
    )

    parser.add_argument(
        "--days",
        type=int,
        default=2,
        help="예보 일수 (기본 2일)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="출력 디렉토리 (기본 result/)"
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="샘플 크기 (테스트용, 지정하지 않으면 전체 지역)"
    )

    args = parser.parse_args()

    try:
        main(
            days=args.days,
            output_dir=args.output_dir,
            sample_size=args.sample
        )
    except KeyboardInterrupt:
        print("\n\n중단됨")
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
