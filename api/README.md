# PhotoSpot Korea - API Documentation

## Overview

FastAPI-based REST API for PhotoSpot Korea service. Provides endpoints for theme queries, region details, feedback submission, and internal operations.

## Architecture

```
api/
├── main.py              # FastAPI application entry point
├── routes/
│   ├── health.py        # Health check endpoint (UptimeRobot)
│   ├── themes.py        # Theme-related endpoints
│   ├── regions.py       # Region details and forecasts
│   ├── feedback.py      # User feedback submission
│   ├── map.py           # Map boundaries (GeoJSON)
│   └── internal.py      # Internal APIs (authenticated)
└── README.md
```

## Running the API

### Development Mode

```bash
# Run API only (without scheduler)
uvicorn api.main:app --reload --port 8000

# Run with scheduler
python main.py
```

### Production Mode (Render)

```bash
# Render will use this command (specified in render.yaml or dashboard)
uvicorn main:fastapi_app --host 0.0.0.0 --port $PORT
```

## API Endpoints

### Public Endpoints

#### Health Check
```
GET /health
Response: { "status": "healthy", "timestamp": "...", "service": "PhotoSpot Korea" }
```

#### Themes
```
GET /api/v1/themes
Response: List of all photography themes

GET /api/v1/themes/{theme_id}/top?limit=10
Response: Top N regions for specified theme
```

#### Regions
```
GET /api/v1/regions/{region_code}
Response: Region metadata and scores

GET /api/v1/regions/{region_code}/forecast
Response: 3-day weather forecast
```

#### Feedback
```
POST /api/v1/feedback
Body: {
  "region_code": "1168010100",
  "theme_id": 1,
  "score_success": true,
  "rating": 5,
  "comment": "Great recommendation!"
}
Response: Confirmation and feedback ID
```

#### Map
```
GET /api/v1/map/boundaries?level=sido&region_code=11
Response: GeoJSON FeatureCollection
```

### Internal Endpoints (Authenticated)

Require `X-API-Key` header with `INTERNAL_API_KEY` value.

```
POST /internal/collect
Trigger: Weather data collection

POST /internal/score
Trigger: Score recalculation

POST /internal/notify
Trigger: Telegram notifications
```

## Environment Variables

```env
# Internal API authentication
INTERNAL_API_KEY=your-secret-key

# Other settings inherited from config/settings.py
ENVIRONMENT=development
LOG_LEVEL=INFO
```

## Integration with Scheduler

The scheduler (`scheduler.py`) calls internal endpoints at scheduled times:
- 06:00, 18:00: Data collection
- 07:00, 19:00: Score calculation
- 20:00: Daily notifications

## CORS Configuration

Currently set to `allow_origins=["*"]` for development. Update for production:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-domain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

## API Documentation

Interactive API docs available at:
- Swagger UI: `/docs`
- ReDoc: `/redoc`

## Testing

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test themes endpoint
curl http://localhost:8000/api/v1/themes

# Test internal endpoint (requires auth)
curl -X POST http://localhost:8000/internal/collect \
  -H "X-API-Key: dev-internal-key"
```

## Next Steps

1. Implement database integration (SQLite/Supabase)
2. Connect to collector/scorer modules
3. Add authentication for public endpoints (optional)
4. Implement rate limiting
5. Add response caching
6. Set up monitoring and logging
