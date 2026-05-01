# Revision History

Chronological log of project modifications.

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
