# 빠른 시작: 기상청 API 허브 테스트

## 즉시 테스트하기

사용자의 API 키로 기상청 API 허브를 바로 테스트할 수 있습니다.

### 1단계: 환경 변수 설정

`.env` 파일을 열고 다음을 추가하거나 수정하세요:

```bash
KMA_API_KEY=hdqgJkruQ4CaoCZK7pOAug
KMA_API_SOURCE=apihub.kma.go.kr
```

또는 터미널에서 직접 설정:

```bash
export KMA_API_KEY=hdqgJkruQ4CaoCZK7pOAug
export KMA_API_SOURCE=apihub.kma.go.kr
```

### 2단계: 테스트 실행

```bash
# 프로젝트 루트 디렉토리에서
python scripts/test_kma_api.py apihub.kma.go.kr
```

### 예상 출력

성공 시:
```
============================================================
기상청 단기예보 API 테스트
============================================================
✅ API 키 확인: hdqgJkruQ4...
✅ API 소스: apihub.kma.go.kr

📍 테스트 지역: 서울특별시 강남구 역삼동
   지역명 기반 조회 (격자 좌표 불필요)

⏳ apihub.kma.go.kr API 호출 중...

✅ API 호출 성공!
------------------------------------------------------------
🌐 API 소스: apihub.kma.go.kr
🕐 수집 시각: 2026-01-30T12:00:00
...
```

실패 시:
```
❌ API 오류: ...
가능한 원인:
  1. API 키가 올바르지 않음
  2. API 키 활성화가 안 됨
  3. 일일 호출 한도 초과
  4. API 허브의 응답 구조가 예상과 다를 수 있음
```

## API 직접 테스트 (curl)

Python 스크립트 없이 API를 직접 테스트하려면:

```bash
# 서울 지역 최신 예보 조회
curl "https://apihub.kma.go.kr/api/typ01/url/fct_afs_dl.php?reg=서울&tmfc=latest&authKey=hdqgJkruQ4CaoCZK7pOAug"

# 부산 지역 최신 예보 조회
curl "https://apihub.kma.go.kr/api/typ01/url/fct_afs_dl.php?reg=부산&tmfc=latest&authKey=hdqgJkruQ4CaoCZK7pOAug"
```

응답을 확인하여 API가 정상 작동하는지 검증하세요.

## 다음 단계

1. **응답 구조 확인**: curl로 받은 실제 응답 JSON 구조를 확인하세요.
2. **파싱 로직 완성**: `collectors/kma_forecast.py`의 `_parse_apihub_data()` 메서드를 실제 응답에 맞게 수정하세요.
3. **매핑 테이블 구축**: region_code → region_name 정확한 매핑을 데이터베이스나 JSON 파일로 만드세요.

## 문제가 있나요?

- **API 키 오류**: 기상청 API 허브에서 키가 활성화되었는지 확인하세요.
- **파싱 오류**: 실제 API 응답 예시를 GitHub 이슈로 제보해주세요.
- **네트워크 오류**: 방화벽이나 프록시 설정을 확인하세요.

## 상세 문서

- [docs/KMA_API_INTEGRATION.md](docs/KMA_API_INTEGRATION.md) - 전체 통합 가이드
- [docs/API_SOURCE_MIGRATION.md](docs/API_SOURCE_MIGRATION.md) - 마이그레이션 가이드
