# PhotoSpot Korea - 기술 명세서 (Technical Specification)

**버전**: 1.0
**작성일**: 2026-01-29
**프로젝트명**: Weather Lens (PhotoSpot Korea)

---

## 1. 서비스 개요

### 1.1 목적
풍경사진가를 위한 날씨 기반 출사지 큐레이션 서비스. 기상 데이터와 해양 데이터를 분석하여 최적의 촬영 장소와 시간을 추천한다.

### 1.2 핵심 기능
- 전국 읍/면/동 단위(약 3,500개) 날씨 데이터 수집 및 분석
- 8개 촬영 테마별 점수 산출
- 지역별 TOP 추천 및 AI 기반 큐레이션 문구 생성
- Telegram을 통한 실시간 알림 발송
- 지도 기반 시각화

---

## 2. 시스템 아키텍처

### 2.1 데이터 흐름
```
[기상청 + Open-Meteo] → [평균값 산출] → [읍면동 JSON 캐시]
    → [테마별 점수 계산] → [Gemini 큐레이션] → [Telegram 발송]
```

### 2.2 기술 스택

| 구분 | 기술 | 선정 사유 |
|------|------|----------|
| 언어 | Python 3.10+ | FastAPI/APScheduler 생태계 |
| DB (MVP) | SQLite | 설치 불필요, 파일 1개로 운영 |
| DB (확장) | Supabase Postgres | 500MB 무료, REST API 내장 |
| 호스팅 | Render Free + UptimeRobot | 750시간/월, 5분 핑으로 슬립 회피 |
| 기상 API (Primary) | 기상청 단기예보 | 한국 공식, 무제한, 3시간 간격 |
| 기상 API (Secondary) | Open-Meteo | 10K콜/일 무료, API키 불필요 |
| 대기질 API | 에어코리아 | PM2.5/PM10 데이터 |
| 해양 API | 바다누리 | 조석/파고/수온 데이터 |
| 지도 API | Leaflet + OSM (MVP) / Kakao Maps (확장) | MVP: 비용 0원 |
| LLM | Gemini 1.5 Flash | 무료 1,500콜/일 |
| 메시징 | Telegram Bot API | 완전 무료, 제한 없음 |

---

## 3. 데이터 수집

### 3.1 기상 데이터

#### 3.1.1 수집 항목
| 항목 | Primary (기상청) | Secondary (Open-Meteo) |
|------|------------------|------------------------|
| 기온/습도/풍속 | VilageFcstInfoService | temperature_2m, humidity_2m, wind_speed_10m |
| 강수확률/강수량 | POP/PCP | precipitation_probability |
| 하늘상태/구름량 | SKY | cloud_cover |
| 미세먼지 | 에어코리아 (단일 소스) | - |

#### 3.1.2 평균값 산출 로직
```python
final_value = (kma_value * 0.6) + (openmeteo_value * 0.4)  # 기상청 가중치 60%

if abs(kma_value - openmeteo_value) > threshold:
    deviation_flag = True  # 편차 경고 플래그
```

#### 3.1.3 수집 범위
- 예보 기간: D-day ~ D+2 (3일간)
- 갱신 주기: 3시간 간격 (일 8회)
- Open-Meteo: hourly 데이터로 세밀한 보간 가능

### 3.2 해양 데이터

| API | 제공 데이터 | 출처 |
|-----|------------|------|
| 바다누리 조석예보 | 만조/간조 시각, 조위 | 국립해양조사원 |
| 바다누리 파고정보 | 유의파고, 파주기 | 국립해양조사원 |
| 해수온 관측 | 표층 수온 | 바다누리/기상청 |

---

## 4. 데이터 저장 구조

### 4.1 2계층 저장 전략

| 계층 | 저장소 | 용도 |
|------|--------|------|
| 정본 (Source of Truth) | SQLite → Supabase Postgres | 읍면동 메타, 점수 이력, 추천 결과 |
| 캐시 (Fast Access) | JSON 파일 (날짜별 폴더) | 당일~D+2 예보, API 응답 속도 향상 |

### 4.2 읍면동 JSON 스키마

**파일 경로**: `/data/cache/{date}/{sido}_{sigungu}_{emd}.json`

```json
{
  "region_code": "1168010100",
  "region_name": "서울특별시 강남구 역삼동",
  "coordinates": {
    "lat": 37.5000,
    "lng": 127.0364
  },
  "updated_at": "2026-01-29T06:00:00+09:00",
  "forecast": [
    {
      "datetime": "2026-01-29T06:00:00",
      "temp": {
        "kma": -3.2,
        "openmeteo": -2.8,
        "avg": -3.0,
        "deviation_flag": false
      },
      "cloud": {
        "kma": 30,
        "openmeteo": 35,
        "avg": 32
      },
      "rain_prob": {
        "kma": 10,
        "openmeteo": 12,
        "avg": 11
      },
      "pm25": 18,
      "sunrise": "07:35",
      "sunset": "17:52"
    }
  ],
  "ocean_station_id": "DT_0001"
}
```

### 4.3 해양-읍면동 매핑 테이블

```sql
CREATE TABLE ocean_region_mapping (
  region_code TEXT PRIMARY KEY,
  region_name TEXT,
  ocean_station_id TEXT,
  ocean_station_name TEXT,
  distance_km REAL,
  is_coastal BOOLEAN DEFAULT FALSE
);

-- 해안선 30km 이내만 is_coastal = TRUE
```

---

## 5. 테마별 점수 산출

### 5.1 8개 촬영 테마

| No | 테마명 | 핵심 조건 |
|----|--------|----------|
| 1 | 일출 | 구름 30~60%, 강수확률 <20%, PM2.5 좋음, 동해안 우선 |
| 2 | 일출 오메가 | 수평선 맑음, 해수온 > 기온+5°C, 풍속 <3m/s, 동해안 필수 |
| 3 | 일몰 | 구름 40~70%, 강수확률 <20%, 서해안 우선 |
| 4 | 일몰 오메가 | 일출 오메가와 동일 조건, 서해안 적용 |
| 5 | 은하수 | 월령 신월±3일, 구름 <20%, 광해 낮은 지역 |
| 6 | 야광충 | 수온 18~25°C, 신월±5일, 4~9월, 남해안/동해안 |
| 7 | 바다 장노출 | 파고 0.3~1.0m, 풍랑특보 없음, 간조 전후 2시간 |
| 8 | 운해 | 저지대 습도 >85%, 기온역전, 풍속 <3m/s, 해발 500m+ |

### 5.2 점수 산출 범위
- 점수: 0 ~ 100점
- 시/도 단위 그룹핑 후 테마별 TOP 1 추출
- 전국 테마별 TOP 10 리스트 생성

### 5.3 불확실성 표기 (오메가/야광충)
```
⚠️ 야광충/오메가는 '예측'이 아닌 '가능성 점수'로 표현
- 오메가: "조건 충족 시에도 불확실성 높음, 실제 발생률 ~30%"
- 야광충: "관측 이력 + 수온 기반 가능성, 보장 아님"
```

---

## 6. 추천 알고리즘

### 6.1 처리 흐름
1. 전국 읍/면/동 캐시 JSON 로드 (약 3,500개)
2. 각 지역별 8개 테마 점수 계산 (0~100점)
3. 시/도 단위 그룹핑 → 테마별 TOP 1 추출
4. 전국 테마별 TOP 10 리스트 생성
5. Gemini로 자연어 추천 문구 생성 (TOP N만)

### 6.2 Gemini 호출 최적화
```
무료 할당량: 1,500 요청/일

❌ 읍면동별 호출 → 3,500+ 호출로 초과
✅ 테마별 TOP 10 × 8테마 = 80 호출/일
→ 실제 사용: ~100 호출/일 (여유 확보)
```

---

## 7. 지도 시각화

### 7.1 지도 API 선정

| 단계 | API | 특징 |
|------|-----|------|
| MVP | Leaflet + OSM | 완전 무료, BSD 라이선스 |
| 확장 | Kakao Maps API | 한국 특화, POI 풍부, GeoJSON 지원 |

### 7.2 읍면동 경계 데이터 소스

| 소스 | 라이선스 |
|------|----------|
| 공공데이터포털 SGIS | 공공누리 1유형 |
| VWorld 센서스경계 | 공공누리 |
| GitHub admdongkor | SGIS 가공, 출처표기 필요 |

### 7.3 폴리곤 성능 최적화 (줌 레벨별 로딩)

| 줌 레벨 | 표시 단위 | 폴리곤 수 |
|---------|----------|----------|
| 1~8 | 시도/시군구 | ~17개 |
| 9~11 | 단순화(simplify)된 읍면동 | ~500개 |
| 12+ | 현재 bbox 내 고해상도 | 동적 |

---

## 8. 프로젝트 구조

```
photospot-korea/
├── config/
│   ├── settings.py           # API 키, 환경변수
│   └── weights.json          # 테마별 가중치
├── data/
│   ├── regions.db            # SQLite 정본 DB
│   ├── cache/                # JSON 캐시 (날짜별)
│   ├── boundaries/           # GeoJSON 경계 파일
│   └── ocean_mapping.db      # 해양-읍면동 매칭
├── collectors/
│   ├── kma_forecast.py       # 기상청 단기예보
│   ├── openmeteo.py          # Open-Meteo
│   ├── airkorea.py           # 에어코리아
│   └── khoa_ocean.py         # 바다누리 해양
├── processors/
│   ├── data_merger.py        # 복수 API 평균값 + 편차 플래그
│   └── cache_writer.py       # JSON 캐시 저장
├── scorers/
│   ├── base_scorer.py        # 점수 산출 베이스 클래스
│   └── theme_scorers.py      # 8개 테마 스코어러
├── recommenders/
│   └── region_recommender.py # 시도별 TOP 추출
├── curators/
│   └── gemini_curator.py     # LLM 문구 생성 (TOP N만)
├── messengers/
│   └── telegram_bot.py       # Telegram 발송
├── api/
│   └── main.py               # FastAPI 웹 API
├── scheduler.py              # APScheduler
└── warmup.py                 # UptimeRobot 핑 응답
```

---

## 9. API 엔드포인트 (예정)

### 9.1 공개 API

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/health` | 헬스체크 (UptimeRobot 핑용) |
| GET | `/api/v1/themes` | 테마 목록 조회 |
| GET | `/api/v1/themes/{theme_id}/top` | 테마별 TOP 10 지역 |
| GET | `/api/v1/regions/{region_code}` | 특정 지역 상세 정보 |
| GET | `/api/v1/regions/{region_code}/forecast` | 특정 지역 예보 |
| GET | `/api/v1/map/boundaries` | 지도 경계 GeoJSON |

### 9.2 내부 API

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/internal/collect` | 데이터 수집 트리거 |
| POST | `/internal/score` | 점수 재계산 트리거 |
| POST | `/internal/notify` | Telegram 알림 발송 |

---

## 10. 환경 변수

```env
# 기상청 API
KMA_API_KEY=

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

# 환경 설정
ENVIRONMENT=development  # development | production
LOG_LEVEL=INFO
```

---

## 11. 비용 분석

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

## 12. 리스크 및 대응

| 리스크 | 대응 전략 | 전환 기준 |
|--------|----------|----------|
| Render 콜드스타트 25초 | UptimeRobot 5분 핑으로 웜업 | 사용자 불만 시 Render Starter($7) |
| Supabase 7일 미활동 정지 | 스케줄러로 매일 DB 쿼리 실행 | Pro($25) 전환 시 정지 없음 |
| Open-Meteo 상업적 이용 제한 | 비상업 커뮤니티 서비스 운영 | 수익화 시 $29/월 구독 |
| 지도 쿼터 초과 | Leaflet+OSM으로 폴백 | 일일 쿼터 80% 도달 시 |
| 오메가/야광충 예측 과장 | '가능성 점수' + 불확실성 표기 | 사용자 피드백 반영 |

---

## 13. 개발 마일스톤

| 단계 | 작업 내용 |
|------|----------|
| 1 | 읍면동 기초 데이터 + 경계 GeoJSON 수급 |
| 2 | 기상청 + Open-Meteo 연동 및 평균값 로직 |
| 3 | 해양 API + 매칭 테이블 구축 |
| 4 | 8개 테마 점수 산출 알고리즘 |
| 5 | 지역별 추천 로직 + JSON 캐시 |
| 6 | Gemini 연동 (TOP N만) |
| 7 | Telegram 봇 + 스케줄러 |
| 8 | 지도 경계 단순화 + 성능 테스트 |
| 9 | Render 배포 + UptimeRobot 설정 |
| 10 | 베타 운영 및 피드백 |

---

*— End of Specification —*
