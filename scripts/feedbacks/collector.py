"""Feedback Collector for PhotoSpot Korea - User feedback collection and storage"""
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional
import sqlite3
from pathlib import Path


@dataclass
class Feedback:
    """User feedback data structure

    Attributes:
        region_code: Region code (10 digits)
        theme_id: Theme ID (1-8)
        score_success: Whether photography was successful
        actual_weather: Actual weather conditions reported by user
        rating: User satisfaction rating (1-5 stars)
        comment: Optional user comment
        photo_url: Optional URL to uploaded photo
        created_at: Timestamp of feedback submission
    """
    region_code: str
    theme_id: int
    score_success: bool
    actual_weather: dict
    rating: int
    comment: Optional[str] = None
    photo_url: Optional[str] = None
    created_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate and set defaults"""
        if self.created_at is None:
            self.created_at = datetime.now()

        # Validate rating
        if not 1 <= self.rating <= 5:
            raise ValueError(f"Rating must be between 1 and 5, got {self.rating}")

        # Validate theme_id
        if not 1 <= self.theme_id <= 8:
            raise ValueError(f"Theme ID must be between 1 and 8, got {self.theme_id}")

        # Validate region_code length
        if len(self.region_code) != 10:
            raise ValueError(f"Region code must be 10 digits, got {self.region_code}")


class FeedbackCollector:
    """Collector for user feedback on photography scores

    Handles submission, validation, and storage of user feedback.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize feedback collector

        Args:
            db_path: Path to SQLite database. If None, uses default from config.
        """
        if db_path is None:
            from config.settings import DATA_DIR
            db_path = DATA_DIR / "feedbacks.db"

        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feedbacks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    region_code TEXT NOT NULL,
                    theme_id INTEGER NOT NULL,
                    score_success BOOLEAN NOT NULL,
                    actual_weather TEXT NOT NULL,
                    rating INTEGER NOT NULL,
                    comment TEXT,
                    photo_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (theme_id) REFERENCES themes(id)
                )
            """)

            # Create indexes for efficient queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedbacks_region_theme
                ON feedbacks(region_code, theme_id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedbacks_created_at
                ON feedbacks(created_at)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedbacks_success
                ON feedbacks(score_success)
            """)

            conn.commit()

    def submit_feedback(self, feedback: Feedback) -> int:
        """Submit user feedback to database

        Args:
            feedback: Feedback object to submit

        Returns:
            int: ID of inserted feedback record

        Raises:
            ValueError: If feedback validation fails
            sqlite3.Error: If database operation fails
        """
        import json

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO feedbacks (
                    region_code, theme_id, score_success,
                    actual_weather, rating, comment, photo_url, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                feedback.region_code,
                feedback.theme_id,
                feedback.score_success,
                json.dumps(feedback.actual_weather),
                feedback.rating,
                feedback.comment,
                feedback.photo_url,
                feedback.created_at.isoformat()
            ))

            conn.commit()
            return cursor.lastrowid

    def get_recent_feedbacks(
        self,
        region_code: Optional[str] = None,
        theme_id: Optional[int] = None,
        hours: int = 1,
        success_only: Optional[bool] = None
    ) -> list[dict]:
        """Get recent feedbacks within specified time window

        Args:
            region_code: Filter by region code (optional)
            theme_id: Filter by theme ID (optional)
            hours: Time window in hours (default: 1)
            success_only: Filter by success status (optional)

        Returns:
            list[dict]: List of feedback records
        """
        import json
        from datetime import timedelta

        query = """
            SELECT id, region_code, theme_id, score_success,
                   actual_weather, rating, comment, photo_url, created_at
            FROM feedbacks
            WHERE created_at >= datetime('now', ?)
        """
        params = [f'-{hours} hours']

        if region_code:
            query += " AND region_code = ?"
            params.append(region_code)

        if theme_id:
            query += " AND theme_id = ?"
            params.append(theme_id)

        if success_only is not None:
            query += " AND score_success = ?"
            params.append(success_only)

        query += " ORDER BY created_at DESC"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            feedbacks = []
            for row in rows:
                feedback = dict(row)
                feedback['actual_weather'] = json.loads(feedback['actual_weather'])
                feedback['created_at'] = datetime.fromisoformat(feedback['created_at'])
                feedback['score_success'] = bool(feedback['score_success'])
                feedbacks.append(feedback)

            return feedbacks

    def get_feedback_stats(
        self,
        region_code: Optional[str] = None,
        theme_id: Optional[int] = None,
        days: int = 7
    ) -> dict:
        """Get aggregated feedback statistics

        Args:
            region_code: Filter by region code (optional)
            theme_id: Filter by theme ID (optional)
            days: Time window in days (default: 7)

        Returns:
            dict: Statistics including success rate, average rating, etc.
        """
        query = """
            SELECT
                COUNT(*) as total_count,
                SUM(CASE WHEN score_success = 1 THEN 1 ELSE 0 END) as success_count,
                AVG(rating) as avg_rating,
                MIN(rating) as min_rating,
                MAX(rating) as max_rating
            FROM feedbacks
            WHERE created_at >= datetime('now', ?)
        """
        params = [f'-{days} days']

        if region_code:
            query += " AND region_code = ?"
            params.append(region_code)

        if theme_id:
            query += " AND theme_id = ?"
            params.append(theme_id)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            row = cursor.fetchone()

            if row['total_count'] == 0:
                return {
                    'total_count': 0,
                    'success_count': 0,
                    'success_rate': 0.0,
                    'avg_rating': 0.0,
                    'min_rating': 0,
                    'max_rating': 0
                }

            return {
                'total_count': row['total_count'],
                'success_count': row['success_count'],
                'success_rate': row['success_count'] / row['total_count'] * 100,
                'avg_rating': row['avg_rating'],
                'min_rating': row['min_rating'],
                'max_rating': row['max_rating']
            }

    def count_recent_failures(
        self,
        region_code: str,
        theme_id: int,
        hours: int = 1
    ) -> int:
        """Count recent failure reports for specific region and theme

        Args:
            region_code: Region code
            theme_id: Theme ID
            hours: Time window in hours

        Returns:
            int: Number of failure reports
        """
        query = """
            SELECT COUNT(*) as count
            FROM feedbacks
            WHERE region_code = ?
              AND theme_id = ?
              AND score_success = 0
              AND created_at >= datetime('now', ?)
        """

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, (region_code, theme_id, f'-{hours} hours'))
            result = cursor.fetchone()
            return result[0] if result else 0

    def get_weekly_comparison_data(self, theme_id: Optional[int] = None) -> list[dict]:
        """Get weekly data for prediction vs actual comparison

        Args:
            theme_id: Filter by theme ID (optional)

        Returns:
            list[dict]: Feedback data for weekly analysis
        """
        import json

        query = """
            SELECT region_code, theme_id, score_success,
                   actual_weather, rating, created_at
            FROM feedbacks
            WHERE created_at >= datetime('now', '-7 days')
        """
        params = []

        if theme_id:
            query += " AND theme_id = ?"
            params.append(theme_id)

        query += " ORDER BY created_at ASC"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            data = []
            for row in rows:
                record = dict(row)
                record['actual_weather'] = json.loads(record['actual_weather'])
                record['created_at'] = datetime.fromisoformat(record['created_at'])
                record['score_success'] = bool(record['score_success'])
                data.append(record)

            return data
