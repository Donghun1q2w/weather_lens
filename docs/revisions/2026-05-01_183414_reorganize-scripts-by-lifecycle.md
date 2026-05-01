# Reorganize `scripts/` by lifecycle

- **Date**: 2026-05-01 18:34:14
- **Author**: Claude Code (user request, ultrawork)
- **Plan**: [2026-05-01_181800_reorganize-scripts-by-lifecycle.md](../plans/2026-05-01_181800_reorganize-scripts-by-lifecycle.md)
- **Commits**: `6c001f8` (plan docs), `fdf42c4` (WIP code group), `92ec301` (reorg)

## Rationale / Plan

User asked to reorganize `scripts/` (14 flat Python files) into lifecycle-based subfolders so the bootstrap-vs-recurring distinction is explicit. Per plan decision, no `__init__.py` is added to the new subfolders — scripts are run standalone, not imported as a package, so namespace packages suffice. The existing `scripts/__init__.py` (with docstring) is preserved.

In-progress edits in `collectors/`, `scorers/`, `config/`, `data/`, `utils/`, `scripts/generate_forecast_report.py`, plus the new `utils/ocean_mapping.py`, were committed first as a WIP block (commit `fdf42c4`) so the reorg's rename diff stayed clean.

## Changed Files

### Renames (14 files, all detected at 92–99% similarity)

| From | To |
|------|-----|
| `scripts/init_database.py` | `scripts/setup/init_database.py` |
| `scripts/init_photo_spots.py` | `scripts/setup/init_photo_spots.py` |
| `scripts/setup_user_collections.py` | `scripts/setup/setup_user_collections.py` |
| `scripts/setup_beaches.py` | `scripts/setup/setup_beaches.py` |
| `scripts/setup_marine_zones.py` | `scripts/setup/setup_marine_zones.py` |
| `scripts/setup_ocean_stations.py` | `scripts/setup/setup_ocean_stations.py` |
| `scripts/download_regions.py` | `scripts/ingest/download_regions.py` |
| `scripts/import_regions.py` | `scripts/ingest/import_regions.py` |
| `scripts/import_all_regions.py` | `scripts/ingest/import_all_regions.py` |
| `scripts/import_naver_spots.py` | `scripts/ingest/import_naver_spots.py` |
| `scripts/import_json_helper.py` | `scripts/ingest/import_json_helper.py` |
| `scripts/collect_weather_report.py` | `scripts/ops/collect_weather_report.py` |
| `scripts/generate_forecast_report.py` | `scripts/ops/generate_forecast_report.py` |
| `scripts/check_config.py` | `scripts/dev/check_config.py` |

### Modifications (16 files in reorg commit)

| File | Change |
|------|--------|
| 13× moved scripts | `PROJECT_ROOT = Path(__file__).parent.parent` → `parent.parent.parent` (path depth fix) |
| `scripts/ingest/import_json_helper.py:7` | `DB_PATH = Path(__file__).parent.parent / "data" / "regions.db"` → `parent.parent.parent / ...` |
| Docstring usage hints in moved scripts | Flat-path examples (`python scripts/<file>.py`) updated to new subfolder paths |
| `scheduler.py:75` | `Path(__file__).parent / "scripts" / "collect_weather_report.py"` → `... / "scripts" / "ops" / "collect_weather_report.py"` |

### Deletions

| File | Reason |
|------|--------|
| `warmup.py` (root) | Unreferenced shim. `grep -rn "warmup"` found 0 imports anywhere. Helper functions `log_warmup_ping` / `get_warmup_status` were never called. |

### Plan documents (committed as `6c001f8`)

| File | Change |
|------|--------|
| `docs/plan_history.md` | Added (new index) |
| `docs/plans/2026-05-01_181800_reorganize-scripts-by-lifecycle.md` | Added (the plan, Korean translation) |

### Pre-reorg WIP block (committed as `fdf42c4`)

In-progress theme scorer reconstruction + marine integration, committed as a single block to avoid breaking the reorg's rename diff. Files: `.env.example`, `collectors/{example_usage,khoa_ocean}.py`, `config/{settings.py,weights.json}`, `data/ocean_stations.py`, `scorers/*.py`, `scripts/generate_forecast_report.py` (pre-move), `utils/astronomy.py`, `utils/ocean_mapping.py` (new).

## Verification

- ✅ All 14 moved scripts pass `python -m py_compile`.
- ✅ `from scheduler import collect_weather_data` imports cleanly (apscheduler info logs only, no errors).
- ✅ `scheduler.py:75` resolves to `scripts/ops/collect_weather_report.py` (regex-verified).
- ✅ No `__init__.py` exists in the four new subfolders (namespace package); only `scripts/__init__.py` (preserved).
- ✅ `git status` reports the moves as renames at 92–99% similarity (clean rename detection).
- ✅ No stale flat-path references remain inside `scripts/` (docstrings rewritten).
- ✅ `warmup.py` deletion has no broken imports; only intentional references in plan/history docs.
- ⚠️ `ruff` lint step skipped — tool not installed in current environment.

## Out of scope (not touched)

- `.obsidian/workspace.json` — editor state noise.
- External docs in `docs/` (`기상청48 가이드` `.docx/.xlsx/.hwp`, `조석예보데이터.md`).
- `출사리스트.json` — user data file.
- `docs/{DATABASE_CLEANUP_REPORT, KMA_API_INTEGRATION, COASTAL_CLASSIFICATION_COMPLETE, API_SOURCE_MIGRATION}.md` — these reference *already-deleted* scripts (`fix_database.py`, `generate_regions_list.py`, `test_kma_api.py`), not the 14 moved files. Stale doc cleanup is a separate task.
- `main.py`, `scheduler.py` — runtime entry points, kept at project root by design (`render.yaml:8` binds `main:fastapi_app`).
