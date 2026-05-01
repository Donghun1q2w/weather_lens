"""공통 로깅 설정 — main / scheduler / 라이프사이클 스크립트가 동일 포맷을 공유."""
import logging

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    """루트 로거를 설정하고 호출 모듈용 logger 반환."""
    logging.basicConfig(level=level, format=LOG_FORMAT)
    return logging.getLogger()
