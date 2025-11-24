"""
Prediction Result Caching
Caches prediction results to avoid redundant computations
"""
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class CachedPrediction:
    """Cached prediction result"""
    prediction: float
    delay_probability: float
    factors: dict
    message: str
    using_mock_data: bool
    warning: Optional[str]
    cached_at: str
    model_version: Optional[str]


class PredictionCache:
    """
    Cache for prediction results with TTL
    """

    def __init__(self, ttl_minutes: int = 30):
        """
        Initialize prediction cache

        Args:
            ttl_minutes: Time to live for cache entries in minutes
        """
        self.cache = {}
        self.ttl = timedelta(minutes=ttl_minutes)
        self.hits = 0
        self.misses = 0

    def _generate_cache_key(
        self,
        flight_number: str,
        departure_airport: str,
        arrival_airport: str,
        scheduled_departure: str,
        airline: Optional[str] = None
    ) -> str:
        """
        Generate a unique cache key for a prediction request

        Args:
            flight_number: Flight number
            departure_airport: Departure airport IATA code
            arrival_airport: Arrival airport IATA code
            scheduled_departure: ISO format datetime string
            airline: Optional airline code

        Returns:
            Cache key hash
        """
        # Round scheduled departure to the nearest hour to increase cache hits
        # for requests with slightly different times
        try:
            dt = datetime.fromisoformat(scheduled_departure)
            # Round to nearest hour
            rounded_dt = dt.replace(minute=0, second=0, microsecond=0)
            rounded_str = rounded_dt.isoformat()
        except:
            rounded_str = scheduled_departure

        # Create a deterministic key
        key_parts = [
            flight_number,
            departure_airport,
            arrival_airport,
            rounded_str,
            airline or "none"
        ]
        key_string = "|".join(key_parts)

        # Generate hash
        return hashlib.sha256(key_string.encode()).hexdigest()[:16]

    def get(
        self,
        flight_number: str,
        departure_airport: str,
        arrival_airport: str,
        scheduled_departure: str,
        airline: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Get cached prediction if available and valid

        Returns:
            Cached prediction dict or None
        """
        cache_key = self._generate_cache_key(
            flight_number,
            departure_airport,
            arrival_airport,
            scheduled_departure,
            airline
        )

        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]

            # Check if cache is still valid
            if datetime.now() - timestamp < self.ttl:
                self.hits += 1
                # Add cache metadata
                result = cached_data.copy()
                result['from_cache'] = True
                result['cached_at'] = timestamp.isoformat()
                return result
            else:
                # Expired, remove it
                del self.cache[cache_key]

        self.misses += 1
        return None

    def set(
        self,
        flight_number: str,
        departure_airport: str,
        arrival_airport: str,
        scheduled_departure: str,
        prediction_result: Dict,
        model_version: Optional[str] = None,
        airline: Optional[str] = None
    ):
        """
        Cache a prediction result

        Args:
            flight_number: Flight number
            departure_airport: Departure airport IATA code
            arrival_airport: Arrival airport IATA code
            scheduled_departure: ISO format datetime string
            prediction_result: Prediction response dict
            model_version: Model version used for prediction
            airline: Optional airline code
        """
        cache_key = self._generate_cache_key(
            flight_number,
            departure_airport,
            arrival_airport,
            scheduled_departure,
            airline
        )

        # Store prediction with timestamp and model version
        cached_data = prediction_result.copy()
        cached_data['model_version'] = model_version
        cached_data['from_cache'] = False

        self.cache[cache_key] = (cached_data, datetime.now())

    def invalidate_by_model_version(self, model_version: str) -> int:
        """
        Invalidate all cache entries for a specific model version

        Args:
            model_version: Model version to invalidate

        Returns:
            Number of entries invalidated
        """
        keys_to_remove = []

        for key, (cached_data, _) in self.cache.items():
            if cached_data.get('model_version') == model_version:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self.cache[key]

        return len(keys_to_remove)

    def invalidate_all(self):
        """Clear all cached predictions"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def invalidate_expired(self) -> int:
        """
        Remove expired cache entries

        Returns:
            Number of entries removed
        """
        keys_to_remove = []
        now = datetime.now()

        for key, (_, timestamp) in self.cache.items():
            if now - timestamp >= self.ttl:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self.cache[key]

        return len(keys_to_remove)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dict with cache stats
        """
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests) if total_requests > 0 else 0

        # Count valid entries
        now = datetime.now()
        valid_entries = sum(
            1 for _, timestamp in self.cache.values()
            if now - timestamp < self.ttl
        )

        return {
            'total_entries': len(self.cache),
            'valid_entries': valid_entries,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'ttl_minutes': self.ttl.total_seconds() / 60
        }

    def get_cache_size_mb(self) -> float:
        """
        Estimate cache size in MB

        Returns:
            Approximate cache size in megabytes
        """
        import sys

        total_size = 0
        for key, (data, _) in self.cache.items():
            total_size += sys.getsizeof(key)
            total_size += sys.getsizeof(json.dumps(data))

        return total_size / (1024 * 1024)


# Global prediction cache instance
_prediction_cache = None


def get_prediction_cache(ttl_minutes: int = 30) -> PredictionCache:
    """
    Get or create global prediction cache instance

    Args:
        ttl_minutes: Cache TTL in minutes (only used on first call)

    Returns:
        PredictionCache instance
    """
    global _prediction_cache
    if _prediction_cache is None:
        _prediction_cache = PredictionCache(ttl_minutes=ttl_minutes)
    return _prediction_cache
