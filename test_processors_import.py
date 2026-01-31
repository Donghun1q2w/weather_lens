"""Quick import test for processors module"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    # Test imports
    from processors import (
        WeatherData,
        WeatherValue,
        calculate_weighted_average,
        merge_weather_data,
        CacheWriter,
        write_weather_cache,
        Region,
        RegionLoader,
        initialize_regions_db,
        load_all_regions,
        load_region,
    )

    print("✓ All imports successful")
    print(f"✓ WeatherData: {WeatherData}")
    print(f"✓ Region: {Region}")
    print(f"✓ CacheWriter: {CacheWriter}")

except Exception as e:
    print(f"✗ Import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nModule structure validated successfully!")
