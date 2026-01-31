# Recommenders, Curators & Messengers Modules

## Quick Start

### Installation
All dependencies are already in `requirements.txt`:
```bash
pip install -r requirements.txt
```

### Configuration
Set environment variables in `.env`:
```bash
GEMINI_API_KEY=your_gemini_api_key
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### Basic Usage

#### 1. Recommenders
```python
from recommenders import RegionRecommender

recommender = RegionRecommender()

# Get top region for a theme in a specific sido
top_regions = await recommender.get_sido_top(theme_id=1, sido="서울특별시")

# Get national top 10 for a theme
national_top = await recommender.get_national_top(theme_id=1, limit=10)

# Get all recommendations for all 8 themes
all_recs = await recommender.get_all_recommendations()
```

#### 2. Curators
```python
from curators import GeminiCurator

curator = GeminiCurator()

# Generate curation text for a single region
curation = await curator.generate_curation(
    region_name="서울특별시 강남구 역삼동",
    theme_name="일출",
    score=87.5,
    weather_summary={"temp": -3, "cloud": 30, "rain_prob": 10, "pm25": 18}
)

# Batch generate curations
curations = await curator.generate_batch_curations([
    {
        "region_code": "1168010100",
        "region_name": "서울특별시 강남구 역삼동",
        "theme_name": "일출",
        "score": 87.5,
        "weather_summary": {...}
    },
    # ... more regions
])

# Check API usage
stats = curator.get_usage_stats()
print(f"Used: {stats['call_count']}/{stats['daily_limit']}")
```

#### 3. Messengers
```python
from messengers import TelegramMessenger

messenger = TelegramMessenger()

# Send daily recommendations for each theme
recommendations = {
    1: [  # Theme ID 1 (일출)
        {
            "region_name": "강원도 양양군 현북면",
            "score": 92.3,
            "curation": "맑은 하늘과 적당한 구름으로...",
            "lat": 38.1234,
            "lng": 128.5678
        },
        # ... more regions
    ],
    # ... more themes
}

results = await messenger.send_daily_recommendations(recommendations)

# Send daily summary (compact)
await messenger.send_daily_summary(recommendations)

# Send alerts
await messenger.send_alert("Data collection completed", priority="info")

# Send feedback report
await messenger.send_feedback_report(
    region_name="강원도 양양군 현북면",
    theme_name="일출",
    fail_count=3,
    penalty_score=-20
)
```

---

## Module Details

### RegionRecommender

**Purpose**: Extract top-scoring regions for photography themes.

**Methods**:
- `get_sido_top(theme_id, sido)` - Get top region in a sido
- `get_national_top(theme_id, limit=10)` - Get national top N
- `get_all_recommendations()` - All 8 themes, all top regions
- `get_sido_summary(theme_id)` - All sidos, top 1 each
- `clear_cache()` - Clear in-memory score cache

**Data Structure**:
```python
RegionScore(
    region_code="1168010100",
    region_name="서울특별시 강남구 역삼동",
    sido="서울특별시",
    sigungu="강남구",
    emd="역삼동",
    score=87.5,
    lat=37.5000,
    lng=127.0364,
    weather_summary={"temp": -3, "cloud": 30, ...},
    forecast_datetime="2026-01-29T06:00:00",
    theme_id=1
)
```

**Performance**:
- Caches scores per theme in memory
- O(n log n) sorting for ~3,500 regions
- Async I/O for non-blocking operations

---

### GeminiCurator

**Purpose**: Generate natural language curation text using Gemini AI.

**Methods**:
- `generate_curation(region_name, theme_name, score, weather_summary)` - Single curation
- `generate_batch_curations(regions_data)` - Parallel batch processing
- `get_usage_stats()` - API usage tracking

**Rate Limiting**:
- Daily limit: 1,500 requests
- Actual usage: ~100 requests/day
- Auto-reset at midnight
- Pre-call limit check

**Prompt Strategy**:
- Context-rich: region, theme, score, weather
- Theme-specific warnings (omega, bioluminescence)
- 2-3 sentence output
- Realistic, non-exaggerated

**Error Handling**:
- Graceful degradation on missing API key
- Returns `None` on failure
- Detailed error logging

---

### TelegramMessenger

**Purpose**: Send recommendations and alerts via Telegram Bot.

**Methods**:
- `send_message(message, parse_mode="HTML")` - Generic send
- `send_daily_recommendations(recommendations)` - Theme-by-theme
- `send_daily_summary(all_recommendations)` - Compact overview
- `send_alert(message, priority="info")` - Real-time alerts
- `send_feedback_report(...)` - User feedback alerts
- `send_system_status(status)` - Health check report

**Formatting**:
- HTML parse mode with emojis
- Ranking indicators (🥇🥈🥉)
- Google Maps links for each location
- Priority emojis (ℹ️⚠️🚨)

**Rate Limiting**:
- Telegram limit: 30 messages/second
- Implementation: 0.5s delay between messages
- Sequential batch sending

---

## Integration with Other Modules

### Flow Diagram
```
[Collectors]
    ↓ (weather data)
[Processors]
    ↓ (merged cache)
[Scorers]
    ↓ (theme scores)
[Recommenders] ← YOU ARE HERE
    ↓ (top regions)
[Curators]
    ↓ (curation text)
[Messengers]
    ↓ (telegram delivery)
```

### Dependencies
```python
# From config/settings.py
- CACHE_DIR, THEME_IDS
- NATIONAL_TOP, REGIONS_PER_SIDO_TOP
- GEMINI_API_KEY, GEMINI_MODEL, GEMINI_DAILY_LIMIT
- TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
```

### Integration Points
1. **Scorers → Recommenders**: Score calculation needed
2. **Recommenders → Curators**: TOP regions feed curation
3. **Curators → Messengers**: Curation text in messages
4. **Scheduler**: Triggers daily workflow
5. **API**: Exposes recommendations via REST endpoints

---

## Testing

### Unit Tests
```bash
# Test module imports and instantiation
python test_modules.py
```

### Integration Testing (Manual)
```python
import asyncio
from recommenders import RegionRecommender
from curators import GeminiCurator
from messengers import TelegramMessenger

async def test_workflow():
    # 1. Get recommendations
    recommender = RegionRecommender()
    recs = await recommender.get_all_recommendations()

    # 2. Generate curations (requires GEMINI_API_KEY)
    curator = GeminiCurator()
    for theme_id, regions in recs.items():
        for region in regions[:3]:  # Test first 3
            curation = await curator.generate_curation(
                region_name=region.region_name,
                theme_name=THEME_IDS[theme_id],
                score=region.score,
                weather_summary=region.weather_summary
            )
            print(f"{region.region_name}: {curation}")

    # 3. Send to Telegram (requires TELEGRAM_BOT_TOKEN)
    messenger = TelegramMessenger()
    await messenger.send_daily_summary(recs)

asyncio.run(test_workflow())
```

---

## API Keys Setup

### 1. Gemini API Key
1. Visit: https://aistudio.google.com/app/apikey
2. Create new API key
3. Add to `.env`: `GEMINI_API_KEY=your_key_here`

### 2. Telegram Bot
1. Message @BotFather on Telegram
2. Send `/newbot` and follow instructions
3. Copy bot token
4. Add to `.env`: `TELEGRAM_BOT_TOKEN=your_token_here`

### 3. Telegram Chat ID
1. Message @userinfobot or @get_id_bot
2. Copy your chat ID
3. Add to `.env`: `TELEGRAM_CHAT_ID=your_id_here`

---

## Troubleshooting

### "Gemini model not initialized"
- Check `GEMINI_API_KEY` is set in environment
- Verify `google-generativeai` is installed
- Run `pip install google-generativeai`

### "Telegram bot not initialized"
- Check `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are set
- Verify `python-telegram-bot` is installed
- Run `pip install python-telegram-bot`

### "No scores found for theme_id"
- RegionRecommender needs scorers module integration
- Currently returns empty lists (TODO in code)
- Complete scorers module first

### "API rate limit exceeded"
- Gemini: 1,500 calls/day limit reached
- Wait for daily reset (midnight)
- Check usage: `curator.get_usage_stats()`

### "Telegram rate limit"
- Sending too fast (>30 msg/sec)
- Increase delay in batch sending
- Default 0.5s should be safe

---

## Performance Tips

### Recommenders
- Cache scores in memory (already implemented)
- Clear cache after daily workflow: `recommender.clear_cache()`
- Batch load regions if processing multiple themes

### Curators
- Use `generate_batch_curations()` for parallel processing
- Limit to TOP N regions only (~80-100 calls/day)
- Monitor daily usage with `get_usage_stats()`

### Messengers
- Use `send_daily_summary()` for compact messages
- Avoid sending too many individual messages
- Respect 0.5s delay between messages

---

## Future Enhancements

### Recommenders
- [ ] Real score calculation integration
- [ ] Persistent cache (Redis/Memcached)
- [ ] Region filtering by user preferences
- [ ] Custom ranking algorithms

### Curators
- [ ] A/B testing for prompt variations
- [ ] Multi-language support
- [ ] Prompt template customization
- [ ] Fallback to rule-based curation

### Messengers
- [ ] Multi-user support (broadcast)
- [ ] Message queuing with retry
- [ ] Discord integration
- [ ] Email delivery option
- [ ] Web push notifications

---

## Contributing

### Code Style
- Use type hints on all methods
- Async/await for I/O operations
- Comprehensive docstrings
- Error handling with logging

### Testing
- Add unit tests for new features
- Integration tests for workflows
- Manual testing with real APIs

### Documentation
- Update this README for new features
- Add docstrings to new methods
- Update IMPLEMENTATION_SUMMARY.md

---

## License

MIT License - See LICENSE file

---

## Support

For issues or questions:
1. Check this README
2. Review IMPLEMENTATION_SUMMARY.md
3. Check learnings.md in .omc/notepads/
4. Open an issue on GitHub

---

*Last Updated: 2026-01-30*
*Modules: Recommenders, Curators, Messengers*
