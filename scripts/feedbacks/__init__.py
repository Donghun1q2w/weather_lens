"""Feedbacks module for PhotoSpot Korea - User feedback collection and analysis"""
from scripts.feedbacks.collector import Feedback, FeedbackCollector
from scripts.feedbacks.analyzer import FeedbackAnalyzer
from scripts.feedbacks.automation import (
    ScorePenaltyManager,
    FeedbackAutomation,
)

__all__ = [
    'Feedback',
    'FeedbackCollector',
    'FeedbackAnalyzer',
    'ScorePenaltyManager',
    'FeedbackAutomation',
]
