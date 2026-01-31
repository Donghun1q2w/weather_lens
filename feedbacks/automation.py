"""Feedback Automation for PhotoSpot Korea - Real-time penalties and auto-tuning"""
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from feedbacks.collector import FeedbackCollector
from feedbacks.analyzer import FeedbackAnalyzer


class ScorePenaltyManager:
    """Manager for real-time score penalties based on user feedback"""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize penalty manager

        Args:
            db_path: Path to database (uses regions.db by default)
        """
        if db_path is None:
            from config.settings import SQLITE_DB_PATH
            db_path = SQLITE_DB_PATH

        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize score_penalties table"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS score_penalties (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    region_code TEXT NOT NULL,
                    theme_id INTEGER NOT NULL,
                    penalty_score INTEGER DEFAULT 0,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reason TEXT,
                    UNIQUE(region_code, theme_id)
                )
            """)

            # Index for efficient lookups
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_penalties_expiry
                ON score_penalties(expires_at)
            """)

            conn.commit()

    def apply_penalty(
        self,
        region_code: str,
        theme_id: int,
        penalty_score: int,
        duration_hours: int,
        reason: str
    ) -> bool:
        """Apply penalty to region-theme combination

        Args:
            region_code: Region code
            theme_id: Theme ID
            penalty_score: Penalty points (negative value)
            duration_hours: How long penalty should last
            reason: Reason for penalty

        Returns:
            bool: True if penalty applied successfully
        """
        expires_at = datetime.now() + timedelta(hours=duration_hours)

        with sqlite3.connect(self.db_path) as conn:
            # Use INSERT OR REPLACE to handle existing penalties
            conn.execute("""
                INSERT OR REPLACE INTO score_penalties
                (region_code, theme_id, penalty_score, expires_at, reason, created_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (region_code, theme_id, penalty_score, expires_at.isoformat(), reason))

            conn.commit()

        return True

    def get_active_penalty(
        self,
        region_code: str,
        theme_id: int
    ) -> Optional[dict]:
        """Get active penalty for region-theme combination

        Args:
            region_code: Region code
            theme_id: Theme ID

        Returns:
            dict: Penalty info or None if no active penalty
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT penalty_score, expires_at, reason, created_at
                FROM score_penalties
                WHERE region_code = ?
                  AND theme_id = ?
                  AND expires_at > datetime('now')
            """, (region_code, theme_id))

            row = cursor.fetchone()
            if row:
                return {
                    'penalty_score': row['penalty_score'],
                    'expires_at': datetime.fromisoformat(row['expires_at']),
                    'reason': row['reason'],
                    'created_at': datetime.fromisoformat(row['created_at'])
                }

        return None

    def cleanup_expired_penalties(self) -> int:
        """Remove expired penalties from database

        Returns:
            int: Number of penalties removed
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM score_penalties
                WHERE expires_at <= datetime('now')
            """)
            conn.commit()
            return cursor.rowcount


class FeedbackAutomation:
    """Automation logic for real-time penalties and weight tuning"""

    def __init__(
        self,
        feedback_db_path: Optional[Path] = None,
        penalty_db_path: Optional[Path] = None
    ):
        """Initialize feedback automation

        Args:
            feedback_db_path: Path to feedback database
            penalty_db_path: Path to penalty database (regions.db)
        """
        self.collector = FeedbackCollector(feedback_db_path)
        self.analyzer = FeedbackAnalyzer(feedback_db_path)
        self.penalty_manager = ScorePenaltyManager(penalty_db_path)

    def check_and_apply_realtime_penalty(
        self,
        region_code: str,
        theme_id: int,
        failure_threshold: int = 3,
        time_window_hours: int = 1,
        penalty_score: int = -20,
        penalty_duration_hours: int = 6
    ) -> Optional[dict]:
        """Check for failure surge and apply penalty if needed

        This should be called after each feedback submission.

        Args:
            region_code: Region code
            theme_id: Theme ID
            failure_threshold: Number of failures to trigger penalty
            time_window_hours: Time window to check failures
            penalty_score: Penalty points to apply
            penalty_duration_hours: How long penalty lasts

        Returns:
            dict: Penalty info if applied, None otherwise
        """
        # Count recent failures
        failure_count = self.collector.count_recent_failures(
            region_code, theme_id, time_window_hours
        )

        if failure_count >= failure_threshold:
            # Apply penalty
            from config.settings import THEME_IDS
            theme_name = THEME_IDS.get(theme_id, f"Theme {theme_id}")

            reason = (
                f"{failure_count} failure reports in {time_window_hours}h "
                f"for {theme_name} at {region_code}"
            )

            self.penalty_manager.apply_penalty(
                region_code=region_code,
                theme_id=theme_id,
                penalty_score=penalty_score,
                duration_hours=penalty_duration_hours,
                reason=reason
            )

            return {
                'region_code': region_code,
                'theme_id': theme_id,
                'penalty_score': penalty_score,
                'duration_hours': penalty_duration_hours,
                'failure_count': failure_count,
                'reason': reason
            }

        return None

    def get_adjusted_score(
        self,
        region_code: str,
        theme_id: int,
        base_score: float
    ) -> float:
        """Get score with penalties applied

        Args:
            region_code: Region code
            theme_id: Theme ID
            base_score: Original calculated score

        Returns:
            float: Adjusted score (0-100)
        """
        penalty = self.penalty_manager.get_active_penalty(region_code, theme_id)

        if penalty:
            adjusted_score = base_score + penalty['penalty_score']
            return max(0.0, min(100.0, adjusted_score))

        return base_score

    def run_monthly_auto_tuning(
        self,
        min_samples_per_theme: int = 50,
        max_weight_delta: float = 0.1
    ) -> dict:
        """Run monthly automatic weight tuning

        This should be run as a scheduled job once per month.

        Args:
            min_samples_per_theme: Minimum samples required for tuning
            max_weight_delta: Maximum allowed weight change per iteration

        Returns:
            dict: Tuning results and changes applied
        """
        from config.settings import THEME_IDS, BASE_DIR

        weights_path = BASE_DIR / "config" / "weights.json"

        # Load current weights
        with open(weights_path, 'r', encoding='utf-8') as f:
            current_weights = json.load(f)

        tuning_results = {
            'timestamp': datetime.now().isoformat(),
            'themes': {},
            'changes_applied': False,
            'backup_created': False
        }

        # Create backup
        backup_path = weights_path.parent / f"weights_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(current_weights, f, indent=2)
        tuning_results['backup_created'] = True
        tuning_results['backup_path'] = str(backup_path)

        # Analyze each theme
        weights_modified = False

        for theme_id, theme_name in THEME_IDS.items():
            suggestions = self.analyzer.suggest_weight_adjustments(
                theme_id, min_samples=min_samples_per_theme
            )

            tuning_results['themes'][theme_name] = {
                'sample_size': suggestions.get('sample_size', 0),
                'status': suggestions.get('status', 'unknown'),
                'adjustments': suggestions.get('adjustments', [])
            }

            # Apply adjustments if available
            if suggestions.get('status') == 'analysis_complete':
                adjustments = suggestions.get('adjustments', [])

                for adj in adjustments:
                    param = adj['parameter']
                    change = adj['suggested_change']

                    # Clamp change to max_weight_delta
                    change = max(-max_weight_delta, min(max_weight_delta, change))

                    # Apply change to weights
                    if theme_name in current_weights['themes']:
                        theme_config = current_weights['themes'][theme_name]
                        if param in theme_config:
                            old_weight = theme_config[param].get('weight', 0)
                            new_weight = old_weight + change

                            # Ensure weight stays in valid range [0, 1]
                            new_weight = max(0.0, min(1.0, new_weight))

                            theme_config[param]['weight'] = round(new_weight, 3)
                            weights_modified = True

                            tuning_results['themes'][theme_name]['applied'] = True

        # Save modified weights if changes were made
        if weights_modified:
            current_weights['last_updated'] = datetime.now().strftime('%Y-%m-%d')
            current_weights['version'] = current_weights.get('version', '1.0')

            with open(weights_path, 'w', encoding='utf-8') as f:
                json.dump(current_weights, f, indent=2, ensure_ascii=False)

            tuning_results['changes_applied'] = True

        return tuning_results

    def cleanup_expired_penalties(self) -> int:
        """Cleanup expired penalties

        Returns:
            int: Number of penalties removed
        """
        return self.penalty_manager.cleanup_expired_penalties()

    def send_penalty_notification(
        self,
        penalty_info: dict,
        telegram_enabled: bool = True
    ) -> bool:
        """Send notification about applied penalty

        Args:
            penalty_info: Penalty information from check_and_apply_realtime_penalty
            telegram_enabled: Whether to send Telegram notification

        Returns:
            bool: True if notification sent successfully
        """
        if not telegram_enabled:
            return False

        try:
            from config.settings import THEME_IDS

            theme_name = THEME_IDS.get(penalty_info['theme_id'], f"Theme {penalty_info['theme_id']}")

            message = (
                f"⚠️ [User Report Alert]\n\n"
                f"Region: {penalty_info['region_code']}\n"
                f"Theme: {theme_name}\n"
                f"Failure Count: {penalty_info['failure_count']}\n"
                f"Penalty Applied: {penalty_info['penalty_score']} points\n"
                f"Duration: {penalty_info['duration_hours']} hours\n\n"
                f"Reason: {penalty_info['reason']}"
            )

            # In production, send via Telegram
            # For now, just log
            print(message)

            return True

        except Exception as e:
            print(f"Failed to send penalty notification: {e}")
            return False
