"""
설정 확인 스크립트

환경변수와 데이터베이스가 올바르게 설정되었는지 확인합니다.

사용법:
    python scripts/check_config.py
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# .env 파일 로드
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from config.settings import (
    KMA_API_KEY,
    AIRKOREA_API_KEY,
    KHOA_API_KEY,
    GEMINI_API_KEY,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    SQLITE_DB_PATH,
    OCEAN_MAPPING_DB_PATH,
    DATA_DIR,
    CACHE_DIR,
)


def check_item(name: str, value, is_required: bool = False) -> bool:
    """항목 체크 및 출력"""
    if value:
        if len(str(value)) > 20:
            display = str(value)[:20] + "..."
        else:
            display = str(value)
        print(f"  ✅ {name}: {display}")
        return True
    else:
        if is_required:
            print(f"  ❌ {name}: 설정 안됨 (필수)")
        else:
            print(f"  ⚪ {name}: 설정 안됨 (선택)")
        return False


def main():
    print("=" * 50)
    print("Weather Lens 설정 확인")
    print("=" * 50)

    # 1. API 키 확인
    print("\n📡 API 키 상태:")
    required_ok = check_item("기상청 API (KMA)", KMA_API_KEY, is_required=True)
    check_item("에어코리아 API", AIRKOREA_API_KEY)
    check_item("바다누리 API (KHOA)", KHOA_API_KEY)
    check_item("Gemini API", GEMINI_API_KEY)
    check_item("Telegram Bot Token", TELEGRAM_BOT_TOKEN)
    check_item("Telegram Chat ID", TELEGRAM_CHAT_ID)

    # 2. 데이터베이스 확인
    print("\n💾 데이터베이스 상태:")
    if SQLITE_DB_PATH.exists():
        import sqlite3
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM regions")
        count = cursor.fetchone()[0]
        conn.close()
        print(f"  ✅ regions.db: {count}개 지역 등록됨")
        db_ok = True
    else:
        print(f"  ❌ regions.db: 파일 없음")
        print(f"     → python scripts/init_database.py 실행 필요")
        db_ok = False

    if OCEAN_MAPPING_DB_PATH.exists():
        print(f"  ✅ ocean_mapping.db: 존재함")
    else:
        print(f"  ⚪ ocean_mapping.db: 파일 없음")

    # 3. 디렉토리 확인
    print("\n📁 디렉토리 상태:")
    print(f"  {'✅' if DATA_DIR.exists() else '❌'} data/: {DATA_DIR}")
    print(f"  {'✅' if CACHE_DIR.exists() else '⚪'} data/cache/: {CACHE_DIR}")

    # 4. 종합 결과
    print("\n" + "=" * 50)
    if required_ok and db_ok:
        print("✅ 기본 설정 완료! 서버를 실행할 수 있습니다.")
        print("\n다음 명령어로 서버 시작:")
        print("  python main.py")
    else:
        print("⚠️  필수 설정이 누락되었습니다.")
        if not required_ok:
            print("  → .env 파일에 KMA_API_KEY를 설정하세요")
        if not db_ok:
            print("  → python scripts/init_database.py를 실행하세요")
    print("=" * 50)


if __name__ == "__main__":
    main()
