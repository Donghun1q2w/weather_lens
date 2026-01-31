"""Feedbacks module for PhotoSpot Korea - User feedback collection and analysis"""
from feedbacks.collector import Feedback, FeedbackCollector
from feedbacks.analyzer import FeedbackAnalyzer
from feedbacks.automation import (
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
