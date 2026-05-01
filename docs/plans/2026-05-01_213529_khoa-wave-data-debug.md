# KHOA / Beach 파고(wave) 데이터 미수집 디버깅

- **작성일**: 2026-05-01 21:35:29
- **상태**: 제안됨 (Proposed)
- **작성자**: Claude Code (사용자 요청)
- **선행 검증**: 2026-05-01 전수 테스트(`f6220fc`) 결과 — `해양 데이터 포함: 0개 해수욕장`, "바다 장노출(동/서/남해)" 3개 테마 모두 7,232 표본 전체가 0점, factors.reason="no wave data".

## 요약

전수 테스트에서 18개 테마 중 16개는 정상 점수 분포를 보였으나, **바다 장노출 3종(동·서·남해)** 만 모든 region·일자에서 score=0으로 산출됨. 모든 0점의 사유는 `factors.reason: "no wave data"` — 즉 ThemeScorer가 정상 동작했지만 입력 marine_data에 `wave_height`가 채워지지 않은 것. 본 plan은 이 누락의 root cause를 단계적으로 좁혀 수정한다.

## 배경

### 검증된 사실

- `scripts/ops/generate_forecast_report.py:682-686`: `if beaches and BEACH_API_KEY_TO_USE:` 분기에서 `asyncio.run(fetch_beach_marine_data(beaches, BEACH_API_KEY_TO_USE))` 호출. `BEACH_API_KEY_TO_USE = BEACH_API_KEY or KMA_API_KEY`(line 49). `.env`에 `BEACH_API_KEY` 존재 확인됨.
- `scripts/ops/generate_forecast_report.py:442` `fetch_beach_marine_data` 본체: `BeachInfoCollector(api_key)`로 파고 호출, `KHOAOceanCollector(api_key)`로 조석/수온 호출. 결과를 `marine_data = {wave_height, sea_temperature, tide_info, sun_info, moon_info}` dict로 묶어 `Dict[beach_code, marine_data]` 반환.
- `scripts/ops/generate_forecast_report.py:511-518` 파고 호출 코드:
  ```python
  wave_data = await collector.get_wave_height(beach_num, search_time)
  if wave_data and wave_data.get("items"):
      items = wave_data["items"]
      ...
      marine_data["wave_height"] = {"height": ...}
  ```
  실패 시 wave_height는 `None`으로 남음.
- `scripts/ops/generate_forecast_report.py:269-280` `get_merged_forecast_data`에서 `beach_marine_data[beach_code]`를 `beach_entry["marine"]`로 set. 그러나 `beach_marine_data`의 키가 `beach_code` 형식이고, `beaches`의 키가 다를 가능성.
- `scripts/scorers/theme_scorers.py:1093-1098` `SeaLongExposureEastScorer`의 GATE: `if not marine_data or not marine_data.get("wave_height"): return {"score": 0, "factors": {"reason": "no wave data"}, "time_used": "N/A"}` — 결과적으로 wave_height가 None 또는 missing이면 0점.
- 전수 테스트 stdout에 `해양 데이터 포함: 0개 해수욕장` (line 285의 print). 즉 `merged_data` 의 어떤 beach 항목에도 `b.get("marine")`이 truthy로 나오지 않음. (sample 50, full 3616 모두 동일)

### 가능한 Root cause (가설, 우선순위)

| # | 가설 | 근거 | 검증 방법 |
|---|---|---|---|
| H1 | `fetch_beach_marine_data`가 **빈 dict 반환** (모든 beach 처리에서 try/except로 실패 묵살) | 진행 메시지조차 stdout에 안 나옴 (전수 로그 검토 시 "해양 데이터 수집" 류 print 없음) — 함수가 일찍 return 하거나 실패가 silent | 1개 beach에 대해 함수를 격리 호출, 결과 dict 직접 검증 |
| H2 | `get_merged_forecast_data`의 **키 매칭 실패** — `beach_marine_data[beach_code]`의 `beach_code`가 `beaches[i]`의 매칭 키와 다름 | line 269-280 재검토 필요 | merged_data 산출물의 beach 항목 sample을 dump해 marine 키 존재 여부 확인 |
| H3 | `BEACH_API_KEY` / `KMA_API_KEY`가 KHOA / Beach API에 **권한 없음** | 4개 API 키가 각각 다른 서비스 계정 가능성. KMA fallback이 BeachInfo API에서 거부될 수 있음 | 1개 beach·1개 시점으로 직접 호출해 응답 코드/메시지 확인 |
| H4 | KHOA/Beach API가 **응답 없거나 빈 items 반환** (search_time 형식 불일치, 영업일/시간 제한 등) | line 511의 `search_time` 인자 — 어떤 형식인지 확인 필요 | 동일 |
| H5 | **timeout/concurrency 문제** — 비동기 호출 누락 또는 silent 실패 | 비동기 코드의 예외 mask 가능성 | 함수에 `print` 또는 `logger.exception` 추가 |

H1·H2가 가장 가능성 높음. 1단계 진단으로 좁힐 예정.

## 제안

### 단계 1: 진단 (코드 변경 없이 실행)

1. **격리 단위 테스트** — `scripts/dev/`에 1회용 진단 스크립트 작성:
   ```python
   # scripts/dev/check_marine_fetch.py
   import asyncio, json
   from scripts.config.settings import BEACH_API_KEY, KMA_API_KEY
   from scripts.ops.generate_forecast_report import (
       fetch_beach_marine_data, load_beaches_from_db
   )

   async def main():
       beaches = load_beaches_from_db()
       sample = beaches[:3]
       result = await fetch_beach_marine_data(sample, BEACH_API_KEY or KMA_API_KEY)
       print(json.dumps(result, ensure_ascii=False, indent=2)[:2000])
       print(f"\nbeach_codes returned: {list(result.keys())}")
       print(f"sample beach codes: {[b.get('code') or b.get('beach_num') for b in sample]}")

   asyncio.run(main())
   ```
2. **결과 분석 분기**:
   - **결과 비어있음 (H1 확인)** → fetch_beach_marine_data 내부 try/except 묵살. logger.exception 추가, 한 번 더 실행하여 stack trace 확인 → API 키/엔드포인트 결함이면 H3, 응답 형식이면 H4.
   - **결과는 있는데 wave_height=None** → H4. `get_wave_height` 응답 raw dump해서 items 구조 검증.
   - **결과는 있는데 merged 후 marine 사라짐** → H2. `get_merged_forecast_data`의 key 매칭 라인 점검.

### 단계 2: 수정 (root cause 확정 후)

|  Root cause | 수정 내용 |
|---|---|
| H1 (silent except) | try/except를 좁히고 `logger.error(traceback)` 도입. 실패 시 retry 1회 + 명시적 stdout 진행 메시지. |
| H2 (key mismatch) | `beach_marine_data` dict의 키와 `beaches[i]`의 매칭 키를 명시화. (`beach_num` vs `beach_code` vs `beach_id`?) |
| H3 (auth) | `.env.example`/문서에 정확한 BEACH_API_KEY / KHOA_API_KEY 출처 명시. `BEACH_API_KEY_TO_USE` fallback 로직 재검토. |
| H4 (response shape) | items 파싱 코드 보정 + `search_time` 포맷 검증. |
| H5 (silent failure) | `fetch_beach_marine_data`의 외부 try/except를 narrow하게 + 진행 메시지 추가. |

### 영향 범위

- **수정 대상 후보**: `scripts/ops/generate_forecast_report.py` (fetch_beach_marine_data, get_merged_forecast_data), 잠재적으로 `scripts/collectors/{khoa_ocean, beach_info}.py` (응답 파싱), `scripts/config/settings.py` (API 키 정의)
- **scoring 영향**: SeaLongExposure 3개 테마(동/서/남해)가 0점에서 정상 분포로 회복.
- **외부 호출**: 진단 단계는 1~3개 beach만 호출(<1초). 단계 2 검증 시 sample 50 beach 호출 (~30초).

### 리스크 표

| 리스크 | 가능성 | 영향 | 대응 |
|---|---|---|---|
| API 응답 포맷 변경/Rate Limit | 중간 | 중간 | 진단 시 raw response 저장하여 재현 |
| `BEACH_API_KEY` 권한 부족 (KMA_API_KEY로 fallback) | 중간 | 높음 | 키 출처를 .env.example에 명시 |
| `search_time` 형식 / 시간대 mismatch | 낮음 | 중간 | KST/UTC 모두 시도 |
| 진단 스크립트가 .env 미로드로 실패 | 낮음 | 낮음 | python-dotenv 명시적 로드 |

### 수용 기준

- [ ] `python scripts/dev/check_marine_fetch.py` 실행 시 1개 이상의 beach에 대해 `wave_height: {"height": <float>, ...}` 형태의 비-None 값 반환.
- [ ] 전수 테스트 재실행 시 `해양 데이터 포함: N개 해수욕장` (N > 0).
- [ ] forecast_scores JSON에서 "바다 장노출(동/서/남해)" 중 최소 한 종류는 비0 점수 region이 ≥ 1개 존재.
- [ ] py_compile / 기존 18 theme 점수 분포 비-회귀.
- [ ] `fetch_beach_marine_data`에 진행 메시지(`[X/Y] beach marine 수집 중...` 또는 logger.info) 도입.

### 검증 단계

1. **격리 단위 테스트** (단계 1).
2. **단계 2 적용 후 sample 50 + days 1 재실행**.
3. **단계 2 적용 후 full 3616 + days 1 재실행** — 6분 예상.
4. **stat 비교**: 직전 결과(`forecast_scores_20260501_211400.json`) ↔ 새 결과 — wave_height 채워진 beach 수, 바다 장노출 점수 분포 변화.

## Open Questions

1. KHOA 파고 API와 BeachInfo 파고 API 중 어느 것이 본 reorg에서 의도된 wave 출처인가? (`khoa_ocean.py:56` `collect_wave: bool = True`로 KHOA도 wave 가능, `BeachInfoCollector.get_wave_height`도 별도) — 진단 결과로 명확화.
2. KHOA에 wave_height 메서드가 있는데 `khoa_ocean.py`가 현재 tide만 collector 메인 흐름에 등록 — wave는 BeachInfoCollector가 담당? 코드 의도 사용자 컨펌.
3. 본 작업을 ralph/dh-dev로 전체 자동화할지, 진단(단계 1)만 먼저 보고하고 사용자 결정 받을지.

## 적용 범위 외

- 다른 16개 테마 점수 분포 조정.
- KHOA tide/sea_temperature 데이터 흐름 (별개 — 이미 일부 동작 중).
- ThemeScorer 알고리즘 변경.
- `run_collection`(MD report) 흐름의 marine 호출 — 별도 경로.
