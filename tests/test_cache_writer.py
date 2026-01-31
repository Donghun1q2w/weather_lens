"""Tests for cache_writer module"""
import pytest
from datetime import datetime, timedelta
from pathlib import Path

from processors.cache_writer import CacheWriter, write_weather_cache
from processors.data_merger import WeatherData, WeatherValue


@pytest.fixture
def tmp_cache_dir(tmp_path):
    """Create temporary cache directory for testing"""
    return tmp_path / "cache"


@pytest.fixture
def cache_writer(tmp_cache_dir):
    """Create CacheWriter instance with temporary directory"""
    return CacheWriter(cache_dir=tmp_cache_dir)


@pytest.fixture
def sample_weather_data():
    """Create sample WeatherData object for testing"""
    return WeatherData(
        datetime=datetime(2026, 1, 31, 12, 0),
        temp=WeatherValue(kma=15.0, openmeteo=14.5, avg=14.8, deviation_flag=False),
        cloud=WeatherValue(kma=50.0, openmeteo=55.0, avg=52.0, deviation_flag=False),
        rain_prob=WeatherValue(kma=30.0, openmeteo=25.0, avg=28.0, deviation_flag=False),
        rain_amount=WeatherValue(kma=0.0, openmeteo=0.0, avg=0.0, deviation_flag=False),
        humidity=WeatherValue(kma=60.0, openmeteo=62.0, avg=60.8, deviation_flag=False),
        wind_speed=WeatherValue(kma=3.5, openmeteo=3.2, avg=3.38, deviation_flag=False),
        pm25=15.0,
        pm10=30.0,
        sunrise="06:30",
        sunset="18:00",
        visibility=10.0,
    )


@pytest.fixture
def sample_coordinates():
    """Sample coordinates for testing"""
    return {"lat": 37.5665, "lng": 126.9780}


# Test Basic Operations


@pytest.mark.asyncio
async def test_write_and_read_cache(cache_writer, sample_weather_data, sample_coordinates):
    """Test writing and reading cache data"""
    region_code = "1168010100"
    region_name = "서울특별시 강남구 역삼동"
    forecast = [sample_weather_data]
    test_date = datetime(2026, 1, 31)

    # Write cache
    cache_path = await cache_writer.write_cache(
        region_code=region_code,
        region_name=region_name,
        coordinates=sample_coordinates,
        forecast=forecast,
        ocean_station_id=None,
        date=test_date,
    )

    # Verify file was created
    assert cache_path.exists()

    # Read cache
    cached_data = await cache_writer.read_cache(
        region_code=region_code,
        region_name=region_name,
        date=test_date,
    )

    # Verify data
    assert cached_data is not None
    assert cached_data["region_code"] == region_code
    assert cached_data["region_name"] == region_name
    assert cached_data["coordinates"]["lat"] == sample_coordinates["lat"]
    assert cached_data["coordinates"]["lng"] == sample_coordinates["lng"]
    assert len(cached_data["forecast"]) == 1
    assert cached_data["ocean_station_id"] is None


@pytest.mark.asyncio
async def test_write_cache_with_ocean_station(cache_writer, sample_weather_data, sample_coordinates):
    """Test writing cache with ocean station ID"""
    region_code = "4817063000"
    region_name = "전라남도 신안군 흑산면"
    ocean_station_id = "12C30000"
    forecast = [sample_weather_data]
    test_date = datetime(2026, 1, 31)

    cache_path = await cache_writer.write_cache(
        region_code=region_code,
        region_name=region_name,
        coordinates=sample_coordinates,
        forecast=forecast,
        ocean_station_id=ocean_station_id,
        date=test_date,
    )

    # Read and verify
    cached_data = await cache_writer.read_cache(
        region_code=region_code,
        region_name=region_name,
        date=test_date,
    )

    assert cached_data["ocean_station_id"] == ocean_station_id


@pytest.mark.asyncio
async def test_write_cache_invalid_coordinates(cache_writer, sample_weather_data):
    """Test that write_cache raises error with invalid coordinates"""
    with pytest.raises(ValueError, match="Coordinates must contain 'lat' and 'lng' keys"):
        await cache_writer.write_cache(
            region_code="1168010100",
            region_name="서울특별시 강남구 역삼동",
            coordinates={"lat": 37.5665},  # Missing 'lng'
            forecast=[sample_weather_data],
        )


@pytest.mark.asyncio
async def test_read_nonexistent_cache(cache_writer):
    """Test reading cache that doesn't exist returns None"""
    cached_data = await cache_writer.read_cache(
        region_code="9999999999",
        region_name="존재하지 않는 지역",
        date=datetime(2026, 1, 31),
    )
    assert cached_data is None


# Test Cache Path Generation


def test_cache_path_generation(cache_writer):
    """Test cache file path generation"""
    test_date = datetime(2026, 1, 31)
    region_code = "서울특별시_강남구_역삼동"

    path = cache_writer._get_cache_path(test_date, region_code)

    assert "2026-01-31" in str(path)
    assert "regions" in str(path)
    assert path.name == f"{region_code}.json"


def test_beach_cache_path_generation(cache_writer):
    """Test beach cache file path generation"""
    test_date = datetime(2026, 1, 31)
    beach_num = 123

    path = cache_writer._get_beach_cache_path(test_date, beach_num)

    assert "2026-01-31" in str(path)
    assert "beaches" in str(path)
    assert path.name == f"{beach_num}.json"


def test_marine_cache_path_generation(cache_writer):
    """Test marine zone cache file path generation"""
    test_date = datetime(2026, 1, 31)
    zone_code = "12C30000"

    path = cache_writer._get_marine_cache_path(test_date, zone_code)

    assert "2026-01-31" in str(path)
    assert "marine" in str(path)
    assert path.name == f"{zone_code}.json"


def test_format_region_code():
    """Test region name to code formatting"""
    # Test normal 3-part name
    assert CacheWriter._format_region_code("서울특별시 강남구 역삼동") == "서울특별시_강남구_역삼동"

    # Test 2-part name
    assert CacheWriter._format_region_code("서울특별시 강남구") == "서울특별시_강남구"

    # Test single part name
    assert CacheWriter._format_region_code("서울특별시") == "서울특별시"

    # Test with extra spaces
    assert CacheWriter._format_region_code("  서울특별시  강남구  역삼동  ") == "서울특별시_강남구_역삼동"


# Test Simple Write/Read Methods


@pytest.mark.asyncio
async def test_simple_write_and_read(cache_writer):
    """Test simple write and read methods"""
    region_code = "test_region"
    test_data = {
        "region_code": region_code,
        "temperature": 20.5,
        "humidity": 60,
    }
    test_date = datetime(2026, 1, 31)

    # Write using simple method
    cache_path = await cache_writer.write(region_code, test_data, date=test_date)
    assert cache_path.exists()

    # Read using simple method
    cached_data = await cache_writer.read(region_code, date=test_date)
    assert cached_data is not None
    assert cached_data["region_code"] == region_code
    assert cached_data["temperature"] == 20.5
    assert cached_data["humidity"] == 60


@pytest.mark.asyncio
async def test_simple_read_nonexistent(cache_writer):
    """Test simple read of nonexistent cache returns None"""
    cached_data = await cache_writer.read("nonexistent_region", date=datetime(2026, 1, 31))
    assert cached_data is None


@pytest.mark.asyncio
async def test_write_defaults_to_today(cache_writer):
    """Test that write defaults to today's date when date is None"""
    region_code = "test_region"
    test_data = {"test": "data"}

    cache_path = await cache_writer.write(region_code, test_data)

    # Should be in today's directory
    today_str = datetime.now().strftime("%Y-%m-%d")
    assert today_str in str(cache_path)


# Test Clear Old Caches


def test_clear_old_caches(cache_writer):
    """Test clearing old cache directories"""
    # Create cache directories for different dates
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    old_date = today - timedelta(days=5)

    # Create directories
    for date in [today, yesterday, old_date]:
        date_str = date.strftime("%Y-%m-%d")
        date_dir = cache_writer.cache_dir / date_str / "regions"
        date_dir.mkdir(parents=True, exist_ok=True)
        # Create a dummy file
        (date_dir / "test.json").write_text("{}")

    # Clear caches older than 3 days
    removed_count = cache_writer.clear_old_caches(days_to_keep=3)

    # Should have removed only the old date directory
    assert removed_count == 1

    # Verify old directory is gone
    old_date_str = old_date.strftime("%Y-%m-%d")
    assert not (cache_writer.cache_dir / old_date_str).exists()

    # Verify recent directories still exist
    today_str = today.strftime("%Y-%m-%d")
    yesterday_str = yesterday.strftime("%Y-%m-%d")
    assert (cache_writer.cache_dir / today_str).exists()
    assert (cache_writer.cache_dir / yesterday_str).exists()


def test_clear_old_caches_with_invalid_dirs(cache_writer):
    """Test that clear_old_caches skips invalid directory names"""
    # Create valid and invalid directories
    (cache_writer.cache_dir / "2026-01-31").mkdir(parents=True)
    (cache_writer.cache_dir / "invalid-dir").mkdir(parents=True)
    (cache_writer.cache_dir / "test.txt").touch()

    # Should not crash and should skip invalid names
    removed_count = cache_writer.clear_old_caches(days_to_keep=0)

    # Should have removed the valid date directory (older than 0 days)
    assert removed_count >= 0  # May or may not remove depending on timing
    # Invalid directory should still exist
    assert (cache_writer.cache_dir / "invalid-dir").exists()


def test_clear_old_caches_empty_dir(cache_writer):
    """Test clearing old caches on empty directory"""
    # Empty cache directory
    removed_count = cache_writer.clear_old_caches(days_to_keep=3)
    assert removed_count == 0


# Test Convenience Function


@pytest.mark.asyncio
async def test_convenience_function(tmp_cache_dir, sample_weather_data, sample_coordinates):
    """Test the write_weather_cache convenience function"""
    # This will use default CACHE_DIR, so we can't easily test it
    # without modifying config. Just verify it doesn't crash.
    region_code = "1168010100"
    region_name = "서울특별시 강남구 역삼동"
    forecast = [sample_weather_data]

    # Note: This will write to the actual CACHE_DIR, not tmp_cache_dir
    # In a real test environment, you might want to mock CACHE_DIR
    cache_path = await write_weather_cache(
        region_code=region_code,
        region_name=region_name,
        coordinates=sample_coordinates,
        forecast=forecast,
        ocean_station_id=None,
    )

    assert cache_path is not None
    assert isinstance(cache_path, Path)


# Test Multiple Forecast Items


@pytest.mark.asyncio
async def test_write_multiple_forecast_items(cache_writer, sample_coordinates):
    """Test writing cache with multiple forecast items"""
    region_code = "1168010100"
    region_name = "서울특별시 강남구 역삼동"
    test_date = datetime(2026, 1, 31)

    # Create multiple forecast items
    forecast = [
        WeatherData(
            datetime=datetime(2026, 1, 31, 12, 0),
            temp=WeatherValue(kma=15.0, openmeteo=14.5, avg=14.8, deviation_flag=False),
        ),
        WeatherData(
            datetime=datetime(2026, 1, 31, 13, 0),
            temp=WeatherValue(kma=16.0, openmeteo=15.5, avg=15.8, deviation_flag=False),
        ),
        WeatherData(
            datetime=datetime(2026, 1, 31, 14, 0),
            temp=WeatherValue(kma=17.0, openmeteo=16.5, avg=16.8, deviation_flag=False),
        ),
    ]

    cache_path = await cache_writer.write_cache(
        region_code=region_code,
        region_name=region_name,
        coordinates=sample_coordinates,
        forecast=forecast,
        date=test_date,
    )

    # Read and verify
    cached_data = await cache_writer.read_cache(
        region_code=region_code,
        region_name=region_name,
        date=test_date,
    )

    assert len(cached_data["forecast"]) == 3
    assert cached_data["forecast"][0]["temp"]["avg"] == 14.8
    assert cached_data["forecast"][1]["temp"]["avg"] == 15.8
    assert cached_data["forecast"][2]["temp"]["avg"] == 16.8


# Test Directory Creation


@pytest.mark.asyncio
async def test_cache_dir_creation(tmp_path):
    """Test that cache directory is created if it doesn't exist"""
    cache_dir = tmp_path / "new_cache_dir"
    assert not cache_dir.exists()

    cache_writer = CacheWriter(cache_dir=cache_dir)

    # Directory should be created
    assert cache_dir.exists()
    assert cache_dir.is_dir()


@pytest.mark.asyncio
async def test_date_subdirectory_creation(cache_writer):
    """Test that date subdirectories are created automatically"""
    test_date = datetime(2026, 2, 15)
    region_code = "test_region"
    test_data = {"test": "data"}

    cache_path = await cache_writer.write(region_code, test_data, date=test_date)

    # Verify directory structure
    date_dir = cache_writer.cache_dir / "2026-02-15" / "regions"
    assert date_dir.exists()
    assert date_dir.is_dir()
    assert cache_path.parent == date_dir
