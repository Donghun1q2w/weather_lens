"""PhotoSpot Korea - Main Entry Point

This module runs both the FastAPI application and the APScheduler
together in a single process, suitable for Render deployment.
"""
import logging
import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from api.main import app as fastapi_app
from scheduler import start_scheduler, stop_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI app.
    Starts scheduler on startup, stops on shutdown.
    """
    logger.info("Starting PhotoSpot Korea application...")
    start_scheduler()
    logger.info("Application startup complete")

    yield

    logger.info("Shutting down application...")
    stop_scheduler()
    logger.info("Application shutdown complete")


# Attach lifespan to FastAPI app
fastapi_app.router.lifespan_context = lifespan


if __name__ == "__main__":
    # Run with uvicorn
    # For Render deployment, use: uvicorn main:fastapi_app --host 0.0.0.0 --port $PORT
    uvicorn.run(
        "main:fastapi_app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable reload in production
        log_level="info",
    )
