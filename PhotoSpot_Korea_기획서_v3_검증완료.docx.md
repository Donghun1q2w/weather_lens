풍경사진가를 위한

**날씨 기반 출사지 큐레이션 서비스**

기획서 v3.0 (커뮤니티 검증 반영)

*프로젝트명: PhotoSpot Korea*

작성일: 2026년 1월 29일 | Reddit/GitHub 검증 완료

# **1\. GPT 제안 서비스 검증 결과**

GPT가 제안한 서비스들의 실제 무료 사용 가능 여부를 Reddit, GitHub 커뮤니티 및 공식 문서에서 검증했습니다.

## **1.1 데이터베이스 서비스**

| 서비스 | 무료 티어 | 검증 결과 | 권장 여부 |
| ----- | ----- | ----- | ----- |
| Supabase | 500MB DB, 50K MAU | ✅ 검증됨: 7일 미활동 시 일시정지, 프로젝트 2개 제한 | ✅ 1순위 권장 (MVP\~프로덕션) |
| Neon | 0.5GB/프로젝트, 100 CU-hours | ✅ 검증됨: Databricks 인수 후 무료 티어 강화 (2025.10) | ✅ 2순위 권장 (서버리스 선호 시) |
| SQLite | 완전 무료 (로컬) | ✅ 최적: 설치 없이 파일 1개로 운영 | ✅ MVP 단계 최적 |

## **1.2 호스팅 서비스**

| 서비스 | 무료 티어 | 검증 결과 | 권장 여부 |
| ----- | ----- | ----- | ----- |
| Render | 750시간/월, 1GB DB | ⚠️ 주의: 15분 미활동 시 슬립, 콜드스타트 25초 | ⚠️ 조건부 권장 (UptimeRobot으로 웜업 필수) |
| Railway | $5 크레딧 (30일) | ⚠️ 주의: 영구 무료 아님, Hobby $5/월 필수 | ⚠️ 완전 무료 불가 (최소 $5/월) |

## **1.3 기상 API**

| 서비스 | 무료 티어 | 검증 결과 | 권장 여부 |
| ----- | ----- | ----- | ----- |
| 기상청 단기예보 | 무제한 (공공데이터) | ✅ 최적: 한국 전용, 정확도 높음 | ✅ Primary 소스 |
| Open-Meteo | 10,000콜/일 (비상업) | ✅ 검증됨: API키 불필요, CC BY 4.0 | ✅ Secondary 소스 (글로벌) |
| OpenWeatherMap | 1,000콜/일, 60콜/분 | ✅ 검증됨: 상업적 이용 가능 (출처 표기) | ✅ Tertiary 소스 (검증용) |
| AccuWeather | 14일 트라이얼 \+ 50콜 | ❌ 탈락: 장기 무료 아님, 트라이얼 성격 | ❌ 사용 불가 |

## **1.4 지도 API**

| 서비스 | 무료 티어 | 검증 결과 | 권장 여부 |
| ----- | ----- | ----- | ----- |
| Kakao Maps API | 무료 쿼터 제공 (앱별) | ✅ 검증됨: 한국 특화, GeoJSON 지원 | ✅ 1순위 권장 |
| Leaflet \+ OSM | 완전 무료 (오픈소스) | ✅ 최적: 상업적 이용 가능 (BSD) | ✅ 대안 (비용 0원) |
| Naver Maps (Ncloud) | 월 무료 이용량 존재 | ⚠️ 주의: AI NAVER API 무료 종료, Ncloud만 무료 | ⚠️ Ncloud Maps 한정 사용 |

# **2\. 검증 기반 시스템 아키텍처**

## **2.1 데이터 흐름 (수정안)**

**\[기상청 \+ Open-Meteo\] → \[평균값\] → \[읍면동 JSON\] → \[테마 점수\] → \[Gemini 큐레이션\] → \[Telegram 발송\]**

## **2.2 확정 기술 스택**

| 구분 | 선정 기술 | 선정 사유 |
| :---: | ----- | ----- |
| 언어 | Python 3.10+ | FastAPI/APScheduler 생태계, 초보자 친화 |
| DB (MVP) | SQLite | 설치 없음, 파일 1개, 동시접속 낮은 MVP에 최적 |
| DB (확장) | Supabase Postgres | 500MB 무료, REST API 내장, 인증/스토리지 포함 |
| 호스팅 | Render Free \+ UptimeRobot | 15분 슬립을 5분 핑으로 회피, 750시간/월 충분 |
| 기상 API (1차) | 기상청 단기예보 | 한국 공식, 무제한, 3시간 간격 갱신 |
| 기상 API (2차) | Open-Meteo | 10K콜/일 무료, API키 불필요, 글로벌 모델 |
| 지도 API | Kakao Maps 또는 Leaflet+OSM | Kakao: 한국 특화 / OSM: 완전 무료 |
| LLM | Gemini 1.5 Flash | 무료 1,500콜/일, 추천 문구 생성에 충분 |
| 메시징 | Telegram Bot | 완전 무료, 제한 없음, 그룹/채널 지원 |

# **3\. 데이터 수집 전략 (수정)**

## **3.1 복수 API 평균값 \- 수정된 조합**

**💡 핵심 변경: AccuWeather 제외 → Open-Meteo로 대체 (장기 무료 검증됨)**

| 데이터 항목 | Primary (기상청) | Secondary (Open-Meteo) |
| ----- | ----- | ----- |
| 기온/습도/풍속 | 단기예보 VilageFcstInfoService | open-meteo.com/en/docs (temperature\_2m 등) |
| 강수확률/강수량 | 단기예보 POP/PCP | Open-Meteo precipitation\_probability |
| 하늘상태/구름량 | 단기예보 SKY | Open-Meteo cloud\_cover |
| 미세먼지 | 에어코리아 (단일 소스) | 측정소 매핑으로 읍면동 연결 |

**평균값 산출 로직:**

final\_value \= (kma\_value × 0.6 \+ openmeteo\_value × 0.4)  \# 기상청 가중치 높음if abs(kma \- openmeteo) \> threshold: set deviation\_flag \= True  \# 편차 경고

## **3.2 예보 데이터 수집 범위**

* D-day \~ D+2 (3일간) \- 단기예보 기준  
* 3시간 간격 데이터 (일 8회 갱신)  
* Open-Meteo: hourly 데이터로 더 세밀한 보간 가능

## **3.3 해양 데이터 (변경 없음)**

| API명 | 제공 데이터 | 출처 |
| ----- | ----- | ----- |
| 바다누리 조석예보 | 만조/간조 시각, 조위 | 국립해양조사원 (무료) |
| 바다누리 파고정보 | 유의파고, 파주기 | 국립해양조사원 (무료) |
| 해수온 관측 | 표층 수온 (야광충 예측) | 바다누리/기상청 (무료) |

# **4\. 데이터 저장 구조**

## **4.1 2단계 저장 전략 (GPT 제안 반영)**

읍면동 3,500개 × 날짜 × 시간별 JSON 파일은 관리 난도가 높으므로, DB \+ 캐시 2계층 구조 채택:

| 계층 | 저장소 | 용도 |
| ----- | ----- | ----- |
| 정본 (Source of Truth) | SQLite → Supabase Postgres | 읍면동 메타, 점수 이력, 추천 결과 |
| 캐시 (Fast Access) | JSON 파일 (날짜별 폴더) | 당일\~D+2 예보, API 응답 속도 향상 |

## **4.2 읍면동 JSON 스키마 (수정)**

파일: /data/cache/{date}/{sido}\_{sigungu}\_{emd}.json

{  "region\_code": "1168010100",  "region\_name": "서울특별시 강남구 역삼동",  "coordinates": { "lat": 37.5000, "lng": 127.0364 },  "updated\_at": "2026-01-29T06:00:00+09:00",  "forecast": \[    {      "datetime": "2026-01-29T06:00:00",      "temp": { "kma": \-3.2, "openmeteo": \-2.8, "avg": \-3.0, "deviation\_flag": false },      "cloud": { "kma": 30, "openmeteo": 35, "avg": 32 },      "rain\_prob": { "kma": 10, "openmeteo": 12, "avg": 11 },      "pm25": 18,      "sunrise": "07:35", "sunset": "17:52"    }  \],  "ocean\_station\_id": "DT\_0001"  // 해안 지역만}

## **4.3 해양-읍면동 매칭 테이블**

SQLite 테이블: ocean\_region\_mapping

CREATE TABLE ocean\_region\_mapping (  region\_code TEXT PRIMARY KEY,  region\_name TEXT,  ocean\_station\_id TEXT,  ocean\_station\_name TEXT,  distance\_km REAL,  is\_coastal BOOLEAN DEFAULT FALSE);-- 해안선 30km 이내만 is\_coastal \= TRUE

# **5\. 출사 테마별 점수 산출**

## **5.1 8개 테마 (GPT 제안 반영)**

| No | 테마명 | 핵심 조건 요약 |
| :---: | ----- | ----- |
| 1 | 일출 | 구름 30\~60%, 강수확률 \<20%, PM2.5 좋음, 동해안 우선 |
| 2 | 일출 오메가 | 수평선 맑음, 해수온 \> 기온+5°C, 풍속 \<3m/s, 동해안 필수 |
| 3 | 일몰 | 구름 40\~70%, 강수확률 \<20%, 서해안 우선 |
| 4 | 일몰 오메가 | 일출 오메가와 동일, 서해안 적용 |
| 5 | 은하수 | 월령 신월±3일, 구름 \<20%, 광해 낮은 지역 |
| 6 | 야광충 | 수온 18\~25°C, 신월±5일, 4\~9월, 남해안/동해안 |
| 7 | 바다 장노출 | 파고 0.3\~1.0m, 풍랑특보 없음, 간조 전후 2시간 |
| 8 | 운해 | 저지대 습도 \>85%, 기온역전, 풍속 \<3m/s, 해발 500m+ |

## **5.2 야광충/오메가 불확실성 표기 (GPT 비판 반영)**

⚠️ 야광충/오메가는 '예측'이 아닌 '가능성 점수'로 표현합니다.• 오메가: "조건 충족 시에도 불확실성 높음, 실제 발생률 \~30%" 표기• 야광충: "관측 이력 \+ 수온 기반 가능성, 보장 아님" 표기• 메시지에 항상 불확실성 플래그 포함

# **6\. 지역별 추천 로직**

## **6.1 추천 알고리즘**

1. 전국 읍/면/동 캐시 JSON 로드 (약 3,500개)  
2. 각 지역별 8개 테마 점수 계산 (0\~100점)  
3. 시/도 단위 그룹핑 → 테마별 TOP 1 추출  
4. 전국 테마별 TOP 10 리스트 생성  
5. Gemini로 자연어 추천 문구 생성 (TOP N만)

## **6.2 Gemini 호출 최적화 (GPT 비판 반영)**

💡 Gemini 무료 할당량: 일 1,500 요청• 읍면동별 호출 ❌ → 3,500+ 호출로 초과• 테마별 TOP 10 × 8테마 \= 80 호출/일 ✅• 실제 사용: \~100 호출/일 (여유 확보)

# **7\. 지도 시각화 전략**

## **7.1 지도 API 최종 선정**

네이버 지도 AI NAVER API는 무료 이용량 종료로 제외, Kakao Maps 또는 Leaflet+OSM 선택:

| 옵션 | 장점 | 단점 |
| ----- | ----- | ----- |
| Kakao Maps API | 한국 특화, POI 풍부, GeoJSON 지원 | 무료 쿼터 제한 있음 (앱별) |
| Leaflet \+ OSM | 완전 무료, 상업적 이용 OK, BSD 라이선스 | 한국 POI 빈약, 한글 지명 부족 |

**권장: MVP는 Leaflet+OSM으로 비용 0원 시작 → 트래픽 증가 시 Kakao Maps 전환**

## **7.2 읍면동 경계 데이터 (GPT 제안 반영)**

| 소스 | URL/위치 | 라이선스 |
| ----- | ----- | ----- |
| 공공데이터포털 SGIS | data.go.kr (행정구역 경계) | 공공누리 1유형 |
| VWorld 센서스경계 | data.go.kr (행정동경계) | 공공누리 |
| GitHub admdongkor | github.com/vuski/admdongkor | SGIS 가공, 출처표기 필요 |

## **7.3 3,500개 폴리곤 성능 전략**

줌 레벨별 단계적 로딩으로 브라우저 부하 방지:

* Zoom 1\~8: 시도/시군구 단위만 표시 (17개 폴리곤)  
* Zoom 9\~11: 단순화(simplify)된 읍면동 표시  
* Zoom 12+: 현재 bbox 내 고해상도 폴리곤만 로딩

# **8\. 프로젝트 구조 (수정)**

photospot-korea/├── config/│   ├── settings.py           \# API 키, 환경변수│   └── weights.json          \# 테마별 가중치├── data/│   ├── regions.db            \# SQLite 정본 DB│   ├── cache/                \# JSON 캐시 (날짜별)│   ├── boundaries/           \# GeoJSON 경계 파일│   └── ocean\_mapping.db      \# 해양-읍면동 매칭├── collectors/│   ├── kma\_forecast.py       \# 기상청 단기예보│   ├── openmeteo.py          \# Open-Meteo (AccuWeather 대체)│   ├── airkorea.py           \# 에어코리아│   └── khoa\_ocean.py         \# 바다누리 해양├── processors/│   ├── data\_merger.py        \# 복수 API 평균값 \+ 편차 플래그│   └── cache\_writer.py       \# JSON 캐시 저장├── scorers/│   ├── base\_scorer.py        \# 점수 산출 베이스│   └── theme\_scorers.py      \# 8개 테마 통합├── recommenders/│   └── region\_recommender.py \# 시도별 TOP 추출├── curators/│   └── gemini\_curator.py     \# LLM 문구 (TOP N만)├── messengers/│   └── telegram\_bot.py       \# 텔레그램 발송├── api/│   └── main.py               \# FastAPI (웹앱용)├── scheduler.py              \# APScheduler└── warmup.py                 \# UptimeRobot 핑 응답

# **9\. 개발 일정 (수정)**

**💡 GPT 피드백 반영: 지도 경계 \+ 성능 테스트 스프린트 추가**

| 단계 | 작업 내용 | 예상 기간 |
| :---: | ----- | :---: |
| 1 | 읍면동 기초 데이터 \+ 경계 GeoJSON 수급 | 1주 |
| 2 | 기상청 \+ Open-Meteo 연동 및 평균값 로직 | 2주 |
| 3 | 해양 API \+ 매칭 테이블 구축 | 1주 |
| 4 | 8개 테마 점수 산출 알고리즘 | 2주 |
| 5 | 지역별 추천 로직 \+ JSON 캐시 | 1주 |
| 6 | Gemini 연동 (TOP N만) | 1주 |
| 7 | Telegram 봇 \+ 스케줄러 | 1주 |
| 8 | 🆕 지도 경계 단순화 \+ 성능 테스트 | 1주 (추가) |
| 9 | Render 배포 \+ UptimeRobot 설정 | 1주 |
| 10 | 베타 운영 및 피드백 | 2주 |

**총 예상 개발 기간: 약 13주 (기존 11주 \+ 지도/성능 2주)**

# **10\. 비용 분석**

| 항목 | MVP 단계 | 확장 단계 | 비고 |
| ----- | ----- | ----- | ----- |
| DB | $0 (SQLite) | $0 (Supabase Free) | 500MB 한도 |
| 호스팅 | $0 (Render Free) | $0\~7 (Render Starter) | 슬립 회피 필수 |
| 기상 API | $0 (기상청+Open-Meteo) | $0 | 무제한 |
| 지도 API | $0 (Leaflet+OSM) | $0 (Kakao 무료 쿼터) | 쿼터 모니터링 |
| LLM | $0 (Gemini Free) | $0 | 1,500콜/일 |
| 메시징 | $0 (Telegram) | $0 | 완전 무료 |

**✅ MVP 총 비용: $0/월 | 확장 단계: $0\~7/월 (안정성 향상 시)**

# **11\. 리스크 및 대응 전략**

| 리스크 | 대응 전략 | 전환 기준 |
| ----- | ----- | ----- |
| Render 콜드스타트 25초 | UptimeRobot 5분 핑으로 웜업 유지 | 사용자 불만 시 Render Starter($7) |
| Supabase 7일 미활동 정지 | 스케줄러로 매일 DB 쿼리 실행 | Pro($25) 전환 시 정지 없음 |
| Open-Meteo 상업적 이용 제한 | 비상업 커뮤니티 서비스로 운영 | 수익화 시 $29/월 구독 |
| 지도 쿼터 초과 | Leaflet+OSM으로 폴백 | 일일 쿼터 80% 도달 시 |
| 오메가/야광충 과장 비판 | '가능성 점수' \+ 불확실성 표기 | 사용자 피드백 반영 |

*— End of Document —*

검증 소스: Reddit, GitHub Discussions, 공식 Pricing/Docs 페이지