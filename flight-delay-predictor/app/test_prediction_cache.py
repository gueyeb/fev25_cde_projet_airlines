"""
Tests for Prediction Result Caching
"""
import sys
from pathlib import Path
from datetime import datetime
import time

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))


def test_prediction_cache_basic():
    """Test basic cache operations"""
    print("Testing Prediction Cache - Basic Operations...")

    from utils.prediction_cache import PredictionCache

    cache = PredictionCache(ttl_minutes=30)

    # Test cache miss
    result = cache.get("AA123", "JFK", "LAX", "2025-12-01T10:00:00", "AA")
    assert result is None, "Cache should be empty initially"
    assert cache.misses == 1, "Should record cache miss"

    # Test cache set
    prediction_data = {
        "prediction": 25.5,
        "delay_probability": 0.7,
        "factors": {"Time of Day": 0.35},
        "message": "Moderate delay risk",
        "using_mock_data": False,
        "warning": None
    }

    cache.set("AA123", "JFK", "LAX", "2025-12-01T10:00:00", prediction_data, "v1.0", "AA")

    # Test cache hit
    result = cache.get("AA123", "JFK", "LAX", "2025-12-01T10:00:00", "AA")
    assert result is not None, "Cache should return result"
    assert result["prediction"] == 25.5, "Cached prediction should match"
    assert result["from_cache"] == True, "Should indicate from cache"
    assert cache.hits == 1, "Should record cache hit"

    print("✓ Prediction Cache - Basic Operations test passed")


def test_cache_key_generation():
    """Test cache key generation and rounding"""
    print("Testing Cache Key Generation...")

    from utils.prediction_cache import PredictionCache

    cache = PredictionCache()

    # Test that times within same hour generate same key
    key1 = cache._generate_cache_key("AA123", "JFK", "LAX", "2025-12-01T10:15:00", "AA")
    key2 = cache._generate_cache_key("AA123", "JFK", "LAX", "2025-12-01T10:45:00", "AA")

    assert key1 == key2, "Same hour should generate same cache key"

    # Test that different hours generate different keys
    key3 = cache._generate_cache_key("AA123", "JFK", "LAX", "2025-12-01T11:15:00", "AA")
    assert key1 != key3, "Different hours should generate different keys"

    # Test that different routes generate different keys
    key4 = cache._generate_cache_key("AA123", "LAX", "JFK", "2025-12-01T10:15:00", "AA")
    assert key1 != key4, "Different routes should generate different keys"

    print("✓ Cache Key Generation test passed")


def test_cache_expiration():
    """Test cache TTL and expiration"""
    print("Testing Cache Expiration...")

    from utils.prediction_cache import PredictionCache

    cache = PredictionCache(ttl_minutes=0.01)  # 0.6 seconds

    prediction_data = {
        "prediction": 25.5,
        "delay_probability": 0.7,
        "factors": {},
        "message": "Test",
        "using_mock_data": False,
        "warning": None
    }

    cache.set("AA123", "JFK", "LAX", "2025-12-01T10:00:00", prediction_data)

    # Should be available immediately
    result = cache.get("AA123", "JFK", "LAX", "2025-12-01T10:00:00")
    assert result is not None, "Cache should have result immediately"

    # Wait for expiration
    time.sleep(1)

    # Should be expired
    result = cache.get("AA123", "JFK", "LAX", "2025-12-01T10:00:00")
    assert result is None, "Cache should be expired"

    print("✓ Cache Expiration test passed")


def test_cache_stats():
    """Test cache statistics"""
    print("Testing Cache Statistics...")

    from utils.prediction_cache import PredictionCache

    cache = PredictionCache()

    prediction_data = {
        "prediction": 25.5,
        "delay_probability": 0.7,
        "factors": {},
        "message": "Test",
        "using_mock_data": False,
        "warning": None
    }

    # Add some entries
    cache.set("AA123", "JFK", "LAX", "2025-12-01T10:00:00", prediction_data)
    cache.set("AA124", "LAX", "JFK", "2025-12-01T11:00:00", prediction_data)

    # Generate some hits and misses
    cache.get("AA123", "JFK", "LAX", "2025-12-01T10:00:00")  # Hit
    cache.get("AA999", "SFO", "ORD", "2025-12-01T12:00:00")  # Miss

    stats = cache.get_stats()

    assert stats['total_entries'] == 2, "Should have 2 entries"
    assert stats['hits'] == 1, "Should have 1 hit"
    assert stats['misses'] == 1, "Should have 1 miss"
    assert stats['hit_rate'] == 0.5, "Hit rate should be 50%"

    print("✓ Cache Statistics test passed")


def test_cache_invalidation():
    """Test cache invalidation strategies"""
    print("Testing Cache Invalidation...")

    from utils.prediction_cache import PredictionCache

    cache = PredictionCache(ttl_minutes=0.02)  # 1.2 seconds

    prediction_data = {
        "prediction": 25.5,
        "delay_probability": 0.7,
        "factors": {},
        "message": "Test",
        "using_mock_data": False,
        "warning": None
    }

    # Add entries with different model versions
    cache.set("AA123", "JFK", "LAX", "2025-12-01T10:00:00", prediction_data, "v1.0")
    cache.set("AA124", "LAX", "JFK", "2025-12-01T11:00:00", prediction_data, "v2.0")
    cache.set("AA125", "SFO", "ORD", "2025-12-01T12:00:00", prediction_data, "v1.0")

    # Test invalidate by model version
    invalidated = cache.invalidate_by_model_version("v1.0")
    assert invalidated == 2, "Should invalidate 2 entries with v1.0"

    # Test that v2.0 entries remain
    result = cache.get("AA124", "LAX", "JFK", "2025-12-01T11:00:00")
    assert result is not None, "v2.0 entry should remain"

    # Add expired entry
    cache.set("AA126", "BOS", "MIA", "2025-12-01T13:00:00", prediction_data, "v2.0")
    time.sleep(1.5)  # Wait for expiration

    # Test expired cleanup
    expired = cache.invalidate_expired()
    assert expired >= 1, "Should remove at least 1 expired entry"

    # Test invalidate all
    cache.invalidate_all()
    stats = cache.get_stats()
    assert stats['total_entries'] == 0, "Cache should be empty"

    print("✓ Cache Invalidation test passed")


def test_cache_size_estimation():
    """Test cache size estimation"""
    print("Testing Cache Size Estimation...")

    from utils.prediction_cache import PredictionCache

    cache = PredictionCache()

    prediction_data = {
        "prediction": 25.5,
        "delay_probability": 0.7,
        "factors": {"Time of Day": 0.35, "Weather": 0.25},
        "message": "Moderate delay risk",
        "using_mock_data": False,
        "warning": None
    }

    # Add multiple entries
    for i in range(10):
        cache.set(f"AA{i}", "JFK", "LAX", f"2025-12-01T{i:02d}:00:00", prediction_data)

    size_mb = cache.get_cache_size_mb()
    assert size_mb > 0, "Cache size should be greater than 0"
    assert size_mb < 1, "Cache size should be less than 1 MB for 10 entries"

    print(f"✓ Cache Size Estimation test passed (size: {size_mb:.4f} MB)")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Prediction Cache Tests")
    print("=" * 60)
    print()

    try:
        test_prediction_cache_basic()
        test_cache_key_generation()
        test_cache_expiration()
        test_cache_stats()
        test_cache_invalidation()
        test_cache_size_estimation()

        print()
        print("=" * 60)
        print("✓ All Prediction Cache tests passed!")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"✗ Test failed: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1

    except Exception as e:
        print()
        print("=" * 60)
        print(f"✗ Unexpected error: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
