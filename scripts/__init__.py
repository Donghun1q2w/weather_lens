"""Weather Lens — Python source tree.

이 패키지는 프로젝트의 모든 런타임 코드를 호스팅한다:

- 진입점: ``scripts.main`` (FastAPI 앱), ``scripts.scheduler`` (APScheduler)
- 도메인 패키지: ``api``, ``collectors``, ``config``, ``curators``, ``data``,
  ``feedbacks``, ``messengers``, ``models``, ``processors``, ``recommenders``,
  ``scorers``, ``utils``
- 라이프사이클 스크립트: ``setup`` (1회성 부트스트랩), ``ingest`` (외부 데이터 import),
  ``ops`` (정기 운영), ``dev`` (개발자 도구)

배포 진입점은 ``uvicorn scripts.main:fastapi_app`` (``render.yaml`` 참조).
"""
