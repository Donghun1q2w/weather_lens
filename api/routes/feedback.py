"""Feedback submission endpoint"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

router = APIRouter()


class FeedbackSubmission(BaseModel):
    """Feedback submission model"""

    region_code: str = Field(..., description="10-digit region code")
    theme_id: int = Field(..., ge=1, le=8, description="Theme ID (1-8)")
    score_success: bool = Field(..., description="Was the photography successful?")
    actual_weather: Optional[Dict[str, Any]] = Field(
        None, description="Actual weather conditions observed"
    )
    rating: int = Field(..., ge=1, le=5, description="Satisfaction rating (1-5)")
    comment: Optional[str] = Field(None, description="Optional user comment")
    photo_url: Optional[str] = Field(None, description="Optional evidence photo URL")


@router.post("/feedback")
async def submit_feedback(feedback: FeedbackSubmission) -> Dict[str, Any]:
    """
    Submit user feedback for a photography spot recommendation.

    Args:
        feedback: Feedback data including success status, rating, and comments

    Returns:
        Confirmation message and feedback ID
    """
    # TODO: Save to database
    # TODO: Trigger real-time penalty check if score_success is False
    # For now, return success response

    feedback_data = {
        "id": f"fb_{datetime.utcnow().timestamp()}",
        "region_code": feedback.region_code,
        "theme_id": feedback.theme_id,
        "score_success": feedback.score_success,
        "rating": feedback.rating,
        "created_at": datetime.utcnow().isoformat(),
        "status": "received",
    }

    return {
        "message": "Feedback received successfully",
        "feedback": feedback_data,
        "note": "Database integration pending",
    }
