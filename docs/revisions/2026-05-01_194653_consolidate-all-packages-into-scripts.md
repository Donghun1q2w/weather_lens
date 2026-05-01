# Consolidate all packages into `scripts/`

- **Date**: 2026-05-01 19:46:53
- **Author**: Claude Code (사용자 요청, ultrawork)
- **Plan**: [2026-05-01_190730_consolidate-all-packages-into-scripts.md](../plans/2026-05-01_190730_consolidate-all-packages-into-scripts.md)
- **Commits**: `cf94a38` (plan baseline), `dcf7823` (reorg 본 작업), `b9bfb44` (.gitignore 후처리)

## Rationale / Plan

직전 plan(`2026-05-01_181800_...`)에서 “out of scope”로 명시했던 결정을 사용자 지시로 뒤집어, 루트의 12개 도메인 패키지(`api`, `collectors`, `config`, `curators`, `data`, `feedbacks`, `messengers`, `models`, `processors`, `recommenders`, `scorers`, `utils`) + 두 진입점(`main.py`, `scheduler.py`)을 모두 `scripts/` 하위로 통합. “모든 Python 코드는 `scripts/` 안에 있다”는 단일 트리 구조로 정리하고, 루트에는 배포·환경·문서·산출물만 남김.

사용자 컨펌 5건:
1. `data/__init__.py` 추가 안 함 (현 namespace package 유지).
2. `pyproject.toml`에 `[tool.setuptools.packages.find]` 블록 추가.
3. `docs/{DATABASE_CLEANUP_REPORT, KMA_API_INTEGRATION, COASTAL_CLASSIFICATION_COMPLETE, API_SOURCE_MIGRATION}.md`에 stale notice 헤더 추가.
4. `collectors/example_usage.py` 삭제 (dead code).
5. `scheduler.py`의 ops 호출을 subprocess → import + `asyncio.to_thread` 형태로 전환.

## Changed Files

### Renames (14 항목, 67 파일/하위 트리, similarity 84–100%)

| From | To |
|------|-----|
| `api/` | `scripts/api/` |
| `collectors/` | `scripts/collectors/` |
| `config/` | `scripts/config/` |
| `curators/` | `scripts/curators/` |
| `data/` | `scripts/data/` |
| `feedbacks/` | `scripts/feedbacks/` |
| `messengers/` | `scripts/messengers/` |
| `models/` | `scripts/models/` |
| `processors/` | `scripts/processors/` |
| `recommenders/` | `scripts/recommenders/` |
| `scorers/` | `scripts/scorers/` |
| `utils/` | `scripts/utils/` |
| `main.py` | `scripts/main.py` |
| `scheduler.py` | `scripts/scheduler.py` |

### Modifications

| File | Change |
|------|--------|
| 42개 `.py` 파일 | 절대 import 66건에 `scripts.` 접두어 추가 (모든 `from <pkg>...` / `import <pkg>` 패턴) |
| `scripts/scheduler.py` | `generate_weather_report` 함수의 subprocess 호출을 제거하고 `from scripts.ops.collect_weather_report import run_collection` + `asyncio.wait_for(asyncio.to_thread(run_collection, sample_mode=False, hourly_mode=False), timeout=1800)` 패턴으로 전환 |
| `render.yaml:8` | startCommand: `uvicorn main:fastapi_app` → `uvicorn scripts.main:fastapi_app` |
| `pyproject.toml` | `[tool.setuptools.packages.find]` 블록 추가 (`where = ["."]`, `include = ["scripts*"]`) |
| `scripts/__init__.py` | docstring 보강 (전체 코드 호스트 역할 명시) |
| `docs/{DATABASE_CLEANUP_REPORT, KMA_API_INTEGRATION, COASTAL_CLASSIFICATION_COMPLETE, API_SOURCE_MIGRATION}.md` | 상단에 stale notice 헤더 추가 |
| `.gitignore` | 평탄 `data/...` 패턴 4건 → `scripts/data/...`로 갱신 (별도 후처리 commit `b9bfb44`) |

### Deletions

| File | Reason |
|------|--------|
| `collectors/example_usage.py` | 사용자 결정 — dead code (다른 코드에서 import 안 됨) |

### Untracked (이전엔 추적되었으나 본 reorg로 untrack됨, b9bfb44)

| File | Action |
|------|--------|
| `scripts/data/regions.db` | git rm --cached (filesystem 유지) |
| `scripts/data/ocean_mapping.db` | git rm --cached |
| `scripts/data/cache/2026-01-31/regions/서울특별시_강남구_역삼동.json` | git rm --cached |

## 결정 정정 (실행 중 발견)

- **Plan 4단계 (`BASE_DIR` 깊이 갱신)**: 시행하지 않음. 이유: `BASE_DIR`이 가리키는 자원(`scripts/data/`, `scripts/config/weights.json`)이 본 reorg로 함께 이동했기 때문에, `Path(__file__).parent.parent`를 그대로 두면 `BASE_DIR`이 새 위치(`scripts/`)를 가리켜 의미는 “프로젝트 루트”에서 “scripts/ 디렉터리”로 바뀌지만 결과적으로 모든 자원 경로가 자연스럽게 정합. 검증: `BASE_DIR`, `DATA_DIR`, `SQLITE_DB_PATH` 모두 새 위치로 정상 해석되며 실제 파일 존재 확인.
- **`.gitignore` 후처리**: 본 reorg가 `data/` 디렉터리를 `git mv`로 이동시킨 직후, `.gitignore`의 평탄 `data/...` 패턴이 더이상 매치하지 않아 런타임 DB와 캐시 JSON이 의도치 않게 새 경로에서 추적 대상이 됨. 후속 commit `b9bfb44`로 패턴 갱신 + 추적 해제.

## Verification

- ✅ 72개 `.py` 파일 모두 `python -m py_compile` 성공.
- ✅ 평탄 import 잔재 0건 (`grep -rEn '^(from|import) (api|collectors|...|scheduler)\b' scripts/` → 매치 0).
- ✅ `scripts.scheduler` 정상 import (4개 cron job 등록 확인: `collect_weather`, `generate_weather_report`, `recalculate_scores`, `send_daily_recommendations`).
- ✅ `scripts.config.settings`의 `BASE_DIR`/`DATA_DIR`/`SQLITE_DB_PATH` 정상 해석 + 실제 파일 존재 확인.
- ✅ `scripts/scheduler.py` 내 `subprocess` / `sys.executable` 사용 0건 (import 형태 전환 검증).
- ✅ `scripts/collectors/example_usage.py` 삭제 확인.
- ✅ `pyproject.toml`에 `[tool.setuptools.packages.find]` 블록 존재.
- ✅ docs 4개 파일 상단에 stale notice 헤더 존재.
- ✅ git rename 인식: 67개 항목 84–100% similarity.
- ⚠️ `python -c "from scripts.main import fastapi_app"` 실행은 시스템 Python 3.9 환경의 pydantic_core 아키텍처 (arm64/x86_64) 불일치로 차단됨 — 코드 변경과 무관한 환경 문제. ast 파싱·py_compile은 통과. render 배포 환경(python 3.10)에서는 정상 동작 예상.
- ⚠️ ruff 린터: 미설치 — 검증 스킵.

## Out of scope (not touched)

- `result/`, `.env`, `LICENSE`, `CLAUDE.md`, `requirements.txt` — 비코드/배포 설정.
- 패키지 내부 추가 분류 (예: `scripts/processors/{cache,merge}/`).
- `tests/` 부활 / CI 추가.
- `data/__init__.py` 추가 (사용자 결정으로 제외).
- 외부 runbook이나 third-party 문서 갱신 (해당 없음).
