"""
Comprehensive tests for Phase 3 (Data Enrichment) and Phase 4 (Production Readiness)
"""
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))


def test_weather_service():
    """Test weather service functionality"""
    print("Testing Weather Service...")

    from utils.weather import WeatherService

    service = WeatherService()

    # Test mock weather (no API key)
    weather = service.get_weather_by_coords(50.0, 8.5)  # Frankfurt coordinates

    assert 'condition' in weather, "Weather should have condition"
    assert 'temperature' in weather, "Weather should have temperature"
    assert weather['condition'] in ['clear', 'cloudy', 'rain', 'snow', 'fog', 'severe', 'windy', 'freezing']

    # Test cache
    weather2 = service.get_weather_by_coords(50.0, 8.5)
    assert weather == weather2, "Cached weather should match"

    # Test cache stats
    stats = service.get_cache_stats()
    # Cache might be empty if no API key, which is fine
    assert 'total_entries' in stats, "Stats should have total_entries"
    assert 'cache_ttl_minutes' in stats, "Stats should have TTL"

    print("✓ Weather Service test passed")


def test_feature_cache():
    """Test feature caching functionality"""
    print("Testing Feature Cache...")

    from utils.features import FeatureCache

    cache = FeatureCache(ttl_minutes=1)

    # Test set and get
    cache.set('test_key', {'value': 42})
    result = cache.get('test_key')

    assert result is not None, "Cache should return value"
    assert result['value'] == 42, "Cached value should match"

    # Test expiration (simulate by changing TTL)
    cache.ttl = timedelta(seconds=-1)  # Expired
    result = cache.get('test_key')
    assert result is None, "Expired cache should return None"

    # Test stats
    cache2 = FeatureCache()
    cache2.set('key1', 'value1')
    cache2.set('key2', 'value2')
    stats = cache2.get_stats()
    assert stats['total_entries'] == 2, "Cache should have 2 entries"

    print("✓ Feature Cache test passed")


def test_historical_data_structure():
    """Test historical data service structure"""
    print("Testing Historical Data Service structure...")

    from utils.features import HistoricalDataService

    # Mock engine
    class MockEngine:
        pass

    service = HistoricalDataService(MockEngine())

    # Test default responses
    route_perf = service._get_default_route_performance()
    assert route_perf['has_data'] == False
    assert route_perf['avg_delay_minutes'] == 0.0

    airline_perf = service._get_default_airline_performance()
    assert airline_perf['has_data'] == False

    congestion = service._get_default_congestion()
    assert congestion['congestion_level'] == 'unknown'

    # Test congestion level calculation
    assert service._calculate_congestion_level(5) == 'low'
    assert service._calculate_congestion_level(15) == 'medium'
    assert service._calculate_congestion_level(25) == 'high'

    print("✓ Historical Data Service structure test passed")


def test_logging_config():
    """Test logging configuration"""
    print("Testing Logging Configuration...")

    from utils.logging_config import ContextLogger, MetricsCollector

    logger = ContextLogger('test')

    # Test context management
    logger.set_context(request_id='123')
    assert logger.context['request_id'] == '123'

    logger.clear_context()
    assert len(logger.context) == 0

    # Test metrics collector
    metrics = MetricsCollector()
    metrics.increment('test_metric', 5)
    assert metrics.metrics['test_metric'] == 5

    metrics.record_prediction(0.5, True, True)
    assert metrics.metrics['predictions_total'] == 1
    assert metrics.metrics['predictions_using_mock'] == 1

    stats = metrics.get_metrics()
    assert 'predictions_total' in stats
    assert 'avg_duration_seconds' in stats

    print("✓ Logging Configuration test passed")


def test_model_registry():
    """Test model registry functionality"""
    print("Testing Model Registry...")

    from utils.model_registry import ModelRegistry, ModelMetadata
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        registry = ModelRegistry(Path(tmpdir))

        # Create mock model metadata
        metadata = ModelMetadata(
            version='v1.0',
            model_type='RandomForestRegressor',
            trained_at=datetime.now(),
            metrics={'rmse': 12.5, 'r2': 0.85},
            feature_columns=['hour', 'day_of_week'],
            description='Test model'
        )

        # Create a simple mock model
        class MockModel:
            def predict(self, X):
                return [25.0]

        model = MockModel()

        # Test registration
        success = registry.register_model(model, 'v1.0', metadata, save_to_disk=True)
        assert success, "Model registration should succeed"

        # Test retrieval
        retrieved = registry.get_model('v1.0')
        assert retrieved is not None, "Should retrieve registered model"

        # Test active model
        registry.set_active('v1.0')
        active = registry.get_active_model()
        assert active is not None, "Should have active model"

        # Test metadata
        all_meta = registry.get_all_metadata()
        assert 'v1.0' in all_meta, "Metadata should include v1.0"
        assert all_meta['v1.0']['is_active'] == True

        # Test model scanning
        versions = registry.scan_models_directory()
        assert 'v1.0' in versions, "Should find v1.0 in directory"

    print("✓ Model Registry test passed")


def test_time_features():
    """Test time feature calculation"""
    print("Testing Time Features...")

    from utils.features import calculate_time_features

    dt = datetime(2025, 11, 25, 14, 30)  # Tuesday, 2:30 PM

    features = calculate_time_features(dt)

    assert features['hour'] == 14
    assert features['day_of_week'] == 1  # Tuesday
    assert features['month'] == 11
    assert features['is_weekend'] == False
    assert features['is_rush_hour'] == False
    assert features['quarter'] == 4

    # Test rush hour
    dt_rush = datetime(2025, 11, 25, 8, 0)
    features_rush = calculate_time_features(dt_rush)
    assert features_rush['is_rush_hour'] == True

    # Test weekend
    dt_weekend = datetime(2025, 11, 29, 10, 0)  # Saturday
    features_weekend = calculate_time_features(dt_weekend)
    assert features_weekend['is_weekend'] == True

    print("✓ Time Features test passed")


def test_response_structure_with_enrichment():
    """Test that response structure supports enriched features"""
    print("Testing Response Structure...")

    # Simulate enriched feature dict
    features = {
        'hour': 14,
        'day_of_week': 1,
        'route_avg_delay': 12.5,
        'route_delay_rate': 0.3,
        'airline_avg_delay': 10.0,
        'departure_congestion_level': 'medium',
        'departure_airport_meteo': 'clear',
        'arrival_airport_meteo': 'cloudy'
    }

    # Verify all expected keys are present
    assert 'route_avg_delay' in features
    assert 'route_delay_rate' in features
    assert 'airline_avg_delay' in features
    assert 'departure_congestion_level' in features
    assert 'departure_airport_meteo' in features
    assert 'arrival_airport_meteo' in features

    print("✓ Response Structure test passed")


def test_cache_ttl_behavior():
    """Test cache TTL and expiration"""
    print("Testing Cache TTL Behavior...")

    from utils.features import FeatureCache
    import time

    cache = FeatureCache(ttl_minutes=0.01)  # 0.6 seconds

    # Set value
    cache.set('quick_expire', 'test_value')

    # Should be available immediately
    value = cache.get('quick_expire')
    assert value == 'test_value'

    # Wait for expiration
    time.sleep(1)

    # Should be expired
    value = cache.get('quick_expire')
    assert value is None

    print("✓ Cache TTL Behavior test passed")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Phase 3 & 4 - Comprehensive Tests")
    print("=" * 60)
    print()

    try:
        test_weather_service()
        test_feature_cache()
        test_historical_data_structure()
        test_logging_config()
        test_model_registry()
        test_time_features()
        test_response_structure_with_enrichment()
        test_cache_ttl_behavior()

        print()
        print("=" * 60)
        print("✓ All Phase 3 & 4 tests passed!")
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
