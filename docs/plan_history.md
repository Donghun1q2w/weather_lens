# Plan History

Chronological log of project plans (newest first).

---

## 2026-05-01 21:35:29 — KHOA / Beach 파고(wave) 데이터 미수집 디버깅

[Detail](plans/2026-05-01_213529_khoa-wave-data-debug.md)

**Status**: Proposed

전수 테스트(`f6220fc`) 결과 18개 테마 중 "바다 장노출(동/서/남해)" 3종이 7,232 표본 전체에서 0점, factors.reason="no wave data"로 산출됨. ThemeScorer는 정상이지만 입력 marine_data의 `wave_height`가 비어 있음. fetch_beach_marine_data ↔ get_merged_forecast_data 흐름의 root cause 후보 5개(silent except / key mismatch / API auth / response shape / async failure) 진단 후 수정. 단계 1은 `scripts/dev/check_marine_fetch.py` 격리 호출로 1~3개 beach 응답 raw 검증, 단계 2는 root cause에 따라 분기 수정. 수용 기준: 전수 재실행 시 "해양 데이터 포함: N>0개", 바다 장노출 비0 region ≥ 1.

---

## 2026-05-01 20:46:20 — Dead code cleanup + consolidation

[Detail](plans/2026-05-01_204620_dead-code-cleanup-and-consolidation.md)

**Status**: Completed (2026-05-01 20:55, commit `91c4a33`)

`/dh-dev` 1-a explore 결과 식별된 통합/간결화 후보 5개 카테고리 처리: (A) Dead code 제거 — `models/{region,weather,ocean,feedback}.py` 전체, `collectors/airkorea.py`, `feedbacks/automation.py`. (B) 미사용 processor 함수 — `weather_integrator.py`, `region_beach_merger.py` 전체. (C) `__init__.py` re-export 정리 — `processors/__init__.py` 13+ internal-only 항목, `feedbacks/__init__.py`, `collectors/__init__.py`. (D) `ops/collect_weather_report.py` `fetch_openmeteo_bulk`의 동일 블록 2회를 `_process_batch_response()` 헬퍼로 추출. (E) KMA collector 공통 dict 이관은 보류 (별도 plan). 외부 진입점 동작 동일 유지가 acceptance 핵심.

---

## 2026-05-01 19:07:30 — Consolidate all packages into `scripts/`

[Detail](plans/2026-05-01_190730_consolidate-all-packages-into-scripts.md)

**Status**: Completed (2026-05-01 19:50, commits `cf94a38`, `dcf7823`, `b9bfb44`)

루트의 12개 도메인 패키지(`api/`, `collectors/`, `config/`, `curators/`, `data/`, `feedbacks/`, `messengers/`, `models/`, `processors/`, `recommenders/`, `scorers/`, `utils/`)와 두 진입점(`main.py`, `scheduler.py`)을 모두 `scripts/` 하위로 통합. 모든 절대 import에 `scripts.` 접두어 추가, `render.yaml`의 startCommand를 `uvicorn scripts.main:fastapi_app`으로 갱신, `config/settings.py` `BASE_DIR` 깊이 갱신, `scheduler.py`의 ops 호출을 subprocess → import + `asyncio.to_thread` 형태로 전환, `pyproject.toml`에 setuptools 패키지 발견 블록 추가, `collectors/example_usage.py`(dead code) 삭제, docs/ stale 문서 4건에 stale notice 헤더 추가. 직전 plan(`2026-05-01_181800_...`)의 “out of scope” 결정을 명시적으로 뒤집음.

---

## 2026-05-01 18:18:00 — Reorganize `scripts/` by lifecycle

[Detail](plans/2026-05-01_181800_reorganize-scripts-by-lifecycle.md)

**Status**: Completed (2026-05-01 18:35, commits `6c001f8`, `92ec301`)

Restructure flat `scripts/` (14 files) into 4 lifecycle subfolders — `setup/`, `ingest/`, `ops/`, `dev/`. Patch `PROJECT_ROOT` path math in every moved script (`parent.parent` → `parent.parent.parent`), redirect `scheduler.py:75` to `scripts/ops/collect_weather_report.py`, and delete the unreferenced `warmup.py` shim. `main.py` and `scheduler.py` remain at root as runtime entry points.

---
