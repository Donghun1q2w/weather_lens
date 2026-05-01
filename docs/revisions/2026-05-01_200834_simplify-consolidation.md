# /simplify 리뷰 반영 — scripts/ 통합 후 정리

- **Date**: 2026-05-01 20:08:34
- **Author**: Claude Code (사용자 요청, /simplify 두 패스)
- **Related Plan**: [2026-05-01_190730_consolidate-all-packages-into-scripts.md](../plans/2026-05-01_190730_consolidate-all-packages-into-scripts.md)
- **Commits**: `bd67e43` (1차 — 안전 항목), `452ab70` (2차 — "모두 반영")

## Summary

직전 `scripts/` 통합 reorg(`dcf7823..e0d9681`) 직후 `/simplify`로 3개 review agent(reuse / quality / efficiency)를 병렬 실행해 발견사항을 모두 반영. 1차에서 안전한 3건, 2차에서 사용자 "모두 반영" 지시에 따라 잔여 HIGH/MED/LOW를 모두 처리. scheduler-internal API 통합으로 가장 큰 inconsistency가 사라지고, 공용 logging 모듈, 문서 단일화, 잔재 typo 수정까지 마무리.

## Rationale / Plan

`/simplify`의 3개 agent가 다음을 보고:
- **HIGH**: scheduler가 ops 패키지를 직접 import (`run_collection`)하면서 다른 3개 cron job은 HTTP self-loopback(`call_internal_api`)을 사용 — 두 패턴이 공존하는 inconsistency.
- **MED**: `INTERNAL_API_BASE` 하드코딩, `INTERNAL_API_KEY` 이중 default, `RESULT_DIR.mkdir`가 import 시점 부수효과, `pyproject.toml` packages discovery가 namespace package 5개를 누락, docs 4개에 동일 stale notice 하드코딩 날짜.
- **LOW**: `scripts/__init__.py` 13줄 docstring이 빈 CLAUDE.md와 분리되어 발견 어려움, `main.py`/`scheduler.py`의 `logging.basicConfig` 중복, `main.py:49`의 옛 진입점 문자열 잔재, scheduler.py의 WHAT 주석 3건.

1차에서 안전 항목(pyproject namespaces, mkdir 이동, 주석 제거) 적용, 2차에서 사용자 "모두 반영" 지시로 큰 통합 작업까지 마무리.

## Changed Files

### Commit `bd67e43` (1차 — 안전 항목)

| File | Status | Description |
|------|--------|-------------|
| `pyproject.toml` | Modified | `[tool.setuptools.packages.find]`에 `namespaces = true` 추가 (lifecycle / data 등 `__init__.py` 없는 namespace package 5개도 빌드 대상에 포함) |
| `scripts/ops/collect_weather_report.py` | Modified | `RESULT_DIR.mkdir(exist_ok=True)`을 모듈 import 시점 → `run_collection()` 함수 진입 시점으로 이동 |
| `scripts/scheduler.py` | Modified | WHAT 주석 3건 제거 (`# Configure logging`, `# Initialize scheduler`, `# Internal API base URL`) |

### Commit `452ab70` (2차 — "모두 반영")

| File | Status | Description |
|------|--------|-------------|
| `scripts/api/routes/internal.py` | Modified | 3개 inner async 함수(`run_collection`, `run_scoring`, `run_notification`)를 module-level로 추출 → `collect_weather`, `calculate_scores`, `send_notification`. API 라우트는 그 함수를 `BackgroundTasks`로 래핑. `INTERNAL_API_KEY` 중복 정의 제거 → settings에서 import. `import os` 제거. |
| `scripts/scheduler.py` | Modified | HTTP self-loopback(`call_internal_api`, `INTERNAL_API_BASE`, `httpx`) 제거. 4개 cron job 모두 동일한 비즈니스 로직 함수를 직접 await. `configure_logging()` 사용. 사용 안 하는 `from datetime import datetime` 제거. |
| `scripts/main.py` | Modified | `configure_logging()` 사용으로 중복 제거. `"main:fastapi_app"` → `"scripts.main:fastapi_app"` (이동 후 잔재 fix). `import asyncio` 제거 (사용처 없음). |
| `scripts/config/logging.py` | Added | `configure_logging(level=INFO)` + `LOG_FORMAT` 상수. main / scheduler / 라이프사이클 스크립트가 동일 포맷 공유. |
| `scripts/__init__.py` | Modified | 13줄 docstring → 1줄로 축소 ("architecture is documented in CLAUDE.md"). |
| `CLAUDE.md` | Modified | Project Overview / Build & Development Commands / Architecture 섹션 채움. `scripts/` 트리 다이어그램 포함. |
| `docs/DATABASE_CLEANUP_REPORT.md` | Modified | stale notice 헤더에서 하드코딩 `(2026-05-01)` 제거 → `revision_history.md` 참조. |
| `docs/KMA_API_INTEGRATION.md` | Modified | 동일. |
| `docs/COASTAL_CLASSIFICATION_COMPLETE.md` | Modified | 동일. |
| `docs/API_SOURCE_MIGRATION.md` | Modified | 동일. |

## Details

### Commit `bd67e43` 핵심
- `pyproject.toml`: `namespaces = true` 한 줄 추가로 `scripts/{ops,setup,ingest,dev,data}` 5개 namespace 패키지가 `pip install .` 빌드 대상에 포함됨. 이전엔 누락되어 PyPI 빌드 시 ship 안 됨.
- `collect_weather_report.py`: 모듈 import 시 `RESULT_DIR.mkdir`이 디스크에 폴더 생성하는 부수효과 제거. scheduler 부팅 시점에 결과 폴더가 생기는 문제 해소.
- `scheduler.py`: WHAT만 설명하는 주석 3건 제거.

### Commit `452ab70` 핵심

#### scheduler ↔ internal 통합 (HIGH 해소)

**Before**:
- `scheduler.py`: `httpx.AsyncClient.post(http://localhost:8000/internal/{collect|score|notify})` + `INTERNAL_API_BASE` 하드코딩
- 라우트 안의 inner async function은 즉시 200 반환 + `background_tasks.add_task`로 비동기 실행 → scheduler는 작업 완료를 기다리지 않음
- 단, `generate_weather_report`만 `from scripts.ops.collect_weather_report import run_collection` 직접 호출 — 1개 job만 다른 패턴

**After**:
- `internal.py`의 inner async 함수 3개를 module-level로 끌어올려 `collect_weather`, `calculate_scores`, `send_notification` 명명. 라우트는 그 함수를 `BackgroundTasks`로 래핑.
- `scheduler.py`는 4개 cron job 모두 동일한 비즈니스 로직 함수를 `await`. `httpx`, `call_internal_api`, `INTERNAL_API_BASE` 모두 제거. 4개 모두 작업 완료를 기다림.
- 결과: HTTP round-trip 제거, auth 우회 또는 설정 분기 없음, 일관된 직접 호출 패턴.

#### 공용 logging
- `scripts/config/logging.py` 신규: `LOG_FORMAT`(asctime / name / levelname / message) + `configure_logging(level=INFO)`.
- `main.py` / `scheduler.py`: 13줄짜리 동일한 `logging.basicConfig` 블록 → `configure_logging()` 한 줄 호출.

#### 문서 통합
- `CLAUDE.md`: 비어있던 Architecture 섹션을 `scripts/__init__.py`의 docstring 내용 + 트리 다이어그램으로 채움. Build/Dev 커맨드 명시(`uvicorn scripts.main:fastapi_app`, `python -m scripts.scheduler` 등).
- `scripts/__init__.py`: 13줄 → 1줄. 단일 정보 출처(CLAUDE.md)로 통합.
- docs/ 4개 stale notice: 하드코딩 `(2026-05-01)` 제거. 시점 정보는 `revision_history.md`가 단일 source of truth.

#### main.py 진입점 fix
- `uvicorn.run("main:fastapi_app", ...)` → `uvicorn.run("scripts.main:fastapi_app", ...)`. reorg 후 잔재 typo. `__main__` 직접 실행이 또 다른 main 모듈을 찾으려 했다가 실패하는 corner-case 제거.

## Verification

- ✅ 73/73 `.py` 파일 `python -m py_compile` 성공 (logging.py 1개 추가).
- ✅ ast 파싱 4개 핵심 파일(scheduler, main, internal, logging) 모두 OK + import 그래프 일관성 확인.
- ✅ `grep -rn 'call_internal_api\|INTERNAL_API_BASE' scripts/` 매치 0건.
- ⚠️ `python -c "from scripts.scheduler import scheduler"` 시 pydantic_core arm64/x86_64 mismatch — 시스템 Python 3.9 stock 환경 문제 (코드 변경 무관, render python 3.10에서 정상 예상).
- ⚠️ ruff 미설치 — 린터 단계 스킵.

## Out of Scope

- **`Efficiency #6` (RSS 누적 → ProcessPoolExecutor)**: 현 시점 보류. `to_thread` 유지 (간단함). 메모리 격리는 실제 RSS 관측 후 ProcessPoolExecutor로 전환 검토.
- **`sys.path.insert` 제거**: agent 권고했으나 거부. 14개 라이프사이클 스크립트의 직접 실행(`python scripts/setup/init_database.py`) 호환성 위해 유지.
- **stringly-typed operation tags**: 4개 사이트만 있어 over-engineering — skip.
