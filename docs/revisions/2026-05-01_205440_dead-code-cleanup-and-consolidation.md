# Dead code 제거 + __init__.py 재export 정리 + bulk helper 추출

- **Date**: 2026-05-01 20:54:40
- **Author**: Claude Code (사용자 요청, /skill_donghun:dh-dev)
- **Plan**: [2026-05-01_204620_dead-code-cleanup-and-consolidation.md](../plans/2026-05-01_204620_dead-code-cleanup-and-consolidation.md)
- **Commits**: `91c4a33`

## Summary

`/dh-dev` 워크플로우의 1-a explore 단계에서 호출 사이트 0건으로 확정된 dead code 7개 파일과 미사용 함수 ~20개를 제거하고, `__init__.py`의 과도한 re-export를 외부 public 항목만 노출하도록 정리. 동일 코드 50줄을 2회 반복하던 Open-Meteo bulk 응답 후처리를 `_process_batch_response()` 헬퍼 함수로 추출. 외부 진입점(API 라우트, 스케줄러, 라이프사이클 스크립트) 동작은 동일.

## Rationale / Plan

직전의 두 reorg(scripts/ 라이프사이클 분류 + 모든 패키지 통합) 후 `/dh-dev` 1-a 단계에서 `Explore` agent로 객관적 검증된 항목들. 모든 변경은 사용자 plan 컨펌 후 진행. 각 dead code는 grep으로 호출 사이트 재확인.

## Changed Files

### Deleted (9 files)

| File | Reason |
|------|--------|
| `scripts/models/__init__.py` | 패키지 자체 제거 (자식 모두 미사용) |
| `scripts/models/region.py` | `from scripts.models.region import Region` 사이트 0건. `processors.region_loader.Region` 단일 사용. |
| `scripts/models/weather.py` | import 0건 |
| `scripts/models/ocean.py` | import 0건 |
| `scripts/models/feedback.py` | import 0건 |
| `scripts/collectors/airkorea.py` | `AirKoreaCollector` 정의. `internal.py`에서 import만, 호출 0건. |
| `scripts/feedbacks/automation.py` | `ScorePenaltyManager`, `FeedbackAutomation` 정의. cron 미등록, 외부 호출 0건. |
| `scripts/processors/weather_integrator.py` | `fetch_all_weather_data`, `filter_3hour_intervals`, `get_integrated_weather` 정의. 3개 함수 모두 호출 0건. (단, `ops/generate_forecast_report.py`가 동일 이름의 *자체 정의* 함수를 가지고 있어 헷갈리기 쉬우므로 검증). |
| `scripts/processors/region_beach_merger.py` | `get_region_beach_mapping`, `merge_region_with_beaches`, `get_merged_forecast_data` 정의. 3개 모두 호출 0건. |

### Modified

| File | Change |
|------|--------|
| `scripts/processors/__init__.py` | 13+ internal-only re-export 제거. `__all__`에 `CacheWriter`, `merge_weather_data`, `RegionLoader` 3개만. 기존 `WeatherData`, `WeatherValue`, `weather_data_to_dict`, `write_*_cache`, `batch_cache_*`, `BatchCacheProcessor`, `Region`, `initialize_regions_db`, `load_all_regions`, `load_region` 등은 모듈 내부 정의로만 남고 `__all__`에서 빠짐. |
| `scripts/feedbacks/__init__.py` | `ScorePenaltyManager`, `FeedbackAutomation` import/`__all__` 제거 → `Feedback`, `FeedbackCollector`, `FeedbackAnalyzer` 3개만. |
| `scripts/collectors/__init__.py` | `AirKoreaCollector` import/`__all__` 제거 → 6개 collector + `BaseCollector`/`CollectorError` 등 7개로 감소. |
| `scripts/api/routes/internal.py` | `AirKoreaCollector` import line 제거. 사용 안 하던 `weather_data_to_dict` import line 제거. |
| `scripts/ops/collect_weather_report.py` | `fetch_openmeteo_bulk` 안의 동일한 50줄 응답 후처리 블록 2회(라인 244-279, 298-331)를 `_process_batch_response(data, batch, hourly_mode, results)` 모듈-private 헬퍼로 추출. 1213 → 1188 라인. |
| `CLAUDE.md` | Directory Tree에서 `models/` 제거. Diagram 4에서 `ACol[AirKoreaCollector]` 노드 제거. Diagram 7 (Module Dependency)에서 `mod[scripts.models...]` 노드 + 4개 점선 의존성 제거. Cross-Cutting Notes: dead code 제거 사실 + processors public surface 정리 명시. |

## Verification

- ✅ Pre-delete grep audit: AirKoreaCollector / FeedbackAutomation / ScorePenaltyManager / scripts.models / weather_integrator funcs / region_beach_merger funcs 모두 plan에서 식별한 사이트 외 호출 0건 재확인.
- ✅ `find scripts -type f -name "*.py"` 73 → 64 (-9 파일).
- ✅ 64/64 `python -m py_compile` 성공.
- ✅ `_process_batch_response` 정의 1, 호출 2 (line 194 / 278 / 290) — 두 곳에서 헬퍼 호출.
- ✅ `git status`에 9개 파일 deletion 깔끔하게 표시.
- ✅ CLAUDE.md mermaid 다이어그램 모두 dead 항목 미참조.
- ⚠️ 시스템 Python 3.9의 pydantic_core arm64/x86_64 mismatch로 `from scripts.scheduler import scheduler` 직접 smoke test는 환경 차원에서 차단 — 코드 변경과 무관 (이전 reorg 시점에 동일 이슈 확인됨).
- ⚠️ ruff 미설치 — 린터 단계 스킵.

## 결정 정정 / 메모

- **`processors/region_loader.py`의 module-level `load_all_regions`, `load_region`, `initialize_regions_db` 함수**: 외부 사용 0건이지만, `RegionLoader` 클래스와 함께 한 파일에 살고 있어 파일 단위 삭제는 부적합. plan은 `__init__.py`의 export만 제거하여 *private화* 하기로 결정. 추후 사용처 발생 시 다시 export 추가하거나, 영원히 안 쓰면 별도 cleanup에서 제거.
- **동일하게 `cache_writer.py`의 `write_beach_weather_cache` / `write_marine_forecast_cache`, `data_merger.py`의 `WeatherValue` / `merge_weather_value` / `weather_data_to_dict`, `batch_cache.py`의 `BatchCacheProcessor` / `batch_cache_*`** 모두 모듈 내부에 남아 있고 `__all__`에서만 빠짐. 모듈 내부에서 서로 사용 중이므로 함수 정의 자체는 유지.
- **`KMA{Forecast,MarineForecast}Collector` 공통 dict 이관 (E1)**: 본 plan에서 보류. 별도 plan으로 진행.

## Out of Scope

- KMA collector 공통 dict 이관 (별도 plan 필요).
- 18개 ThemeScorer 통합 — theme별 독립 로직.
- `ops.run_collection` ↔ `internal.collect_weather` 통합 — 입력/출력이 다름.
- 외부 docs/runbook의 dead 함수 인용 (repo 외부).
- 신규 기능 / 버그 수정.
