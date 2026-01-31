"""
날씨 데이터 수집 및 리포트 생성

매일 03:00, 15:00 실행
- 모든 지역의 날씨 데이터 수집 (Open-Meteo)
- 해양 예보 데이터 수집 (KMA 해상예보)
- 테마별 점수 계산
- MD 리포트 파일 생성
"""
import sqlite3
import json
import requests
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import sys
import time

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import SQLITE_DB_PATH, THEME_IDS, KMA_API_KEY, BEACH_API_KEY

# 결과 저장 폴더
RESULT_DIR = PROJECT_ROOT / "result"
RESULT_DIR.mkdir(exist_ok=True)

# Open-Meteo API
OPENMETEO_URL = "https://api.open-meteo.com/v1/forecast"

# KMA 해상예보 API
KMA_MARINE_URL = "https://apihub.kma.go.kr/api/typ02/openApi/VilageFcstMsgService/getWthrMarFcst"

# 해수욕장 예보 API
BEACH_API_URL = "http://apis.data.go.kr/1360000/BeachInfoservice/getVilageFcstBeach"

# 해상예보구역 코드
MARINE_ZONE_CODES = {
    "12A10000": "서해북부",
    "12A20000": "서해중부",
    "12A30000": "서해남부",
    "12B10000": "남해서부",
    "12B20000": "남해동부",
    "12C10000": "동해남부",
    "12C20000": "동해중부",
    "12C30000": "동해북부",
    "12D10000": "제주도"
}

# 시도별 해상구역 매핑 (해안 지역용)
SIDO_TO_MARINE_ZONE = {
    "인천광역시": "12A10000",      # 서해북부
    "경기도": "12A10000",          # 서해북부
    "충청남도": "12A20000",        # 서해중부
    "전북특별자치도": "12A30000",  # 서해남부
    "전라남도": "12A30000",        # 서해남부 (서해안)
    "광주광역시": "12A30000",      # 서해남부
    "부산광역시": "12B20000",      # 남해동부
    "울산광역시": "12C10000",      # 동해남부
    "경상남도": "12B10000",        # 남해서부
    "경상북도": "12C20000",        # 동해중부
    "강원특별자치도": "12C30000",  # 동해북부
    "제주특별자치도": "12D10000",  # 제주도
}

# 동해안/서해안별 해상구역 결정
def get_marine_zone_for_region(region):
    """지역의 해상예보구역 코드 반환"""
    if not region.get("is_coastal"):
        return None

    sido = region.get("sido", "")

    # 동해안
    if region.get("is_east_coast"):
        if "강원" in sido:
            return "12C30000"  # 동해북부
        elif "경상북" in sido:
            return "12C20000"  # 동해중부
        elif "울산" in sido or "부산" in sido:
            return "12C10000"  # 동해남부

    # 서해안
    if region.get("is_west_coast"):
        if "인천" in sido or "경기" in sido:
            return "12A10000"  # 서해북부
        elif "충청남" in sido:
            return "12A20000"  # 서해중부
        elif "전북" in sido or "전라남" in sido:
            return "12A30000"  # 서해남부

    # 남해안 (동/서 구분 없는 경우)
    if "경상남" in sido:
        return "12B10000"  # 남해서부
    if "부산" in sido:
        return "12B20000"  # 남해동부

    # 제주
    if "제주" in sido:
        return "12D10000"

    # 기본값: 시도별 매핑
    return SIDO_TO_MARINE_ZONE.get(sido)


def get_all_regions():
    """모든 지역 정보 조회"""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT code, name, sido, lat, lon, nx, ny,
               is_coastal, is_east_coast, is_west_coast, elevation
        FROM regions
        ORDER BY sido, name
    """)

    regions = []
    for row in cursor.fetchall():
        regions.append({
            "code": row[0],
            "name": row[1],
            "sido": row[2],
            "lat": row[3],
            "lon": row[4],
            "nx": row[5],
            "ny": row[6],
            "is_coastal": bool(row[7]),
            "is_east_coast": bool(row[8]),
            "is_west_coast": bool(row[9]),
            "elevation": row[10] or 0,
        })

    conn.close()
    return regions


def fetch_openmeteo(lat, lon, hourly_mode=False):
    """Open-Meteo에서 날씨 데이터 수집 (단일 위치)

    Args:
        lat: 위도
        lon: 경도
        hourly_mode: True면 72시간 전체 데이터 반환, False면 현재 시간만
    """
    try:
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,cloud_cover,wind_speed_10m",
            "timezone": "Asia/Seoul",
            "forecast_days": 3,
        }

        response = requests.get(OPENMETEO_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "hourly" not in data:
            return None

        hourly = data["hourly"]
        times = hourly.get("time", [])

        if hourly_mode:
            # 72시간 전체 데이터 반환
            hourly_data = []
            for i in range(len(times)):
                hourly_data.append({
                    "datetime": times[i],
                    "temperature": hourly["temperature_2m"][i] if i < len(hourly["temperature_2m"]) else None,
                    "humidity": hourly["relative_humidity_2m"][i] if i < len(hourly["relative_humidity_2m"]) else None,
                    "rain_probability": hourly["precipitation_probability"][i] if i < len(hourly["precipitation_probability"]) else None,
                    "cloud_cover": hourly["cloud_cover"][i] if i < len(hourly["cloud_cover"]) else None,
                    "wind_speed": hourly["wind_speed_10m"][i] if i < len(hourly["wind_speed_10m"]) else None,
                })
            return {"hourly": hourly_data, "current": hourly_data[datetime.now().hour] if hourly_data else None}
        else:
            # 현재 시간 데이터만 반환 (기존 동작)
            now = datetime.now()
            current_hour = now.hour
            idx = current_hour

            return {
                "temperature": hourly["temperature_2m"][idx] if idx < len(hourly["temperature_2m"]) else None,
                "humidity": hourly["relative_humidity_2m"][idx] if idx < len(hourly["relative_humidity_2m"]) else None,
                "rain_probability": hourly["precipitation_probability"][idx] if idx < len(hourly["precipitation_probability"]) else None,
                "cloud_cover": hourly["cloud_cover"][idx] if idx < len(hourly["cloud_cover"]) else None,
                "wind_speed": hourly["wind_speed_10m"][idx] if idx < len(hourly["wind_speed_10m"]) else None,
            }
    except Exception as e:
        return None


def fetch_openmeteo_bulk(regions, hourly_mode=False, batch_size=1000):
    """Open-Meteo Bulk API로 여러 위치의 날씨 데이터 일괄 수집

    Args:
        regions: 지역 목록 (lat, lon 포함)
        hourly_mode: True면 72시간 전체 데이터 반환
        batch_size: 한 번에 요청할 좌표 수 (최대 1000)

    Returns:
        dict: {region_code: weather_data} 형태
    """
    results = {}
    total = len(regions)

    # 유효한 좌표가 있는 지역만 필터링
    valid_regions = [(r, i) for i, r in enumerate(regions) if r.get("lat") and r.get("lon")]

    print(f"\n[Bulk API] 총 {len(valid_regions)}개 지역, {(len(valid_regions) + batch_size - 1) // batch_size}개 배치")

    for batch_start in range(0, len(valid_regions), batch_size):
        batch = valid_regions[batch_start:batch_start + batch_size]
        batch_num = batch_start // batch_size + 1
        total_batches = (len(valid_regions) + batch_size - 1) // batch_size

        print(f"\r  배치 {batch_num}/{total_batches} ({len(batch)}개 좌표)...", end="", flush=True)

        # 좌표를 쉼표로 연결
        lats = ",".join(str(r["lat"]) for r, _ in batch)
        lons = ",".join(str(r["lon"]) for r, _ in batch)

        try:
            params = {
                "latitude": lats,
                "longitude": lons,
                "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,cloud_cover,wind_speed_10m",
                "timezone": "Asia/Seoul",
                "forecast_days": 3,
            }

            response = requests.get(OPENMETEO_URL, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()

            # 응답이 배열인지 확인 (단일 위치면 dict, 여러 위치면 list)
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

                if hourly_mode:
                    hourly_data = []
                    for i in range(len(times)):
                        hourly_data.append({
                            "datetime": times[i],
                            "temperature": hourly["temperature_2m"][i] if i < len(hourly["temperature_2m"]) else None,
                            "humidity": hourly["relative_humidity_2m"][i] if i < len(hourly["relative_humidity_2m"]) else None,
                            "rain_probability": hourly["precipitation_probability"][i] if i < len(hourly["precipitation_probability"]) else None,
                            "cloud_cover": hourly["cloud_cover"][i] if i < len(hourly["cloud_cover"]) else None,
                            "wind_speed": hourly["wind_speed_10m"][i] if i < len(hourly["wind_speed_10m"]) else None,
                        })
                    results[region["code"]] = {
                        "hourly": hourly_data,
                        "current": hourly_data[datetime.now().hour] if hourly_data else None
                    }
                else:
                    current_hour = datetime.now().hour
                    idx_h = current_hour
                    results[region["code"]] = {
                        "temperature": hourly["temperature_2m"][idx_h] if idx_h < len(hourly["temperature_2m"]) else None,
                        "humidity": hourly["relative_humidity_2m"][idx_h] if idx_h < len(hourly["relative_humidity_2m"]) else None,
                        "rain_probability": hourly["precipitation_probability"][idx_h] if idx_h < len(hourly["precipitation_probability"]) else None,
                        "cloud_cover": hourly["cloud_cover"][idx_h] if idx_h < len(hourly["cloud_cover"]) else None,
                        "wind_speed": hourly["wind_speed_10m"][idx_h] if idx_h < len(hourly["wind_speed_10m"]) else None,
                    }

            time.sleep(1)  # API 부하 방지 (배치 간)

        except Exception as e:
            print(f"\n  ⚠️ 배치 {batch_num} 오류: {e}")
            # 실패한 배치는 개별 호출로 폴백
            for region, _ in batch:
                if region["code"] not in results:
                    weather = fetch_openmeteo(region["lat"], region["lon"], hourly_mode)
                    if weather:
                        results[region["code"]] = weather
                    time.sleep(0.1)

    print(f"\r  Bulk API 완료: {len(results)}/{len(valid_regions)} 성공                    ")
    return results


def fetch_marine_forecast(marine_zone_code):
    """KMA 해상예보 수집"""
    if not KMA_API_KEY:
        return None

    try:
        params = {
            "pageNo": 1,
            "numOfRows": 20,
            "dataType": "JSON",
            "regId": marine_zone_code,
            "authKey": KMA_API_KEY
        }

        response = requests.get(KMA_MARINE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        header = data.get("response", {}).get("header", {})
        if header.get("resultCode") != "00":
            return None

        items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        if not items:
            return None

        if isinstance(items, dict):
            items = [items]

        # 파고 등급 → 높이 변환
        wave_mapping = {1: 0.25, 2: 0.75, 3: 1.5, 4: 2.5, 5: 3.5}
        wave_desc = {1: "0~0.5m", 2: "0.5~1m", 3: "1~2m", 4: "2~3m", 5: "3m+"}

        forecasts = []
        base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        for item in items:
            num_ef = item.get("numEf", 0)

            # numEf를 시간으로 변환 (0=오늘밤, 1=내일아침, ...)
            day_offset = num_ef // 2
            if num_ef == 0:
                forecast_dt = base_date + timedelta(hours=21)
            else:
                is_morning = (num_ef % 2) == 1
                forecast_dt = base_date + timedelta(days=day_offset)
                forecast_dt = forecast_dt.replace(hour=6 if is_morning else 15)

            # 파고 파싱
            wav_str = item.get("wav", "")
            wave_height = None
            wave_desc_str = None
            if wav_str:
                try:
                    wav_level = int(wav_str)
                    wave_height = wave_mapping.get(wav_level)
                    wave_desc_str = wave_desc.get(wav_level)
                except ValueError:
                    pass

            # 풍속 파싱
            ws_str = item.get("ws", "")
            wind_speed = None
            if ws_str:
                try:
                    wind_speed = float(ws_str)
                except ValueError:
                    pass

            forecasts.append({
                "datetime": forecast_dt.isoformat(),
                "period_name": ["오늘밤", "내일아침", "내일낮", "내일밤", "모레아침", "모레낮", "모레밤"][min(num_ef, 6)],
                "weather": item.get("wf"),
                "wave_height": wave_height,
                "wave_desc": wave_desc_str,
                "wind_dir": item.get("wd1"),
                "wind_speed": wind_speed,
            })

        return {
            "zone_code": marine_zone_code,
            "zone_name": MARINE_ZONE_CODES.get(marine_zone_code, ""),
            "announce_time": items[0].get("announceTime") if items else None,
            "forecasts": forecasts
        }
    except Exception as e:
        return None


def fetch_beach_forecast(beach_num):
    """해수욕장 날씨 데이터 수집

    Args:
        beach_num: 해수욕장 번호 (1~420)

    Returns:
        해수욕장 날씨 데이터 dict or None
        - temperature: 기온
        - wave_height: 파고 (WAV)
        - wind_speed: 풍속 (WSD)
        - sky_state: 하늘상태 (SKY)
        - rain_probability: 강수확률 (POP)
        - water_temp: 수온 (WTA, 있는 경우)
    """
    if not BEACH_API_KEY:
        return None

    try:
        # base_date, base_time 계산 (최근 발표 시각)
        now = datetime.now()
        base_date = now.strftime("%Y%m%d")

        # 예보 발표 시각: 02, 05, 08, 11, 14, 17, 20, 23시
        base_hours = [2, 5, 8, 11, 14, 17, 20, 23]
        current_hour = now.hour

        # 현재 시각 이전의 가장 최근 발표 시각 찾기
        base_time = None
        for h in reversed(base_hours):
            if current_hour >= h:
                base_time = f"{h:02d}00"
                break

        if not base_time:
            # 당일 발표가 없으면 전날 23시 사용
            yesterday = now - timedelta(days=1)
            base_date = yesterday.strftime("%Y%m%d")
            base_time = "2300"

        params = {
            "serviceKey": BEACH_API_KEY,
            "beach_num": beach_num,
            "base_date": base_date,
            "base_time": base_time,
            "numOfRows": 50,
            "pageNo": 1,
            "dataType": "JSON"
        }

        response = requests.get(BEACH_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        # 응답 헤더 확인
        header = data.get("response", {}).get("header", {})
        if header.get("resultCode") != "00":
            return None

        items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        if not items:
            return None

        if isinstance(items, dict):
            items = [items]

        # 카테고리별로 데이터 추출
        beach_data = {
            "beach_num": beach_num,
            "base_date": base_date,
            "base_time": base_time,
            "temperature": None,
            "wave_height": None,
            "wind_speed": None,
            "sky_state": None,
            "rain_probability": None,
            "water_temp": None,
        }

        # 가장 최근 시간의 데이터 추출 (fcstTime 기준)
        for item in items:
            category = item.get("category", "")
            fcst_value = item.get("fcstValue", "")

            try:
                if category == "TMP":  # 기온
                    beach_data["temperature"] = float(fcst_value)
                elif category == "WAV":  # 파고
                    beach_data["wave_height"] = float(fcst_value)
                elif category == "WSD":  # 풍속
                    beach_data["wind_speed"] = float(fcst_value)
                elif category == "SKY":  # 하늘상태 (1:맑음, 3:구름많음, 4:흐림)
                    beach_data["sky_state"] = int(fcst_value)
                elif category == "POP":  # 강수확률
                    beach_data["rain_probability"] = int(fcst_value)
                elif category == "WTA":  # 수온 (일부 해수욕장만 제공)
                    beach_data["water_temp"] = float(fcst_value)
            except (ValueError, TypeError):
                continue

        # 최소한 하나의 데이터라도 있으면 반환
        if any([beach_data["temperature"], beach_data["wave_height"], beach_data["wind_speed"]]):
            return beach_data

        return None

    except Exception as e:
        return None


def calculate_simple_scores(weather, region, marine=None, beach=None):
    """간단한 테마별 점수 계산

    Args:
        weather: 기상 데이터 (기온, 습도, 구름, 강수확률, 풍속)
        region: 지역 정보 (해안 여부, 고도 등)
        marine: 해양 예보 데이터 (파고, 해상 풍속 등)
        beach: 해수욕장 데이터 (파고, 수온 등)
    """
    if not weather:
        return {}

    scores = {}
    cloud = weather.get("cloud_cover", 50) or 50
    rain = weather.get("rain_probability", 50) or 50
    wind = weather.get("wind_speed", 5) or 5
    temp = weather.get("temperature", 15) or 15
    humidity = weather.get("humidity", 60) or 60

    is_coastal = region.get("is_coastal", False)
    is_east = region.get("is_east_coast", False)
    is_west = region.get("is_west_coast", False)
    elevation = region.get("elevation", 0)

    # 해양 데이터 추출 (해상예보 우선, 없으면 해수욕장 데이터)
    wave_height = None
    marine_wind = None
    water_temp = None

    if marine and marine.get("forecasts"):
        # 가장 가까운 예보 사용
        fc = marine["forecasts"][0]
        wave_height = fc.get("wave_height")  # 파고 (m)
        marine_wind = fc.get("wind_speed")  # 해상 풍속 (m/s)

    # 해수욕장 데이터가 있으면 보완 (더 정확한 파고 데이터)
    if beach:
        if beach.get("wave_height") is not None:
            wave_height = beach["wave_height"]  # 해수욕장 파고 우선 사용
        if beach.get("wind_speed") is not None and not marine_wind:
            marine_wind = beach["wind_speed"]
        if beach.get("water_temp") is not None:
            water_temp = beach["water_temp"]

    # 1. 일출 (동해안 우선, 구름 30~60%, 낮은 강수확률)
    score = 50
    if 30 <= cloud <= 60:
        score += 20
    if rain < 30:
        score += 15
    if is_east:
        score += 15
        # 해상 조건이 좋으면 추가 점수
        if wave_height is not None and wave_height < 1.0:
            score += 5
    scores[1] = {"name": "일출", "score": min(100, score)}

    # 2. 일출 오메가 (동해안 필수, 맑음, 낮은 풍속, 잔잔한 바다)
    score = 30
    if cloud < 30:
        score += 25
    if wind < 3:
        score += 15
    if is_east:
        score += 25
        # 오메가 현상은 잔잔한 바다에서 더 잘 보임
        if wave_height is not None and wave_height < 0.5:
            score += 10
        if marine_wind is not None and marine_wind < 3:
            score += 5
    else:
        score -= 30
    scores[2] = {"name": "일출 오메가", "score": max(0, min(100, score))}

    # 3. 일몰 (서해안 우선, 구름 40~70%)
    score = 50
    if 40 <= cloud <= 70:
        score += 20
    if rain < 30:
        score += 15
    if is_west:
        score += 15
        if wave_height is not None and wave_height < 1.0:
            score += 5
    scores[3] = {"name": "일몰", "score": min(100, score)}

    # 4. 일몰 오메가 (서해안 필수, 잔잔한 바다)
    score = 30
    if cloud < 30:
        score += 25
    if wind < 3:
        score += 15
    if is_west:
        score += 25
        if wave_height is not None and wave_height < 0.5:
            score += 10
        if marine_wind is not None and marine_wind < 3:
            score += 5
    else:
        score -= 30
    scores[4] = {"name": "일몰 오메가", "score": max(0, min(100, score))}

    # 5. 은하수 (낮은 구름, 높은 고도, 비시즌)
    month = datetime.now().month
    score = 30
    if cloud < 20:
        score += 30
    if elevation > 500:
        score += 20
    if month in [5, 6, 7, 8]:
        score += 20
    elif month in [3, 4, 9, 10]:
        score += 10
    else:
        score -= 20
    scores[5] = {"name": "은하수", "score": max(0, min(100, score))}

    # 6. 야광충 (해안, 따뜻한 수온 시기)
    score = 20
    if is_coastal:
        score += 30
    if month in [5, 6, 7, 8, 9]:
        score += 25
    # 수온 데이터가 있으면 우선 사용, 없으면 기온으로 추정
    if water_temp is not None:
        if water_temp > 20:
            score += 20
        elif water_temp > 18:
            score += 15
    elif temp > 18:
        score += 15
    scores[6] = {"name": "야광충", "score": max(0, min(100, score))}

    # 7. 바다 장노출 (파고가 중요!)
    score = 40
    if is_coastal:
        score += 20
        # 해양 데이터가 있으면 파고 기반 점수
        if wave_height is not None:
            if wave_height < 0.5:
                score += 25  # 잔잔한 바다 최적
            elif wave_height < 1.0:
                score += 15
            elif wave_height > 2.0:
                score -= 15  # 너무 거친 바다
        if marine_wind is not None and marine_wind < 5:
            score += 10
    if wind < 5:
        score += 10
    if cloud < 70:
        score += 5
    scores[7] = {"name": "바다 장노출", "score": max(0, min(100, score))}

    # 8. 운해 (높은 습도, 높은 고도, 낮은 풍속)
    score = 30
    if humidity > 85:
        score += 25
    if elevation > 500:
        score += 25
    if wind < 3:
        score += 15
    scores[8] = {"name": "운해", "score": min(100, score)}

    # 9. 별궤적
    score = 40
    if cloud < 30:
        score += 30
    if rain < 20:
        score += 15
    if wind < 5:
        score += 10
    scores[9] = {"name": "별궤적", "score": min(100, score)}

    # 10. 야경
    score = 50
    if cloud < 50:
        score += 20
    if rain < 30:
        score += 15
    if wind < 7:
        score += 10
    scores[10] = {"name": "야경", "score": min(100, score)}

    # 11. 안개
    score = 30
    if humidity > 90:
        score += 35
    if temp < 10:
        score += 15
    if wind < 3:
        score += 15
    scores[11] = {"name": "안개", "score": min(100, score)}

    # 12. 반영 (잔잔한 수면)
    score = 40
    if wind < 2:
        score += 30
    if rain < 20:
        score += 15
    if cloud < 60:
        score += 10
    scores[12] = {"name": "반영", "score": min(100, score)}

    # 13. 골든아워
    score = 50
    if 30 <= cloud <= 70:
        score += 25
    if rain < 30:
        score += 15
    scores[13] = {"name": "골든아워", "score": min(100, score)}

    # 14. 블루아워
    score = 50
    if cloud < 50:
        score += 25
    if rain < 30:
        score += 15
    scores[14] = {"name": "블루아워", "score": min(100, score)}

    # 15. 상고대 (겨울, 습도, 저온)
    score = 20
    if month in [12, 1, 2]:
        score += 25
    if temp < 0:
        score += 25
    if humidity > 80:
        score += 20
    if elevation > 500:
        score += 15
    scores[15] = {"name": "상고대", "score": min(100, score)}

    # 16. 월출
    score = 50
    if cloud < 40:
        score += 25
    if rain < 20:
        score += 15
    if is_east:
        score += 10
    scores[16] = {"name": "월출", "score": min(100, score)}

    return scores


def generate_markdown_report(results, timestamp):
    """마크다운 리포트 생성"""
    report_lines = []

    # hourly 데이터 포함 여부 확인
    has_hourly = any(r.get("hourly") for r in results)

    # 헤더
    report_lines.append(f"# 날씨 수집 리포트")
    report_lines.append(f"")
    report_lines.append(f"**수집 시각**: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"**총 지역 수**: {len(results)}")
    if has_hourly:
        end_date = timestamp + timedelta(days=2)
        report_lines.append(f"**예보 범위**: {timestamp.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')} (72시간)")
    report_lines.append(f"")

    # 요약 통계
    successful = len([r for r in results if r.get("weather")])
    failed = len(results) - successful
    coastal_with_marine = len([r for r in results if r.get("marine")])
    beach_count = len([r for r in results if r.get("beach")])
    report_lines.append(f"## 수집 현황")
    report_lines.append(f"- 기상 데이터 성공: {successful}개 지역")
    report_lines.append(f"- 기상 데이터 실패: {failed}개 지역")
    report_lines.append(f"- 해양 예보 포함: {coastal_with_marine}개 해안 지역")
    report_lines.append(f"- 해수욕장 데이터 포함: {beach_count}개 지역")
    report_lines.append(f"")

    # 해양 예보 섹션
    marine_zones = {}
    for r in results:
        if r.get("marine"):
            zone_code = r["marine"]["zone_code"]
            if zone_code not in marine_zones:
                marine_zones[zone_code] = r["marine"]

    if marine_zones:
        report_lines.append(f"## 해양 예보 (오늘 ~ +2일)")
        report_lines.append(f"")

        for zone_code, marine in sorted(marine_zones.items(), key=lambda x: x[0]):
            zone_name = marine.get("zone_name", zone_code)
            report_lines.append(f"### {zone_name}")
            report_lines.append(f"")
            report_lines.append(f"| 시점 | 날씨 | 파고 | 풍향 | 풍속 |")
            report_lines.append(f"|------|------|------|------|------|")

            for fc in marine.get("forecasts", [])[:7]:  # 최대 7개 (모레밤까지)
                period = fc.get("period_name", "-")
                weather = fc.get("weather", "-") or "-"
                wave = fc.get("wave_desc", "-") or "-"
                wind_dir = fc.get("wind_dir", "-") or "-"
                wind_spd = fc.get("wind_speed")
                wind_spd_str = f"{wind_spd:.1f}m/s" if wind_spd else "-"
                report_lines.append(f"| {period} | {weather} | {wave} | {wind_dir} | {wind_spd_str} |")

            report_lines.append(f"")
        report_lines.append(f"")

    # 해수욕장 날씨 섹션
    beach_regions = [r for r in results if r.get("beach")]
    if beach_regions:
        report_lines.append(f"## 해수욕장 날씨 (상위 20개 지역)")
        report_lines.append(f"")
        report_lines.append(f"| 지역 | 시도 | 기온 | 파고 | 풍속 | 수온 | 강수확률 |")
        report_lines.append(f"|------|------|------|------|------|------|----------|")

        for r in sorted(beach_regions, key=lambda x: x['name'])[:20]:
            beach = r.get("beach", {})
            name = r["name"][:15]
            sido = r["sido"][:8]
            temp = f"{beach.get('temperature'):.1f}°C" if beach.get('temperature') is not None else "-"
            wave = f"{beach.get('wave_height'):.1f}m" if beach.get('wave_height') is not None else "-"
            wind = f"{beach.get('wind_speed'):.1f}m/s" if beach.get('wind_speed') is not None else "-"
            water = f"{beach.get('water_temp'):.1f}°C" if beach.get('water_temp') is not None else "-"
            rain = f"{beach.get('rain_probability')}%" if beach.get('rain_probability') is not None else "-"

            report_lines.append(f"| {name} | {sido} | {temp} | {wave} | {wind} | {water} | {rain} |")

        report_lines.append(f"")

    # 테마별 TOP 10
    report_lines.append(f"## 테마별 TOP 10")
    report_lines.append(f"")

    for theme_id, theme_name in THEME_IDS.items():
        report_lines.append(f"### {theme_id}. {theme_name}")
        report_lines.append(f"")
        report_lines.append(f"| 순위 | 지역 | 시도 | 점수 |")
        report_lines.append(f"|------|------|------|------|")

        # 점수 순으로 정렬
        theme_results = []
        for r in results:
            if r.get("scores") and theme_id in r["scores"]:
                theme_results.append({
                    "name": r["name"],
                    "sido": r["sido"],
                    "score": r["scores"][theme_id]["score"],
                })

        theme_results.sort(key=lambda x: x["score"], reverse=True)

        for i, item in enumerate(theme_results[:10], 1):
            report_lines.append(f"| {i} | {item['name'][:25]} | {item['sido'][:10]} | {item['score']} |")

        report_lines.append(f"")

    # 시간대별 최적 테마 (hourly 모드일 때만)
    if has_hourly:
        report_lines.append(f"## 시간대별 최적 촬영 추천")
        report_lines.append(f"")
        report_lines.append(f"각 테마별로 72시간 내 최적의 촬영 시간대를 보여줍니다.")
        report_lines.append(f"")

        for theme_id, theme_name in THEME_IDS.items():
            report_lines.append(f"### {theme_id}. {theme_name} - 최적 시간대 TOP 5")
            report_lines.append(f"")
            report_lines.append(f"| 순위 | 시간대 | 지역 | 점수 |")
            report_lines.append(f"|------|--------|------|------|")

            # 모든 지역의 모든 시간대에서 최고 점수 찾기
            all_hourly_scores = []
            for r in results:
                if r.get("hourly"):
                    for hour_data in r["hourly"]:
                        if hour_data.get("scores") and theme_id in hour_data["scores"]:
                            all_hourly_scores.append({
                                "datetime": hour_data["datetime"],
                                "name": r["name"],
                                "sido": r["sido"],
                                "score": hour_data["scores"][theme_id]["score"],
                            })

            all_hourly_scores.sort(key=lambda x: x["score"], reverse=True)

            for i, item in enumerate(all_hourly_scores[:5], 1):
                dt = item["datetime"].replace("T", " ")
                report_lines.append(f"| {i} | {dt} | {item['name'][:15]} ({item['sido'][:6]}) | {item['score']} |")

            report_lines.append(f"")

    # 시도별 상세 데이터
    report_lines.append(f"## 시도별 상세 데이터")
    report_lines.append(f"")

    # 시도별로 그룹핑
    sido_groups = {}
    for r in results:
        sido = r.get("sido", "기타")
        if sido not in sido_groups:
            sido_groups[sido] = []
        sido_groups[sido].append(r)

    for sido in sorted(sido_groups.keys()):
        regions_list = sido_groups[sido]
        report_lines.append(f"### {sido} ({len(regions_list)}개 지역)")
        report_lines.append(f"")
        report_lines.append(f"<details>")
        report_lines.append(f"<summary>상세 보기</summary>")
        report_lines.append(f"")
        report_lines.append(f"| 지역명 | 기온 | 습도 | 구름 | 강수확률 | 풍속 | 최고점수 테마 |")
        report_lines.append(f"|--------|------|------|------|----------|------|---------------|")

        for r in sorted(regions_list, key=lambda x: x["name"])[:100]:  # 시도당 최대 100개
            weather = r.get("weather") or {}
            scores = r.get("scores", {})

            temp = weather.get("temperature", "-")
            if temp != "-":
                temp = f"{temp:.1f}"
            humidity = weather.get("humidity", "-")
            cloud = weather.get("cloud_cover", "-")
            rain_prob = weather.get("rain_probability", "-")
            wind = weather.get("wind_speed", "-")
            if wind != "-":
                wind = f"{wind:.1f}"

            # 최고 점수 테마
            best_theme = "-"
            best_score = 0
            for tid, tdata in scores.items():
                if tdata.get("score", 0) > best_score:
                    best_score = tdata["score"]
                    best_theme = f"{tdata['name']}({best_score})"

            name_short = r['name'][:20] if len(r['name']) > 20 else r['name']
            report_lines.append(f"| {name_short} | {temp} | {humidity} | {cloud} | {rain_prob} | {wind} | {best_theme} |")

        report_lines.append(f"")
        report_lines.append(f"</details>")
        report_lines.append(f"")

    return "\n".join(report_lines)


def run_collection(sample_mode=False, sample_size=50, hourly_mode=False):
    """날씨 수집 및 리포트 생성 실행

    Args:
        sample_mode: 샘플 모드 (일부 지역만)
        sample_size: 샘플 크기
        hourly_mode: True면 72시간 전체 데이터 수집
    """
    timestamp = datetime.now()
    print(f"=" * 60)
    print(f"날씨 수집 시작: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    if hourly_mode:
        print(f"모드: 72시간 전체 데이터 수집 (오늘 ~ +2일)")
    print(f"=" * 60)

    # 지역 목록 로드
    regions = get_all_regions()
    print(f"총 {len(regions)}개 지역 로드됨")

    # 샘플 모드 (테스트용)
    if sample_mode:
        # 각 시도에서 일부만 선택
        import random
        sido_samples = {}
        for r in regions:
            sido = r["sido"]
            if sido not in sido_samples:
                sido_samples[sido] = []
            sido_samples[sido].append(r)

        sampled = []
        for sido, sido_regions in sido_samples.items():
            sampled.extend(random.sample(sido_regions, min(3, len(sido_regions))))

        regions = sampled[:sample_size]
        print(f"샘플 모드: {len(regions)}개 지역만 수집")

    # 해상예보 수집 (해역별로 한 번만)
    marine_forecasts = {}
    if KMA_API_KEY:
        print("\n해상예보 수집 중...")
        for zone_code, zone_name in MARINE_ZONE_CODES.items():
            print(f"\r  {zone_name}...", end="", flush=True)
            forecast = fetch_marine_forecast(zone_code)
            if forecast:
                marine_forecasts[zone_code] = forecast
            time.sleep(0.3)  # API 부하 방지
        print(f"\r해상예보 수집 완료: {len(marine_forecasts)}/{len(MARINE_ZONE_CODES)} 해역")
    else:
        print("⚠️ KMA_API_KEY 없음 - 해상예보 건너뜀")

    # 해수욕장 데이터 수집 (해안 지역용)
    beach_forecasts = {}
    if BEACH_API_KEY:
        print("\n해수욕장 날씨 수집 중...")
        # 해안 지역에 대해 beach_num 매핑 (임시로 1~420 범위에서 지역별 할당)
        # 실제로는 DB에 beach_num이 저장되어 있어야 하지만,
        # 현재는 해안 지역 순서대로 1~420 범위 내에서 매핑
        coastal_regions = [r for r in regions if r["is_coastal"]]
        beach_count = min(len(coastal_regions), 420)

        for idx, region in enumerate(coastal_regions[:beach_count], 1):
            beach_num = idx  # 임시 매핑
            print(f"\r  해수욕장 {idx}/{beach_count}...", end="", flush=True)
            beach_data = fetch_beach_forecast(beach_num)
            if beach_data:
                beach_forecasts[region["code"]] = beach_data
            time.sleep(0.1)  # API 부하 방지

        print(f"\r해수욕장 데이터 수집 완료: {len(beach_forecasts)}/{beach_count}개")
    else:
        print("⚠️ BEACH_API_KEY 없음 - 해수욕장 데이터 건너뜀")

    # Bulk API로 날씨 데이터 일괄 수집
    print("\n기상 데이터 수집 중 (Bulk API)...")
    weather_data = fetch_openmeteo_bulk(regions, hourly_mode=hourly_mode, batch_size=1000)

    results = []
    success_count = 0

    print("\n결과 처리 중...")
    for i, region in enumerate(regions, 1):
        if i % 500 == 0 or i == len(regions):
            print(f"\r  처리 중: {i}/{len(regions)}...", end="", flush=True)

        # Bulk API 결과에서 날씨 데이터 가져오기
        weather = weather_data.get(region["code"])

        # 해양 예보 (해안 지역만)
        marine_data = None
        if region["is_coastal"]:
            zone_code = get_marine_zone_for_region(region)
            if zone_code and zone_code in marine_forecasts:
                marine_data = marine_forecasts[zone_code]

        # 해수욕장 데이터 (해안 지역만)
        beach_data = None
        if region["is_coastal"] and region["code"] in beach_forecasts:
            beach_data = beach_forecasts[region["code"]]

        # 테마별 점수 계산 (해양 데이터 + 해수욕장 데이터 포함)
        scores = {}
        hourly_scores = []

        if weather:
            success_count += 1
            if hourly_mode and "hourly" in weather:
                # 각 시간별로 점수 계산
                for hour_data in weather["hourly"]:
                    hour_scores = calculate_simple_scores(hour_data, region, marine_data, beach_data)
                    hourly_scores.append({
                        "datetime": hour_data["datetime"],
                        "weather": hour_data,
                        "scores": hour_scores,
                    })
                # 현재 시간 점수도 저장
                if weather.get("current"):
                    scores = calculate_simple_scores(weather["current"], region, marine_data, beach_data)
            else:
                scores = calculate_simple_scores(weather, region, marine_data, beach_data)

        result = {
            "code": region["code"],
            "name": region["name"],
            "sido": region["sido"],
            "lat": region["lat"],
            "lon": region["lon"],
            "is_coastal": region["is_coastal"],
            "is_east_coast": region["is_east_coast"],
            "is_west_coast": region["is_west_coast"],
            "elevation": region["elevation"],
            "weather": weather.get("current") if hourly_mode and weather else weather,
            "scores": scores,
        }

        if hourly_mode and hourly_scores:
            result["hourly"] = hourly_scores

        if marine_data:
            result["marine"] = marine_data

        if beach_data:
            result["beach"] = beach_data

        results.append(result)

    print(f"\r  처리 완료                              ")
    print(f"\n수집 완료: {success_count}/{len(regions)} 성공")
    coastal_count = len([r for r in results if r.get("marine")])
    beach_count = len([r for r in results if r.get("beach")])
    print(f"해안 지역 (해상예보 포함): {coastal_count}개")
    print(f"해수욕장 데이터 포함: {beach_count}개")

    # 리포트 생성
    print("리포트 생성 중...")
    report = generate_markdown_report(results, timestamp)

    # 파일 저장
    suffix = "_hourly" if hourly_mode else ""
    filename = f"weather_report_{timestamp.strftime('%Y%m%d_%H%M%S')}{suffix}.md"
    filepath = RESULT_DIR / filename

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"✅ 리포트 저장: {filepath}")

    # JSON 데이터 저장 (hourly 모드일 때 전체 데이터 저장)
    if hourly_mode:
        json_filename = f"weather_data_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        json_filepath = RESULT_DIR / json_filename

        with open(json_filepath, "w", encoding="utf-8") as f:
            json.dump({
                "collected_at": timestamp.isoformat(),
                "forecast_range": {
                    "start": timestamp.strftime('%Y-%m-%d'),
                    "end": (timestamp + timedelta(days=2)).strftime('%Y-%m-%d'),
                    "hours": 72,
                },
                "regions_count": len(results),
                "success_count": success_count,
                "marine_forecasts": marine_forecasts,
                "regions": results,
            }, f, ensure_ascii=False, indent=2)

        print(f"✅ JSON 데이터 저장: {json_filepath}")

    # 최신 리포트 링크 업데이트
    latest_link = RESULT_DIR / "latest.md"
    with open(latest_link, "w", encoding="utf-8") as f:
        f.write(f"# 최신 리포트\n\n")
        f.write(f"[{filename}](./{filename})\n\n")
        f.write(f"생성 시각: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
        if hourly_mode:
            f.write(f"예보 범위: {timestamp.strftime('%Y-%m-%d')} ~ {(timestamp + timedelta(days=2)).strftime('%Y-%m-%d')} (72시간)\n")

    print(f"=" * 60)
    print(f"완료!")
    print(f"=" * 60)

    return filepath


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="날씨 수집 및 리포트 생성")
    parser.add_argument("--sample", action="store_true", help="샘플 모드 (일부 지역만)")
    parser.add_argument("--sample-size", type=int, default=50, help="샘플 크기")
    parser.add_argument("--full", action="store_true", help="전체 지역 수집")
    parser.add_argument("--hourly", action="store_true", help="72시간 전체 데이터 수집 (오늘 ~ +2일)")
    parser.add_argument("--test", action="store_true", help="테스트 모드 (10개 지역만)")

    args = parser.parse_args()

    if args.test:
        # 테스트: 10개 지역만 (해안 포함)
        run_collection(sample_mode=True, sample_size=10, hourly_mode=args.hourly)
    elif args.full:
        run_collection(sample_mode=False, hourly_mode=args.hourly)
    else:
        run_collection(sample_mode=args.sample, sample_size=args.sample_size, hourly_mode=args.hourly)
