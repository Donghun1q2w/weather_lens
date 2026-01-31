"""
기상청 API 테스트 스크립트

샘플 지역(서울 강남구 역삼동)의 날씨 데이터를 수집합니다.

사용법:
    python scripts/test_kma_api.py [api_source]

    api_source: "data.go.kr" (기본값) 또는 "apihub.kma.go.kr"

예시:
    python scripts/test_kma_api.py
    python scripts/test_kma_api.py data.go.kr
    python scripts/test_kma_api.py apihub.kma.go.kr
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# .env 파일 로드
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from config.settings import KMA_API_KEY, KMA_API_SOURCE
from collectors import KMAForecastCollector, CollectorError


async def test_kma_api(api_source: str = None):
    """
    기상청 API 테스트

    Args:
        api_source: API 소스 ("data.go.kr" 또는 "apihub.kma.go.kr")
    """
    # API 소스 결정 (우선순위: 인자 > 환경변수 > 기본값)
    if api_source is None:
        api_source = KMA_API_SOURCE

    print("=" * 60)
    print("기상청 단기예보 API 테스트")
    print("=" * 60)

    # API 키 확인
    if not KMA_API_KEY or KMA_API_KEY == "your_kma_api_key_here":
        print("❌ KMA_API_KEY가 설정되지 않았습니다.")
        print("   .env 파일에 실제 API 키를 입력하세요.")
        return

    print(f"✅ API 키 확인: {KMA_API_KEY[:10]}...")
    print(f"✅ API 소스: {api_source}")

    # 테스트 지역: 서울 강남구 역삼동
    test_region = {
        "code": "1168010100",
        "name": "서울특별시 강남구 역삼동",
        "nx": 61,   # 기상청 격자 X 좌표
        "ny": 126,  # 기상청 격자 Y 좌표
    }

    print(f"\n📍 테스트 지역: {test_region['name']}")

    if api_source == "data.go.kr":
        print(f"   격자 좌표: nx={test_region['nx']}, ny={test_region['ny']}")
    else:
        print(f"   지역명 기반 조회 (격자 좌표 불필요)")

    print(f"\n⏳ {api_source} API 호출 중...")

    try:
        async with KMAForecastCollector(KMA_API_KEY, api_source=api_source) as collector:
            # API 소스에 따라 다른 파라미터 전달
            if api_source == "data.go.kr":
                result = await collector.collect(
                    region_code=test_region["code"],
                    nx=test_region["nx"],
                    ny=test_region["ny"]
                )
            else:  # apihub.kma.go.kr
                result = await collector.collect(
                    region_code=test_region["code"]
                )

        print("\n✅ API 호출 성공!")
        print("-" * 60)

        # 결과 출력
        print(f"🌐 API 소스: {result.get('api_source')}")
        if result.get('base_date'):
            print(f"📅 기준 일시: {result.get('base_date')} {result.get('base_time')}")
        print(f"🕐 수집 시각: {result.get('collected_at')}")

        forecasts = result.get("forecast", [])
        print(f"\n📊 예보 데이터: {len(forecasts)}개 시간대")

        if forecasts:
            print("\n[ 오늘/내일 예보 미리보기 ]")
            print("-" * 60)
            print(f"{'시간':<20} {'기온':>6} {'습도':>6} {'강수확률':>8} {'하늘':>10}")
            print("-" * 60)

            # 처음 12개 시간대만 출력
            for forecast in forecasts[:12]:
                dt = forecast.get("datetime", "")[:16]  # YYYY-MM-DDTHH:MM
                temp = forecast.get("temp")
                humidity = forecast.get("humidity")
                rain_prob = forecast.get("rain_prob")
                sky = forecast.get("sky")

                # 하늘상태 코드 변환
                sky_text = {1: "맑음☀️", 3: "구름많음🌤️", 4: "흐림☁️"}.get(sky, f"코드:{sky}")

                temp_str = f"{temp}°C" if temp is not None else "-"
                humidity_str = f"{humidity}%" if humidity is not None else "-"
                rain_str = f"{rain_prob}%" if rain_prob is not None else "-"

                print(f"{dt:<20} {temp_str:>6} {humidity_str:>6} {rain_str:>8} {sky_text:>10}")

        print("\n" + "=" * 60)
        print("✅ 기상청 API 테스트 완료!")
        print("=" * 60)

        return result

    except CollectorError as e:
        print(f"\n❌ API 오류: {e}")
        print("\n가능한 원인:")
        print("  1. API 키가 올바르지 않음")
        print("  2. API 키 활성화가 안 됨 (신청 후 1-2일 소요)")
        print("  3. 일일 호출 한도 초과")
        if api_source == "apihub.kma.go.kr":
            print("  4. API 허브의 응답 구조가 예상과 다를 수 있음 (파싱 로직 확인 필요)")
        return None

    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # 커맨드 라인 인자로 API 소스 지정 가능
    api_source_arg = sys.argv[1] if len(sys.argv) > 1 else None

    if api_source_arg and api_source_arg not in ["data.go.kr", "apihub.kma.go.kr"]:
        print(f"❌ 잘못된 API 소스: {api_source_arg}")
        print("   사용 가능한 소스: data.go.kr, apihub.kma.go.kr")
        sys.exit(1)

    asyncio.run(test_kma_api(api_source_arg))
