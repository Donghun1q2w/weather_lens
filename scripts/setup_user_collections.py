"""
사용자 컬렉션 테이블 설정 스크립트

사용자가 자신만의 출사지 컬렉션을 만들고 관리할 수 있는 테이블을 생성합니다.
- user_collections: 사용자의 컬렉션(폴더/앨범) 정보
- user_collection_spots: 컬렉션에 포함된 출사지 정보

사용법:
    python scripts/setup_user_collections.py
"""
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import SQLITE_DB_PATH


def create_user_collections_tables():
    """사용자 컬렉션 테이블 생성"""

    print(f"데이터베이스: {SQLITE_DB_PATH}")

    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()

    # 사용자 컬렉션 테이블 (폴더/앨범)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_collections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            color_code TEXT DEFAULT '1',
            icon_id TEXT DEFAULT '1',
            is_default BOOLEAN DEFAULT FALSE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, name)
        )
    """)

    # 컬렉션 내 출사지 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_collection_spots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            collection_id INTEGER NOT NULL,
            photo_spot_id INTEGER,
            custom_name TEXT,
            custom_lat REAL,
            custom_lon REAL,
            region_code TEXT,
            memo TEXT,
            tags TEXT,
            source_url TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (collection_id) REFERENCES user_collections(id) ON DELETE CASCADE,
            FOREIGN KEY (photo_spot_id) REFERENCES photo_spots(id)
        )
    """)

    # 인덱스 생성
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_collections_user ON user_collections(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_collection_spots_collection ON user_collection_spots(collection_id)")

    conn.commit()
    print("✅ 테이블 생성 완료")

    # 테이블 확인
    cursor.execute("SELECT COUNT(*) FROM user_collections")
    collections = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM user_collection_spots")
    spots = cursor.fetchone()[0]

    print(f"📊 현재 컬렉션 수: {collections}개")
    print(f"📊 현재 컬렉션 내 출사지 수: {spots}개")

    conn.close()


def main():
    print("=" * 60)
    print("사용자 컬렉션 테이블 설정")
    print("=" * 60)

    create_user_collections_tables()

    print("\n" + "=" * 60)
    print("✅ 설정 완료!")
    print("=" * 60)
    print("\n다음 단계:")
    print("  - scripts/import_naver_spots.py 실행하여 네이버 지도 데이터 임포트")


if __name__ == "__main__":
    main()
