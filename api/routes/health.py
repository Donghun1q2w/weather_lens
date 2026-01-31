"""Health check endpoint for UptimeRobot monitoring"""
from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint for UptimeRobot monitoring.

    Returns:
        dict: Service status and timestamp
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "PhotoSpot Korea",
    }
