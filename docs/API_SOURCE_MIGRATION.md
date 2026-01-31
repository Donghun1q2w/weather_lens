# 기상청 API 소스 마이그레이션 가이드

## 변경 사항 요약

Weather Lens의 기상청 API 연동이 두 가지 API 소스를 지원하도록 업데이트되었습니다.

### 수정된 파일

1. **collectors/kma_forecast.py**
   - `api_source` 파라미터 추가 (data.go.kr / apihub.kma.go.kr)
   - `_collect_from_data_go_kr()` 메서드 추가
   - `_collect_from_apihub()` 메서드 추가
   - 응답에 `api_source` 필드 추가

2. **config/settings.py**
   - `KMA_API_SOURCE` 설정 추가

3. **scripts/test_kma_api.py**
   - API 소스 선택 지원
   - 커맨드 라인 인자 처리

4. **.env.example**
   - `KMA_API_SOURCE` 환경 변수 문서화

## 사용자 API 키 정보

사용자가 제공한 API 키: `hdqgJkruQ4CaoCZK7pOAug`

이 키는 **기상청 API 허브 (apihub.kma.go.kr)** 에서 발급받은 키입니다.

### 설정 방법

`.env` 파일에 다음과 같이 설정하세요:

```bash
# 기상청 API 허브 사용
KMA_API_KEY=hdqgJkruQ4CaoCZK7pOAug
KMA_API_SOURCE=apihub.kma.go.kr
```

## 테스트 방법

### 1. 기상청 API 허브 테스트

```bash
# .env 파일 설정
echo "KMA_API_KEY=hdqgJkruQ4CaoCZK7pOAug" >> .env
echo "KMA_API_SOURCE=apihub.kma.go.kr" >> .env

# 테스트 실행
python scripts/test_kma_api.py apihub.kma.go.kr
```

### 2. 공공데이터포털 테스트 (추후)

공공데이터포털에서 별도 키를 발급받은 경우:

```bash
# .env 파일 설정
KMA_API_KEY=your_data_go_kr_key
KMA_API_SOURCE=data.go.kr

# 테스트 실행
python scripts/test_kma_api.py data.go.kr
```

## 코드 예시

### 기본 사용 (환경 변수 기반)

```python
from collectors import KMAForecastCollector
from config.settings import KMA_API_KEY, KMA_API_SOURCE

async with KMAForecastCollector(KMA_API_KEY, api_source=KMA_API_SOURCE) as collector:
    result = await collector.collect(region_code="1168010100")
```

### API 소스 명시적 지정

```python
# 기상청 API 허브 사용
async with KMAForecastCollector(
    api_key="hdqgJkruQ4CaoCZK7pOAug",
    api_source="apihub.kma.go.kr"
) as collector:
    result = await collector.collect(region_code="1168010100")

# 공공데이터포털 사용 (격자 좌표 필수)
async with KMAForecastCollector(
    api_key="your_data_go_kr_key",
    api_source="data.go.kr"
) as collector:
    result = await collector.collect(
        region_code="1168010100",
        nx=61,
        ny=126
    )
```

## 주의사항

### 기상청 API 허브 (apihub.kma.go.kr)

1. **지역명 기반 조회**: 격자 좌표(nx, ny) 대신 지역명을 사용합니다.
2. **매핑 필요**: 현재 region_code → region_name 매핑은 임시 구현입니다.
   - 서울: `region_code[:2] == "11"` → `"서울"`
   - 부산: `region_code[:2] == "26"` → `"부산"`
   - 등등...

3. **파싱 로직 미완성**: API 허브의 실제 응답 구조를 확인한 후 `_parse_apihub_data()` 메서드를 완성해야 합니다.

### 공공데이터포털 (data.go.kr)

1. **격자 좌표 필수**: nx, ny 파라미터를 반드시 제공해야 합니다.
2. **좌표 변환 필요**: 위경도를 격자 좌표로 변환하는 로직이 필요합니다.

## 다음 단계

### 1. API 허브 응답 구조 확인

실제 API를 호출하여 응답 구조를 확인하세요:

```bash
curl "https://apihub.kma.go.kr/api/typ01/url/fct_afs_dl.php?reg=서울&tmfc=latest&authKey=hdqgJkruQ4CaoCZK7pOAug"
```

응답 예시를 확인한 후 `_parse_apihub_data()` 메서드를 완성하세요.

### 2. region_code → region_name 매핑 테이블 구축

데이터베이스 또는 JSON 파일로 정확한 매핑 테이블을 만드세요:

```json
{
  "1168010100": {
    "sido": "서울특별시",
    "sigungu": "강남구",
    "emd": "역삼동",
    "api_hub_region": "서울"
  }
}
```

### 3. 두 API 소스 응답 병합

spec.md의 3.1.2 평균값 산출 로직을 구현하세요:

```python
final_value = (kma_value * 0.6) + (openmeteo_value * 0.4)
```

## 문제 해결

### 테스트 실패 시

1. **API 키 확인**: 올바른 API 소스의 키인지 확인
2. **환경 변수 확인**: `.env` 파일이 올바르게 로드되는지 확인
3. **네트워크 확인**: API 엔드포인트 접근 가능 여부 확인
4. **로그 확인**: 상세한 에러 메시지 확인

### API 허브 파싱 오류 시

현재 `_parse_apihub_data()`는 플레이스홀더 구현입니다. 실제 응답 구조에 맞게 수정이 필요합니다.

## 참고 문서

- [KMA_API_INTEGRATION.md](./KMA_API_INTEGRATION.md) - 전체 가이드
- [spec.md](../spec.md) - 프로젝트 기술 명세서
