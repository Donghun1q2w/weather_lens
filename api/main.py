"""PhotoSpot Korea - FastAPI Main Application"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import health, themes, regions, feedback, internal, astronomy, photo_spots, user_collections, marine
from api.routes import map as map_routes

app = FastAPI(
    title="PhotoSpot Korea API",
    description="Weather-based photography spot curation service",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router, tags=["health"])
app.include_router(themes.router, prefix="/api/v1", tags=["themes"])
app.include_router(regions.router, prefix="/api/v1", tags=["regions"])
app.include_router(feedback.router, prefix="/api/v1", tags=["feedback"])
app.include_router(map_routes.router, prefix="/api/v1", tags=["map"])
app.include_router(internal.router, prefix="/internal", tags=["internal"])
app.include_router(astronomy.router, prefix="/api/v1", tags=["astronomy"])
app.include_router(photo_spots.router, prefix="/api/v1", tags=["photo-spots"])
app.include_router(user_collections.router, prefix="/api/v1", tags=["user-collections"])
app.include_router(marine.router, prefix="/api/v1", tags=["marine"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "PhotoSpot Korea",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }
