# PhotoSpot Korea - 기술 명세서 (Technical Specification)

**버전**: 2.0
**작성일**: 2026-01-31
**최종 수정일**: 2026-01-31
**프로젝트명**: Weather Lens (PhotoSpot Korea)

---

## 1. 서비스 개요

### 1.1 목적
풍경사진가를 위한 날씨 기반 출사지 큐레이션 서비스. 기상 데이터와 해양 데이터를 분석하여 최적의 촬영 장소와 시간을 추천한다.

### 1.2 핵심 기능
- 전국 읍/면/동 단위 (3,616개) 날씨 데이터 수집 및 분석
- **16개** 촬영 테마별 점수 산출 (기존 8개에서 확장)
- 지역별 TOP 추천 및 AI 기반 큐레이션 문구 생성
- Telegram을 통한 실시간 알림 발송
- 지도 기반 시각화

### 1.3 현재 구현 상태 (2026-01-31 기준)

| 구성요소 | 상태 | 설명 |
|---------|------|------|
| 지역 데이터베이스 | ✅ 완료 | 3,616개 읍면동, 653개 해안 지역 |
| 데이터 수집기 | ✅ 완료 | 기상청, Open-Meteo, 에어코리아, 바다누리 |
| 테마별 스코어러 | ✅ 완료 | 16개 테마 점수 산출 알고리즘 |
| 피드백 시스템 | ✅ 완료 | 수집, 분석, 자동 보정 로직 |
| REST API | ✅ 완료 | FastAPI 기반 API 서버 |
| 스케줄러 | ✅ 완료 | APScheduler 기반 자동 실행 |
| Telegram 봇 | ✅ 완료 | 알림 발송 기능 |
| Gemini 큐레이터 | ✅ 완료 | AI 문구 생성 |

---

## 2. 시스템 아키텍처

### 2.1 데이터 흐름
```
┌─────────────────────────────────────────────────────────────────────────┐
│                           데이터 수집 (Collectors)                        │
├─────────────────────────────────────────────────────────────────────────┤
│  [기상청 API]  [Open-Meteo]  [에어코리아]  [바다누리]  [기상청 해상예보]     │
│       ↓            ↓             ↓            ↓              ↓          │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                         데이터 처리 (Processors)                         │
├─────────────────────────────────────────────────────────────────────────┤
│  [DataMerger]            [CacheWriter]           [RegionLoader]          │
│  - 복수 API 평균값         - JSON 캐시 저장         - DB 지역 로드          │
│  - 편차 플래그 계산         - 날짜별 폴더 관리        - 해안 분류            │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                         점수 산출 (Scorers)                              │
├─────────────────────────────────────────────────────────────────────────┤
│  [16개 테마 스코어러]                                                      │
│  - SunriseScorer, SunriseOmegaScorer, SunsetScorer, SunsetOmegaScorer   │
│  - MilkyWayScorer, BioluminescenceScorer, SeaLongExposureScorer         │
│  - SeaOfCloudsScorer, StarTrailScorer, NightCityscapeScorer             │
│  - FogLandscapeScorer, ReflectionScorer, GoldenHourScorer               │
│  - BlueHourScorer, FrostRimeScorer, MoonriseScorer                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                          추천 및 알림                                     │
├─────────────────────────────────────────────────────────────────────────┤
│  [RegionRecommender]     [GeminiCurator]        [TelegramBot]            │
│  - 시도별 TOP 추출         - AI 문구 생성          - 알림 발송             │
│  - 전국 TOP 10 생성        - 1,500콜/일 최적화     - 무제한 무료            │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 기술 스택

| 구분 | 기술 | 선정 사유 |
|------|------|----------|
| 언어 | Python 3.10+ | FastAPI/APScheduler 생태계 |
| 웹 프레임워크 | FastAPI 0.109+ | 비동기 지원, 자동 문서화 |
| DB (MVP) | SQLite | 설치 불필요, 파일 1개로 운영 |
| DB (확장) | Supabase Postgres | 500MB 무료, REST API 내장 |
| 호스팅 | Render Free + UptimeRobot | 750시간/월, 5분 핑으로 슬립 회피 |
| 기상 API (Primary) | 기상청 단기예보 | 한국 공식, 무제한, 3시간 간격 |
| 기상 API (Secondary) | Open-Meteo | 10K콜/일 무료, API키 불필요 |
| 대기질 API | 에어코리아 | PM2.5/PM10 데이터 |
| 해양 API | 바다누리 | 조석/파고/수온 데이터 |
| 해양예보 API | 기상청 API Hub | 해상예보구역별 예보 |
| 지도 API | Leaflet + OSM (MVP) / Kakao Maps (확장) | MVP: 비용 0원 |
| LLM | Gemini 1.5 Flash | 무료 1,500콜/일 |
| 메시징 | Telegram Bot API | 완전 무료, 제한 없음 |
| 스케줄러 | APScheduler | 비동기 스케줄링, CronTrigger |

---

## 3. 데이터 수집 (Collectors)

### 3.1 Collector 모듈 구조

```
collectors/
├── __init__.py
├── base_collector.py      # 추상 베이스 클래스
├── kma_forecast.py        # 기상청 단기예보
├── kma_marine_forecast.py # 기상청 해상예보
├── openmeteo.py           # Open-Meteo
├── airkorea.py            # 에어코리아
├── khoa_ocean.py          # 바다누리 해양
└── example_usage.py       # 사용 예시
```

### 3.2 기상 데이터

#### 3.2.1 수집 항목
| 항목 | Primary (기상청) | Secondary (Open-Meteo) |
|------|------------------|------------------------|
| 기온/습도/풍속 | VilageFcstInfoService | temperature_2m, humidity_2m, wind_speed_10m |
| 강수확률/강수량 | POP/PCP | precipitation_probability |
| 하늘상태/구름량 | SKY | cloud_cover |
| 미세먼지 | 에어코리아 (단일 소스) | - |

#### 3.2.2 평균값 산출 로직
```python
final_value = (kma_value * 0.6) + (openmeteo_value * 0.4)  # 기상청 가중치 60%

if abs(kma_value - openmeteo_value) > threshold:
    deviation_flag = True  # 편차 경고 플래그
```

#### 3.2.3 수집 범위
- 예보 기간: D-day ~ D+2 (3일간)
- 갱신 주기: 12시간 간격 (일 2회: 06:00, 18:00)
- Open-Meteo: hourly 데이터로 세밀한 보간 가능

### 3.3 해양 데이터

| API | 제공 데이터 | 출처 |
|-----|------------|------|
| 바다누리 조석예보 | 만조/간조 시각, 조위 | 국립해양조사원 |
| 바다누리 파고정보 | 유의파고, 파주기 | 국립해양조사원 |
| 해수온 관측 | 표층 수온 | 바다누리/기상청 |
| 기상청 해상예보 | 파고, 날씨, 풍랑특보 | 기상청 API Hub |

### 3.4 해양예보구역 (Marine Zones)

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

> **Note**:
> - 해양 데이터의 위치명은 읍면동 단위로 변환됨 (`region_marine_zone` 테이블)
> - 해양 데이터는 12시간 간격으로 업데이트됨

---

## 4. 데이터 저장 구조

### 4.1 2계층 저장 전략

| 계층 | 저장소 | 용도 |
|------|--------|------|
| 정본 (Source of Truth) | SQLite → Supabase Postgres | 읍면동 메타, 점수 이력, 추천 결과 |
| 캐시 (Fast Access) | JSON 파일 (날짜별 폴더) | 당일~D+2 예보, API 응답 속도 향상 |

### 4.2 데이터베이스 스키마

#### 4.2.1 regions (지역 정보) - 3,616개

```sql
CREATE TABLE regions (
    code TEXT PRIMARY KEY,          -- 읍면동 코드 (예: "1168010100")
    name TEXT NOT NULL,             -- 전체 지역명 (예: "서울특별시 강남구 역삼동")
    sido TEXT NOT NULL,             -- 시/도 (예: "서울특별시")
    sigungu TEXT NOT NULL,          -- 시/군/구 (예: "강남구")
    emd TEXT NOT NULL,              -- 읍/면/동 (예: "역삼동")
    lat REAL NOT NULL,              -- 위도
    lon REAL NOT NULL,              -- 경도
    nx INTEGER,                     -- 기상청 격자 X 좌표
    ny INTEGER,                     -- 기상청 격자 Y 좌표
    elevation REAL DEFAULT 0,       -- 해발고도 (m)
    is_coastal INTEGER DEFAULT 0,   -- 해안가 여부 (0 or 1)
    is_east_coast INTEGER DEFAULT 0,-- 동해안 여부
    is_west_coast INTEGER DEFAULT 0,-- 서해안 여부
    is_south_coast INTEGER DEFAULT 0,-- 남해안 여부
    ocean_station_id TEXT,          -- 연결된 해양관측소 ID
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_regions_sido ON regions(sido);
CREATE INDEX idx_regions_coastal ON regions(is_coastal);
CREATE INDEX idx_regions_elevation ON regions(elevation);
```

#### 4.2.2 themes (촬영 테마) - 16개

```sql
CREATE TABLE themes (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT
);
```

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

#### 4.2.3 photo_spots (출사지)

```sql
CREATE TABLE photo_spots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    region_code TEXT,
    lat REAL,
    lon REAL,
    elevation INTEGER DEFAULT 0,
    description TEXT,
    tags TEXT,                      -- 쉼표 구분 태그
    created_by TEXT DEFAULT 'system',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1,
    FOREIGN KEY (region_code) REFERENCES regions(code)
);
```

#### 4.2.4 marine_zones (해양예보구역)

```sql
CREATE TABLE marine_zones (
    zone_code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    name_en TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE region_marine_zone (
    region_code TEXT PRIMARY KEY,
    zone_code TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (region_code) REFERENCES regions(code),
    FOREIGN KEY (zone_code) REFERENCES marine_zones(zone_code)
);
```

#### 4.2.5 user_collections (사용자 컬렉션)

```sql
CREATE TABLE user_collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    color_code TEXT DEFAULT '1',
    icon_id TEXT DEFAULT '1',
    is_default BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, name)
);

CREATE TABLE user_collection_spots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_id INTEGER NOT NULL,
    photo_spot_id INTEGER,
    custom_name TEXT,
    custom_lat REAL,
    custom_lon REAL,
    region_code TEXT,
    memo TEXT,
    tags TEXT,
    source_url TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (collection_id) REFERENCES user_collections(id) ON DELETE CASCADE,
    FOREIGN KEY (photo_spot_id) REFERENCES photo_spots(id)
);
```

### 4.3 시/도별 지역 통계

| 시/도 | 총 지역 수 | 해안 지역 |
|-------|-----------|----------|
| 경기도 | 611 | 0 |
| 서울특별시 | 427 | 0 |
| 경상북도 | 336 | 61 |
| 경상남도 | 311 | 112 |
| 전라남도 | 295 | 194 |
| 전북특별자치도 | 253 | 1 |
| 충청남도 | 214 | 65 |
| 부산광역시 | 208 | 111 |
| 강원특별자치도 | 189 | 60 |
| 인천광역시 | 163 | 24 |
| 충청북도 | 154 | 0 |
| 대구광역시 | 139 | 0 |
| 광주광역시 | 102 | 0 |
| 대전광역시 | 85 | 0 |
| 울산광역시 | 62 | 13 |
| 제주특별자치도 | 43 | 12 |
| 세종특별자치시 | 24 | 0 |
| **합계** | **3,616** | **653** |

---

## 5. 테마별 점수 산출 (Scorers)

### 5.1 Scorer 모듈 구조

```
scorers/
├── __init__.py
├── base_scorer.py        # 추상 베이스 클래스 (점수 정규화, 범위 계산)
└── theme_scorers.py      # 16개 테마 스코어러 구현
```

### 5.2 16개 촬영 테마 점수 조건

| No | 테마명 | 핵심 조건 | 가중치 |
|----|--------|----------|--------|
| 1 | 일출 | 구름 30~60%, 강수확률 <20%, PM2.5 좋음, 동해안 보너스 | config/weights.json |
| 2 | 일출 오메가 | 수평선 맑음, 해수온 > 기온+5°C, 풍속 <3m/s, 동해안 필수 | 불확실성 높음 |
| 3 | 일몰 | 구름 40~70%, 강수확률 <20%, 서해안 보너스 | config/weights.json |
| 4 | 일몰 오메가 | 일출 오메가와 동일 조건, 서해안 적용 | 불확실성 높음 |
| 5 | 은하수 | 월령 신월±3일, 구름 <20%, 광해 낮은 지역 | config/weights.json |
| 6 | 야광충 | 수온 18~25°C, 신월±5일, 4~9월, 남해안/동해안 | 불확실성 높음 |
| 7 | 바다 장노출 | 파고 0.3~1.0m, 풍랑특보 없음, 간조 전후 2시간 | config/weights.json |
| 8 | 운해 | 저지대 습도 >85%, 기온역전, 풍속 <3m/s, 해발 500m+ | config/weights.json |
| 9 | 별궤적 | 신월±5일, 구름 <15%, 광해 낮음, 풍속 <5m/s | config/weights.json |
| 10 | 야경 | 구름 <50%, 강수확률 <10%, 시정 >10km | config/weights.json |
| 11 | 안개 | 습도 >90%, 주야온도차 큼, 풍속 <2m/s | config/weights.json |
| 12 | 반영 | 풍속 <2m/s, 강수확률 <10%, 구름 20~60% | config/weights.json |
| 13 | 골든아워 | 구름 20~50%, 강수확률 <15%, PM2.5 좋음 | config/weights.json |
| 14 | 블루아워 | 구름 <40%, 강수확률 <10%, 시정 좋음 | config/weights.json |
| 15 | 상고대 | 기온 <-5°C, 습도 >85%, 풍속 <3m/s, 11~2월 | config/weights.json |
| 16 | 월출 | 보름달±2일, 구름 <30%, 시정 좋음 | config/weights.json |

### 5.3 점수 산출 범위
- 점수: 0 ~ 100점
- 시/도 단위 그룹핑 후 테마별 TOP 1 추출
- 전국 테마별 TOP 10 리스트 생성

### 5.4 불확실성 표기 (오메가/야광충)
```
⚠️ 야광충/오메가는 '예측'이 아닌 '가능성 점수'로 표현
- 오메가: "조건 충족 시에도 불확실성 높음, 실제 발생률 ~30%"
- 야광충: "관측 이력 + 수온 기반 가능성, 보장 아님"
```

### 5.5 가중치 설정 (config/weights.json)

```json
{
  "themes": {
    "sunrise": {
      "cloud_cover": {"min": 30, "max": 60, "weight": 0.3},
      "rain_prob": {"max": 20, "weight": 0.25},
      "pm25": {"max": 50, "weight": 0.2},
      "visibility": {"min": 10, "weight": 0.15},
      "east_coast_bonus": 10
    },
    "milky_way": {
      "moon_phase": {"target": "new_moon", "range_days": 3, "weight": 0.35},
      "cloud_cover": {"max": 20, "weight": 0.3},
      "light_pollution": {"max": 3, "weight": 0.25},
      "visibility": {"min": 15, "weight": 0.1}
    }
    // ... 16개 테마 전체 설정
  },
  "version": "2.0",
  "last_updated": "2026-01-30"
}
```

---

## 6. 피드백 시스템 (Feedbacks)

### 6.1 모듈 구조

```
feedbacks/
├── __init__.py
├── collector.py       # 피드백 수집 및 DB 저장
├── analyzer.py        # 피드백 분석 및 가중치 조정 제안
└── automation.py      # 실시간 페널티 및 자동 튜닝 로직
```

### 6.2 피드백 수집 항목
- **성공 여부** (O/X): 촬영 성공/실패
- **실제 기상 상황**: 구름량, 시정, 파고 등 (선택지 제공)
- **만족도 별점**: 1~5점
- **코멘트**: 자유 의견 (선택)
- **증빙 사진**: 현장 상황 사진 (선택)

### 6.3 자동 보정 프로세스

1. **실시간 이상치 탐지**: 특정 지역/테마에서 1시간 내 3건 이상 '실패' 리포트 → 점수 일시 하향 (-20점, 6시간)
2. **정확도 검증 (Weekly)**: 주간 단위로 "예측 vs 실제" 데이터 비교 분석
3. **가중치 최적화 (Monthly)**: RMSE 최소화 기반 weights.json 자동 조정
4. **알고리즘 개선 (Quarterly)**: 분기별 리뷰를 통해 점수 산출 공식 업데이트

---

## 7. 추천 알고리즘 (Recommenders)

### 7.1 모듈 구조

```
recommenders/
├── __init__.py
└── region_recommender.py   # RegionRecommender 클래스
```

### 7.2 처리 흐름
1. 전국 읍/면/동 캐시 JSON 로드 (3,616개)
2. 각 지역별 16개 테마 점수 계산 (0~100점)
3. 시/도 단위 그룹핑 → 테마별 TOP 1 추출
4. 전국 테마별 TOP 10 리스트 생성
5. Gemini로 자연어 추천 문구 생성 (TOP N만)

### 7.3 Gemini 호출 최적화
```
무료 할당량: 1,500 요청/일

❌ 읍면동별 호출 → 3,616+ 호출로 초과
✅ 테마별 TOP 10 × 16테마 = 160 호출/일
→ 실제 사용: ~200 호출/일 (여유 확보)
```

---

## 8. REST API (api/)

### 8.1 모듈 구조

```
api/
├── __init__.py
├── main.py              # FastAPI 앱 설정
└── routes/
    ├── __init__.py
    ├── health.py        # /health
    ├── themes.py        # /api/v1/themes
    ├── regions.py       # /api/v1/regions
    ├── photo_spots.py   # /api/v1/photo-spots
    ├── marine.py        # /api/v1/marine
    ├── astronomy.py     # /api/v1/astronomy
    ├── feedback.py      # /api/v1/feedback
    ├── user_collections.py  # /api/v1/user
    ├── map.py           # /api/v1/map
    └── internal.py      # /internal (스케줄러용)
```

### 8.2 공개 API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/health` | 헬스체크 (UptimeRobot 핑용) |
| GET | `/api/v1/themes` | 테마 목록 조회 |
| GET | `/api/v1/themes/{theme_id}/top` | 테마별 TOP 10 지역 |
| GET | `/api/v1/regions` | 지역 목록 조회 (필터링/페이지네이션) |
| GET | `/api/v1/regions/{region_code}` | 특정 지역 상세 정보 |
| GET | `/api/v1/regions/{region_code}/forecast` | 특정 지역 예보 |
| GET | `/api/v1/photo-spots` | 출사지 목록 조회 |
| GET | `/api/v1/photo-spots/{id}` | 출사지 상세 |
| GET | `/api/v1/marine/zones` | 해양예보구역 목록 |
| GET | `/api/v1/marine/{region_code}/forecast` | 지역별 해양 예보 |
| GET | `/api/v1/astronomy` | 천문 정보 (일출/일몰/월령) |
| POST | `/api/v1/feedback` | 사용자 피드백 제출 |
| GET | `/api/v1/map/boundaries` | 지도 경계 GeoJSON |
| GET | `/api/v1/user/collections` | 사용자 컬렉션 목록 |
| POST | `/api/v1/user/collections` | 컬렉션 생성 |
| GET | `/api/v1/user/collections/{id}` | 컬렉션 상세 |
| POST | `/api/v1/user/collections/{id}/spots` | 컬렉션에 스팟 추가 |

### 8.3 내부 API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/internal/collect` | 데이터 수집 트리거 |
| POST | `/internal/score` | 점수 재계산 트리거 |
| POST | `/internal/notify` | Telegram 알림 발송 |

---

## 9. 스케줄러 (scheduler.py)

### 9.1 스케줄된 작업

| 작업 | 실행 시간 (KST) | 설명 |
|------|----------------|------|
| `collect_weather_data` | 06:00, 18:00 | 날씨 데이터 수집 |
| `generate_weather_report` | 03:00, 15:00 | MD 리포트 생성 |
| `recalculate_scores` | 07:00, 19:00 | 테마별 점수 재계산 |
| `send_daily_recommendations` | 20:00 | Telegram 일일 추천 발송 |

### 9.2 실행 방식
```python
# APScheduler AsyncIOScheduler 사용
scheduler = AsyncIOScheduler()

@scheduler.scheduled_job(CronTrigger(hour="6,18"))
async def collect_weather_data():
    await call_internal_api("collect", "WeatherCollection")
```

---

## 10. 프로젝트 구조 (현재 구현)

```
weather_lens/
├── main.py                    # 앱 진입점 (FastAPI + Scheduler)
├── scheduler.py               # APScheduler 스케줄 작업
├── warmup.py                  # UptimeRobot 핑 응답
├── config/
│   ├── __init__.py
│   ├── settings.py            # API 키, 환경변수, 경로
│   └── weights.json           # 16개 테마별 가중치
├── data/
│   ├── regions.db             # SQLite 메인 DB (3,616 지역)
│   ├── ocean_mapping.db       # 해양 관측소 매핑
│   ├── marine_zones.py        # 해양예보구역 정의
│   ├── cache/                 # JSON 캐시 (날짜별)
│   └── boundaries/            # GeoJSON 경계 파일
├── collectors/
│   ├── __init__.py
│   ├── base_collector.py      # BaseCollector 추상 클래스
│   ├── kma_forecast.py        # 기상청 단기예보
│   ├── kma_marine_forecast.py # 기상청 해상예보
│   ├── openmeteo.py           # Open-Meteo
│   ├── airkorea.py            # 에어코리아
│   └── khoa_ocean.py          # 바다누리 해양
├── processors/
│   ├── __init__.py
│   ├── data_merger.py         # 복수 API 평균값 + 편차 플래그
│   ├── cache_writer.py        # JSON 캐시 저장
│   └── region_loader.py       # DB 지역 로더
├── scorers/
│   ├── __init__.py
│   ├── base_scorer.py         # BaseScorer 추상 클래스
│   └── theme_scorers.py       # 16개 테마 스코어러
├── feedbacks/
│   ├── __init__.py
│   ├── collector.py           # 피드백 수집 및 DB 저장
│   ├── analyzer.py            # 피드백 분석 및 가중치 조정 제안
│   └── automation.py          # 실시간 페널티 및 자동 튜닝
├── recommenders/
│   ├── __init__.py
│   └── region_recommender.py  # 시도별/전국 TOP 추출
├── curators/
│   ├── __init__.py
│   └── gemini_curator.py      # LLM 문구 생성 (TOP N만)
├── messengers/
│   ├── __init__.py
│   └── telegram_bot.py        # Telegram 발송
├── api/
│   ├── __init__.py
│   ├── main.py                # FastAPI 웹 API
│   └── routes/                # 엔드포인트별 라우터
├── utils/
│   ├── __init__.py
│   └── astronomy.py           # 천문 계산 (일출/일몰/월령)
├── scripts/                   # 유틸리티 스크립트
│   ├── init_database.py       # DB 초기화
│   ├── import_regions.py      # 지역 데이터 임포트
│   ├── setup_marine_zones.py  # 해양구역 설정
│   └── collect_weather_report.py  # 날씨 리포트 생성
├── docs/
│   ├── DB_API_GUIDE.md        # DB/API 사용 가이드
│   └── ...
├── requirements.txt           # Python 의존성
├── pyproject.toml             # 프로젝트 메타데이터
└── render.yaml                # Render 배포 설정
```

---

## 11. 환경 변수

```env
# 기상청 API
KMA_API_KEY=
KMA_API_SOURCE=data.go.kr  # data.go.kr 또는 apihub.kma.go.kr

# 에어코리아 API
AIRKOREA_API_KEY=

# 바다누리 API
KHOA_API_KEY=

# Kakao Maps (확장 단계)
KAKAO_REST_API_KEY=

# Gemini
GEMINI_API_KEY=

# Telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Supabase (확장 단계)
SUPABASE_URL=
SUPABASE_KEY=

# 내부 API
INTERNAL_API_KEY=dev-internal-key

# 환경 설정
ENVIRONMENT=development  # development | production
LOG_LEVEL=INFO
```

---

## 12. 비용 분석

| 항목 | MVP 단계 | 확장 단계 | 비고 |
|------|----------|----------|------|
| DB | $0 (SQLite) | $0 (Supabase Free) | 500MB 한도 |
| 호스팅 | $0 (Render Free) | $0~7 (Render Starter) | 슬립 회피 필수 |
| 기상 API | $0 | $0 | 무제한 |
| 지도 API | $0 (Leaflet+OSM) | $0 (Kakao 무료 쿼터) | 쿼터 모니터링 |
| LLM | $0 (Gemini Free) | $0 | 1,500콜/일 |
| 메시징 | $0 (Telegram) | $0 | 완전 무료 |
| **총계** | **$0/월** | **$0~7/월** | |

---

## 13. 리스크 및 대응

| 리스크 | 대응 전략 | 전환 기준 |
|--------|----------|----------|
| Render 콜드스타트 25초 | UptimeRobot 5분 핑으로 웜업 | 사용자 불만 시 Render Starter($7) |
| Supabase 7일 미활동 정지 | 스케줄러로 매일 DB 쿼리 실행 | Pro($25) 전환 시 정지 없음 |
| Open-Meteo 상업적 이용 제한 | 비상업 커뮤니티 서비스 운영 | 수익화 시 $29/월 구독 |
| 지도 쿼터 초과 | Leaflet+OSM으로 폴백 | 일일 쿼터 80% 도달 시 |
| 오메가/야광충 예측 과장 | '가능성 점수' + 불확실성 표기 | 사용자 피드백 반영 |

---

## 14. 개발 마일스톤

| 단계 | 작업 내용 | 상태 |
|------|----------|------|
| 1 | 읍면동 기초 데이터 + 경계 GeoJSON 수급 | ✅ 완료 |
| 2 | 기상청 + Open-Meteo 연동 및 평균값 로직 | ✅ 완료 |
| 3 | 해양 API + 매핑 테이블 구축 | ✅ 완료 |
| 4 | 16개 테마 점수 산출 알고리즘 | ✅ 완료 |
| 5 | 지역별 추천 로직 + JSON 캐시 | ✅ 완료 |
| 6 | Gemini 연동 (TOP N만) | ✅ 완료 |
| 7 | Telegram 봇 + 스케줄러 | ✅ 완료 |
| 8 | 지도 경계 단순화 + 성능 테스트 | 🔄 진행중 |
| 9 | Render 배포 + UptimeRobot 설정 | 📋 예정 |
| 10 | 베타 운영 및 피드백 | 📋 예정 |

---

## 부록: 관련 문서

| 문서 | 위치 | 설명 |
|------|------|------|
| DB/API 사용 가이드 | `docs/DB_API_GUIDE.md` | 초보자용 DB 및 API 사용법 |
| 지역 전체 목록 | `docs/REGIONS_FULL_LIST.md` | 시도별 읍면동 목록 |
| 해안 분류 완료 보고 | `docs/COASTAL_CLASSIFICATION_COMPLETE.md` | 해안 분류 작업 결과 |
| 기상청 API 연동 | `docs/KMA_API_INTEGRATION.md` | 기상청 API 상세 |
| 배포 가이드 | `DEPLOYMENT.md` | Render 배포 방법 |
| 빠른 시작 가이드 | `QUICKSTART.md` | 개발 환경 설정 |

---

*— End of Specification —*
