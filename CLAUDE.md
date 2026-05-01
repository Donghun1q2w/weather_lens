# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Weather Lens — Korean photography spot recommendation backend. Pulls weather, marine,
and astronomy data from public APIs, scores each region per theme (sunrise/sunset,
Milky Way, etc.), and serves recommendations via FastAPI + Telegram. Single-process
Render deployment combining FastAPI app and APScheduler.

## Build and Development Commands

- Install: `pip install -r requirements.txt`
- Local server: `uvicorn scripts.main:fastapi_app --reload`
- Scheduler standalone: `python -m scripts.scheduler`
- One-shot weather report: `python scripts/ops/collect_weather_report.py --full`
- Lint: `ruff check scripts/`
- Tests: removed by request — none currently.

## Architecture

All Python source lives under `scripts/`. The root holds only deployment config
(`render.yaml`, `pyproject.toml`, `requirements.txt`), environment (`.env`),
documentation (`docs/`), runtime output (`result/`), and license/notes.

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
├── messengers/      # Telegram bot
├── models/          # Domain dataclasses (region, weather, ocean, feedback)
├── processors/      # Cache writer, data merger, region/beach merger, weather integrator
├── recommenders/    # Region recommender (theme-top selection)
├── scorers/         # Theme scorers + batch scorer
├── utils/           # Astronomy, ocean station mapping
├── setup/           # 1회성 부트스트랩 스크립트 (DB init, beaches/zones/stations seed)
├── ingest/          # 외부 데이터 import (regions, naver spots)
├── ops/             # 정기 운영 (collect_weather_report, generate_forecast_report)
└── dev/             # 개발자 도구 (check_config)
```

Scheduler jobs and the `/internal/{collect,score,notify}` endpoints share the same
business-logic functions (`scripts.api.routes.internal.{collect_weather,
calculate_scores, send_notification}`); the API route wraps them in
`BackgroundTasks` for HTTP-triggered runs while the scheduler awaits them directly.
The fourth scheduler job (`generate_weather_report`) calls `run_collection` from
`scripts.ops.collect_weather_report` via `asyncio.to_thread` because that function
is sync and CPU/IO-bound.
