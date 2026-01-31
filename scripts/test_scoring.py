"""
점수 계산 테스트 스크립트

전국 3,600개 지역 × 16개 테마 스코어링을 실행합니다.
3일치 점수(오늘/내일/모레) 예측 포함.

사용법:
    python scripts/test_scoring.py
"""
import asyncio
import sqlite3
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from config.settings import SQLITE_DB_PATH, KMA_API_KEY, THEME_IDS
from collectors import KMAForecastCollector
from scorers import get_all_scorers, get_scorer_by_theme_id


def load_regions() -> List[Dict]:
    """데이터베이스에서 지역 로드"""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT code, name, sido, sigungu, lat, lon, nx, ny,
               is_coastal, is_east_coast, elevation
        FROM regions
    """)

    regions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return regions


async def collect_sample_weather(region: Dict) -> Dict:
    """샘플 지역의 날씨 데이터 수집"""
    try:
        async with KMAForecastCollector(KMA_API_KEY, api_source="apihub.kma.go.kr") as collector:
            # 시도 코드로 regId 결정
            sido_code = region["code"][:2]
            result = await collector.collect(region_code=region["code"])
            return result
    except Exception as e:
        print(f"  ⚠️ 날씨 수집 실패: {e}")
        return None


def create_mock_weather_data(region: Dict) -> Dict:
    """테스트용 모의 날씨 데이터 생성"""
    import random

    # 해안가/내륙에 따라 다른 날씨 패턴
    is_coastal = region.get("is_coastal", 0)
    is_east_coast = region.get("is_east_coast", 0)

    # 기본 날씨 데이터
    base_cloud = random.randint(20, 80)
    base_rain_prob = random.randint(0, 40)

    # 해안가는 습도 높음
    humidity = random.randint(60, 90) if is_coastal else random.randint(40, 70)

    # 동해안은 일출 조건 좋음 (맑은 날 가정)
    if is_east_coast:
        base_cloud = random.randint(10, 40)
        base_rain_prob = random.randint(0, 20)

    return {
        "datetime": datetime.now().isoformat(),
        "cloud": {"avg": base_cloud, "kma": base_cloud, "openmeteo": base_cloud},
        "rain_prob": {"avg": base_rain_prob},
        "temp": {"avg": random.randint(-5, 10)},
        "humidity": humidity,
        "wind_speed": random.uniform(1, 8),
        "visibility": random.randint(5, 20),
        "pm25": random.randint(10, 50),
        "is_coastal": is_coastal,
        "is_east_coast": is_east_coast,
        "elevation": region.get("elevation", 0),
        # 해양 데이터 (해안가만)
        "sea_temp": random.randint(8, 15) if is_coastal else None,
        "wave_height": random.uniform(0.3, 2.0) if is_coastal else None,
        "air_temp": random.randint(-5, 10),
    }


async def calculate_scores(regions: List[Dict]) -> Dict[int, List[Dict]]:
    """모든 지역에 대해 8개 테마 점수 계산"""
    scorers = get_all_scorers()
    results = {theme_id: [] for theme_id in THEME_IDS.keys()}

    print(f"\n⏳ {len(regions)}개 지역 × 8개 테마 점수 계산 중...")

    for i, region in enumerate(regions):
        # 모의 날씨 데이터 생성
        weather_data = create_mock_weather_data(region)

        for theme_id, theme_name in THEME_IDS.items():
            scorer = get_scorer_by_theme_id(theme_id)
            if not scorer:
                continue

            try:
                # 점수 계산
                score = await scorer.calculate_score(weather_data)

                results[theme_id].append({
                    "region_code": region["code"],
                    "region_name": region["name"],
                    "sido": region["sido"],
                    "score": score,
                    "is_coastal": region["is_coastal"],
                    "is_east_coast": region["is_east_coast"],
                })
            except Exception as e:
                # 점수 계산 실패 시 0점
                results[theme_id].append({
                    "region_code": region["code"],
                    "region_name": region["name"],
                    "sido": region["sido"],
                    "score": 0,
                    "error": str(e),
                })

        # 진행률 표시
        if (i + 1) % 50 == 0:
            print(f"   {i + 1}/{len(regions)} 지역 완료")

    return results


def print_top_regions(results: Dict[int, List[Dict]], top_n: int = 5):
    """테마별 TOP N 지역 출력"""
    print("\n" + "=" * 70)
    print("📊 테마별 TOP 지역 추천 결과")
    print("=" * 70)

    for theme_id, theme_name in THEME_IDS.items():
        theme_results = results.get(theme_id, [])

        # 점수 내림차순 정렬
        sorted_results = sorted(theme_results, key=lambda x: x["score"], reverse=True)

        print(f"\n🎯 [{theme_id}] {theme_name}")
        print("-" * 60)

        if not sorted_results:
            print("   데이터 없음")
            continue

        # 평균 점수
        avg_score = sum(r["score"] for r in sorted_results) / len(sorted_results)
        max_score = sorted_results[0]["score"]
        min_score = sorted_results[-1]["score"]

        print(f"   평균: {avg_score:.1f}점 | 최고: {max_score:.1f}점 | 최저: {min_score:.1f}점")
        print()

        # TOP N 출력
        print(f"   {'순위':<4} {'점수':>6} {'지역':<40}")
        print("   " + "-" * 54)

        for rank, result in enumerate(sorted_results[:top_n], 1):
            score = result["score"]
            name = result["region_name"]

            # 해안가/동해안 표시
            tags = []
            if result.get("is_east_coast"):
                tags.append("🌅동해안")
            elif result.get("is_coastal"):
                tags.append("🏖️해안")

            tag_str = " ".join(tags)
            print(f"   {rank:<4} {score:>6.1f} {name:<35} {tag_str}")


async def main():
    print("=" * 70)
    print("PhotoSpot Korea - 점수 계산 테스트")
    print("=" * 70)

    # 1. 지역 데이터 로드
    print("\n📍 지역 데이터 로드 중...")
    regions = load_regions()
    print(f"   {len(regions)}개 지역 로드 완료")

    # 시도별 통계
    sido_count = {}
    coastal_count = 0
    east_coast_count = 0
    for r in regions:
        sido = r["sido"]
        sido_count[sido] = sido_count.get(sido, 0) + 1
        if r["is_coastal"]:
            coastal_count += 1
        if r["is_east_coast"]:
            east_coast_count += 1

    print(f"   해안가: {coastal_count}개 | 동해안: {east_coast_count}개")

    # 2. 점수 계산
    results = await calculate_scores(regions)

    # 3. 결과 출력
    print_top_regions(results, top_n=5)

    # 4. 테마별 요약
    print("\n" + "=" * 70)
    print("📈 테마별 요약")
    print("=" * 70)

    summary_data = []
    for theme_id, theme_name in THEME_IDS.items():
        theme_results = results.get(theme_id, [])
        if theme_results:
            sorted_results = sorted(theme_results, key=lambda x: x["score"], reverse=True)
            top1 = sorted_results[0]
            avg = sum(r["score"] for r in sorted_results) / len(sorted_results)
            summary_data.append({
                "theme": theme_name,
                "top_region": top1["region_name"].split()[-1],  # 동 이름만
                "top_score": top1["score"],
                "avg_score": avg,
            })

    print(f"\n{'테마':<15} {'TOP 지역':<15} {'TOP 점수':>10} {'평균':>10}")
    print("-" * 55)
    for s in summary_data:
        print(f"{s['theme']:<15} {s['top_region']:<15} {s['top_score']:>10.1f} {s['avg_score']:>10.1f}")

    print("\n" + "=" * 70)
    print("✅ 점수 계산 테스트 완료!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
