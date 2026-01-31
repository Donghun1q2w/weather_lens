"""Region Loader - Loads and manages regional data (읍면동) from SQLite database"""
import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import aiosqlite

from config.settings import SQLITE_DB_PATH


@dataclass
class Region:
    """Represents a Korean administrative region (읍면동)"""
    region_code: str
    sido: str
    sigungu: str
    emd: str
    lat: float
    lng: float
    is_coastal: bool = False
    elevation: Optional[int] = None

    @property
    def full_name(self) -> str:
        """Get full region name: 시도 시군구 읍면동"""
        return f"{self.sido} {self.sigungu} {self.emd}"

    @property
    def coordinates(self) -> dict[str, float]:
        """Get coordinates as dictionary"""
        return {"lat": self.lat, "lng": self.lng}


class RegionLoader:
    """Handles loading and querying regional data from SQLite database"""

    def __init__(self, db_path: Path = SQLITE_DB_PATH):
        """
        Initialize region loader.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path

    async def initialize_schema(self) -> None:
        """
        Initialize database schema if it doesn't exist.
        Creates the regions table according to spec.md schema.
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS regions (
                    region_code TEXT PRIMARY KEY,
                    sido TEXT NOT NULL,
                    sigungu TEXT NOT NULL,
                    emd TEXT NOT NULL,
                    lat REAL NOT NULL,
                    lng REAL NOT NULL,
                    is_coastal BOOLEAN DEFAULT FALSE,
                    elevation INTEGER
                )
            """)

            # Create indices for common queries
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_sido ON regions(sido)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_sigungu ON regions(sigungu)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_coastal ON regions(is_coastal)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_elevation ON regions(elevation)
            """)

            await db.commit()

    async def get_region(self, region_code: str) -> Optional[Region]:
        """
        Get a specific region by code.

        Args:
            region_code: Region code (e.g., "1168010100")

        Returns:
            Optional[Region]: Region object if found, None otherwise
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM regions WHERE region_code = ?",
                (region_code,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_region(row)
                return None

    async def get_all_regions(self) -> list[Region]:
        """
        Get all regions (approximately 3,500 읍면동).

        Returns:
            list[Region]: List of all regions
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM regions") as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_region(row) for row in rows]

    async def get_regions_by_sido(self, sido: str) -> list[Region]:
        """
        Get all regions in a specific sido (시/도).

        Args:
            sido: Sido name (e.g., "서울특별시")

        Returns:
            list[Region]: List of regions in the sido
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM regions WHERE sido = ?",
                (sido,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_region(row) for row in rows]

    async def get_regions_by_sigungu(self, sido: str, sigungu: str) -> list[Region]:
        """
        Get all regions in a specific sigungu (시/군/구).

        Args:
            sido: Sido name
            sigungu: Sigungu name (e.g., "강남구")

        Returns:
            list[Region]: List of regions in the sigungu
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM regions WHERE sido = ? AND sigungu = ?",
                (sido, sigungu)
            ) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_region(row) for row in rows]

    async def get_coastal_regions(self) -> list[Region]:
        """
        Get all coastal regions (is_coastal = TRUE).

        Returns:
            list[Region]: List of coastal regions
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM regions WHERE is_coastal = TRUE"
            ) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_region(row) for row in rows]

    async def get_high_elevation_regions(self, min_elevation: int = 500) -> list[Region]:
        """
        Get regions above specified elevation.

        Args:
            min_elevation: Minimum elevation in meters (default: 500)

        Returns:
            list[Region]: List of high-elevation regions
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM regions WHERE elevation >= ?",
                (min_elevation,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_region(row) for row in rows]

    async def insert_region(self, region: Region) -> None:
        """
        Insert a new region into the database.

        Args:
            region: Region object to insert
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO regions
                (region_code, sido, sigungu, emd, lat, lng, is_coastal, elevation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                region.region_code,
                region.sido,
                region.sigungu,
                region.emd,
                region.lat,
                region.lng,
                region.is_coastal,
                region.elevation,
            ))
            await db.commit()

    async def insert_regions_bulk(self, regions: list[Region]) -> None:
        """
        Insert multiple regions in bulk (more efficient).

        Args:
            regions: List of Region objects to insert
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.executemany("""
                INSERT OR REPLACE INTO regions
                (region_code, sido, sigungu, emd, lat, lng, is_coastal, elevation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                (
                    r.region_code,
                    r.sido,
                    r.sigungu,
                    r.emd,
                    r.lat,
                    r.lng,
                    r.is_coastal,
                    r.elevation,
                )
                for r in regions
            ])
            await db.commit()

    async def count_regions(self) -> int:
        """
        Count total number of regions in database.

        Returns:
            int: Total region count
        """
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM regions") as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def get_sidos(self) -> list[str]:
        """
        Get list of all sidos (시/도) in the database.

        Returns:
            list[str]: List of sido names
        """
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT DISTINCT sido FROM regions ORDER BY sido") as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]

    @staticmethod
    def _row_to_region(row: aiosqlite.Row) -> Region:
        """
        Convert database row to Region object.

        Args:
            row: Database row

        Returns:
            Region: Region object
        """
        return Region(
            region_code=row["region_code"],
            sido=row["sido"],
            sigungu=row["sigungu"],
            emd=row["emd"],
            lat=row["lat"],
            lng=row["lng"],
            is_coastal=bool(row["is_coastal"]),
            elevation=row["elevation"],
        )


# Convenience functions for common operations
async def load_all_regions() -> list[Region]:
    """
    Convenience function to load all regions.

    Returns:
        list[Region]: List of all regions
    """
    loader = RegionLoader()
    return await loader.get_all_regions()


async def load_region(region_code: str) -> Optional[Region]:
    """
    Convenience function to load a specific region.

    Args:
        region_code: Region code

    Returns:
        Optional[Region]: Region if found
    """
    loader = RegionLoader()
    return await loader.get_region(region_code)


async def initialize_regions_db() -> None:
    """
    Convenience function to initialize the regions database schema.
    """
    loader = RegionLoader()
    await loader.initialize_schema()
