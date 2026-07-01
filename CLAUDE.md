# [CLAUDE.md](http://CLAUDE.md)

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Weather Lens — Korean photography spot recommendation backend. Pulls weather, marine, and astronomy data from public APIs, scores each region per theme (sunrise/sunset, Milky Way, etc.), and serves recommendations via FastAPI. Single-process Render deployment combining FastAPI app and APScheduler.

## Build and Development Commands

- Install: `pip install -r requirements.txt`
- Local server: `uvicorn scripts.main:fastapi_app --reload`
- Scheduler standalone: `python -m scripts.scheduler`
- One-shot weather report: `python scripts/ops/collect_weather_report.py --full`
- Lint: `ruff check scripts/`
- Tests: removed by request — none currently.

## Architecture

All Python source lives under `scripts/`. The root holds only deployment config (`render.yaml`, `pyproject.toml`, `requirements.txt`), environment (`.env`), documentation (`docs/`), runtime output (`result/`), and license/notes.

### Directory Tree

```
scripts/
├── main.py          # FastAPI entry (uvicorn scripts.main:fastapi_app)
├── scheduler.py     # APScheduler cron jobs (4 jobs)
├── api/             # FastAPI routes (api.routes.{health, themes, regions, ...})
├── collectors/      # External data fetchers (KMA, Open-Meteo, KHOA, AirKorea, beach)
├── config/          # settings + shared logging config
├── curators/        # Gemini text curation
├── data/            # Static reference data + runtime SQLite (regions.db, ocean_mapping.db)
├── feedbacks/       # User-feedback collection / analysis / automation
├── processors/      # Cache writer, data merger, region loader
├── recommenders/    # Region recommender (theme-top selection)
├── scorers/         # Theme scorers + batch scorer
├── utils/           # Astronomy, ocean station mapping
├── setup/           # 1회성 부트스트랩 스크립트 (DB init, beaches/zones/stations seed)
├── ingest/          # 외부 데이터 import (regions, naver spots)
├── ops/             # 정기 운영 (collect_weather_report, generate_forecast_report)
└── dev/             # 개발자 도구 (check_config)
```

### 1. Runtime Topology

`render.yaml`의 `uvicorn scripts.main:fastapi_app` 단일 프로세스에서 FastAPI 앱과 APScheduler가 함께 동작한다. `main.py`의 `lifespan`이 startup 시 scheduler를 켜고 shutdown 시 끈다. CORS 미들웨어가 `*`로 열려 있고, `/docs`/`/redoc`는 자동.

```mermaid
flowchart LR
    Client[HTTP Client] --> Uvicorn[uvicorn worker]
    subgraph Render["Render web service (single process)"]
        direction TB
        Uvicorn --> Main["scripts.main:fastapi_app"]
        Main -- "lifespan startup" --> Scheduler["scripts.scheduler<br/>(AsyncIOScheduler, 4 jobs)"]
        Main -- "ASGI" --> APIMain["scripts.api.main<br/>FastAPI + CORS + /docs"]
        APIMain --> Routes[scripts.api.routes/]
        Scheduler -. "lifespan shutdown" .-> Stop[stop_scheduler]
    end
```

### 2. API Surface Map

10개 router(11개 모듈, `/internal`은 다음 다이어그램에서 자세히)이 등록되며 각 라우트가 사용하는 의존성:

```mermaid
flowchart LR
    subgraph Routes["scripts.api.routes/"]
        H["/health"]
        AS["/astronomy/* (5)"]
        TH["/themes/* (4)"]
        RG["/regions/* (4)"]
        MR["/marine/* (4)"]
        MP["/map/boundaries"]
        PS["/photo-spots/* (9)"]
        UC["/collections/* (9)"]
        FB["/feedback (POST)"]
        IN["/internal/* (4)"]
    end

    subgraph Deps["의존 모듈/리소스"]
        UA[scripts.utils.astronomy]
        REC[scripts.recommenders<br/>RegionRecommender]
        SQL[(scripts/data/regions.db)]
        BD[scripts/data/boundaries/]
        WJ[scripts/config/weights.json]
        FBM[scripts.feedbacks/*]
        INT[scripts.api.routes.internal<br/>collect_weather / calculate_scores]
        CACHE[scripts/data/cache/]
    end

    H -.- noop[no deps]
    AS --> UA
    TH --> WJ
    TH --> REC
    RG --> SQL
    RG --> CACHE
    MR --> SQL
    MP --> BD
    PS --> SQL
    UC --> SQL
    FB --> FBM
    IN --> INT
```

### 3. Scheduler Cron Jobs

3개 cron job은 모두 KST. 2개는 `internal.py`의 동일 비즈니스 함수를 직접 await; 1개(`generate_weather_report`)만 sync `run_collection`을 `asyncio.to_thread`로 실행.

```mermaid
flowchart TB
    subgraph Sched["scripts.scheduler (AsyncIOScheduler, 3 cron jobs)"]
        J1["collect_weather_data<br/>06:00, 18:00 KST"]
        J2["generate_weather_report<br/>03:00, 15:00 KST"]
        J3["recalculate_scores<br/>07:00, 19:00 KST"]
    end

    subgraph Logic["scripts.api.routes.internal (module-level async)"]
        F1[collect_weather]
        F3[calculate_scores]
    end

    OPS["scripts.ops.collect_weather_report:<br/>run_collection (sync)"]

    J1 -- await --> F1
    J3 -- await --> F3
    J2 -- "asyncio.to_thread<br/>+ wait_for(timeout=1800)" --> OPS

    subgraph API["POST /internal/* (auth: X-API-Key)"]
        E1["/internal/collect"]   -- BackgroundTasks --> F1
        E3["/internal/score"]     -- BackgroundTasks --> F3
        E5["/internal/status (GET)<br/>cache health + config flags"]
    end
```

### 4. Data Pipeline — collect → score

`internal.py`의 2단계 비즈니스 함수가 외부 API → 캐시 → 점수 → 추천으로 흘러간다. 각 단계의 처리 모듈을 모두 표시:

```mermaid
flowchart LR
    subgraph External["External APIs"]
        KMA[KMA forecast API]
        OM[Open-Meteo API]
        AirK[AirKorea API]
    end

    subgraph CollectPhase["Phase 1: collect_weather"]
        BC[BaseCollector ABC] -.subclassed by.- KCol
        KCol[KMAForecastCollector]
        OCol[OpenMeteoCollector]
        RL[RegionLoader<br/>scripts.processors]
        DM[merge_weather_data<br/>scripts.processors.data_merger]
        CW["CacheWriter<br/>scripts.processors.cache_writer"]
        BCP[BatchCacheProcessor<br/>scripts.processors.batch_cache]

        KMA --> KCol --> DM
        OM --> OCol --> DM
        AirK -.- ACol
        RL --> CollectLoop[per-region loop]
        DM --> CW
        CW <-. used by .- BCP
    end

    subgraph ScorePhase["Phase 2: calculate_scores"]
        Base[BaseScorer ABC]
        Themes["16 ThemeScorer<br/>(Sunrise/Sunset/MilkyWay/<br/>SeaLongExposure E/W/S/<br/>SeaOfClouds/StarTrail/<br/>NightCity/Fog/Reflection/<br/>Golden/Blue/Frost/Moonrise/<br/>Bioluminescence)"]
        Batch["batch_calculate_scores<br/>batch_calculate_daily_scores<br/>scripts.scorers.batch_scorer"]
        Recommender["RegionRecommender<br/>scripts.recommenders<br/>cache_theme_scores → CACHE_DIR"]
        Base -.subclassed.- Themes
        Themes --> Batch
        CW -. read cache .-> Batch
        Batch --> Recommender
        WJ2[scripts/config/weights.json] -.weights.- Themes
    end

    SQLite[(scripts/data/regions.db)]
    Recommender -. read regions .-> SQLite
    RL -. read regions .-> SQLite
```

### 5. ops.collect_weather_report (independent MD report)

`scheduler.generate_weather_report`가 호출하는 별도 sync 파이프라인. `internal.py`와 무관하게 자체적으로 외부 API를 호출하고 한 번에 MD/JSON 리포트를 생성한다.

```mermaid
flowchart LR
    Cron["scheduler.generate_weather_report<br/>03:00, 15:00 KST"]
    Cron -- "to_thread" --> RC[run_collection]

    subgraph RCInternal["run_collection (sync)"]
        direction TB
        RC --> GR[get_all_regions<br/>regions.db]
        GR --> Bulk[fetch_openmeteo_bulk]
        GR --> MZ[get_marine_zone_for_region]
        Bulk --> MarineFC[fetch_marine_forecast]
        MarineFC --> BeachFC[fetch_beach_forecast]
        BeachFC --> CalcSimple[calculate_simple_scores]
        CalcSimple --> GenMD[generate_markdown_report]
        GenMD --> ResultDir[scripts/result/<br/>*.md / *.json / latest.md]
    end

    subgraph ExtAPI["External APIs"]
        OM2[Open-Meteo API]
        KMAM[KMA marine API]
        BeachAPI[Beach API]
        OMap[scripts.utils.ocean_mapping<br/>find_nearest_tide_station/_temp_station]
        OcStations[scripts.data.ocean_stations<br/>OCEAN_STATIONS]
    end

    Bulk --> OM2
    MarineFC --> KMAM
    BeachFC --> BeachAPI
    OMap --> OcStations
    CalcSimple -. uses .-> OMap
    CalcSimple -. uses .-> AstroU[scripts.utils.astronomy<br/>get_sunrise_sunset / moon]
```

### 6. Feedback Subsystem

사용자 피드백 수집/분석/자동화 — 별도 mini-pipeline. `/feedback` POST 라우트가 진입점이고, 백그라운드/배치 자동화는 `FeedbackAutomation`이 담당.

```mermaid
flowchart LR
    Client[HTTP Client] -- POST --> FBR["/feedback (api.routes.feedback)"]
    FBR --> FC[Feedback dataclass]
    FBR --> FCol[FeedbackCollector<br/>scripts.feedbacks.collector]
    FCol --> FBDB[(피드백 저장소<br/>SQLite/jsonl)]

    subgraph Analysis["배치/오프라인 분석"]
        FAna[FeedbackAnalyzer<br/>scripts.feedbacks.analyzer]
        SPM[ScorePenaltyManager<br/>scripts.feedbacks.automation]
        FAuto[FeedbackAutomation<br/>scripts.feedbacks.automation]
        FCol -. read .-> FAna
        FAna --> SPM
        SPM --> FAuto
        FAuto -. adjust .-> WJ3[config/weights.json or override store]
    end
```

> **참고**: `feedbacks/automation.py`는 자동 호출 cron이 현재 등록되어 있지 않다. 수동/외부 트리거 또는 향후 cron 추가가 필요하다.

### 7. Module Dependency Overview

패키지 간 import 화살표 요약. 위쪽이 상위 계층(라우트/스케줄러), 아래쪽이 하위 인프라.

```mermaid
flowchart TB
    main[scripts.main]
    sch[scripts.scheduler]
    apim[scripts.api.main]
    routes[scripts.api.routes/*]
    intnl[scripts.api.routes.internal]
    ops[scripts.ops/*]

    main --> apim --> routes
    main --> sch
    sch --> intnl
    sch --> ops
    routes --> intnl

    subgraph Domain["Domain logic"]
        col[scripts.collectors]
        proc[scripts.processors]
        sco[scripts.scorers]
        rec[scripts.recommenders]
        cur[scripts.curators]
        fb[scripts.feedbacks]
        utl[scripts.utils]
    end

    subgraph Static["Config / Static data"]
        cfg[scripts.config<br/>settings + logging]
        dat[scripts.data<br/>beaches / marine_zones / ocean_stations / *.db]
    end

    intnl --> col
    intnl --> proc
    intnl --> sco
    intnl --> rec

    ops --> proc
    ops --> utl
    ops --> dat

    routes --> fb
    routes --> utl
    routes --> rec

    col --> cfg
    proc --> cfg
    sco --> cfg
    rec --> cfg
    fb --> cfg
    utl --> dat
    proc --> dat
    rec --> dat
```

### 8. Lifecycle Scripts

`scripts/{setup,ingest,ops,dev}/`는 cron이 아닌 사람/scheduler가 직접 실행하는 스크립트.

```mermaid
flowchart LR
    subgraph S["setup/  (1회성, 멱등)"]
        S1[init_database]
        S2[init_photo_spots]
        S3[setup_user_collections]
        S4[setup_beaches]
        S5[setup_marine_zones]
        S6[setup_ocean_stations]
    end

    subgraph I["ingest/  (외부 데이터 수집)"]
        I1[download_regions]
        I2[import_regions]
        I3[import_all_regions]
        I4[import_naver_spots]
        I5[import_json_helper]
    end

    subgraph O["ops/  (정기 운영)"]
        O1[collect_weather_report<br/>↑ scheduler.generate_weather_report]
        O2[generate_forecast_report]
    end

    subgraph D["dev/  (개발자 도구)"]
        D1[check_config]
    end

    DB[(scripts/data/regions.db)]
    Result[scripts/result/<br/>.md / .json]
    StaticData[scripts.data.beaches/<br/>marine_zones/<br/>ocean_stations]

    S1 --> DB
    S2 --> DB
    S3 --> DB
    S5 --> DB
    S5 -. seed .- StaticData
    S4 --> DB
    S4 -. seed .- StaticData
    S6 --> DB
    S6 -. seed .- StaticData
    I1 --> DB
    I2 --> DB
    I3 --> DB
    I4 --> DB
    I5 --> DB
    O1 --> Result
    O2 --> Result
```

### Cross-Cutting Notes

- **Scheduler-route 통합**: 3개 cron job 중 2개(`collect_weather_data`, `recalculate_scores`)는 `internal.py`의 동일 비즈니스 함수를 직접 await, API 라우트는 그 함수를 `BackgroundTasks`로 래핑한다 (단일 source of truth).
- `generate_weather_report` **만 다름**: `run_collection`이 sync 대용량 IO 함수라 `asyncio.to_thread` + `asyncio.wait_for(timeout=1800)`로 격리. 내부에서 자체적으로 외부 API를 호출(Diagram 5).
- **공용 logging**: `scripts/config/logging.py`의 `configure_logging()`이 main과 scheduler에서 동일 포맷을 적용.
- `BASE_DIR`**의 의미**: `scripts/config/settings.py`의 `BASE_DIR = Path(__file__).parent.parent`는 *프로젝트 루트가 아니라* `scripts/` *디렉터리*를 가리킨다. 모든 자원(`data/`, `config/weights.json`)이 함께 이동했기 때문에 의미가 자연스럽게 정합.
- **라이프사이클 스크립트 직접 실행 호환**: 14개 스크립트가 `sys.path.insert(0, PROJECT_ROOT)` (3단계 위 = repo root)를 유지해 `python scripts/setup/...` 형태 직접 실행이 동작. 표준 사용은 `python -m scripts.setup.init_database`도 가능.
- `AirKoreaCollector`**,** `FeedbackAutomation/ScorePenaltyManager`**,** `models/{region,weather,ocean,feedback}.py`**,** `processors/{weather_integrator, region_beach_merger}.py` 모두 호출 사이트 0건 확인 후 2026-05-01에 제거됨 (`docs/plans/2026-05-01_204620_dead-code-cleanup-and-consolidation.md`).
- `processors/__init__.py`**는 외부 public 항목만 노출**: `CacheWriter`, `merge_weather_data`, `RegionLoader`. 그 외 helper(`WeatherData`, `WeatherValue`, `weather_data_to_dict`, `write_*_cache`, `batch_cache_*`, `initialize_regions_db`, `load_all_regions`, `load_region`)는 모듈 내부 정의로만 남고 `__all__`에서 빠짐.
- **CORS**: `api/main.py`에서 `allow_origins=["*"]`로 열려 있음 — 프로덕션에선 좁힐 것을 코멘트에 명시.
- **인증 게이트**: `/internal/*`는 `verify_internal_key`(헤더 `X-API-Key` 검증, 401 또는 403)로 보호. scheduler는 직접 import이므로 인증 우회 — 같은 비즈니스 함수가 두 진입 경로를 가짐을 인지할 것.