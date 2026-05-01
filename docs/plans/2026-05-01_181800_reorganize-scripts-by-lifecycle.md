# `scripts/`를 라이프사이클 기준으로 재구성

- **작성일**: 2026-05-01 18:18:00
- **상태**: 제안됨 (Proposed)
- **작성자**: Claude Code (계획 세션)

## 요약

현재 평탄(flat) 구조로 14개의 Python 파일이 들어 있는 `scripts/` 디렉터리를 라이프사이클 기준의 4개 하위 폴더 — `setup/`, `ingest/`, `ops/`, `dev/` — 로 재구성하여 부트스트랩(bootstrap) 작업과 반복(recurring) 작업의 구분을 명확히 한다. 새로운 디렉터리 깊이에 맞게 모든 스크립트의 `PROJECT_ROOT` 경로 계산을 패치하고, `scheduler.py:75`가 새로운 위치의 `collect_weather_report.py`를 가리키도록 수정하며, 참조되지 않는 `warmup.py` shim은 삭제한다. 애플리케이션 런타임 모듈(`main.py`, `scheduler.py`)은 프로젝트 루트에 그대로 둔다.

> **결정**: 신규 하위 폴더에 `__init__.py`를 두지 않는다. 스크립트는 단독 실행(`python scripts/<sub>/<file>.py` 또는 `scheduler.py`의 subprocess 호출)되며 패키지로 import 되지 않는다. Python 3.3+ namespace package 규칙으로 충분하다. 기존 `scripts/__init__.py`(docstring 포함)는 그대로 유지한다.

## 배경

사용자가 "모든 스크립트를 한 폴더로 모아 분류해 달라"고 요청했고, 본 프로젝트의 모든 스크립트가 백엔드 전용인지 질문했다.

**검증된 사실:**

- `scripts/` 내 14개 파일 모두 순수 Python 백엔드 코드이며, 프론트엔드 관련 코드는 없다.
- `scripts/`는 이미 이 파일들의 위치이며, 부족한 것은 내부 분류(categorization)이다.
- 14개 스크립트 모두 `PROJECT_ROOT = Path(__file__).parent.parent` 후 `sys.path.insert`를 사용해 프로젝트 루트를 찾는다. 하위 폴더로 이동하면 이 경로 계산이 깨지므로 수정이 필요하다.
- `scheduler.py:75`는 런타임에 `Path(__file__).parent / "scripts" / "collect_weather_report.py"`를 호출한다 — 코드베이스 내부에서 `scripts/`를 참조하는 유일한 곳이다. `collect_weather_report.py`를 옮기려면 이 경로를 갱신해야 한다.
- 루트의 `warmup.py`는 도우미 함수 2개(`log_warmup_ping`, `get_warmup_status`)를 포함하지만, 프로젝트 전체 grep에서 참조가 **0건**이다. 도큐스트링조차 "추가 서버 불필요(No additional server needed)"라고 명시되어 있어 사실상 데드 코드이다.
- `main.py`는 `render.yaml:8`(`uvicorn main:fastapi_app`)에 묶여 있고, `scheduler.py`는 `main.py:14`에서 임포트된다. 이들을 옮기면 배포 설정과 여러 import 변경이 강제되며 조직화 측면의 실익이 거의 없다 — 이들은 스크립트가 아니라 런타임 진입점이다.

**계획서가 필요한 이유:** 명시적 경로 패치가 없으면 이동된 모든 스크립트가 import 시점에 `ModuleNotFoundError: No module named 'config'`로 실패한다. 체크리스트 없이 grep-and-edit 방식으로 접근하면 누락이 발생한다.

## 제안

### 목표 레이아웃

```
scripts/
├── __init__.py                    # 기존 유지 (docstring 보존)
├── setup/                         # 신규 — 1회성 부트스트랩 (멱등)
│   ├── init_database.py
│   ├── init_photo_spots.py
│   ├── setup_user_collections.py
│   ├── setup_beaches.py
│   ├── setup_marine_zones.py
│   └── setup_ocean_stations.py
├── ingest/                        # 신규 — 외부 소스에서의 데이터 수집
│   ├── download_regions.py
│   ├── import_regions.py
│   ├── import_all_regions.py
│   ├── import_naver_spots.py
│   └── import_json_helper.py
├── ops/                           # 신규 — 반복/스케줄 운영 작업
│   ├── collect_weather_report.py  # ← scheduler.py:75 가 가리킬 대상
│   └── generate_forecast_report.py
└── dev/                           # 신규 — 개발자 도구
    └── check_config.py
```

신규 하위 폴더에는 `__init__.py`를 두지 않는다 (namespace package).

프로젝트 루트에서 제거: `warmup.py` (참조 없음, 삭제).

### 구현 단계

1. **하위 폴더 생성** (namespace package, `__init__.py` 추가하지 않음)

   - `mkdir -p scripts/{setup,ingest,ops,dev}`

2. `git mv`**로 파일 이동** (rename 이력 보존)

   - `setup/`: `init_database.py`, `init_photo_spots.py`, `setup_user_collections.py`, `setup_beaches.py`, `setup_marine_zones.py`, `setup_ocean_stations.py`
   - `ingest/`: `download_regions.py`, `import_regions.py`, `import_all_regions.py`, `import_naver_spots.py`, `import_json_helper.py`
   - `ops/`: `collect_weather_report.py`, `generate_forecast_report.py`
   - `dev/`: `check_config.py`

3. **13개 스크립트의** `PROJECT_ROOT` **패치** (`sys.path.insert`를 사용하는 모든 파일):

   - `PROJECT_ROOT = Path(__file__).parent.parent` → `Path(__file__).parent.parent.parent`
   - 대상 파일: `check_config.py`, `collect_weather_report.py`, `generate_forecast_report.py`, `download_regions.py`, `import_regions.py`, `import_all_regions.py`, `import_naver_spots.py`, `init_database.py`, `init_photo_spots.py`, `setup_marine_zones.py`, `setup_ocean_stations.py`, `setup_user_collections.py`, `setup_beaches.py` (참고: `setup_ocean_stations.py`와 `setup_beaches.py`는 소문자 `project_root`를 사용함).

4. `import_json_helper.py:7` **패치** (다른 패턴):

   - `DB_PATH = Path(__file__).parent.parent / "data" / "regions.db"` → `Path(__file__).parent.parent.parent / "data" / "regions.db"`

5. `scheduler.py:75` **갱신**:

   - `Path(__file__).parent / "scripts" / "collect_weather_report.py"` → `Path(__file__).parent / "scripts" / "ops" / "collect_weather_report.py"`

6. `warmup.py` **삭제** (프로젝트 루트). `grep -rn "warmup"`으로 참조 0건이 이미 검증됨.

7. **검증 패스 수행** (Verification 섹션 참조).

## 영향 분석

### 변경 대상 파일

| 파일 | 작업 |
| --- | --- |
| `scripts/setup/` | 디렉터리 생성 (namespace package) |
| `scripts/ingest/` | 디렉터리 생성 (namespace package) |
| `scripts/ops/` | 디렉터리 생성 (namespace package) |
| `scripts/dev/` | 디렉터리 생성 (namespace package) |
| `scripts/{init_database,init_photo_spots,setup_user_collections,setup_beaches,setup_marine_zones,setup_ocean_stations}.py` | `scripts/setup/`로 이동 + `PROJECT_ROOT` 패치 |
| `scripts/{download_regions,import_regions,import_all_regions,import_naver_spots,import_json_helper}.py` | `scripts/ingest/`로 이동 + 경로 패치 |
| `scripts/{collect_weather_report,generate_forecast_report}.py` | `scripts/ops/`로 이동 + `PROJECT_ROOT` 패치 |
| `scripts/check_config.py` | `scripts/dev/`로 이동 + `PROJECT_ROOT` 패치 |
| `scheduler.py` | 수정 — 75번째 줄 경로 갱신 |
| `warmup.py` | 삭제 |

### 의존성

- 외부 라이브러리 변경 없음.
- `requirements.txt` / `pyproject.toml` 변경 없음.
- `render.yaml` 변경 없음 (진입점 `main:fastapi_app`은 루트 유지).
- 데이터베이스 스키마 변경 없음.

### 리스크 표

| 리스크 | 발생 가능성 | 영향도 | 대응 방안 |
| --- | --- | --- | --- |
| 절대 경로로 호출하는 숨은 진입점 (CI, cron, README, 문서 등) | 낮음\~중간 | 중간 | 이동 전 리포지토리 + `docs/` 전체에서 `scripts/<name>.py` grep |
| `warmup.py`가 동적으로 호출되고 있을 가능성 (`importlib` 등) | 매우 낮음 | 낮음 | 정적 grep으로 참조 0건 확인 완료, 삭제는 git으로 복구 가능 |
| `scheduler.py:75`의 `__file__` 상대 경로 깊이 오산 | 낮음 | 높음 (스케줄 작업 중단) | 5단계에서 명시적으로 처리, 7단계 검증에 dry-resolve 서브프로세스 포함 |
| 한 스크립트의 `PROJECT_ROOT` 패치 누락 | 중간 | 중간 (해당 스크립트 첫 실행 시 실패) | 3단계 체크리스트 + 14개 전체 검증 루프 |
| 미스테이징 작업과의 충돌 (scorers/, collectors/ 등) | 중간 | 중간 | 깨끗한 커밋으로 정리 권장. 작업 중인 변경은 먼저 commit 또는 stash 하도록 안내 |
| 작업 중인 `scripts/generate_forecast_report.py`(현재 수정 중)의 diff 노이즈 | 중간 | 낮음 | 이동 *전*에 `generate_forecast_report.py`의 현재 편집을 별도 커밋으로 분리하여 rename diff를 깔끔하게 유지 |

### 수용 기준 (Acceptance Criteria)

- [ ] `find scripts -type f -name "*.py" -not -name "__init__.py"` 결과가 14개이며 모두 `scripts/{setup,ingest,ops,dev}/` 중 하나의 하위에 위치함.

- [ ] 기존 `scripts/__init__.py` 외에 어떤 `.py` 파일도 `scripts/` 직속에 남아있지 않음.

- [ ] 신규 하위 폴더(`setup/`, `ingest/`, `ops/`, `dev/`)에 `__init__.py`가 **없음** (namespace package 정책).

- [ ] `python -c "from scheduler import collect_weather_data"`가 깔끔하게 import 됨.

- [ ] `python scripts/dev/check_config.py`가 `ModuleNotFoundError` 없이 실행됨.

- [ ] 이동된 모든 스크립트에 대해 `python -c "import ast; ast.parse(open('<path>').read())"`가 파싱 성공 (편집으로 인한 구문 문제 없음).

- [ ] `grep -rn 'scripts/[a-z_]*\.py' . --include='*.py' --include='*.yaml' --include='*.md'` (단, `docs/revisions/`와 `docs/plans/` 제외)에 평탄 경로 잔재 없음.

- [ ] `git status`에 이동이 rename으로 표시됨 (delete + add 아님) — `git mv` 정상 동작 확인.

- [ ] `warmup.py`가 사라지고 어디에도 깨진 import 없음.

## 검증 단계

1. **사전 스윕(Pre-move sweep)** — `grep -rn "scripts/" --include='*.py' --include='*.yaml' --include='*.md' .`로 모든 매치 검토. 평탄 경로를 참조하는 항목이 있다면 갱신.
2. **정적 파싱 루프** — 이동된 14개 파일 각각에 대해 `python -m py_compile <path>` 실행으로 편집 후 구문 유효성 확인.
3. **단독 실행 스모크 테스트** — 각 하위 폴더에서 최소 하나의 스크립트를 `python -m py_compile <path>` 또는 `--help`/dry-run 형태로 실행해 `sys.path` 패치가 정상 동작하는지 확인 (namespace package이므로 `import scripts.<sub>` 형태의 import는 검증하지 않음).
4. **스케줄러 자가 검사** — `python -c "from scheduler import generate_weather_report; import asyncio"` 실행 (해당 함수가 이동된 경로를 참조). 경로 해석 계산이 올바른지 확인.
5. **린터** — `ruff check scripts/ scheduler.py` 통과.
6. **수동 점검(Manual sanity)** — `python scripts/dev/check_config.py` 엔드투엔드 실행.

## 미해결 질문

1. `scripts/<flat-name>.py` 호출을 문서화한 외부 런북 / README / Notion 페이지가 존재하는가? 존재한다면 본 리포지토리 외부에서 갱신이 필요하다.
2. 작업 중인 `scripts/generate_forecast_report.py`의 편집(현재 미스테이징)을 본 재구성 *전에* 먼저 커밋하여 rename diff를 깔끔하게 유지해야 하는가? 권장: 그렇다.

## 해소된 결정 사항

- `__init__.py` **정책**: 신규 하위 폴더에는 `__init__.py`를 추가하지 **않는다**. 이유: 스크립트들이 단독 실행되며 패키지로 import 되지 않음. Python 3.3+ namespace package로 충분. 기존 `scripts/__init__.py`는 docstring 보존을 위해 그대로 둔다.
- **MD 영향 분석**: 본 reorg로 갱신이 필요한 md 파일은 없음. `docs/{DATABASE_CLEANUP_REPORT, KMA_API_INTEGRATION, COASTAL_CLASSIFICATION_COMPLETE, API_SOURCE_MIGRATION}.md`가 `scripts/<file>.py` 형태를 참조하지만, 모두 이미 삭제된 스크립트(`fix_database.py`, `generate_regions_list.py`, `test_kma_api.py`)에 대한 stale 문서이므로 본 작업 범위 외.

## 적용 범위 외 (Out of Scope)

- `main.py` / `scheduler.py`를 루트에서 이동 (기각: 이들은 스크립트가 아닌 런타임 진입점).
- 다른 최상위 패키지(`api/`, `collectors/`, `scorers/` 등)의 재구성.
- 이동된 스크립트에 대한 테스트 추가 (사용자 요청에 따라 테스트가 방금 제거됨).
- CI/CD 파이프라인 변경.