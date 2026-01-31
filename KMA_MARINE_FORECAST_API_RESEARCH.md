# 기상청 해상예보 API 완전 가이드

**연구 일자**: 2026-01-31
**대상 API**: 기상청 1.5단기 해상예보 (근해예보)
**작성자**: ULTRAPILOT WORKER [2/3]

---

## 목차

1. [개요](#1-개요)
2. [API 소스 비교](#2-api-소스-비교)
3. [해상예보구역 코드](#3-해상예보구역-코드)
4. [API 명세](#4-api-명세)
5. [응답 필드 상세](#5-응답-필드-상세)
6. [발표 시각 및 예보 기간](#6-발표-시각-및-예보-기간)
7. [사용 예시](#7-사용-예시)
8. [참고 자료](#8-참고-자료)

---

## 1. 개요

기상청은 한반도 주변 해역의 해상예보를 제공하며, 크게 **근해예보**(단기), **중기해상예보**, **특보** 등으로 구분됩니다. 본 문서는 **1.5단기 근해예보 API**에 초점을 맞춥니다.

### 1.1 예보 종류

| 예보 종류 | 예보 기간 | 발표 주기 | 공간 해상도 |
|----------|----------|----------|-----------|
| **근해예보** (단기) | D-day ~ D+2 (3일) | 1일 2회 (06:00, 18:00 추정) | 9개 대구역 + 세분화 |
| **중기해상예보** | D+3 ~ D+10 (11일) | 1일 2회 (06:00, 18:00) | 오전/오후 단위 |
| **해상특보** | 실시간 | 발효 시 즉시 | 구역별 |

---

## 2. API 소스 비교

기상청 해상예보 데이터는 두 가지 주요 경로로 제공됩니다.

### 2.1 공공데이터포털 (data.go.kr)

| 항목 | 내용 |
|------|------|
| **API 이름** | 기상청_동네예보 통보문 조회서비스 |
| **서비스명** | VilageFcstMsgService |
| **엔드포인트** | `http://apis.data.go.kr/1360000/VilageFcstMsgService/getWthrMarFcst` |
| **인증 방식** | `serviceKey` 파라미터 (URL 인코딩 필요) |
| **응답 형식** | JSON/XML |
| **사용 권장** | 안정적인 표준 API, 승인 필요 (1-2일) |

### 2.2 기상청 API 허브 (apihub.kma.go.kr)

| 항목 | 내용 |
|------|------|
| **API 이름** | 해상예보 통보문 조회 API |
| **서비스명** | VilageFcstMsgService/getWthrMarFcst |
| **엔드포인트** | `https://apihub.kma.go.kr/api/typ02/openApi/VilageFcstMsgService/getWthrMarFcst` |
| **인증 방식** | `authKey` 파라미터 |
| **응답 형식** | JSON/XML |
| **사용 권장** | 기상청 공식 허브, 다양한 기상 데이터 통합 제공 |

### 2.3 주요 차이점

- **인증키 이름**: `serviceKey` (공공데이터) vs `authKey` (API 허브)
- **API 키 호환성**: 두 플랫폼의 API 키는 서로 호환되지 않음
- **응답 구조**: 기본적으로 동일하나, 헤더 필드명에 차이 있을 수 있음
- **발급 절차**: 공공데이터포털은 승인 필요, API 허브는 즉시 발급 가능

---

## 3. 해상예보구역 코드

### 3.1 대구역 코드 (regId)

기상청은 한반도 주변 해역을 **9개 대구역**으로 구분합니다.

| 구역 코드 | 한글명 | 영문명 | 주요 관할 |
|----------|--------|--------|----------|
| **12A10000** | 서해북부 | West Sea North | 인천, 경기 해안 |
| **12A20000** | 서해중부 | West Sea Central | 충남 해안 |
| **12A30000** | 서해남부 | West Sea South | 전북, 전남 서해안 |
| **12B10000** | 남해서부 | South Sea West | 전남 남해안 |
| **12B20000** | 남해동부 | South Sea East | 경남 해안 |
| **12C10000** | 동해남부 | East Sea South | 부산, 울산 해안 |
| **12C20000** | 동해중부 | East Sea Central | 경북 해안 |
| **12C30000** | 동해북부 | East Sea North | 강원 해안 |
| **12D10000** | 제주도 | Jeju Island | 제주특별자치도 |

### 3.2 세부 구역 (앞바다/먼바다)

각 대구역은 **앞바다**, **먼바다** (안쪽/바깥)로 세분화됩니다. 현재 공개 API에서는 대구역 코드만 사용하며, 세분화된 구역 코드는 확인되지 않았습니다.

#### 세분화 예시 (웹 페이지 기준)

**서해중부 (12A20000)**:
- 서해중부 앞바다
- 서해중부 안쪽먼바다
- 서해중부 바깥먼바다

**서해남부 (12A30000)**:
- 서해남부 앞바다
- 서해남부 북쪽안쪽먼바다
- 서해남부 북쪽바깥먼바다
- 서해남부 남쪽안쪽먼바다
- 서해남부 남쪽바깥먼바다

**제주도 (12D10000)**:
- 제주도 앞바다
- 제주도 남쪽바깥먼바다
- 제주도 남서쪽안쪽먼바다
- 제주도 남동쪽안쪽먼바다

> **참고**: API에서 세분화 구역별 예보를 받으려면 추가 파라미터가 필요할 수 있으나, 공식 문서에서 확인되지 않았습니다. 현재는 대구역 단위 예보만 제공되는 것으로 추정됩니다.

---

## 4. API 명세

### 4.1 요청 URL

```
[공공데이터포털]
GET http://apis.data.go.kr/1360000/VilageFcstMsgService/getWthrMarFcst

[기상청 API 허브]
GET https://apihub.kma.go.kr/api/typ02/openApi/VilageFcstMsgService/getWthrMarFcst
```

### 4.2 요청 파라미터

| 파라미터 | 타입 | 필수 | 설명 | 예시 |
|---------|------|------|------|------|
| **serviceKey** (공공데이터) | String | O | 공공데이터포털 인증키 (URL 인코딩) | `서비스키` |
| **authKey** (API 허브) | String | O | 기상청 API 허브 인증키 | `인증키` |
| **pageNo** | Integer | O | 페이지 번호 | `1` |
| **numOfRows** | Integer | O | 한 페이지 결과 수 | `20` |
| **dataType** | String | O | 응답 형식 | `JSON` 또는 `XML` |
| **regId** | String | O | 해상예보구역 코드 | `12A10000` |

### 4.3 요청 예시

```bash
# 공공데이터포털
curl -X GET "http://apis.data.go.kr/1360000/VilageFcstMsgService/getWthrMarFcst?serviceKey=YOUR_KEY&pageNo=1&numOfRows=20&dataType=JSON&regId=12A10000"

# 기상청 API 허브
curl -X GET "https://apihub.kma.go.kr/api/typ02/openApi/VilageFcstMsgService/getWthrMarFcst?authKey=YOUR_KEY&pageNo=1&numOfRows=20&dataType=JSON&regId=12A10000"
```

### 4.4 응답 구조 (JSON)

```json
{
  "response": {
    "header": {
      "resultCode": "00",
      "resultMsg": "NORMAL_SERVICE"
    },
    "body": {
      "dataType": "JSON",
      "items": {
        "item": [
          {
            "announceTime": "202601311800",
            "numEf": 0,
            "wf": "맑음",
            "wfCd": "DB01",
            "wav": "1",
            "wd1": "북서",
            "wd2": "북",
            "ws": "3"
          },
          {
            "announceTime": "202601311800",
            "numEf": 1,
            "wf": "구름많음",
            "wfCd": "DB03",
            "wav": "2",
            "wd1": "북",
            "wd2": "북동",
            "ws": "5"
          }
        ]
      },
      "pageNo": 1,
      "numOfRows": 20,
      "totalCount": 9
    }
  }
}
```

### 4.5 응답 코드

| resultCode | resultMsg | 의미 |
|------------|-----------|------|
| **00** | NORMAL_SERVICE | 정상 |
| **03** | NO_DATA | 데이터 없음 |
| **04** | HTTP_ERROR | HTTP 오류 |
| **05** | SERVICETIME_OUT | 서비스 연결 실패 |
| **10** | INVALID_REQUEST_PARAMETER_ERROR | 잘못된 요청 파라미터 |
| **12** | NO_OPENAPI_SERVICE_ERROR | 해당 오픈API 서비스 없음 |
| **22** | SERVICE_KEY_IS_NOT_REGISTERED_ERROR | 등록되지 않은 서비스 키 |
| **30** | EXCEEDS_LIMIT_REQUEST_ERROR | 일일 제한 초과 |
| **31** | UNREGISTERED_IP_ERROR | 등록되지 않은 IP |

---

## 5. 응답 필드 상세

### 5.1 주요 응답 필드

| 필드명 | 타입 | 설명 | 예시 값 | 비고 |
|--------|------|------|---------|------|
| **announceTime** | String | 발표시각 | `202601311800` | YYYYMMDDHHMM 형식 |
| **numEf** | Integer | 예보 시점 | `0`, `1`, `2`, ... | 아래 표 참조 |
| **wf** | String | 날씨 설명 | `맑음`, `구름많음`, `흐림` | 한글 텍스트 |
| **wfCd** | String | 날씨 코드 | `DB01`, `DB03`, `DB04` | 코드 매핑 필요 |
| **wav** | String | 파고 등급 | `1`, `2`, `3`, `4`, `5` | 파고 등급 (아래 표) |
| **wd1** | String | 풍향 1 | `북서`, `북`, `남동` | 16방위 한글 |
| **wd2** | String | 풍향 2 | `북`, `북동` | 변화될 풍향 |
| **ws** | String | 풍속 | `3`, `5`, `10` | m/s 단위 |

### 5.2 numEf (예보 시점) 매핑

`numEf`는 예보 시점을 나타내는 인덱스입니다.

| numEf | 시점명 | 설명 | 시간대 (추정) |
|-------|--------|------|--------------|
| **0** | 오늘 밤 | 발표일 저녁~밤 | 18:00 ~ 익일 06:00 |
| **1** | 내일 아침 | D+1일 아침 | 06:00 ~ 12:00 |
| **2** | 내일 낮 | D+1일 낮 | 12:00 ~ 18:00 |
| **3** | 내일 밤 | D+1일 저녁~밤 | 18:00 ~ 익일 06:00 |
| **4** | 모레 아침 | D+2일 아침 | 06:00 ~ 12:00 |
| **5** | 모레 낮 | D+2일 낮 | 12:00 ~ 18:00 |
| **6** | 모레 밤 | D+2일 저녁~밤 | 18:00 ~ 익일 06:00 |
| **7** | 글피 아침 | D+3일 아침 | 06:00 ~ 12:00 |
| **8** | 글피 낮 | D+3일 낮 | 12:00 ~ 18:00 |

> **참고**: 근해예보는 주로 D+2까지 제공되므로, numEf는 0~6 범위를 주로 사용합니다.

### 5.3 wfCd (날씨 코드) 매핑

| 코드 | 날씨 | SKY 값 | 구름량 (%) |
|------|------|--------|-----------|
| **DB01** | 맑음 | 1 | ~20% |
| **DB03** | 구름많음 | 3 | 40~70% |
| **DB04** | 흐림 | 4 | 80~100% |

> 육상예보의 SKY 코드와 동일한 체계를 사용합니다.

### 5.4 wav (파고 등급) 매핑

파고 등급은 1~5단계로 구분되며, 실제 파고 범위는 다음과 같습니다.

| 등급 | 파고 범위 | 대표값 (m) | 설명 |
|------|----------|-----------|------|
| **1** | 0 ~ 0.5m | 0.25m | 매우 낮음 |
| **2** | 0.5 ~ 1.0m | 0.75m | 낮음 |
| **3** | 1.0 ~ 2.0m | 1.5m | 보통 |
| **4** | 2.0 ~ 3.0m | 2.5m | 높음 |
| **5** | 3.0m 이상 | 3.5m | 매우 높음 |

> **주의**: 실제 파고는 범위이므로, 점수 산출 시 대표값(중간값)을 사용하는 것을 권장합니다.

### 5.5 wd1, wd2 (풍향)

풍향은 16방위 한글로 제공됩니다.

```
북, 북북동, 북동, 동북동,
동, 동남동, 남동, 남남동,
남, 남남서, 남서, 서남서,
서, 서북서, 북서, 북북서
```

- **wd1**: 현재/초기 풍향
- **wd2**: 변화될 풍향 (예: "북서 후 북")

---

## 6. 발표 시각 및 예보 기간

### 6.1 근해예보 발표 시각

기상청 근해예보는 **1일 2회** 발표됩니다 (추정):

| 발표 시각 (KST) | 예보 대상 기간 |
|----------------|--------------|
| **06:00** | 오늘 낮 ~ D+2일 낮 |
| **18:00** | 오늘 밤 ~ D+2일 밤 |

> **주의**: 정확한 발표 시각은 기상청 공식 문서 또는 실제 API 응답의 `announceTime` 필드로 확인해야 합니다.

### 6.2 중기해상예보 발표 시각

중기해상예보는 **1일 2회** 발표됩니다:

| 발표 시각 (KST) | 예보 대상 기간 |
|----------------|--------------|
| **06:00** | D+3 ~ D+10 (8일간) |
| **18:00** | D+3 ~ D+10 (8일간) |

### 6.3 데이터 갱신 주기

- **근해예보**: 12시간 간격 (1일 2회)
- **중기해상예보**: 12시간 간격 (1일 2회)
- **해상특보**: 실시간 (발효 시 즉시)

---

## 7. 사용 예시

### 7.1 Python 코드 예시

```python
import aiohttp
import asyncio
from datetime import datetime

async def fetch_marine_forecast(marine_zone_code: str, api_source: str = "apihub.kma.go.kr"):
    """
    기상청 해상예보 데이터 수집

    Args:
        marine_zone_code: 해상예보구역 코드 (예: "12A10000")
        api_source: "data.go.kr" 또는 "apihub.kma.go.kr"
    """
    if api_source == "data.go.kr":
        url = "http://apis.data.go.kr/1360000/VilageFcstMsgService/getWthrMarFcst"
        params = {
            "serviceKey": "YOUR_SERVICE_KEY",
            "pageNo": 1,
            "numOfRows": 20,
            "dataType": "JSON",
            "regId": marine_zone_code
        }
    else:  # apihub.kma.go.kr
        url = "https://apihub.kma.go.kr/api/typ02/openApi/VilageFcstMsgService/getWthrMarFcst"
        params = {
            "authKey": "YOUR_AUTH_KEY",
            "pageNo": 1,
            "numOfRows": 20,
            "dataType": "JSON",
            "regId": marine_zone_code
        }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return parse_marine_data(data, marine_zone_code)
            else:
                raise Exception(f"API request failed: {response.status}")

def parse_marine_data(response: dict, zone_code: str) -> dict:
    """
    해상예보 응답 파싱
    """
    header = response.get("response", {}).get("header", {})
    result_code = header.get("resultCode")

    if result_code != "00":
        raise Exception(f"API error: {header.get('resultMsg')} (code: {result_code})")

    items = response.get("response", {}).get("body", {}).get("items", {}).get("item", [])

    if isinstance(items, dict):
        items = [items]

    forecast_data = []
    for item in items:
        num_ef = item.get("numEf", 0)

        # numEf를 datetime으로 변환
        forecast_dt = get_forecast_datetime(num_ef)

        # 파고 등급 → 수치 변환
        wav_str = item.get("wav", "")
        wave_height = None
        if wav_str:
            wav_level = int(wav_str)
            wave_height_mapping = {1: 0.25, 2: 0.75, 3: 1.5, 4: 2.5, 5: 3.5}
            wave_height = wave_height_mapping.get(wav_level)

        # 풍속 파싱
        wind_speed = float(item.get("ws", 0)) if item.get("ws") else None

        forecast_data.append({
            "datetime": forecast_dt.isoformat(),
            "period": num_ef,
            "period_name": get_period_name(num_ef),
            "weather": item.get("wf"),
            "weather_code": item.get("wfCd"),
            "wave_height": wave_height,
            "wave_height_level": int(wav_str) if wav_str else None,
            "wind_dir1": item.get("wd1"),
            "wind_dir2": item.get("wd2"),
            "wind_speed": wind_speed
        })

    return {
        "source": "kma_marine",
        "marine_zone_code": zone_code,
        "collected_at": datetime.now().isoformat(),
        "announce_time": items[0].get("announceTime") if items else None,
        "forecast": forecast_data
    }

def get_forecast_datetime(num_ef: int) -> datetime:
    """numEf를 datetime으로 변환"""
    base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    if num_ef == 0:
        # 오늘 밤
        return base_date.replace(hour=21)

    day_offset = num_ef // 2
    is_morning = (num_ef % 2) == 1

    forecast_dt = base_date + timedelta(days=day_offset)
    if is_morning:
        return forecast_dt.replace(hour=6)
    else:
        return forecast_dt.replace(hour=15)

def get_period_name(num_ef: int) -> str:
    """numEf를 한글 시점명으로 변환"""
    period_names = [
        "오늘 밤", "내일 아침", "내일 낮", "내일 밤",
        "모레 아침", "모레 낮", "모레 밤",
        "글피 아침", "글피 낮"
    ]
    if 0 <= num_ef < len(period_names):
        return period_names[num_ef]
    return f"예보 {num_ef}"

# 사용 예시
async def main():
    # 서해북부 해상예보 조회
    result = await fetch_marine_forecast("12A10000", api_source="apihub.kma.go.kr")

    print(f"발표시각: {result['announce_time']}")
    print(f"구역코드: {result['marine_zone_code']}")
    print(f"\n예보 데이터:")
    for fc in result['forecast']:
        print(f"  {fc['period_name']}: {fc['weather']}, 파고 {fc['wave_height']}m, 풍속 {fc['wind_speed']}m/s")

if __name__ == "__main__":
    asyncio.run(main())
```

### 7.2 응답 예시 (파싱 후)

```json
{
  "source": "kma_marine",
  "marine_zone_code": "12A10000",
  "collected_at": "2026-01-31T15:30:00",
  "announce_time": "202601311800",
  "forecast": [
    {
      "datetime": "2026-01-31T21:00:00",
      "period": 0,
      "period_name": "오늘 밤",
      "weather": "맑음",
      "weather_code": "DB01",
      "wave_height": 0.75,
      "wave_height_level": 2,
      "wind_dir1": "북서",
      "wind_dir2": "북",
      "wind_speed": 3.0
    },
    {
      "datetime": "2026-02-01T06:00:00",
      "period": 1,
      "period_name": "내일 아침",
      "weather": "구름많음",
      "weather_code": "DB03",
      "wave_height": 1.5,
      "wave_height_level": 3,
      "wind_dir1": "북",
      "wind_dir2": "북동",
      "wind_speed": 5.0
    }
  ]
}
```

---

## 8. 참고 자료

### 8.1 공식 문서

- [기상청 API 허브](https://apihub.kma.go.kr) - 기상청 공식 API 플랫폼
- [공공데이터포털 - 기상청 동네예보 통보문 조회서비스](https://www.data.go.kr/data/15058629/openapi.do) - 공공데이터포털 API
- [기상청 날씨누리 - 바다예보](https://www.weather.go.kr/w/ocean/forecast/daily-forecast.do) - 해상예보 웹 페이지
- [기상청 중기예보 조회서비스](https://www.data.go.kr/data/15059468/openapi.do) - 중기해상예보 API

### 8.2 관련 문서 (프로젝트 내)

- `collectors/kma_marine_forecast.py` - 해상예보 Collector 구현체
- `data/marine_zones.py` - 해상예보구역 코드 정의
- `docs/KMA_API_INTEGRATION.md` - 기상청 API 연동 가이드
- `spec.md` - 프로젝트 기술 명세서

### 8.3 주요 발견 사항

1. **구역 코드 제한**: API에서는 대구역 9개 코드만 사용 가능하며, 세분화 구역(앞바다/먼바다)에 대한 별도 코드는 확인되지 않음
2. **발표 시각 추정**: 공식 문서에서 명시되지 않았으나, 중기예보와 동일하게 06:00, 18:00로 추정됨
3. **numEf 매핑**: numEf 필드는 오늘 밤(0)부터 시작하여 반일 단위로 증가하는 인덱스
4. **파고 등급**: 1~5 등급으로 제공되며, 실제 파고 범위를 대표값으로 변환 필요
5. **API 소스 선택**: 공공데이터포털은 안정적이나 승인 필요, API 허브는 즉시 발급 가능

### 8.4 미해결 사항

- ⚠ **세분화 구역 코드**: 앞바다/먼바다 세부 구역별 API 코드는 확인되지 않음
- ⚠ **정확한 발표 시각**: 공식 문서에서 명시되지 않음 (실제 API 응답으로 확인 필요)
- ⚠ **예보 기간**: D+2까지인지 D+3까지인지 명확하지 않음 (실제 응답으로 확인 필요)

---

## 9. 결론 및 권장사항

### 9.1 API 선택 가이드

| 사용 사례 | 권장 API |
|----------|---------|
| 안정적인 서비스 운영 | 공공데이터포털 (data.go.kr) |
| 빠른 프로토타입 개발 | 기상청 API 허브 (apihub.kma.go.kr) |
| 다양한 기상 데이터 통합 | 기상청 API 허브 |

### 9.2 구현 체크리스트

- [ ] API 키 발급 (공공데이터포털 또는 API 허브)
- [ ] 9개 대구역 코드 확인 및 매핑
- [ ] numEf → datetime 변환 로직 구현
- [ ] 파고 등급 → 수치(m) 변환 구현
- [ ] 날씨 코드 → SKY 값 매핑
- [ ] 에러 핸들링 (resultCode 체크)
- [ ] 데이터 캐싱 (12시간 주기 갱신)
- [ ] 실제 API 응답으로 발표 시각 검증

### 9.3 향후 개선 방향

1. **세분화 구역 지원**: 웹 스크래핑 또는 추가 API 조사
2. **실시간 특보 연동**: 풍랑특보 API와 결합
3. **파고 정확도 향상**: 바다누리 실측 데이터와 비교 검증
4. **발표 시각 자동 감지**: API 응답 모니터링으로 정확한 갱신 시각 파악

---

**WORKER_COMPLETE**: 기상청 해상예보 API 연구 완료
