# Weather Lens - 예보정보 조회 가이드

> **대상 독자**: API를 활용하여 날씨/해양 데이터를 조회하려는 개발자
> **작성일**: 2026-01-31
> **버전**: 1.0

---

## 목차

1. [개요](#1-개요)
2. [해수욕장 날씨 API (BeachInfoService)](#2-해수욕장-날씨-api-beachinfoservice)
3. [기상청 단기예보 API](#3-기상청-단기예보-api)
4. [기상청 해상예보 API](#4-기상청-해상예보-api)
5. [바다누리 해양 API](#5-바다누리-해양-api)
6. [Open-Meteo API](#6-open-meteo-api)
7. [Collector 사용법](#7-collector-사용법)
8. [에러 처리](#8-에러-처리)

---

## 1. 개요

### 1.1 지원하는 예보 API

| API | 제공 데이터 | 출처 | API 키 필요 |
|-----|------------|------|------------|
| BeachInfoService | 해수욕장 날씨 (420개소) | 기상청 | O |
| VilageFcstInfoService | 읍면동 단기예보 | 기상청 | O |
| 해상예보 | 해양예보구역별 예보 | 기상청 API Hub | O |
| 바다누리 | 조석/파고/수온 | 국립해양조사원 | O |
| Open-Meteo | 글로벌 기상 예보 | Open-Meteo | X |

### 1.2 환경 변수 설정

```bash
# .env 파일
KMA_API_KEY=your_kma_api_key          # 기상청 단기예보
BEACH_API_KEY=your_beach_api_key      # 해수욕장 날씨
KHOA_API_KEY=your_khoa_api_key        # 바다누리
AIRKOREA_API_KEY=your_airkorea_key    # 에어코리아 (대기질)
```

---

## 2. 해수욕장 날씨 API (BeachInfoService)

### 2.1 개요

전국 420개 해수욕장의 날씨 정보를 제공하는 기상청 API입니다.

**Base URL**: `http://apis.data.go.kr/1360000/BeachInfoservice`

### 2.2 제공 엔드포인트

| 엔드포인트 | 설명 | 주요 데이터 |
|-----------|------|------------|
| `getUltraSrtFcst` | 초단기예보 | 기온, 습도, 풍속, 강수형태 |
| `getVilageFcst` | 단기예보 | 기온, 강수확률, 하늘상태 |
| `getWhBuoyFcst` | 파고 정보 | 유의파고, 파향 |
| `getTideFcst` | 조석 정보 | 만조/간조 시각, 조위 |
| `getSunRiseSet` | 일출/일몰 | 일출/일몰 시각 |
| `getSeaWaterTemp` | 수온 | 표층 수온 |

### 2.3 요청 파라미터

| 파라미터 | 설명 | 필수 | 예시 |
|---------|------|------|------|
| `serviceKey` | API 인증키 | O | (발급받은 키) |
| `beach_num` | 해수욕장 번호 | O | 1 (경포해수욕장) |
| `base_date` | 기준일자 | O | 20260131 |
| `base_time` | 기준시각 | O | 0600 |
| `dataType` | 응답형식 | X | JSON (기본값) |

### 2.4 하늘상태 코드 (SKY)

| 코드 | 의미 |
|-----|------|
| 1 | 맑음 |
| 3 | 구름많음 |
| 4 | 흐림 |

### 2.5 강수형태 코드 (PTY)

| 코드 | 의미 |
|-----|------|
| 0 | 없음 |
| 1 | 비 |
| 2 | 비/눈 |
| 3 | 눈 |
| 4 | 소나기 |
| 5 | 빗방울 |
| 6 | 빗방울눈날림 |
| 7 | 눈날림 |

### 2.6 Python 사용 예시

```python
from collectors import BeachInfoCollector

# Collector 초기화
collector = BeachInfoCollector(api_key="YOUR_API_KEY")

# 경포해수욕장(1번) 초단기예보 조회
forecast = await collector.get_ultra_short_forecast(
    beach_num=1,
    base_date="20260131",
    base_time="0600"
)

print(forecast)
# {
#     "beach_num": 1,
#     "base_date": "20260131",
#     "base_time": "0600",
#     "forecasts": [
#         {"category": "T1H", "value": "2", "fcst_time": "0700"},
#         {"category": "SKY", "value": "1", "fcst_time": "0700"},
#         ...
#     ]
# }

# 파고 정보 조회
wave = await collector.get_wave_height(beach_num=1, base_date="20260131")
print(f"유의파고: {wave['wave_height']}m")

# 조석 정보 조회
tide = await collector.get_tide_info(beach_num=1, base_date="20260131")
for t in tide['tides']:
    print(f"{t['type']}: {t['time']} ({t['level']}cm)")

# 일출/일몰 조회
sun = await collector.get_sun_info(beach_num=1, base_date="20260131")
print(f"일출: {sun['sunrise']}, 일몰: {sun['sunset']}")

# 수온 조회
temp = await collector.get_sea_temperature(beach_num=1, base_date="20260131")
print(f"수온: {temp['temperature']}°C")
```

### 2.7 해수욕장 번호 조회

```python
from data.beaches import get_beach_by_num, get_beaches_by_region, BEACHES

# 번호로 해수욕장 찾기
beach = get_beach_by_num(1)
print(beach)  # {"beach_num": 1, "name": "경포해수욕장", ...}

# 지역코드로 해수욕장 찾기
beaches = get_beaches_by_region("4215012500")  # 강원도 강릉시 강문동
for b in beaches:
    print(f"{b['name']} (번호: {b['beach_num']})")

# 전체 해수욕장 수
print(f"총 {len(BEACHES)}개 해수욕장")  # 420개
```

---

## 3. 기상청 단기예보 API

### 3.1 개요

전국 읍면동 단위의 단기예보를 제공합니다.

**Base URL**: `http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0`

### 3.2 제공 엔드포인트

| 엔드포인트 | 설명 | 예보 간격 |
|-----------|------|----------|
| `getUltraSrtNcst` | 초단기실황 | 매시 정각 |
| `getUltraSrtFcst` | 초단기예보 | 6시간 |
| `getVilageFcst` | 단기예보 | 3일 |

### 3.3 예보 카테고리

| 카테고리 | 설명 | 단위 |
|---------|------|------|
| TMP | 기온 | °C |
| TMN | 최저기온 | °C |
| TMX | 최고기온 | °C |
| SKY | 하늘상태 | 코드 |
| PTY | 강수형태 | 코드 |
| POP | 강수확률 | % |
| PCP | 1시간 강수량 | mm |
| REH | 습도 | % |
| WSD | 풍속 | m/s |
| VEC | 풍향 | 도 |

### 3.4 Python 사용 예시

```python
from collectors import KMAForecastCollector

collector = KMAForecastCollector(api_key="YOUR_API_KEY")

# 좌표 기반 예보 조회 (nx, ny는 기상청 격자좌표)
forecast = await collector.get_village_forecast(
    nx=60,
    ny=127,
    base_date="20260131",
    base_time="0500"
)

# 결과 파싱
for item in forecast['items']:
    print(f"{item['category']}: {item['fcstValue']} ({item['fcstDate']} {item['fcstTime']})")
```

### 3.5 격자 좌표 변환

```python
from utils.coordinates import convert_to_grid

# 위경도 → 기상청 격자좌표
lat, lon = 37.5665, 126.9780  # 서울시청
nx, ny = convert_to_grid(lat, lon)
print(f"격자좌표: ({nx}, {ny})")  # (60, 127)
```

---

## 4. 기상청 해상예보 API

### 4.1 개요

해양예보구역별 해상 기상예보를 제공합니다.

**Base URL**: `https://apihub.kma.go.kr/api/typ01/url/fct_shrt_sea.php`

### 4.2 해양예보구역 코드

| 코드 | 구역명 |
|-----|--------|
| 12A10000 | 서해북부 |
| 12A20000 | 서해중부 |
| 12A30000 | 서해남부 |
| 12B10000 | 남해서부 |
| 12B20000 | 남해동부 |
| 12C10000 | 동해남부 |
| 12C20000 | 동해중부 |
| 12C30000 | 동해북부 |
| 12D10000 | 제주도 |

### 4.3 Python 사용 예시

```python
from collectors import KMAMarineForecastCollector

collector = KMAMarineForecastCollector(api_key="YOUR_API_KEY")

# 동해북부 해상예보 조회
forecast = await collector.get_marine_forecast(zone_code="12C30000")

print(f"예보구역: {forecast['zone_name']}")
print(f"파고: {forecast['wave_height']}m")
print(f"풍속: {forecast['wind_speed']}m/s")
print(f"날씨: {forecast['weather']}")
```

---

## 5. 바다누리 해양 API

### 5.1 개요

국립해양조사원에서 제공하는 조석, 파고, 수온 등 해양 관측 데이터입니다.

**Base URL**: `http://www.khoa.go.kr/api/oceangrid`

### 5.2 제공 데이터

| 서비스 | 설명 |
|--------|------|
| `tideObsPreTab` | 조석예보 |
| `obsWaveHight` | 파고 관측 |
| `obsWTemp` | 수온 관측 |

### 5.3 Python 사용 예시

```python
from collectors import KHOAOceanCollector

collector = KHOAOceanCollector(api_key="YOUR_API_KEY")

# 조석 정보 조회 (관측소 ID 필요)
tide = await collector.get_tide_prediction(
    station_id="DT_0001",
    date="20260131"
)

for t in tide['predictions']:
    print(f"{t['type']}: {t['time']} - {t['level']}cm")

# 파고 관측값
wave = await collector.get_wave_observation(station_id="IE_0060")
print(f"현재 파고: {wave['height']}m")

# 수온 관측값
temp = await collector.get_water_temperature(station_id="DT_0001")
print(f"현재 수온: {temp['temperature']}°C")
```

---

## 6. Open-Meteo API

### 6.1 개요

API 키 없이 사용 가능한 무료 글로벌 기상 API입니다. 기상청 데이터의 보조 소스로 활용됩니다.

**Base URL**: `https://api.open-meteo.com/v1/forecast`

### 6.2 제공 데이터

- 시간별 기온, 습도, 풍속, 강수량
- 일별 최고/최저 기온, 일출/일몰
- 구름량, 자외선 지수

### 6.3 Python 사용 예시

```python
from collectors import OpenMeteoCollector

collector = OpenMeteoCollector()

# 위경도로 예보 조회
forecast = await collector.get_forecast(
    lat=37.5665,
    lon=126.9780,
    hourly=["temperature_2m", "humidity", "wind_speed_10m"],
    forecast_days=3
)

# 시간별 데이터
for i, time in enumerate(forecast['hourly']['time']):
    temp = forecast['hourly']['temperature_2m'][i]
    humidity = forecast['hourly']['humidity'][i]
    print(f"{time}: {temp}°C, 습도 {humidity}%")
```

---

## 7. Collector 사용법

### 7.1 모든 Collector 공통 패턴

```python
import asyncio
from collectors import (
    BeachInfoCollector,
    KMAForecastCollector,
    KMAMarineForecastCollector,
    KHOAOceanCollector,
    OpenMeteoCollector
)

async def main():
    # 각 Collector 초기화
    beach = BeachInfoCollector(api_key="BEACH_API_KEY")
    kma = KMAForecastCollector(api_key="KMA_API_KEY")
    marine = KMAMarineForecastCollector(api_key="KMA_API_KEY")
    khoa = KHOAOceanCollector(api_key="KHOA_API_KEY")
    openmeteo = OpenMeteoCollector()  # API 키 불필요

    # 병렬로 데이터 수집
    results = await asyncio.gather(
        beach.get_ultra_short_forecast(beach_num=1, base_date="20260131", base_time="0600"),
        kma.get_village_forecast(nx=60, ny=127, base_date="20260131", base_time="0500"),
        openmeteo.get_forecast(lat=37.5665, lon=126.9780)
    )

    beach_data, kma_data, openmeteo_data = results
    print("수집 완료!")

asyncio.run(main())
```

### 7.2 통합 수집 (collect 메서드)

```python
# BeachInfoCollector의 통합 수집
result = await beach.collect(
    beach_num=1,
    base_date="20260131",
    base_time="0600"
)

# 모든 데이터가 하나의 딕셔너리로 반환
print(result['forecast'])      # 예보 데이터
print(result['wave'])          # 파고 데이터
print(result['tide'])          # 조석 데이터
print(result['sun'])           # 일출/일몰
print(result['temperature'])   # 수온
```

---

## 8. 에러 처리

### 8.1 공통 에러 코드

| 코드 | 의미 | 대응 |
|-----|------|------|
| 00 | 정상 | - |
| 01 | 어플리케이션 에러 | API 키 확인 |
| 02 | DB 에러 | 재시도 |
| 03 | 데이터 없음 | 파라미터 확인 |
| 04 | HTTP 에러 | 네트워크 확인 |
| 05 | 서비스 종료 | 공지사항 확인 |
| 10 | 잘못된 요청 | 파라미터 검증 |
| 11 | 필수값 누락 | 필수 파라미터 확인 |
| 12 | 허용되지 않는 서비스 | 서비스 키 권한 확인 |
| 20 | 서비스 접근 거부 | API 키 갱신 |
| 21 | 사용량 초과 | 일일 한도 확인 |

### 8.2 에러 처리 예시

```python
from collectors import BeachInfoCollector, CollectorError

collector = BeachInfoCollector(api_key="YOUR_API_KEY")

try:
    result = await collector.get_wave_height(
        beach_num=1,
        base_date="20260131"
    )
except CollectorError as e:
    if e.code == "03":
        print("해당 날짜의 데이터가 없습니다.")
    elif e.code == "21":
        print("일일 API 사용량을 초과했습니다.")
    else:
        print(f"API 에러: {e.message}")
except Exception as e:
    print(f"예상치 못한 에러: {e}")
```

### 8.3 재시도 로직

```python
import asyncio
from collectors import BeachInfoCollector

async def fetch_with_retry(collector, beach_num, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await collector.get_wave_height(
                beach_num=beach_num,
                base_date="20260131"
            )
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 지수 백오프
                print(f"재시도 {attempt + 1}/{max_retries} (대기: {wait_time}초)")
                await asyncio.sleep(wait_time)
            else:
                raise
```

---

## 부록: 빠른 참조

### 주요 Collector 메서드

| Collector | 메서드 | 설명 |
|-----------|--------|------|
| `BeachInfoCollector` | `get_ultra_short_forecast()` | 초단기예보 |
| | `get_village_forecast()` | 단기예보 |
| | `get_wave_height()` | 파고 정보 |
| | `get_tide_info()` | 조석 정보 |
| | `get_sun_info()` | 일출/일몰 |
| | `get_sea_temperature()` | 수온 |
| | `collect()` | 전체 통합 수집 |
| `KMAForecastCollector` | `get_ultra_short_ncst()` | 초단기실황 |
| | `get_ultra_short_fcst()` | 초단기예보 |
| | `get_village_forecast()` | 단기예보 |
| `KMAMarineForecastCollector` | `get_marine_forecast()` | 해상예보 |
| `KHOAOceanCollector` | `get_tide_prediction()` | 조석예보 |
| | `get_wave_observation()` | 파고 관측 |
| | `get_water_temperature()` | 수온 관측 |
| `OpenMeteoCollector` | `get_forecast()` | 기상예보 |

### 날짜/시간 포맷

| API | 날짜 | 시간 |
|-----|------|------|
| 기상청 | YYYYMMDD | HHMM |
| 바다누리 | YYYYMMDD | - |
| Open-Meteo | YYYY-MM-DD | ISO8601 |

### API 호출 제한

| API | 일일 한도 | 비고 |
|-----|----------|------|
| 기상청 | 10,000회 | 갱신: 매일 00:00 |
| 바다누리 | 10,000회 | 갱신: 매일 00:00 |
| Open-Meteo | 10,000회 | API 키 없이 사용 가능 |

---

*이 문서는 Weather Lens 프로젝트의 일부입니다.*
