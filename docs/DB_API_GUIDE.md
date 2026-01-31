# Weather Lens - 데이터베이스 및 API 사용 가이드

> **대상 독자**: 데이터베이스를 처음 사용하는 일반 사용자
> **작성일**: 2026-01-31
> **버전**: 1.0

---

## 목차

1. [시작하기 전에](#1-시작하기-전에)
2. [데이터베이스 구조 이해하기](#2-데이터베이스-구조-이해하기)
3. [데이터 조회 방법](#3-데이터-조회-방법)
4. [API 사용하기](#4-api-사용하기)
5. [자주 사용하는 쿼리 예제](#5-자주-사용하는-쿼리-예제)
6. [문제 해결](#6-문제-해결)

---

## 1. 시작하기 전에

### 1.1 필요한 도구 설치

#### macOS에서 SQLite 사용하기
macOS에는 SQLite가 기본 설치되어 있습니다. 터미널을 열고 바로 사용할 수 있습니다.

```bash
# 터미널 열기: Command + Space → "터미널" 입력 → Enter
```

#### 데이터베이스 파일 위치
프로젝트의 데이터베이스 파일은 다음 위치에 있습니다:
- **메인 DB**: `data/regions.db` (지역, 출사지, 테마 등)
- **해양 DB**: `data/ocean_mapping.db` (해양 관측소 정보)

### 1.2 데이터베이스 접속하기

```bash
# 프로젝트 폴더로 이동
cd /Users/donghun/Documents/git_repository/weather_lens

# 메인 데이터베이스 열기
sqlite3 data/regions.db
```

접속 성공 시 `sqlite>` 프롬프트가 나타납니다.

```
SQLite version 3.x.x
Enter ".help" for usage hints.
sqlite>
```

**종료하기**: `.quit` 입력 후 Enter

---

## 2. 데이터베이스 구조 이해하기

### 2.1 테이블 목록

| 테이블명 | 설명 | 레코드 수 |
|---------|------|----------|
| `regions` | 전국 읍/면/동 지역 정보 | 3,616개 |
| `photo_spots` | 추천 출사지 목록 | ~50개 |
| `themes` | 촬영 테마 (일출, 일몰 등) | 16개 |
| `photo_spot_themes` | 출사지-테마 연결 | - |
| `marine_zones` | 해양예보구역 | 9개 |
| `region_marine_zone` | 지역-해양구역 연결 | - |
| `beaches` | 전국 해수욕장 정보 | 420개 |
| `user_collections` | 사용자 컬렉션 | - |
| `user_collection_spots` | 컬렉션에 저장된 스팟 | - |

### 2.2 주요 테이블 상세

#### regions (지역 정보)
전국의 모든 읍/면/동 정보를 담고 있습니다.

| 컬럼명 | 설명 | 예시 |
|-------|------|------|
| `code` | 10자리 지역 코드 (기본키) | "1168010100" |
| `name` | 전체 지역명 | "서울특별시 강남구 역삼동" |
| `sido` | 시/도 | "서울특별시" |
| `sigungu` | 시/군/구 | "강남구" |
| `emd` | 읍/면/동 | "역삼동" |
| `lat` | 위도 | 37.5000 |
| `lon` | 경도 | 127.0364 |
| `nx`, `ny` | 기상청 격자 좌표 | 61, 126 |
| `elevation` | 해발고도 (미터) | 36.0 |
| `is_coastal` | 해안가 여부 (0 또는 1) | 0 |
| `is_east_coast` | 동해안 여부 | 0 |
| `is_west_coast` | 서해안 여부 | 0 |
| `is_south_coast` | 남해안 여부 | 0 |

#### themes (촬영 테마)
16가지 풍경사진 촬영 테마입니다.

| ID | 테마명 | 설명 |
|----|--------|------|
| 1 | 일출 | 동해안의 수평선 일출 촬영 |
| 2 | 일출 오메가 | 태양이 수평선에 접하는 순간의 오메가 형태 |
| 3 | 일몰 | 서해안 일몰 촬영 |
| 4 | 일몰 오메가 | 수평선 위 일몰 오메가 |
| 5 | 은하수 | 은하수 촬영 (3~10월 무월광 시간대) |
| 6 | 야광충 | 바다의 야광충 (여름철) |
| 7 | 바다 장노출 | 바다 장노출 사진 |
| 8 | 운해 | 산지 운해 촬영 |
| 9 | 별궤적 | 별 일주운동 궤적 촬영 |
| 10 | 야경 | 도시 야경 촬영 |
| 11 | 안개 | 안개 낀 풍경 촬영 |
| 12 | 반영 | 수면 반영 촬영 |
| 13 | 골든아워 | 해돋이/해질녘 황금빛 시간대 |
| 14 | 블루아워 | 일출 전/일몰 후 푸른 시간대 |
| 15 | 상고대 | 겨울철 나뭇가지의 서리꽃 |
| 16 | 월출 | 달 촬영 (보름달 전후) |

#### marine_zones (해양예보구역)
기상청 해양예보구역 정보입니다.

| 구역 코드 | 한글명 | 영문명 |
|----------|--------|--------|
| 12A10000 | 서해북부 | West Sea North |
| 12A20000 | 서해중부 | West Sea Central |
| 12A30000 | 서해남부 | West Sea South |
| 12B10000 | 남해서부 | South Sea West |
| 12B20000 | 남해동부 | South Sea East |
| 12C10000 | 동해남부 | East Sea South |
| 12C20000 | 동해중부 | East Sea Central |
| 12C30000 | 동해북부 | East Sea North |
| 12D10000 | 제주도 | Jeju Island |

#### beaches (해수욕장)
전국 420개 해수욕장 정보입니다.

| 컬럼명 | 설명 | 예시 |
|-------|------|------|
| `beach_num` | 해수욕장 고유번호 (기본키) | 1 |
| `name` | 해수욕장명 | "경포해수욕장" |
| `nx` | 기상청 격자 X좌표 | 92 |
| `ny` | 기상청 격자 Y좌표 | 131 |
| `lon` | 경도 | 128.8962 |
| `lat` | 위도 | 37.8055 |
| `region_code` | 연결된 읍면동 코드 | "4215012500" |
| `marine_zone_code` | 해양예보구역 코드 | "12C30000" |

---

## 3. 데이터 조회 방법

### 3.1 기본 SQLite 명령어

```sql
-- 테이블 목록 보기
.tables

-- 테이블 구조 보기
.schema regions

-- 쿼리 결과를 보기 좋게 출력
.headers on
.mode column

-- 종료
.quit
```

### 3.2 기본 SELECT 문법

```sql
-- 모든 데이터 조회
SELECT * FROM 테이블명;

-- 특정 컬럼만 조회
SELECT 컬럼1, 컬럼2 FROM 테이블명;

-- 조건에 맞는 데이터 조회
SELECT * FROM 테이블명 WHERE 조건;

-- 정렬해서 조회
SELECT * FROM 테이블명 ORDER BY 컬럼명;

-- 개수 제한
SELECT * FROM 테이블명 LIMIT 10;
```

---

## 4. API 사용하기

### 4.1 API 서버 시작하기

```bash
# 프로젝트 폴더에서
cd /Users/donghun/Documents/git_repository/weather_lens

# 서버 시작
python main.py
```

서버가 시작되면 `http://localhost:8000`에서 접속 가능합니다.

### 4.2 주요 API 엔드포인트

#### 헬스체크
```
GET /health
```
서버 상태를 확인합니다.

#### 테마 목록 조회
```
GET /api/v1/themes
```

**응답 예시:**
```json
{
  "themes": [
    {"id": 1, "name": "일출", "description": "동해안의 수평선 일출 촬영"},
    {"id": 2, "name": "일출 오메가", "description": "태양이 수평선에 접하는 순간"}
  ]
}
```

#### 테마별 TOP 지역 조회
```
GET /api/v1/themes/{theme_id}/top?limit=10
```

**예시:** 일출 테마(ID:1) TOP 10 지역
```
GET /api/v1/themes/1/top?limit=10
```

#### 지역 목록 조회
```
GET /api/v1/regions?sido=서울특별시&limit=50
```

**파라미터:**
- `sido`: 시/도 필터 (선택)
- `sigungu`: 시/군/구 필터 (선택)
- `is_coastal`: 해안가 여부 (0 또는 1) (선택)
- `limit`: 반환 개수 (기본: 100)
- `offset`: 시작 위치 (기본: 0)

#### 특정 지역 상세 정보
```
GET /api/v1/regions/{region_code}
```

**예시:** 서울시 종로구 청운효자동
```
GET /api/v1/regions/1111000001
```

#### 출사지 목록 조회
```
GET /api/v1/photo-spots?tags=일출&limit=20
```

#### 해양 예보구역 조회
```
GET /api/v1/marine/zones
```

#### 특정 지역의 해양 예보
```
GET /api/v1/marine/{region_code}/forecast
```

#### 천문 정보 조회
```
GET /api/v1/astronomy?region_code=1168010100&date=2026-01-31
```

**응답 예시:**
```json
{
  "region_code": "1168010100",
  "date": "2026-01-31",
  "sunrise": "07:35",
  "sunset": "17:52",
  "moon_age": 12.5,
  "moon_phase": "상현달"
}
```

### 4.3 curl로 API 테스트하기

터미널에서 curl 명령어로 API를 테스트할 수 있습니다.

```bash
# 서버 상태 확인
curl http://localhost:8000/health

# 테마 목록 조회
curl http://localhost:8000/api/v1/themes

# 경기도 지역 목록 조회
curl "http://localhost:8000/api/v1/regions?sido=경기도&limit=10"

# 출사지 목록 조회
curl http://localhost:8000/api/v1/photo-spots
```

### 4.4 웹 브라우저에서 API 문서 보기

서버 실행 중 다음 주소에서 자동 생성된 API 문서를 볼 수 있습니다:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## 5. 자주 사용하는 쿼리 예제

### 5.1 지역 검색

#### 특정 시/도의 모든 지역 조회
```sql
-- 서울특별시의 모든 동 조회
SELECT code, name, emd, lat, lon
FROM regions
WHERE sido = '서울특별시'
ORDER BY sigungu, emd;
```

#### 해안가 지역만 조회
```sql
-- 모든 해안가 지역
SELECT name, sido, lat, lon,
       CASE
           WHEN is_east_coast = 1 THEN '동해안'
           WHEN is_west_coast = 1 THEN '서해안'
           WHEN is_south_coast = 1 THEN '남해안'
       END as coast_type
FROM regions
WHERE is_coastal = 1
ORDER BY sido;
```

#### 동해안 일출 명소 찾기
```sql
-- 동해안 해안가 지역 (일출 촬영 적합)
SELECT name, sido, sigungu, lat, lon
FROM regions
WHERE is_east_coast = 1
ORDER BY lat DESC;  -- 북쪽부터 정렬
```

#### 서해안 일몰 명소 찾기
```sql
-- 서해안 해안가 지역 (일몰 촬영 적합)
SELECT name, sido, sigungu, lat, lon
FROM regions
WHERE is_west_coast = 1
ORDER BY lat DESC;
```

#### 고도가 높은 지역 (운해 촬영 적합)
```sql
-- 해발 500m 이상 지역
SELECT name, sido, elevation
FROM regions
WHERE elevation >= 500
ORDER BY elevation DESC
LIMIT 20;
```

### 5.2 시/도별 통계

#### 시/도별 지역 수
```sql
SELECT sido, COUNT(*) as region_count
FROM regions
GROUP BY sido
ORDER BY region_count DESC;
```

#### 시/도별 해안가 지역 수
```sql
SELECT sido,
       COUNT(*) as total,
       SUM(is_coastal) as coastal_count,
       SUM(is_east_coast) as east_count,
       SUM(is_west_coast) as west_count,
       SUM(is_south_coast) as south_count
FROM regions
GROUP BY sido
HAVING coastal_count > 0
ORDER BY coastal_count DESC;
```

### 5.3 출사지 검색

#### 모든 출사지 조회
```sql
SELECT ps.id, ps.name, ps.description, ps.tags,
       r.sido, r.sigungu
FROM photo_spots ps
LEFT JOIN regions r ON ps.region_code = r.code
WHERE ps.is_active = 1
ORDER BY ps.name;
```

#### 특정 태그의 출사지 찾기
```sql
-- "일출" 태그가 있는 출사지
SELECT name, description, tags, lat, lon
FROM photo_spots
WHERE tags LIKE '%일출%'
  AND is_active = 1;
```

#### 특정 테마의 출사지 찾기
```sql
-- 은하수 테마(ID:5)의 추천 출사지
SELECT ps.name, ps.description, r.name as region_name
FROM photo_spots ps
JOIN photo_spot_themes pst ON ps.id = pst.spot_id
LEFT JOIN regions r ON ps.region_code = r.code
WHERE pst.theme_id = 5
  AND ps.is_active = 1;
```

### 5.4 해양 정보 검색

#### 해양예보구역 목록
```sql
SELECT zone_code, name, name_en
FROM marine_zones
ORDER BY zone_code;
```

#### 특정 지역의 해양예보구역 찾기
```sql
-- 지역 코드로 연결된 해양 구역 찾기
SELECT r.name as region_name, mz.name as zone_name, mz.zone_code
FROM regions r
JOIN region_marine_zone rmz ON r.code = rmz.region_code
JOIN marine_zones mz ON rmz.zone_code = mz.zone_code
WHERE r.sido = '강원특별자치도'
  AND r.is_coastal = 1;
```

### 5.5 해수욕장 검색

#### 모든 해수욕장 조회
```sql
SELECT beach_num, name, lat, lon, region_code, marine_zone_code
FROM beaches
ORDER BY name;
```

#### 해양구역별 해수욕장 조회
```sql
-- 동해북부 해수욕장 목록
SELECT b.name as beach_name, b.lat, b.lon, mz.name as zone_name
FROM beaches b
JOIN marine_zones mz ON b.marine_zone_code = mz.zone_code
WHERE mz.zone_code = '12C30000'
ORDER BY b.lat DESC;
```

#### 해수욕장과 연결된 지역 정보 조회
```sql
-- 해수욕장과 읍면동 정보 함께 조회
SELECT b.name as beach_name, r.name as region_name, r.sido, r.sigungu
FROM beaches b
JOIN regions r ON b.region_code = r.code
WHERE b.name LIKE '%경포%';
```

#### 해양구역별 해수욕장 통계
```sql
SELECT mz.name as zone_name, COUNT(*) as beach_count
FROM beaches b
JOIN marine_zones mz ON b.marine_zone_code = mz.zone_code
GROUP BY mz.zone_code
ORDER BY beach_count DESC;
```

### 5.6 좌표 기반 검색

#### 특정 좌표 근처 지역 찾기
```sql
-- 정동진 근처 (위도: 37.6899, 경도: 129.0344) 반경 내 지역
SELECT name, lat, lon,
       ((lat - 37.6899) * (lat - 37.6899) +
        (lon - 129.0344) * (lon - 129.0344)) as distance_sq
FROM regions
WHERE lat BETWEEN 37.5 AND 37.9
  AND lon BETWEEN 128.8 AND 129.3
ORDER BY distance_sq
LIMIT 10;
```

### 5.7 데이터 내보내기

#### CSV로 내보내기
```sql
-- SQLite에서 CSV로 내보내기
.headers on
.mode csv
.output coastal_regions.csv
SELECT code, name, sido, lat, lon,
       is_east_coast, is_west_coast, is_south_coast
FROM regions
WHERE is_coastal = 1;
.output stdout
```

#### JSON으로 내보내기 (명령줄)
```bash
# 터미널에서 JSON으로 내보내기
sqlite3 -json data/regions.db \
  "SELECT * FROM photo_spots WHERE is_active = 1" \
  > photo_spots.json
```

---

## 6. 문제 해결

### 6.1 일반적인 오류

#### "database is locked" 오류
다른 프로세스가 데이터베이스를 사용 중입니다.
```bash
# 해결: 다른 터미널이나 프로그램에서 DB 접속을 종료
# 또는 잠시 후 다시 시도
```

#### "no such table" 오류
테이블 이름을 정확히 입력했는지 확인하세요.
```sql
-- 테이블 목록 확인
.tables
```

#### 한글이 깨져 보이는 경우
```bash
# 터미널에서 UTF-8 설정 확인
export LANG=ko_KR.UTF-8
```

### 6.2 API 관련 문제

#### 서버가 시작되지 않는 경우
```bash
# 의존성 설치 확인
pip install -r requirements.txt

# 포트 충돌 확인 (다른 프로세스가 8000 포트 사용 중)
lsof -i :8000
```

#### API 응답이 없는 경우
```bash
# 서버 로그 확인
# 서버 시작 시 콘솔에 출력되는 로그를 확인

# 헬스체크로 서버 상태 확인
curl http://localhost:8000/health
```

### 6.3 데이터 백업

정기적으로 데이터베이스를 백업하세요.
```bash
# 백업 생성
cp data/regions.db data/regions.db.backup

# 날짜별 백업
cp data/regions.db "data/regions_$(date +%Y%m%d).db.backup"
```

### 6.4 도움 받기

- **프로젝트 문서**: `docs/` 폴더의 다른 문서 참조
- **API 문서**: 서버 실행 후 `http://localhost:8000/docs` 접속
- **기술 명세**: `spec.md` 파일 참조

---

## 부록: 빠른 참조 카드

### SQLite 기본 명령어
| 명령어 | 설명 |
|-------|------|
| `.tables` | 테이블 목록 |
| `.schema 테이블명` | 테이블 구조 |
| `.headers on` | 컬럼명 표시 |
| `.mode column` | 표 형식 출력 |
| `.quit` | 종료 |

### 자주 쓰는 SQL
| 목적 | SQL |
|------|-----|
| 전체 조회 | `SELECT * FROM 테이블 LIMIT 10;` |
| 조건 검색 | `SELECT * FROM 테이블 WHERE 컬럼='값';` |
| 개수 세기 | `SELECT COUNT(*) FROM 테이블;` |
| 그룹 통계 | `SELECT 컬럼, COUNT(*) FROM 테이블 GROUP BY 컬럼;` |
| 정렬 | `SELECT * FROM 테이블 ORDER BY 컬럼 DESC;` |

### API 엔드포인트
| 기능 | 엔드포인트 |
|------|-----------|
| 헬스체크 | `GET /health` |
| 테마 목록 | `GET /api/v1/themes` |
| 지역 검색 | `GET /api/v1/regions?sido=경기도` |
| 지역 상세 | `GET /api/v1/regions/{code}` |
| 출사지 | `GET /api/v1/photo-spots` |
| 해양 예보 | `GET /api/v1/marine/zones` |
| 해수욕장 목록 | `GET /api/v1/beaches` |
| 해수욕장 날씨 | `GET /api/v1/beaches/{beach_num}/forecast` |

---

*이 문서는 Weather Lens 프로젝트의 일부입니다.*
