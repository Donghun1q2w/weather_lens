# PhotoSpot Korea - Deployment Guide

## Prerequisites

1. GitHub repository with code
2. Render account (https://render.com)
3. UptimeRobot account (https://uptimerobot.com)
4. API keys for:
   - 기상청 (KMA)
   - 에어코리아 (Air Korea)
   - 바다누리 (KHOA)
   - Google Gemini
   - Telegram Bot

## Step 1: Render Deployment

### Option A: Using render.yaml (Recommended)

1. Connect GitHub repository to Render
2. Render will auto-detect `render.yaml`
3. Configure environment variables in Render dashboard
4. Deploy

### Option B: Manual Configuration

1. Create new Web Service in Render
2. Connect GitHub repository
3. Configure:
   - **Name**: photospot-korea
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:fastapi_app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free

### Environment Variables (Render Dashboard)

```
ENVIRONMENT=production
LOG_LEVEL=INFO
KMA_API_KEY=your_key_here
AIRKOREA_API_KEY=your_key_here
KHOA_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
INTERNAL_API_KEY=generate_random_secure_key
```

## Step 2: UptimeRobot Setup (Prevent Cold Starts)

Render Free tier sleeps after 15 minutes of inactivity, causing 25-second cold starts.

### Configure Monitor

1. Log in to UptimeRobot
2. Create New Monitor:
   - **Monitor Type**: HTTP(s)
   - **Friendly Name**: PhotoSpot Korea Health Check
   - **URL**: `https://your-app.onrender.com/health`
   - **Monitoring Interval**: 5 minutes
   - **Alert Contacts**: Add email/Telegram

This keeps your service warm 24/7 within free tier limits.

## Step 3: Verify Deployment

### Check Health Endpoint

```bash
curl https://your-app.onrender.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-30T12:00:00",
  "service": "PhotoSpot Korea"
}
```

### Check API Documentation

Open in browser:
- https://your-app.onrender.com/docs (Swagger UI)
- https://your-app.onrender.com/redoc (ReDoc)

### Test Scheduled Jobs

```bash
# Trigger data collection manually
curl -X POST https://your-app.onrender.com/internal/collect \
  -H "X-API-Key: your_internal_api_key"

# Check logs in Render dashboard
```

## Step 4: Scheduler Verification

The scheduler runs automatically when the app starts. Verify in Render logs:

```
Starting APScheduler...
Scheduled jobs:
  - collect_weather: cron[hour='6,18']
  - recalculate_scores: cron[hour='7,19']
  - send_daily_recommendations: cron[hour='20']
APScheduler started successfully
```

## Step 5: Telegram Bot Setup

1. Create bot via @BotFather
2. Get bot token
3. Get chat ID (send message to bot, then call `https://api.telegram.org/bot<token>/getUpdates`)
4. Add to Render environment variables

## Monitoring & Maintenance

### Render Dashboard
- Check logs for errors
- Monitor resource usage
- Review deployment history

### UptimeRobot Dashboard
- Verify uptime statistics
- Check response times
- Review alert history

### Log Monitoring

Key log patterns to watch:
```
[WARMUP] Ping received
[WeatherCollection] Success
[ScoreCalculation] Success
[DailyRecommendation] Success
```

## Troubleshooting

### Cold Start Issues
- Verify UptimeRobot is pinging every 5 minutes
- Check /health endpoint response time

### Scheduler Not Running
- Check Render logs for APScheduler startup messages
- Verify timezone settings (uses UTC)
- Test internal endpoints manually

### API Key Errors
- Verify all keys are set in Render dashboard
- Check key format and validity
- Review logs for specific error messages

## Costs

### Current Setup (Free Tier)
- Render: $0/month (750 hours)
- UptimeRobot: $0/month (50 monitors)
- APIs: $0/month (within free quotas)
- **Total: $0/month**

### Upgrade Path (If Needed)

| Service | Free | Paid | Cost |
|---------|------|------|------|
| Render | Cold starts | Always warm | $7/month |
| Supabase | 500MB | 8GB | $25/month |
| Open-Meteo | 10K/day | Unlimited | $29/month |

## Next Steps

1. Monitor first 24 hours for errors
2. Verify all scheduled jobs run correctly
3. Test end-to-end workflow
4. Set up backup/restore procedures
5. Document incident response procedures

## Support

For issues:
1. Check Render logs first
2. Review GitHub Issues
3. Check API documentation
4. Contact maintainers

## Rollback Procedure

If deployment fails:
1. Go to Render dashboard
2. Select service
3. Click "Rollback" to previous version
4. Investigate logs
5. Fix issues and redeploy
