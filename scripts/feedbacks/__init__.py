"""User feedback collection and analysis."""
from scripts.feedbacks.collector import Feedback, FeedbackCollector
from scripts.feedbacks.analyzer import FeedbackAnalyzer

__all__ = [
    "Feedback",
    "FeedbackCollector",
    "FeedbackAnalyzer",
]
