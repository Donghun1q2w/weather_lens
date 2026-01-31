"""Test script to verify recommenders, curators, and messengers modules"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test basic imports"""
    print("Testing module imports...")

    try:
        from recommenders import RegionRecommender
        print("✓ RegionRecommender imported successfully")
    except Exception as e:
        print(f"✗ RegionRecommender import failed: {e}")
        return False

    try:
        from curators import GeminiCurator
        print("✓ GeminiCurator imported successfully")
    except Exception as e:
        print(f"✗ GeminiCurator import failed: {e}")
        return False

    try:
        from messengers import TelegramMessenger
        print("✓ TelegramMessenger imported successfully")
    except Exception as e:
        print(f"✗ TelegramMessenger import failed: {e}")
        return False

    return True

def test_instantiation():
    """Test basic instantiation"""
    print("\nTesting instantiation...")

    try:
        from recommenders import RegionRecommender
        recommender = RegionRecommender()
        print("✓ RegionRecommender instantiated")
    except Exception as e:
        print(f"✗ RegionRecommender instantiation failed: {e}")
        return False

    try:
        from curators import GeminiCurator
        curator = GeminiCurator(api_key="test_key")
        print("✓ GeminiCurator instantiated")
    except Exception as e:
        print(f"✗ GeminiCurator instantiation failed: {e}")
        return False

    try:
        from messengers import TelegramMessenger
        messenger = TelegramMessenger(bot_token="test_token", chat_id="test_id")
        print("✓ TelegramMessenger instantiated")
    except Exception as e:
        print(f"✗ TelegramMessenger instantiation failed: {e}")
        return False

    return True

if __name__ == "__main__":
    print("=" * 50)
    print("Module Verification Test")
    print("=" * 50)

    success = True
    success = test_imports() and success
    success = test_instantiation() and success

    print("\n" + "=" * 50)
    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")
    print("=" * 50)
