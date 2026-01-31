# 기상청 API 연동 가이드

## 개요

Weather Lens는 기상청 단기예보 데이터를 수집하기 위해 두 가지 API 소스를 지원합니다:

1. **data.go.kr** (공공데이터포털) - 기본값
2. **apihub.kma.go.kr** (기상청 API 허브)

## API 소스 비교

| 항목 | data.go.kr | apihub.kma.go.kr |
|------|------------|------------------|
| **API 이름** | 기상청_단기예보 ((구)_동네예보) 조회서비스 | 단기예보 서비스 |
| **엔드포인트** | `apis.data.go.kr/1360000/VilageFcstInfoService/getVilageFcst` | `apihub.kma.go.kr/api/typ01/url/fct_afs_dl.php` |
| **인증 방식** | `serviceKey` 파라미터 | `authKey` 파라미터 |
| **위치 지정** | 격자 좌표 (nx, ny) | 지역명 (reg) |
| **응답 형식** | JSON (표준화) | JSON/XML |
| **사용 권장** | 격자 좌표 기반 정밀 조회 | 지역명 기반 간편 조회 |

## 설정 방법

### 1. 환경 변수 설정

`.env` 파일에 다음 설정을 추가합니다:

```bash
# 기상청 API 키
KMA_API_KEY=your_api_key_here

# API 소스 선택 (기본값: data.go.kr)
KMA_API_SOURCE=data.go.kr  # 또는 apihub.kma.go.kr
```

### 2. 코드에서 사용

```python
from collectors import KMAForecastCollector

# data.go.kr 사용 (격자 좌표 필요)
async with KMAForecastCollector(api_key, api_source="data.go.kr") as collector:
    result = await collector.collect(
        region_code="1168010100",
        nx=61,   # 격자 X 좌표
        ny=126   # 격자 Y 좌표
    )

# apihub.kma.go.kr 사용 (지역명 기반)
async with KMAForecastCollector(api_key, api_source="apihub.kma.go.kr") as collector:
    result = await collector.collect(
        region_code="1168010100"  # 격자 좌표 불필요
    )
```

## API 키 발급

### data.go.kr

1. [공공데이터포털](https://data.go.kr) 접속
2. 회원가입 및 로그인
3. "기상청_단기예보 ((구)_동네예보) 조회서비스" 검색
4. 활용신청 (승인까지 1-2일 소요)
5. 마이페이지 > 인증키 발급현황에서 키 확인

### apihub.kma.go.kr

1. [기상청 API 허브](https://apihub.kma.go.kr) 접속
2. 회원가입 및 로그인
3. 마이페이지 > API KEY 발급
4. 단기예보 서비스 신청
5. 발급된 키 확인

**주의**: 각 API의 키는 서로 호환되지 않습니다. 각 API 소스에 맞는 키를 사용해야 합니다.

## 테스트

### 기본 테스트 (환경 변수 사용)

```bash
python scripts/test_kma_api.py
```

### API 소스 지정 테스트

```bash
# data.go.kr 테스트
python scripts/test_kma_api.py data.go.kr

# apihub.kma.go.kr 테스트
python scripts/test_kma_api.py apihub.kma.go.kr
```

## 응답 데이터 구조

두 API 소스 모두 동일한 형식으로 데이터를 반환합니다:

```json
{
  "source": "kma",
  "api_source": "data.go.kr",  // 또는 "apihub.kma.go.kr"
  "region_code": "1168010100",
  "collected_at": "2026-01-30T12:00:00",
  "base_date": "20260130",
  "base_time": "1100",
  "forecast": [
    {
      "datetime": "2026-01-30T12:00:00",
      "temp": -3.0,              // 기온 (℃)
      "humidity": 45,            // 습도 (%)
      "wind_speed": 2.5,         // 풍속 (m/s)
      "rain_prob": 10,           // 강수확률 (%)
      "precipitation": 0.0,      // 강수량 (mm)
      "sky": 1,                  // 하늘상태 (1=맑음, 3=구름많음, 4=흐림)
      "cloud_cover": 20          // 구름량 (%)
    },
    // ... 추가 시간대
  ]
}
```

## 주의사항

### data.go.kr

- **격자 좌표 필수**: nx, ny 파라미터가 반드시 필요합니다.
- **좌표 변환**: 위경도 좌표를 격자 좌표로 변환해야 합니다.
- **발표 시각**: 하루 8번 발표 (02:10, 05:10, 08:10, 11:10, 14:10, 17:10, 20:10, 23:10)

### apihub.kma.go.kr

- **지역명 기반**: 격자 좌표 대신 지역명(reg)을 사용합니다.
- **매핑 필요**: region_code → region_name 매핑 테이블이 필요합니다.
- **응답 구조**: 응답 구조가 data.go.kr과 다를 수 있으며, 실제 응답 확인 후 파싱 로직 조정이 필요합니다.

## 문제 해결

### API 호출 실패

1. **API 키 확인**: 올바른 API 소스의 키를 사용하고 있는지 확인
2. **키 활성화**: 신청 후 1-2일 소요, 활성화 상태 확인
3. **호출 한도**: 일일 호출 한도 초과 여부 확인
4. **네트워크**: 방화벽 또는 프록시 설정 확인

### apihub.kma.go.kr 파싱 오류

현재 apihub.kma.go.kr의 응답 구조는 실제 API 응답을 받아본 후 구현해야 합니다.
파싱 오류가 발생하면:

1. 실제 API 응답 구조 확인
2. `collectors/kma_forecast.py`의 `_parse_apihub_data` 메서드 수정
3. 응답 예시를 이슈로 제보해주시면 개선하겠습니다

## 향후 개선 사항

- [ ] region_code → region_name 매핑 테이블 구축
- [ ] apihub.kma.go.kr 응답 파싱 로직 완성
- [ ] 위경도 → 격자 좌표 변환 유틸리티
- [ ] API 소스별 에러 핸들링 개선
- [ ] 두 API 소스 응답 병합 및 평균값 산출

## 참고 자료

- [공공데이터포털 기상청API](https://data.go.kr/data/15084084/openapi.do)
- [기상청 API 허브](https://apihub.kma.go.kr)
- [기상청 격자 좌표 안내](https://www.weather.go.kr/w/obs-climate/land/city-obs.do)
