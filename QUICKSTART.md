# PhotoSpot Korea - Quick Start Guide

## Prerequisites
```bash
# Ensure Python 3.10+ is installed
python --version

# Install dependencies
pip install -r requirements.txt
```

## Running Locally

### Option 1: Full Application (API + Scheduler)
```bash
# Run both API and scheduler together
python main.py
```

The application will:
- Start FastAPI on port 8000
- Start APScheduler with cron jobs
- Be accessible at http://localhost:8000

### Option 2: API Only (Development)
```bash
# Run API with auto-reload for development
uvicorn api.main:app --reload --port 8000
```

Good for:
- Developing new endpoints
- Testing API changes
- Frontend development

### Option 3: Scheduler Only (Testing)
```bash
# Run scheduler standalone
python scheduler.py
```

Good for:
- Testing scheduled jobs
- Debugging cron schedules
- Verifying internal API calls

## Verify Installation

### 1. Check Health
```bash
curl http://localhost:8000/health
```

Expected:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-30T12:00:00",
  "service": "PhotoSpot Korea"
}
```

### 2. Run Full Test Suite
```bash
python test_api.py
```

### 3. View API Documentation
Open in browser:
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)

## Environment Variables

### Required for Production
```bash
export INTERNAL_API_KEY="your-secret-key"
```

### Optional (with defaults)
```bash
export ENVIRONMENT="development"
export LOG_LEVEL="INFO"
```

### For Full Functionality (when other modules are ready)
```bash
export KMA_API_KEY="your-kma-key"
export AIRKOREA_API_KEY="your-airkorea-key"
export KHOA_API_KEY="your-khoa-key"
export GEMINI_API_KEY="your-gemini-key"
export TELEGRAM_BOT_TOKEN="your-telegram-token"
export TELEGRAM_CHAT_ID="your-chat-id"
```

## Quick API Tests

### Get Themes
```bash
curl http://localhost:8000/api/v1/themes
```

### Get Top Regions for Theme
```bash
curl http://localhost:8000/api/v1/themes/1/top
```

### Submit Feedback
```bash
curl -X POST http://localhost:8000/api/v1/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "region_code": "1168010100",
    "theme_id": 1,
    "score_success": true,
    "rating": 5
  }'
```

### Trigger Internal Operations (with auth)
```bash
# Set your internal API key
export API_KEY="dev-internal-key"

# Trigger data collection
curl -X POST http://localhost:8000/internal/collect \
  -H "X-API-Key: $API_KEY"

# Trigger score calculation
curl -X POST http://localhost:8000/internal/score \
  -H "X-API-Key: $API_KEY"

# Trigger notification
curl -X POST http://localhost:8000/internal/notify \
  -H "X-API-Key: $API_KEY"
```

## Development Workflow

### 1. Make Changes
Edit files in `api/routes/` or other modules

### 2. Test Locally
```bash
# Start with auto-reload
uvicorn api.main:app --reload

# In another terminal, test the change
curl http://localhost:8000/your-new-endpoint
```

### 3. Run Test Suite
```bash
python test_api.py
```

### 4. Check Logs
Watch the console output for any errors or warnings

## Scheduled Jobs (When Running with Scheduler)

Jobs will run at:
- **06:00, 18:00** - Weather data collection
- **07:00, 19:00** - Score calculation
- **20:00** - Daily notifications

To test immediately without waiting:
```bash
# Trigger manually via internal API
curl -X POST http://localhost:8000/internal/collect \
  -H "X-API-Key: dev-internal-key"
```

## Troubleshooting

### Port Already in Use
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use a different port
uvicorn api.main:app --port 8001
```

### Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Verify installation
python -c "import fastapi; import apscheduler; print('OK')"
```

### Scheduler Not Running
- Make sure you're running `main.py`, not `api/main.py`
- Check logs for "Starting APScheduler" message
- Verify no errors during startup

### Internal API 403 Errors
- Check that `X-API-Key` header matches `INTERNAL_API_KEY`
- Default key for development is `dev-internal-key`
- Set `INTERNAL_API_KEY` environment variable if changed

## Next Steps

1. ✅ Install dependencies
2. ✅ Run the application
3. ✅ Test with curl or browser
4. ⏳ Integrate with other modules (collectors, scorers, etc.)
5. ⏳ Deploy to Render
6. ⏳ Set up UptimeRobot monitoring

## Documentation

- **API Reference**: http://localhost:8000/docs
- **API Guide**: `api/README.md`
- **Deployment**: `DEPLOYMENT.md`
- **Implementation Details**: `API_SCHEDULER_IMPLEMENTATION.md`

## Support

For issues or questions:
1. Check logs for error messages
2. Review documentation files
3. Test with `test_api.py`
4. Check `.omc/notepads/` for technical details
