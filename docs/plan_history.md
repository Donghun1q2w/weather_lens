# Plan History

Chronological log of project plans (newest first).

---

## 2026-05-01 18:18:00 — Reorganize `scripts/` by lifecycle

[Detail](plans/2026-05-01_181800_reorganize-scripts-by-lifecycle.md)

**Status**: Proposed

Restructure flat `scripts/` (14 files) into 4 lifecycle subfolders — `setup/`, `ingest/`, `ops/`, `dev/`. Patch `PROJECT_ROOT` path math in every moved script (`parent.parent` → `parent.parent.parent`), redirect `scheduler.py:75` to `scripts/ops/collect_weather_report.py`, and delete the unreferenced `warmup.py` shim. `main.py` and `scheduler.py` remain at root as runtime entry points.

---
