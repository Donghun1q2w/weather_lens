# Revision History

Chronological log of project modifications.

---

## 2026-07-01 23:06:00 — Telegram 알림 기능 전체 제거

[Detail](revisions/2026-07-01_230600_remove-telegram-notification.md)

- Telegram이 유일 알림 수단이라 알림 파이프라인 전체 삭제: `scripts/messengers/` 패키지(2파일), `internal.py`의 `send_notification`·`POST /internal/notify`·`telegram_configured` 플래그, `scheduler.py`의 `send_daily_recommendations`(20시) job. cron 4→3개.
- config/의존성 정리: `settings.py`·`.env`·`.env.example`의 TELEGRAM_*, `requirements.txt`의 `python-telegram-bot`, `check_config.py`의 Telegram 체크 2건, `internal.py`의 죽은 import(`TELEGRAM_*`, `NATIONAL_TOP`, `GeminiCurator`, `TelegramMessenger`).
- 문서: `CLAUDE.md`(개요·트리·Diagram 3/4/7·Cross-Cutting Notes, 2-phase 파이프라인), `scripts/api/README.md`(`/internal/notify` 블록).
- 보존: `GeminiCurator`·`RegionRecommender` 패키지(Telegram 무관, 앱 미사용화되나 별도 cleanup 대상). `THEME_IDS`·`RegionRecommender`는 `calculate_scores`에서 계속 사용.
- 검증: 코드/문서 telegram 0건, messengers 디렉터리 부재, py_compile 통과, TestClient로 cron 3개·`/notify`→404·`/status`에 telegram 키 없음 확인.
- Plan: [`docs/plans/2026-07-01_225224_remove-telegram-notification.md`](plans/2026-07-01_225224_remove-telegram-notification.md).

---

## 2026-05-01 20:54:40 — Dead code 제거 + __init__.py 재export 정리 + bulk helper 추출

[Detail](revisions/2026-05-01_205440_dead-code-cleanup-and-consolidation.md)

- 9개 파일 삭제: `scripts/models/` 전체(5), `collectors/airkorea.py`, `feedbacks/automation.py`, `processors/{weather_integrator, region_beach_merger}.py`. 모두 호출 사이트 0건 확인.
- `processors/__init__.py` 재export를 `CacheWriter` / `merge_weather_data` / `RegionLoader` 3개로 축소. `feedbacks/__init__.py`에서 `ScorePenaltyManager` / `FeedbackAutomation` 제거. `collectors/__init__.py`에서 `AirKoreaCollector` 제거.
- `internal.py`의 사용 안 하던 `AirKoreaCollector` / `weather_data_to_dict` import line 제거.
- `ops/collect_weather_report.py`: `fetch_openmeteo_bulk` 내 동일 50줄 블록 2회 → `_process_batch_response()` 헬퍼로 추출. 1213 → 1188 라인.
- CLAUDE.md: 디렉터리 트리에서 `models/` 제거, Diagram 4/7에서 dead 노드 제거, Cross-Cutting Notes 갱신.
- 검증: 73 → 64 .py 파일, py_compile 64/64 성공, 잔재 import 0건.
- Plan: [`docs/plans/2026-05-01_204620_dead-code-cleanup-and-consolidation.md`](plans/2026-05-01_204620_dead-code-cleanup-and-consolidation.md). Commits: `91c4a33`.

---

## 2026-05-01 20:08:34 — /simplify 리뷰 반영 (scripts/ 통합 후 정리)

[Detail](revisions/2026-05-01_200834_simplify-consolidation.md)

- scheduler ↔ internal 라우트 통합: 3개 inner async 함수(`run_collection`, `run_scoring`, `run_notification`)를 `internal.py` module-level로 추출 → `collect_weather`, `calculate_scores`, `send_notification`. scheduler 4개 cron job 모두 동일 비즈니스 함수를 직접 await로 호출. `call_internal_api` / `INTERNAL_API_BASE` / `httpx` 제거.
- `scripts/config/logging.py` 신규 — 공용 `configure_logging()` + `LOG_FORMAT`. `main.py` / `scheduler.py` 중복 `logging.basicConfig` 제거.
- `pyproject.toml`: `[tool.setuptools.packages.find]`에 `namespaces = true` 추가 (lifecycle/data namespace 패키지 5개 빌드 포함).
- `scripts/ops/collect_weather_report.py`: `RESULT_DIR.mkdir`을 import 시점 → `run_collection()` 진입 시점으로 이동.
- `scripts/api/routes/internal.py`: `INTERNAL_API_KEY` 중복 정의 제거 → settings에서 import.
- `scripts/__init__.py`: 13줄 → 1줄로 축소. CLAUDE.md에 Architecture 섹션 추가하여 단일 source of truth.
- `docs/{DATABASE_CLEANUP_REPORT, KMA_API_INTEGRATION, COASTAL_CLASSIFICATION_COMPLETE, API_SOURCE_MIGRATION}.md` stale notice에서 하드코딩 날짜 `(2026-05-01)` 제거.
- `scripts/main.py`: `"main:fastapi_app"` → `"scripts.main:fastapi_app"` 잔재 fix.
- `scripts/scheduler.py`: WHAT 주석 3건 제거.
- Plan: [`docs/plans/2026-05-01_190730_consolidate-all-packages-into-scripts.md`](plans/2026-05-01_190730_consolidate-all-packages-into-scripts.md) (사후 정리). Commits: `bd67e43`, `452ab70`.

---

## 2026-05-01 19:46:53 — Consolidate all packages into `scripts/`

[Detail](revisions/2026-05-01_194653_consolidate-all-packages-into-scripts.md)

- 12개 도메인 패키지(`api`, `collectors`, `config`, `curators`, `data`, `feedbacks`, `messengers`, `models`, `processors`, `recommenders`, `scorers`, `utils`) + 진입점 2개(`main.py`, `scheduler.py`)를 모두 `scripts/` 하위로 이동 (renames 84–100% similarity).
- 절대 import 66건에 `scripts.` 접두어 일괄 적용 (42 파일).
- `scripts/scheduler.py`: subprocess → import + `asyncio.to_thread` + `asyncio.wait_for(timeout=1800)` 패턴.
- `render.yaml`: `uvicorn scripts.main:fastapi_app`로 startCommand 갱신.
- `pyproject.toml`: `[tool.setuptools.packages.find]` 블록 추가.
- `scripts/__init__.py` docstring 보강.
- `collectors/example_usage.py` 삭제 (dead code).
- `docs/{DATABASE_CLEANUP_REPORT, KMA_API_INTEGRATION, COASTAL_CLASSIFICATION_COMPLETE, API_SOURCE_MIGRATION}.md` 상단에 stale notice 추가.
- `.gitignore` 평탄 `data/...` 패턴 → `scripts/data/...`로 갱신 + 의도치 않게 추적된 런타임 DB·캐시 untrack (`b9bfb44`).
- BASE_DIR 깊이 갱신은 자원 동시 이동으로 결과적 정합 — plan 4단계는 시행하지 않음 (정정 사항).
- Plan: [`docs/plans/2026-05-01_190730_consolidate-all-packages-into-scripts.md`](plans/2026-05-01_190730_consolidate-all-packages-into-scripts.md). Commits: `cf94a38`, `dcf7823`, `b9bfb44`.

---

## 2026-05-01 18:34:14 — Reorganize `scripts/` by lifecycle

[Detail](revisions/2026-05-01_183414_reorganize-scripts-by-lifecycle.md)

- Moved 14 flat scripts into `scripts/{setup,ingest,ops,dev}/` (renames detected at 92–99% similarity).
- Patched `PROJECT_ROOT` path depth in 13 scripts + `import_json_helper.py:7` `DB_PATH` for the new directory level.
- `scheduler.py:75` redirected to `scripts/ops/collect_weather_report.py`.
- Updated docstring usage hints inside moved scripts to reflect new paths.
- Deleted unreferenced `warmup.py` shim (0 imports across the repo).
- New subfolders use namespace packages (no `__init__.py`); existing `scripts/__init__.py` preserved.
- Plan: [`docs/plans/2026-05-01_181800_reorganize-scripts-by-lifecycle.md`](plans/2026-05-01_181800_reorganize-scripts-by-lifecycle.md). Commits: `6c001f8`, `fdf42c4`, `92ec301`.

---

## 2026-05-01 18:01:38 — Cleanup tests, caches, and untracked result outputs

[Detail](revisions/2026-05-01_180138_cleanup-tests-and-result-outputs.md)

- `tests/test_cache_writer.py` — Deleted (sole test file, per user request)
- `tests/`, `.pytest_cache/`, `무제 폴더/` — Deleted (empty/cache directories)
- `weatherlens.db`, `.DS_Store` ×3 — Deleted (placeholders / OS junk)
- `result/forecast_merged_*.json` ×7, `result/forecast_scores_*.json` ×7, `result/latest.md` — Deleted (~454 MB of regeneratable outputs)
- `verify_implementation.py`, `scripts/{fix_database,generate_regions_list,integrate_worker_outputs,mark_south_coast,process_jeolla_regions,verify_jeolla_output,verify_ocean_stations}.py` — Staged via `git rm` (already removed from disk)

---
