"""
날씨 데이터 수집 및 리포트 생성

매일 03:00, 15:00 실행
- 모든 지역의 날씨 데이터 수집
- 테마별 점수 계산
- MD 리포트 파일 생성
"""
import sqlite3
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
import sys
import time

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import SQLITE_DB_PATH, THEME_IDS

# 결과 저장 폴더
RESULT_DIR = PROJECT_ROOT / "result"
RESULT_DIR.mkdir(exist_ok=True)

# Open-Meteo API
OPENMETEO_URL = "https://api.open-meteo.com/v1/forecast"


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


def fetch_openmeteo(lat, lon):
    """Open-Meteo에서 날씨 데이터 수집"""
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

        # 현재 시간에 가장 가까운 데이터 추출
        now = datetime.now()
        current_hour = now.hour

        # 오늘 데이터 인덱스
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


def calculate_simple_scores(weather, region):
    """간단한 테마별 점수 계산"""
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

    # 1. 일출 (동해안 우선, 구름 30~60%, 낮은 강수확률)
    score = 50
    if 30 <= cloud <= 60:
        score += 20
    if rain < 30:
        score += 15
    if is_east:
        score += 15
    scores[1] = {"name": "일출", "score": min(100, score)}

    # 2. 일출 오메가 (동해안 필수, 맑음, 낮은 풍속)
    score = 30
    if cloud < 30:
        score += 25
    if wind < 3:
        score += 20
    if is_east:
        score += 25
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
    scores[3] = {"name": "일몰", "score": min(100, score)}

    # 4. 일몰 오메가
    score = 30
    if cloud < 30:
        score += 25
    if wind < 3:
        score += 20
    if is_west:
        score += 25
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
    if temp > 18:
        score += 15
    scores[6] = {"name": "야광충", "score": max(0, min(100, score))}

    # 7. 바다 장노출
    score = 40
    if is_coastal:
        score += 25
    if wind < 5:
        score += 15
    if cloud < 70:
        score += 10
    scores[7] = {"name": "바다 장노출", "score": min(100, score)}

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

    # 헤더
    report_lines.append(f"# 날씨 수집 리포트")
    report_lines.append(f"")
    report_lines.append(f"**수집 시각**: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"**총 지역 수**: {len(results)}")
    report_lines.append(f"")

    # 요약 통계
    successful = len([r for r in results if r.get("weather")])
    failed = len(results) - successful
    report_lines.append(f"## 수집 현황")
    report_lines.append(f"- 성공: {successful}개 지역")
    report_lines.append(f"- 실패: {failed}개 지역")
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


def run_collection(sample_mode=False, sample_size=50):
    """날씨 수집 및 리포트 생성 실행"""
    timestamp = datetime.now()
    print(f"=" * 60)
    print(f"날씨 수집 시작: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
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

    results = []
    success_count = 0
    batch_size = 10  # API 호출 배치 크기

    for i, region in enumerate(regions, 1):
        print(f"\r[{i}/{len(regions)}] {region['name'][:20]:<20}", end="", flush=True)

        # 날씨 수집
        weather = None
        if region["lat"] and region["lon"]:
            weather = fetch_openmeteo(region["lat"], region["lon"])

        # 테마별 점수 계산
        scores = {}
        if weather:
            success_count += 1
            scores = calculate_simple_scores(weather, region)

        results.append({
            "code": region["code"],
            "name": region["name"],
            "sido": region["sido"],
            "lat": region["lat"],
            "lon": region["lon"],
            "is_coastal": region["is_coastal"],
            "is_east_coast": region["is_east_coast"],
            "is_west_coast": region["is_west_coast"],
            "elevation": region["elevation"],
            "weather": weather,
            "scores": scores,
        })

        # API 부하 방지
        if i % batch_size == 0:
            time.sleep(0.5)

    print(f"\n\n수집 완료: {success_count}/{len(regions)} 성공")

    # 리포트 생성
    print("리포트 생성 중...")
    report = generate_markdown_report(results, timestamp)

    # 파일 저장
    filename = f"weather_report_{timestamp.strftime('%Y%m%d_%H%M%S')}.md"
    filepath = RESULT_DIR / filename

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"✅ 리포트 저장: {filepath}")

    # 최신 리포트 링크 업데이트
    latest_link = RESULT_DIR / "latest.md"
    with open(latest_link, "w", encoding="utf-8") as f:
        f.write(f"# 최신 리포트\n\n")
        f.write(f"[{filename}](./{filename})\n\n")
        f.write(f"생성 시각: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")

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

    args = parser.parse_args()

    if args.full:
        run_collection(sample_mode=False)
    else:
        run_collection(sample_mode=args.sample, sample_size=args.sample_size)
