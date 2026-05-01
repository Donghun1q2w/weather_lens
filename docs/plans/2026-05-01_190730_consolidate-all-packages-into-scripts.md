# 모든 Python 패키지를 `scripts/` 하위로 통합

- **작성일**: 2026-05-01 19:07:30
- **상태**: 제안됨 (Proposed)
- **작성자**: Claude Code (사용자 요청, /plan-context)
- **선행 계획**: [`2026-05-01_181800_reorganize-scripts-by-lifecycle.md`](2026-05-01_181800_reorganize-scripts-by-lifecycle.md) (Completed) — 본 계획은 그 plan의 "out of scope" 결정을 명시적으로 뒤집음

## 요약

루트에 분산된 12개 도메인 패키지(`api/`, `collectors/`, `config/`, `curators/`, `data/`, `feedbacks/`, `messengers/`, `models/`, `processors/`, `recommenders/`, `scorers/`, `utils/`)와 두 런타임 진입점(`main.py`, `scheduler.py`)을 모두 `scripts/` 하위로 이동한다. 코드 트리 단일화로 “모든 Python 코드는 `scripts/` 안에 있다”는 규칙을 정립하고, 루트에는 배포 설정(`render.yaml`, `pyproject.toml`, `requirements.txt`)·환경(`.env`)·문서(`docs/`, `LICENSE`, `CLAUDE.md`)·산출물(`result/`)만 남긴다.

`scripts/{setup,ingest,ops,dev}/`(이전 계획에서 완료한 라이프사이클 분류)는 그대로 유지하고, 그 옆에 12개 도메인 패키지가 형제로 배치된다.

## 배경

직전 계획(`2026-05-01_181800_...`)에서는 `main.py`/`scheduler.py` 및 다른 최상위 패키지 이동을 “out of scope”로 명시했다. 이는 보수적 결정이었다. 사용자의 추가 지시(B안: 전부 통합 + 배포 설정 동시 갱신)로 결정을 뒤집고 단일 트리 구조로 정리한다.

### 검증된 사실

- 루트의 12개 도메인 패키지: `api`(routes/ 하위 11개 라우트 포함), `collectors`(9), `config`(2), `curators`(2), `data`(3), `feedbacks`(4), `messengers`(2), `models`(5), `processors`(7), `recommenders`(2), `scorers`(4), `utils`(3).
- 루트 진입점 2개: `main.py`(46 lines, `from api.main import app as fastapi_app`, `from scheduler import start_scheduler, stop_scheduler`), `scheduler.py`(150 lines, `from config.settings import ENVIRONMENT, INTERNAL_API_KEY` + scripts/ops 호출).
- 절대 import 통계: 42개 파일에서 66건. 패턴은 모두 `from <pkg>.X import Y` 또는 `from <pkg> import Z` (sys.path 조작 없는 표준 절대 import).
- 배포 진입점: `render.yaml:9` → `uvicorn main:fastapi_app --host 0.0.0.0 --port $PORT`. healthCheck `/health`.
- `config/settings.py:6` → `BASE_DIR = Path(__file__).parent.parent` (현재 루트 기준). 이동 후 `parent.parent.parent`로 갱신 필요.
- 외부 sys.path 조작: `collectors/example_usage.py:9` 1건 (데모 파일, parent.parent로 루트 추가) — 이동 후 깊이 갱신 또는 deprecate 결정.
- 라이프사이클 스크립트 14개(`scripts/{setup,ingest,ops,dev}/`)는 모두 `PROJECT_ROOT = Path(__file__).parent.parent.parent`(루트)로 sys.path 조작 후 `from config.settings ...` 등을 사용. 이동 후에는 import 경로를 `from scripts.config.settings ...`로 변경하거나, sys.path에 `scripts/`를 추가하도록 변경해야 함 → **후자(sys.path를 scripts/로 변경)는 거부**한다. 이유: 일관성 유지 및 표준 패키지 import 사용. 따라서 14개 스크립트 import 전부 갱신.
- Procfile, Dockerfile 없음. CI 설정 없음. `render.yaml`이 유일한 배포 설정.
- `pyproject.toml`은 setuptools 빌드 시스템이지만 `[tool.setuptools.packages]` 정의 없음 → 임의 패키지 트리 허용.
- `[tool.pytest.ini_options].testpaths = ["tests"]`인데 `tests/`는 이미 삭제됨 (사실상 dead config) — 이동에 영향 없음.

### 핵심 결정 사항

1. **Import 정책: 표준 절대 import (`from scripts.<pkg>.X`)로 통일.** sys.path 마술이나 PYTHONPATH 환경변수 의존 회피. 모든 import 66건을 `scripts.` 접두어로 갱신한다.
2. **`scripts/__init__.py` 유지 + `scripts/<pkg>/__init__.py` 유지.** 기존에 `__init__.py`가 있던 패키지는 정식 패키지로 유지(`api/`, `collectors/`, `config/`, `curators/`, `feedbacks/`, `messengers/`, `models/`, `processors/`, `recommenders/`, `scorers/`, `utils/`). `data/`만 `__init__.py` 없음 → 그대로 유지(namespace package)하거나 빈 `__init__.py` 추가 결정. **추가 권장**: `scripts/data/__init__.py` 추가하여 일관성 확보 (선택사항, plan에는 포함하지 않고 후속 결정).
3. **`scripts/{setup,ingest,ops,dev}/`은 그대로 유지.** 이미 완료된 라이프사이클 분류이며, 도메인 패키지와 라이프사이클 폴더가 형제로 공존 (디렉터리 상에서 충돌 없음 — 파일명 중복 없음).
4. **라이프사이클 14개 스크립트의 PROJECT_ROOT는 변경하지 않는다.** `Path(__file__).parent.parent.parent`는 여전히 루트를 가리킴(scripts/setup → scripts → root). sys.path에 루트가 추가되므로 `from scripts.config.settings`로 import 변경하면 정상 동작.
5. **`main.py`도 `scripts/main.py`로 이동.** `render.yaml`의 startCommand를 `uvicorn scripts.main:fastapi_app`으로 갱신.
6. **`scheduler.py`도 `scripts/scheduler.py`로 이동.** `scheduler.py:75`의 `Path(__file__).parent / "scripts" / "ops" / ...`는 `Path(__file__).parent / "ops" / ...`로 단축. `main.py`의 `from scheduler import ...`는 `from scripts.scheduler import ...`로 변경.

## 제안

### 목표 레이아웃

```
weather_lens/
├── .env
├── .env.example
├── .gitignore
├── CLAUDE.md
├── LICENSE
├── pyproject.toml
├── requirements.txt
├── render.yaml
├── 출사리스트.json
├── docs/                          # 문서 (변경 없음)
├── result/                        # 산출물 (변경 없음)
└── scripts/                       # ← 모든 Python 코드 통합
    ├── __init__.py                # 기존 유지 (docstring 갱신)
    ├── main.py                    # ← 루트에서 이동
    ├── scheduler.py               # ← 루트에서 이동
    ├── api/                       # ← 루트에서 이동
    │   ├── __init__.py
    │   ├── main.py
    │   └── routes/...
    ├── collectors/                # ← 루트에서 이동
    ├── config/                    # ← 루트에서 이동
    ├── curators/                  # ← 루트에서 이동
    ├── data/                      # ← 루트에서 이동
    ├── feedbacks/                 # ← 루트에서 이동
    ├── messengers/                # ← 루트에서 이동
    ├── models/                    # ← 루트에서 이동
    ├── processors/                # ← 루트에서 이동
    ├── recommenders/              # ← 루트에서 이동
    ├── scorers/                   # ← 루트에서 이동
    ├── utils/                     # ← 루트에서 이동
    ├── setup/                     # 기존 유지 (라이프사이클)
    ├── ingest/                    # 기존 유지
    ├── ops/                       # 기존 유지
    └── dev/                       # 기존 유지
```

### 구현 단계

1. **사전 정리**
   - 작업 디렉터리에 미커밋 변경 없음 확인 (`.obsidian/workspace.json` 외).
   - 백업/안전을 위해 작업 시작 전 `git status` 깨끗한 상태 확인.

2. **`git mv`로 14개 항목 이동** (12 패키지 + main.py + scheduler.py)
   - `git mv api scripts/api`
   - `git mv collectors scripts/collectors`
   - `git mv config scripts/config`
   - `git mv curators scripts/curators`
   - `git mv data scripts/data`
   - `git mv feedbacks scripts/feedbacks`
   - `git mv messengers scripts/messengers`
   - `git mv models scripts/models`
   - `git mv processors scripts/processors`
   - `git mv recommenders scripts/recommenders`
   - `git mv scorers scripts/scorers`
   - `git mv utils scripts/utils`
   - `git mv main.py scripts/main.py`
   - `git mv scheduler.py scripts/scheduler.py`

3. **모든 절대 import에 `scripts.` 접두어 추가** (총 ~66건)
   대상 패턴 (정확한 정규식):
   ```
   ^from (api|collectors|config|curators|data|feedbacks|messengers|models|processors|recommenders|scorers|utils)([\.\s])
   ^import (api|collectors|config|curators|data|feedbacks|messengers|models|processors|recommenders|scorers|utils)([\.\s]|$)
   ```
   치환:
   ```
   ^from scripts.\1\2
   ^import scripts.\1\2
   ```
   적용 범위: `scripts/**/*.py` 전부 (이동 후), 단 `__pycache__` 제외.
   - `from scripts` 동시 처리: `from scheduler` → `from scripts.scheduler` (1건, main.py).
   - `import scheduler` 형태가 있다면 갱신 (확인 필요).

4. **`scripts/config/settings.py:6` BASE_DIR 깊이 갱신**
   - `BASE_DIR = Path(__file__).parent.parent` → `Path(__file__).parent.parent.parent`
   - 이유: settings.py가 한 단계 더 깊어졌으나 BASE_DIR이 가리켜야 할 루트는 변하지 않음.

5. **`scripts/scheduler.py`의 `generate_weather_report`를 subprocess → import 형태로 전환**
   - 제거: `import subprocess`, `script_path = Path(__file__).parent / "scripts" / "ops" / ...`, `subprocess.run([sys.executable, str(script_path), "--full"], capture_output=True, ...)`.
   - 추가: 모듈 상단에 `from scripts.ops.collect_weather_report import run_collection`.
   - 호출 패턴 (async + timeout 유지):
     ```python
     try:
         await asyncio.wait_for(
             asyncio.to_thread(run_collection, sample_mode=False, hourly_mode=False),
             timeout=1800,
         )
         logger.info("Weather report generated successfully")
     except asyncio.TimeoutError:
         logger.error("Weather report generation timed out (>1800s)")
     except Exception as e:
         logger.error(f"Weather report generation failed: {e}")
     ```
   - 트레이드오프 (이미 사용자 인지): 메모리 격리 손실, 별도 프로세스 격리 손실. 이득: 스크립트 경로 의존성 제거, 인자 타입 안정성, traceback 직접 노출.

6. **`render.yaml:9` startCommand 갱신**
   - 변경 전: `uvicorn main:fastapi_app --host 0.0.0.0 --port $PORT`
   - 변경 후: `uvicorn scripts.main:fastapi_app --host 0.0.0.0 --port $PORT`

7. **`scripts/__init__.py` docstring 갱신**
   - 기존 docstring 내용("scripts 폴더는 ...")을 새 역할 ("Weather Lens 의 모든 Python 패키지를 호스팅하는 단일 트리")에 맞게 보강.

8. **`scripts/collectors/example_usage.py` 삭제** (사용자 결정)
   - 이동 후 위치 기준: `scripts/collectors/example_usage.py`. `git rm` 으로 제거.
   - 이유: 다른 코드에서 import 안 됨, 데모/문서 가치 미미한 dead code.
   - 부수 효과: 그 파일이 보유한 외부 sys.path.insert 1건도 자연 제거.

9. **`pyproject.toml` 패키지 설정 추가** (사용자 결정)
   - 추가 블록:
     ```toml
     [tool.setuptools.packages.find]
     where = ["."]
     include = ["scripts*"]
     ```
   - 이유: render 배포는 setuptools 패키지 발견을 사용하지 않지만, 향후 PyPI 빌드/`pip install -e .` 호환을 위해 명시. IDE/툴(예: pyright, ruff)이 모듈 트리를 인식하는 데도 도움.
   - 검토 후 필요 시 `[tool.setuptools]`에 `package_dir = {"" = "."}`도 추가 (대부분 기본값으로 충분).

10. **`docs/` 내 stale 경로 인용 갱신** (사용자 결정)
    - 대상 4개 문서:
      - `docs/DATABASE_CLEANUP_REPORT.md:64-65, 101, 107` — `scripts/fix_database.py`, `scripts/generate_regions_list.py`
      - `docs/KMA_API_INTEGRATION.md:80, 87, 90` — `scripts/test_kma_api.py`
      - `docs/COASTAL_CLASSIFICATION_COMPLETE.md:234` — `…/scripts/generate_regions_list.py`
      - `docs/API_SOURCE_MIGRATION.md:18, 51, 64` — `scripts/test_kma_api.py`
    - 이 문서들이 인용하는 파일들은 *이미 삭제된* 스크립트(2026-05-01 cleanup commit `349a3a2` 이전)라 본 reorg와 직접 충돌은 없으나, “어디에 무슨 스크립트가 있는지” 안내가 stale함.
    - 처리 방법: 각 문서 상단에 다음 헤더 추가:
      ```markdown
      > ⚠️ **Stale notice (2026-05-01)**: 본 문서가 인용하는 일부 `scripts/<flat>.py` 경로는 이미 삭제·통합된 옛 위치입니다. 코드는 `docs/revision_history.md`와 현재 `scripts/` 트리를 참고하세요.
      ```
    - 본문 라인은 그대로 두되 (역사 기록 보존), 헤더로 stale 경고. 추가로 본 reorg가 이동한 14개 항목(예: `scripts/ops/collect_weather_report.py`)은 이 문서들에 등장하지 않으므로 라인 단위 갱신 불요.

11. **검증 패스 수행** (Verification 섹션 참조).

### 영향 분석

#### 변경 대상 파일

| 항목 | 작업 |
|---|---|
| `api/`, `collectors/`, `config/`, `curators/`, `data/`, `feedbacks/`, `messengers/`, `models/`, `processors/`, `recommenders/`, `scorers/`, `utils/` (12 패키지, ~50개 .py) | `scripts/<pkg>/`로 이동 (`git mv`) + 내부 import 일괄 갱신 |
| `main.py` | `scripts/main.py`로 이동, `from api.main` → `from scripts.api.main`, `from scheduler` → `from scripts.scheduler` |
| `scheduler.py` | `scripts/scheduler.py`로 이동, `from config.settings` → `from scripts.config.settings`, `generate_weather_report` 함수를 subprocess → `from scripts.ops.collect_weather_report import run_collection` + `asyncio.to_thread` 형태로 전환 |
| `render.yaml` | startCommand 갱신 (`uvicorn scripts.main:fastapi_app`) |
| `scripts/config/settings.py:6` | BASE_DIR 깊이 갱신 (`parent.parent` → `parent.parent.parent`) |
| `scripts/{setup,ingest,ops,dev}/*.py` (14 라이프사이클 스크립트) | import 라인 일괄 갱신 (`from config...` → `from scripts.config...` 등) |
| `scripts/collectors/example_usage.py` | **삭제** (dead code, 사용자 결정) |
| `scripts/__init__.py` | docstring 갱신 |
| `pyproject.toml` | `[tool.setuptools.packages.find]` 블록 추가 (사용자 결정) |
| `docs/{DATABASE_CLEANUP_REPORT, KMA_API_INTEGRATION, COASTAL_CLASSIFICATION_COMPLETE, API_SOURCE_MIGRATION}.md` | 상단에 stale notice 헤더 추가 (사용자 결정) |

#### 변경 안 함 (out of scope)

- `docs/` 전체 (문서) — `docs/{DATABASE_CLEANUP_REPORT, KMA_API_INTEGRATION, COASTAL_CLASSIFICATION_COMPLETE, API_SOURCE_MIGRATION}.md`의 stale 경로 인용은 별도 cleanup task.
- `result/` (산출물).
- `.env`, `.env.example`, `.gitignore`, `LICENSE`, `CLAUDE.md`, `pyproject.toml`(빌드 설정 변경 보류), `requirements.txt`.
- `출사리스트.json` (사용자 데이터).
- `.obsidian/`, `.git/`, `.claude/`.
- `tests/` (이미 삭제됨), `[tool.pytest.ini_options].testpaths` (dead 설정).

#### 의존성

- 외부 라이브러리 변경 없음.
- `requirements.txt` 변경 없음.
- 데이터베이스 스키마 변경 없음.
- `.env` 키 이름/값 변경 없음.

#### 리스크 표

| 리스크 | 발생 가능성 | 영향도 | 대응 방안 |
|---|---|---|---|
| `render.yaml` startCommand 오타로 배포 실패 | 낮음 | 매우 높음 (서비스 중단) | 변경 후 로컬에서 `uvicorn scripts.main:fastapi_app --port 8001` 실행해 import/시작 검증 |
| 한 import 라인 갱신 누락 | 중간 | 높음 (해당 모듈 import 시점에 ModuleNotFoundError) | sed 일괄 처리 후 grep으로 잔재 0건 검증 + 모든 모듈 `python -m py_compile` |
| 패키지 내부 self-import (예: `from scorers.base_scorer ...`) 누락 | 중간 | 높음 | grep 패턴이 정확한지 검토. 정규식이 12개 패키지 모두 매치하는지 케이스 검증 |
| `tool.setuptools.packages` 미설정으로 패키지 발견 깨짐 | 낮음 | 중간 | render는 pip install -r requirements.txt + uvicorn 직접 실행이므로 setuptools 패키지 발견과 무관. 단, 후속 PyPI 배포가 있다면 갱신 필요 |
| `scripts/scheduler.py:75` 단축 실수 | 낮음 | 높음 (cron job 깨짐) | 변경 후 `python -c "from scripts.scheduler import generate_weather_report"` import 검증 + path 정규식 점검 |
| `config/settings.py:6` BASE_DIR이 다른 곳에서도 참조됨 | 중간 | 중간 (`api/routes/themes.py:8`에서 `from config.settings import ... BASE_DIR` 발견) | BASE_DIR 갱신 후 BASE_DIR을 사용하는 모든 곳에서 경로가 정상 해석되는지 점검 |
| 외부 문서/runbook이 `from collectors.X` 등 옛 경로를 안내 | 중간 | 낮음 (문서만 영향) | docs/*.md 별도 cleanup task로 분리. 본 plan에서는 갱신 안 함 |
| 깊은 import 트리에서 순환 import 발생 가능성 | 낮음 | 중간 | 본 작업이 import 경로만 변경하므로 그래프 모양 자체는 동일. 순환 우려 없음 |
| `git mv` 후 한 번에 commit하지 않으면 일시적으로 broken 상태 | 매우 높음 | 낮음 (작업 중간 상태일 뿐) | mv → import 갱신 → 검증 → 단일 commit으로 묶기 |
| 작업 도중 이미 완료된 lifecycle reorg(`scripts/{setup,...}/`)와의 시너지/충돌 | 낮음 | 낮음 | 14개 라이프사이클 스크립트의 import 라인은 본 plan 범위에 포함되어 동시에 갱신됨 |

### 수용 기준 (Acceptance Criteria)

- [ ] `find . -maxdepth 1 -type d \( -name api -o -name collectors -o -name config -o -name curators -o -name data -o -name feedbacks -o -name messengers -o -name models -o -name processors -o -name recommenders -o -name scorers -o -name utils \)` 결과가 0개 (루트에 도메인 패키지 없음).
- [ ] `find . -maxdepth 1 -type f -name "main.py" -o -maxdepth 1 -type f -name "scheduler.py"` 결과가 0개 (루트에 진입점 없음).
- [ ] `find scripts -maxdepth 1 -type d` 결과가 16개 = 12 도메인 패키지 + 4 라이프사이클(setup, ingest, ops, dev).
- [ ] `scripts/main.py`, `scripts/scheduler.py` 존재.
- [ ] `git status`에서 14개 항목 이동이 모두 rename으로 인식 (delete+add 아님).
- [ ] `grep -rn '^from \(api\|collectors\|config\|curators\|data\|feedbacks\|messengers\|models\|processors\|recommenders\|scorers\|utils\|scheduler\)\b' scripts/ --include='*.py'` 결과가 0건 (모두 `scripts.` 접두어 적용됨).
- [ ] `grep -rn '^import \(api\|collectors\|config\|curators\|data\|feedbacks\|messengers\|models\|processors\|recommenders\|scorers\|utils\|scheduler\)\b' scripts/ --include='*.py'` 결과가 0건.
- [ ] `python -m py_compile` for every `.py` under `scripts/` (제외: `__pycache__`) → 모두 성공.
- [ ] `python -c "from scripts.main import fastapi_app"` 정상 import (FastAPI 앱 로드).
- [ ] `python -c "from scripts.scheduler import start_scheduler, stop_scheduler"` 정상 import.
- [ ] `python -c "from scripts.config.settings import BASE_DIR; assert BASE_DIR.name == 'weather_lens', BASE_DIR"` 통과.
- [ ] 로컬 uvicorn 시작: `uvicorn scripts.main:fastapi_app --port 8001 &` 후 `curl localhost:8001/health` 가 200 응답. (수동)
- [ ] `render.yaml`의 startCommand가 `uvicorn scripts.main:fastapi_app ...`로 갱신됨.
- [ ] `scripts/scheduler.py`에서 `subprocess`/`sys.executable` 사용 0건 (`grep -c "subprocess\|sys\.executable" scripts/scheduler.py` == 0). `from scripts.ops.collect_weather_report import run_collection` 존재. `asyncio.to_thread` 또는 `asyncio.wait_for` 패턴으로 호출.
- [ ] `scripts/collectors/example_usage.py` 파일 부재 (`! -e`).
- [ ] `pyproject.toml`에 `[tool.setuptools.packages.find]` 블록 존재 (`grep "tool.setuptools.packages.find" pyproject.toml` 매치).
- [ ] `docs/{DATABASE_CLEANUP_REPORT, KMA_API_INTEGRATION, COASTAL_CLASSIFICATION_COMPLETE, API_SOURCE_MIGRATION}.md` 모두 상단에 "Stale notice" 헤더 존재.
- [ ] 새 위치의 어떤 파일도 옛 평탄 import (`from collectors.X` 등) 잔재 없음.

### 검증 단계

1. **사전 grep** — 각 패키지 import 패턴 매치 수 베이스라인 확보:
   ```
   grep -rn '^from \(api\|collectors\|...\)\b' . --include='*.py' | wc -l
   ```
   변경 후 같은 명령이 0(scripts/) + 0(루트, 도메인 패키지 없음)이어야 함.
2. **정적 파싱 루프** — `find scripts -name "*.py" -not -path "*__pycache__*" -exec python -m py_compile {} \;` 모두 성공.
3. **루트 진입점 import 검증** — `python -c "from scripts.main import fastapi_app; print(type(fastapi_app))"` → `<class 'fastapi.applications.FastAPI'>`.
4. **스케줄러 검증** — `python -c "from scripts.scheduler import scheduler; print([j.id for j in scheduler.get_jobs()])"` → 4개 job ID 출력.
5. **로컬 서버 부팅 테스트** — `uvicorn scripts.main:fastapi_app --port 8001` 실행 후 `/health` 200 확인 (1회 수동 검증).
6. **린터** — `ruff check scripts/` (ruff 설치 시) 통과.
7. **rename 인식 확인** — `git status --short`에서 14개 디렉터리/파일이 R(ename)로 표시됨 (대량 import 라인 변경으로 일부는 RM/D+A로 보일 수 있음 — 그 경우 `--find-renames=50%`로 재확인).

### 해소된 결정 사항 (사용자 컨펌)

1. **`data/__init__.py`**: 추가하지 않음 (현 namespace package 유지).
2. **`pyproject.toml` 패키지 설정**: 추가함. `[tool.setuptools.packages.find]`로 `scripts/` 하위 패키지 자동 발견 또는 `[tool.setuptools]`의 `package_dir`/`packages` 명시.
3. **docs/ stale 경로 갱신**: 본 plan에 포함. `docs/{DATABASE_CLEANUP_REPORT, KMA_API_INTEGRATION, COASTAL_CLASSIFICATION_COMPLETE, API_SOURCE_MIGRATION}.md` 내 `scripts/<file>.py` 인용을 신규 경로로 갱신 (단, 본문이 *이미 삭제된* 스크립트를 가리키는 경우는 그 부분은 stale 표기를 추가하는 정도로 처리).
4. **`collectors/example_usage.py`**: 삭제. 데모 파일이 아닌 진짜 dead code로 취급.
5. **`scheduler.py`의 ops 호출**: subprocess → import 형태 전환. `from scripts.ops.collect_weather_report import run_collection` 후 async 컨텍스트에서는 `await asyncio.to_thread(run_collection, sample_mode=False, hourly_mode=False)` 패턴으로 호출. **트레이드오프 인지**: 30분 timeout 보장 손실(필요 시 `asyncio.wait_for`로 보완), 메모리 격리 손실(같은 프로세스 내 실행). 장점: 스크립트 호출 오버헤드 제거, traceback 직접 노출, 의존성 명시화.

### 적용 범위 외 (Out of Scope)

- `result/`, `.env`, `LICENSE` 등 비코드 파일.
- `scripts/{setup,ingest,ops,dev}/*.py`의 PROJECT_ROOT 깊이 변경 (현재 그대로 유효).
- 패키지 내부 구조 추가 분류 (예: `scripts/processors/{cache,merge}/` 같은 세분화).
- 테스트 추가/`tests/` 부활.
- CI/CD 신규 추가.
