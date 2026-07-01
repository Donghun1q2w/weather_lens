# Remove Telegram notification feature (전체 제거)

- **Created**: 2026-07-01 22:52:24 KST
- **Status**: Proposed
- **Mode**: dh-dev (direct)
- **Scope decision**: 사용자 확정 — **알림 기능 전체 제거** (Telegram이 유일한 알림 수단이므로 알림 파이프라인 전체 삭제)

## Goal

Weather Lens에서 Telegram 관련 기능을 전부 제거한다. Telegram이 유일한 알림 전송 수단이므로, 알림 파이프라인(`send_notification`, `/internal/notify`, scheduler 20시 job) 전체가 함께 제거된다. 결과적으로 cron job은 4→3개, 알림 API는 사라진다.

## Background / Current State

- `scripts/messengers/` 패키지는 `TelegramMessenger`(telegram_bot.py) 하나뿐 — Telegram 전용.
- `internal.py:send_notification()`은 RegionRecommender로 추천을 모으고 GeminiCurator로 큐레이션한 뒤 **오직 TelegramMessenger로만 발송**한다. 다른 출력 경로 없음.
- `scheduler.py`의 `send_daily_recommendations`(20:00 KST) cron이 `send_notification`을 호출하는 유일한 스케줄.
- `GeminiCurator`와 `RegionRecommender`는 앱 내에서 **오직 `send_notification`에서만** 사용됨(grep 확인). 제거 시 두 패키지는 앱 미사용 상태가 되지만, **본 작업 범위(Telegram 제거)를 벗어나므로 패키지는 보존**하고 internal.py의 죽은 import만 정리한다.
- `RegionRecommender._load_region_scores`는 스텁(`return []`)이라 알림 파이프라인은 현재도 실질 무동작.

## Telegram Touchpoint Map (grep 기준)

| 영역 | 위치 | 처리 |
| --- | --- | --- |
| Messenger 패키지 | `scripts/messengers/telegram_bot.py`, `__init__.py` | **패키지 삭제** |
| 알림 로직 | `scripts/api/routes/internal.py` send_notification(232–297), /notify(300–312) | **삭제** |
| 상태 플래그 | `internal.py` /status의 `telegram_configured`(342) | **삭제** |
| import | `internal.py` 13–14(TELEGRAM_*), 32(RegionRecommender), 33(GeminiCurator), 34(TelegramMessenger), 15–16(THEME_IDS/NATIONAL_TOP — 사용처 재확인 후 정리) | **정리** |
| Scheduler | `scripts/scheduler.py` import(8), send_daily_recommendations(60–69) | **삭제** |
| Config | `scripts/config/settings.py` 29–31(TELEGRAM_*) | **삭제** |
| Dev tool | `scripts/dev/check_config.py` 26–27 import, 63–64 check_item | **삭제** |
| 의존성 | `requirements.txt` 24–25(`# Telegram`, `python-telegram-bot>=20.7`) | **삭제** |
| 환경파일 | `.env` 22–24, `.env.example` 27–29 | **삭제** |
| 문서 | `CLAUDE.md`(NotifyPhase/messengers/job4 다이어그램·서술), `scripts/api/README.md` | **갱신** |

## Implementation Steps

1. **messengers 패키지 삭제** — `scripts/messengers/telegram_bot.py`, `scripts/messengers/__init__.py` 삭제(디렉터리 제거). `__pycache__` 정리.
2. **`internal.py` 정리**
   - `send_notification()`(232–297)와 `@router.post("/notify")` `trigger_notification`(300–312) 삭제.
   - `/status`에서 `"telegram_configured": ...`(342) 줄 삭제.
   - import 정리: `TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID` 제거, `from scripts.messengers import TelegramMessenger` 제거, 삭제 후 미사용이 되는 `RegionRecommender`/`GeminiCurator` import 제거, `THEME_IDS`/`NATIONAL_TOP`은 다른 사용처 있으면 유지·없으면 제거(편집 시 grep 재확인).
3. **`scheduler.py` 정리** — import에서 `send_notification` 제거, `send_daily_recommendations` job(60–69) 삭제. cron 3개(collect_weather, generate_weather_report, recalculate_scores)만 남김.
4. **`settings.py` 정리** — `# Telegram` 주석 + `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`(29–31) 삭제.
5. **`check_config.py` 정리** — TELEGRAM import(26–27), `check_item("Telegram Bot Token"...)`, `check_item("Telegram Chat ID"...)`(63–64) 삭제.
6. **`requirements.txt` 정리** — `# Telegram`, `python-telegram-bot>=20.7`(24–25) 삭제.
7. **`.env` / `.env.example` 정리** — Telegram 블록 삭제.
8. **문서 갱신** — `CLAUDE.md`의 알림/messenger 관련 다이어그램 노드·서술(NotifyPhase, Telegram Bot API, send_daily_recommendations job, messengers 패키지, 4 cron jobs→3) 및 `scripts/api/README.md`의 `/notify`·Telegram 언급 갱신.

## Out of Scope (flag only)

- `GeminiCurator`, `RegionRecommender` 패키지 자체 삭제(제거 후 앱 미사용이 되지만 Telegram과 무관 — 별도 dead-code cleanup 대상).
- `RegionRecommender` 스텁(`_load_region_scores`) 실 구현.

## Acceptance Criteria

- **Before**: `grep -rin telegram scripts/ requirements.txt .env .env.example` → 다수 매치. cron 4개. `POST /internal/notify` 존재. `python-telegram-bot` 의존성.
- **After**:
  - `grep -rin "telegram" scripts/ --include=*.py` → **0건** (문서 제외 코드), `requirements.txt`/`.env`/`.env.example`에 telegram **0건**.
  - `scripts/messengers/` 디렉터리 **부재**.
  - `python -m py_compile`(arm64 venv) — 편집된 모든 파일 통과, `scripts.scheduler`/`scripts.api.routes.internal` import 성공.
  - scheduler cron **3개** (`send_daily_recommendations` 부재), `/internal/notify` 라우트 **부재**, `/internal/status`에 `telegram_configured` **없음**, 나머지 3개 job·auth·수집/점수 경로 **정상 유지**.
  - FastAPI TestClient: `/internal/status`(good-key)→200이고 응답에 telegram 키 없음, `/internal/notify`→404.
  - internal.py에 미사용 import(NameError/F401) **없음**.
- **회귀 없음**: H1 인증, H2 해상예보 등 직전 커밋 기능 영향 없음.

## Verification Plan

1. grep 스윕(telegram 0건) + `scripts/messengers` 부재 확인.
2. arm64 venv로 `scripts.scheduler`, `scripts.api.routes.internal` import + `py_compile`.
3. TestClient로 라우트/상태/인증 확인 (`/notify`→404, `/status`에 telegram 키 없음).
4. 어드버서리 diff 리뷰(누락된 참조·깨진 import·문서 불일치) 후 커밋.
