"""PhotoSpot Korea - Configuration Settings"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
BOUNDARIES_DIR = DATA_DIR / "boundaries"

# Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# API Keys
KMA_API_KEY = os.getenv("KMA_API_KEY", "")
KMA_API_SOURCE = os.getenv("KMA_API_SOURCE", "data.go.kr")  # "data.go.kr" or "apihub.kma.go.kr"
AIRKOREA_API_KEY = os.getenv("AIRKOREA_API_KEY", "")
KHOA_API_KEY = os.getenv("KHOA_API_KEY", "")
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Supabase (expansion phase)
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# Database
SQLITE_DB_PATH = DATA_DIR / "regions.db"
OCEAN_MAPPING_DB_PATH = DATA_DIR / "ocean_mapping.db"

# Data collection settings
KMA_WEIGHT = 0.6  # 기상청 가중치
OPENMETEO_WEIGHT = 0.4  # Open-Meteo 가중치
DEVIATION_THRESHOLD = 5.0  # 편차 경고 임계값

# Forecast settings
FORECAST_DAYS = 3  # D-day ~ D+2
UPDATE_INTERVAL_HOURS = 12  # 갱신 주기

# Gemini settings
GEMINI_MODEL = "gemini-1.5-flash"
GEMINI_DAILY_LIMIT = 1500
GEMINI_TOP_N = 10  # 테마별 TOP N만 호출

# Theme IDs (16 themes total)
THEME_IDS = {
    1: "일출",
    2: "일출 오메가",
    3: "일몰",
    4: "일몰 오메가",
    5: "은하수",
    6: "야광충",
    7: "바다 장노출",
    8: "운해",
    9: "별궤적",
    10: "야경",
    11: "안개",
    12: "반영",
    13: "골든아워",
    14: "블루아워",
    15: "상고대",
    16: "월출"
}

# Regional settings
REGIONS_PER_SIDO_TOP = 1  # 시도별 테마당 TOP N
NATIONAL_TOP = 10  # 전국 테마별 TOP N

# Internal API settings
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "dev-internal-key")  # For scheduled jobs
