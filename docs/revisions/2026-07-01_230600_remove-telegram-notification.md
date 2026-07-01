# Remove Telegram notification feature (전체 제거)

- **Date**: 2026-07-01 23:06:00 KST
- **Plan**: [docs/plans/2026-07-01_225224_remove-telegram-notification.md](../plans/2026-07-01_225224_remove-telegram-notification.md)
- **Scope**: 알림 기능 전체 제거 (Telegram이 유일 알림 수단 → 알림 파이프라인 전체 삭제)

## 변경 요약

Telegram이 유일한 알림 전송 수단이라, 관련 기능 제거가 알림 파이프라인 전체 삭제로 이어짐. cron 4→3개, 알림 API(`/internal/notify`) 제거.

### 삭제
- `scripts/messengers/` 패키지 전체 (`telegram_bot.py`, `__init__.py`) — Telegram 전용 패키지.
- `scripts/api/routes/internal.py`:
  - `send_notification()` 함수 (추천 집계 + Gemini 큐레이션 + Telegram 발송) 전체.
  - `POST /internal/notify` 라우트(`trigger_notification`).
  - `/internal/status`의 `telegram_configured` 플래그.
  - 죽은 import: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `NATIONAL_TOP`, `GeminiCurator`, `TelegramMessenger`. (`THEME_IDS`, `RegionRecommender`는 `calculate_scores`에서 여전히 사용 → 유지.)
- `scripts/scheduler.py`: `send_daily_recommendations`(20:00 KST) job + `send_notification` import.
- `scripts/config/settings.py`: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
- `scripts/dev/check_config.py`: TELEGRAM import + `check_item` 2건.
- `requirements.txt`: `python-telegram-bot>=20.7`.
- `.env` / `.env.example`: TELEGRAM 블록.

### 문서
- `CLAUDE.md`: 개요 문장("+ Telegram" 제거), 디렉터리 트리(`messengers/`), Diagram 3(cron 4→3, J4/F4/E4 노드·엣지), Diagram 4(헤더 "collect → score", NotifyPhase subgraph·Gem·TG 노드), Diagram 7(`msg` 노드, `intnl-->msg`/`intnl-->cur` 엣지), Cross-Cutting Notes(4→3개, 2개 함수).
- `scripts/api/README.md`: `/internal/notify` 엔드포인트 블록 + "20:00 Daily notifications" 스케줄러 항목.

### 범위 밖(보존)
- `GeminiCurator`·`RegionRecommender` 패키지 — 제거 후 앱 미사용이 되나 Telegram과 무관하여 유지(별도 dead-code cleanup 대상). `internal.py`의 죽은 import만 정리.

## 검증

- grep: `scripts/*.py`·`requirements.txt`·`.env(.example)`·`CLAUDE.md`·`api/README.md` 내 telegram/messenger/notify **0건**. 다이어그램 dangling 참조(Gem/TG/Messenger/msg/F4/J4/E4/NotifyPhase) **0건**. mermaid fence 균형(18=9쌍).
- `scripts/messengers/` 디렉터리 부재.
- py_compile: 편집 파일 전부 통과.
- arm64 venv import + FastAPI TestClient:
  - scheduler jobs = 3 (`collect_weather`, `generate_weather_report`, `recalculate_scores`), `send_daily_recommendations` 부재.
  - internal routes = `/collect`, `/score`, `/status`. `POST /internal/notify` → **404**.
  - `GET /internal/status`(good-key) → 200, `telegram_configured` 키 없음.
  - 잔재 import(NameError) 없음.
- 직전 커밋(H1 인증·H2 해상예보) 기능 영향 없음.
