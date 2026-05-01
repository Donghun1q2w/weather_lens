# Revision History

Chronological log of project modifications.

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
