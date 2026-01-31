"""PhotoSpot Korea - Warmup Handler for Render Free Tier

This module prevents Render Free tier from sleeping by responding to
UptimeRobot pings every 5 minutes. The /health endpoint in the API
serves this purpose.

UptimeRobot Configuration:
- Monitor Type: HTTP(s)
- URL: https://your-app.onrender.com/health
- Monitoring Interval: 5 minutes
- Alert Contact: Your email/Telegram

This keeps the service warm and avoids the 25-second cold start delay.
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def log_warmup_ping():
    """
    Log warmup ping for monitoring.
    Called by the /health endpoint when accessed.
    """
    logger.info(f"[WARMUP] Ping received at {datetime.utcnow().isoformat()}")


def get_warmup_status():
    """
    Get current warmup status.

    Returns:
        dict: Warmup status information
    """
    return {
        "warmup_active": True,
        "last_ping": datetime.utcnow().isoformat(),
        "message": "Service is warm and ready",
    }


# Integration with FastAPI app
# The /health endpoint in api/routes/health.py serves as the warmup target
# No additional server needed - UptimeRobot pings the existing API
