"""Feedback Analyzer for PhotoSpot Korea - Analysis and weight optimization"""
import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import sqlite3

from feedbacks.collector import FeedbackCollector


class FeedbackAnalyzer:
    """Analyzer for feedback data and scoring accuracy

    Provides weekly accuracy verification, RMSE calculation,
    and weight adjustment recommendations.
    """

    def __init__(
        self,
        feedback_db_path: Optional[Path] = None,
        weights_path: Optional[Path] = None
    ):
        """Initialize feedback analyzer

        Args:
            feedback_db_path: Path to feedback database
            weights_path: Path to weights.json configuration
        """
        self.collector = FeedbackCollector(feedback_db_path)

        if weights_path is None:
            from config.settings import BASE_DIR
            weights_path = BASE_DIR / "config" / "weights.json"

        self.weights_path = weights_path
        self._load_weights()

    def _load_weights(self):
        """Load current weights configuration"""
        with open(self.weights_path, 'r', encoding='utf-8') as f:
            self.weights = json.load(f)

    def calculate_rmse(
        self,
        predicted_scores: list[float],
        actual_ratings: list[float]
    ) -> float:
        """Calculate Root Mean Square Error

        Args:
            predicted_scores: List of predicted scores (0-100)
            actual_ratings: List of actual user ratings (1-5)

        Returns:
            float: RMSE value
        """
        if len(predicted_scores) != len(actual_ratings):
            raise ValueError("Predicted and actual lists must have same length")

        if len(predicted_scores) == 0:
            return 0.0

        # Normalize ratings to 0-100 scale
        normalized_ratings = [(r - 1) / 4 * 100 for r in actual_ratings]

        # Calculate squared errors
        squared_errors = [
            (pred - actual) ** 2
            for pred, actual in zip(predicted_scores, normalized_ratings)
        ]

        # Return RMSE
        mse = sum(squared_errors) / len(squared_errors)
        return math.sqrt(mse)

    def weekly_accuracy_verification(
        self,
        theme_id: Optional[int] = None
    ) -> dict:
        """Perform weekly accuracy verification

        Compares predicted scores with actual user feedback.

        Args:
            theme_id: Filter by specific theme (optional)

        Returns:
            dict: Accuracy metrics including RMSE, success rate, etc.
        """
        # Get weekly feedback data
        weekly_data = self.collector.get_weekly_comparison_data(theme_id)

        if not weekly_data:
            return {
                'period': 'last_7_days',
                'theme_id': theme_id,
                'sample_size': 0,
                'rmse': 0.0,
                'success_rate': 0.0,
                'avg_rating': 0.0,
                'recommendation': 'Insufficient data for analysis'
            }

        # Extract ratings and success flags
        ratings = [d['rating'] for d in weekly_data]
        successes = [d['score_success'] for d in weekly_data]

        # Calculate metrics
        sample_size = len(weekly_data)
        success_rate = sum(successes) / sample_size * 100
        avg_rating = sum(ratings) / sample_size

        # For RMSE, we would need the predicted scores at time of prediction
        # This is a placeholder - in production, you'd fetch from score history
        # For now, estimate based on success rate
        predicted_scores = [80.0 if s else 40.0 for s in successes]
        rmse = self.calculate_rmse(predicted_scores, ratings)

        # Generate recommendation
        recommendation = self._generate_recommendation(
            rmse, success_rate, avg_rating
        )

        return {
            'period': 'last_7_days',
            'theme_id': theme_id,
            'sample_size': sample_size,
            'rmse': round(rmse, 2),
            'success_rate': round(success_rate, 2),
            'avg_rating': round(avg_rating, 2),
            'recommendation': recommendation
        }

    def _generate_recommendation(
        self,
        rmse: float,
        success_rate: float,
        avg_rating: float
    ) -> str:
        """Generate weight adjustment recommendation

        Args:
            rmse: Root mean square error
            success_rate: Percentage of successful outcomes
            avg_rating: Average user rating

        Returns:
            str: Recommendation text
        """
        recommendations = []

        if rmse > 30:
            recommendations.append("High RMSE detected - consider weight rebalancing")

        if success_rate < 60:
            recommendations.append("Low success rate - scoring may be too optimistic")
        elif success_rate > 90:
            recommendations.append("Very high success rate - consider more strict criteria")

        if avg_rating < 3.0:
            recommendations.append("Low user satisfaction - review scoring criteria")
        elif avg_rating > 4.5:
            recommendations.append("Excellent user satisfaction - current weights performing well")

        if not recommendations:
            return "Performance within acceptable range - no changes needed"

        return " | ".join(recommendations)

    def suggest_weight_adjustments(
        self,
        theme_id: int,
        min_samples: int = 20
    ) -> Optional[dict]:
        """Suggest weight adjustments based on feedback analysis

        Args:
            theme_id: Theme ID to analyze
            min_samples: Minimum samples required for analysis

        Returns:
            dict: Suggested weight adjustments or None if insufficient data
        """
        from config.settings import THEME_IDS

        theme_name = THEME_IDS.get(theme_id, f"theme_{theme_id}")

        # Get weekly data
        weekly_data = self.collector.get_weekly_comparison_data(theme_id)

        if len(weekly_data) < min_samples:
            return {
                'theme_id': theme_id,
                'theme_name': theme_name,
                'status': 'insufficient_data',
                'sample_size': len(weekly_data),
                'required_samples': min_samples,
                'adjustments': []
            }

        # Calculate current performance
        accuracy = self.weekly_accuracy_verification(theme_id)

        # Analyze failure patterns
        failure_patterns = self._analyze_failure_patterns(weekly_data)

        # Generate specific weight adjustments
        adjustments = []

        # If RMSE is high, suggest adjustments
        if accuracy['rmse'] > 25:
            if 'cloud_cover' in failure_patterns:
                adjustments.append({
                    'parameter': 'cloud_cover',
                    'current_weight': self._get_current_weight(theme_name, 'cloud_cover'),
                    'suggested_change': -0.05,
                    'reason': 'Cloud cover predictions showing high variance'
                })

            if 'rain_prob' in failure_patterns:
                adjustments.append({
                    'parameter': 'rain_prob',
                    'current_weight': self._get_current_weight(theme_name, 'rain_prob'),
                    'suggested_change': +0.05,
                    'reason': 'Rain probability more critical than current weight'
                })

        return {
            'theme_id': theme_id,
            'theme_name': theme_name,
            'status': 'analysis_complete',
            'sample_size': len(weekly_data),
            'current_rmse': accuracy['rmse'],
            'success_rate': accuracy['success_rate'],
            'adjustments': adjustments
        }

    def _analyze_failure_patterns(self, weekly_data: list[dict]) -> list[str]:
        """Analyze common patterns in failed predictions

        Args:
            weekly_data: Weekly feedback data

        Returns:
            list[str]: List of problematic parameters
        """
        failures = [d for d in weekly_data if not d['score_success']]

        if not failures:
            return []

        problematic_params = []

        # Analyze actual weather conditions in failures
        for failure in failures:
            actual = failure['actual_weather']

            # Check if cloud cover was problematic
            if actual.get('cloud_cover', 0) > 80:
                problematic_params.append('cloud_cover')

            # Check if rain was problematic
            if actual.get('rain', False):
                problematic_params.append('rain_prob')

            # Check if wind was problematic
            if actual.get('wind_speed', 0) > 10:
                problematic_params.append('wind_speed')

        # Return unique problematic parameters
        return list(set(problematic_params))

    def _get_current_weight(self, theme_name: str, parameter: str) -> float:
        """Get current weight for a parameter

        Args:
            theme_name: Theme name key
            parameter: Parameter name

        Returns:
            float: Current weight value
        """
        try:
            theme_config = self.weights['themes'].get(theme_name, {})
            param_config = theme_config.get(parameter, {})
            return param_config.get('weight', 0.0)
        except (KeyError, TypeError):
            return 0.0

    def generate_weekly_report(self) -> dict:
        """Generate comprehensive weekly report for all themes

        Returns:
            dict: Weekly report with accuracy metrics for all themes
        """
        from config.settings import THEME_IDS

        report = {
            'report_date': datetime.now().isoformat(),
            'period': 'last_7_days',
            'themes': {},
            'overall': {
                'total_feedbacks': 0,
                'avg_success_rate': 0.0,
                'avg_rmse': 0.0
            }
        }

        total_success_rates = []
        total_rmses = []

        for theme_id, theme_name in THEME_IDS.items():
            accuracy = self.weekly_accuracy_verification(theme_id)

            report['themes'][theme_name] = accuracy
            report['overall']['total_feedbacks'] += accuracy['sample_size']

            if accuracy['sample_size'] > 0:
                total_success_rates.append(accuracy['success_rate'])
                total_rmses.append(accuracy['rmse'])

        # Calculate overall averages
        if total_success_rates:
            report['overall']['avg_success_rate'] = round(
                sum(total_success_rates) / len(total_success_rates), 2
            )
            report['overall']['avg_rmse'] = round(
                sum(total_rmses) / len(total_rmses), 2
            )

        return report

    def export_report_to_file(
        self,
        output_path: Optional[Path] = None
    ) -> Path:
        """Export weekly report to JSON file

        Args:
            output_path: Output file path (optional)

        Returns:
            Path: Path to exported report
        """
        report = self.generate_weekly_report()

        if output_path is None:
            from config.settings import DATA_DIR
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = DATA_DIR / f"weekly_report_{timestamp}.json"

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return output_path
