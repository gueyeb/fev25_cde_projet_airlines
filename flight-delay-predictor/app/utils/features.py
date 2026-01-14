"""
Feature Engineering Utilities for Flight Delay Prediction
Includes historical data, caching, and enrichment
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from functools import lru_cache
import hashlib


class FeatureCache:
    """
    In-memory cache for expensive feature computations
    """

    def __init__(self, ttl_minutes: int = 60):
        self.cache = {}
        self.ttl = timedelta(minutes=ttl_minutes)

    def get(self, key: str) -> Optional[any]:
        """Get cached value if valid"""
        if key in self.cache:
            value, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                return value
            else:
                # Expired, remove it
                del self.cache[key]
        return None

    def set(self, key: str, value: any):
        """Cache a value with current timestamp"""
        self.cache[key] = (value, datetime.now())

    def clear(self):
        """Clear all cached values"""
        self.cache.clear()

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        valid_entries = 0
        for key, (_, timestamp) in self.cache.items():
            if datetime.now() - timestamp < self.ttl:
                valid_entries += 1

        return {
            'total_entries': len(self.cache),
            'valid_entries': valid_entries,
            'ttl_minutes': self.ttl.total_seconds() / 60
        }


# Global feature cache instance
_feature_cache = FeatureCache(ttl_minutes=60)


def get_feature_cache() -> FeatureCache:
    """Get global feature cache instance"""
    return _feature_cache


class HistoricalDataService:
    """
    Service for retrieving historical flight performance data
    """

    def __init__(self, engine):
        self.engine = engine

    def get_route_performance(self, departure_airport: str, arrival_airport: str) -> Dict:
        """
        Get historical performance for a specific route

        Args:
            departure_airport: IATA code of departure airport
            arrival_airport: IATA code of arrival airport

        Returns:
            Dict with route performance metrics
        """
        # Check cache first
        cache_key = f"route_perf:{departure_airport}:{arrival_airport}"
        cached = get_feature_cache().get(cache_key)
        if cached is not None:
            return cached

        try:
            # Join with routes table to get airport codes
            # Calculate duration from schedule times (varchar total_journey_duration not reliable)
            query = f"""
                SELECT
                    COUNT(*) as total_flights,
                    AVG(EXTRACT(EPOCH FROM f.delay_on_arrival) / 60.0) as avg_delay_minutes,
                    STDDEV(EXTRACT(EPOCH FROM f.delay_on_arrival) / 60.0) as stddev_delay_minutes,
                    SUM(CASE WHEN f.delay_on_arrival > interval '15 minutes' THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) as delay_rate,
                    AVG(EXTRACT(EPOCH FROM (
                        (f.arrival_schedule_date + f.arrival_schedule_time) -
                        (f.departure_schedule_date + f.departure_schedule_time)
                    )) / 60.0) as avg_duration_minutes
                FROM lufthansa_flight_history f
                JOIN routes r ON f.route_id = r.id
                WHERE (
                    (r.departure_airport = '{departure_airport}' AND r.arrival_airport = '{arrival_airport}' AND f.route_sens = 'A')
                    OR (r.departure_airport = '{arrival_airport}' AND r.arrival_airport = '{departure_airport}' AND f.route_sens = 'R')
                )
                  AND f.delay_on_arrival IS NOT NULL
                  AND f.departure_schedule_date >= CURRENT_DATE - INTERVAL '90 days'
            """
            df = pd.read_sql(query, self.engine)

            if not df.empty and df.iloc[0]['total_flights'] > 0:
                result = {
                    'total_flights': int(df.iloc[0]['total_flights']),
                    'avg_delay_minutes': float(df.iloc[0]['avg_delay_minutes'] or 0),
                    'stddev_delay_minutes': float(df.iloc[0]['stddev_delay_minutes'] or 0),
                    'delay_rate': float(df.iloc[0]['delay_rate'] or 0),
                    'avg_duration_minutes': float(df.iloc[0]['avg_duration_minutes'] or 0),
                    'has_data': True
                }
            else:
                result = self._get_default_route_performance()

            # Cache the result
            get_feature_cache().set(cache_key, result)
            return result

        except Exception as e:
            print(f"Error fetching route performance: {e}")
            return self._get_default_route_performance()

    def get_airline_performance(self, airline_code: str) -> Dict:
        """
        Get historical performance for a specific airline

        Args:
            airline_code: Airline IATA code

        Returns:
            Dict with airline performance metrics
        """
        cache_key = f"airline_perf:{airline_code}"
        cached = get_feature_cache().get(cache_key)
        if cached is not None:
            return cached

        try:
            query = f"""
                SELECT
                    COUNT(*) as total_flights,
                    AVG(EXTRACT(EPOCH FROM delay_on_arrival) / 60.0) as avg_delay_minutes,
                    SUM(CASE WHEN delay_on_arrival > interval '15 minutes' THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) as delay_rate
                FROM lufthansa_flight_history
                WHERE marketing_carrier_airline_id LIKE '{airline_code}%'
                  AND delay_on_arrival IS NOT NULL
                  AND departure_schedule_date >= CURRENT_DATE - INTERVAL '30 days'
            """
            df = pd.read_sql(query, self.engine)

            if not df.empty and df.iloc[0]['total_flights'] > 0:
                result = {
                    'total_flights': int(df.iloc[0]['total_flights']),
                    'avg_delay_minutes': float(df.iloc[0]['avg_delay_minutes'] or 0),
                    'delay_rate': float(df.iloc[0]['delay_rate'] or 0),
                    'has_data': True
                }
            else:
                result = self._get_default_airline_performance()

            get_feature_cache().set(cache_key, result)
            return result

        except Exception as e:
            print(f"Error fetching airline performance: {e}")
            return self._get_default_airline_performance()

    def get_airport_congestion(self, airport_code: str, hour: int, day_of_week: int) -> Dict:
        """
        Get airport congestion patterns for specific time

        Args:
            airport_code: IATA airport code
            hour: Hour of day (0-23)
            day_of_week: Day of week (0-6)

        Returns:
            Dict with congestion metrics
        """
        cache_key = f"airport_cong:{airport_code}:{hour}:{day_of_week}"
        cached = get_feature_cache().get(cache_key)
        if cached is not None:
            return cached

        try:
            # Join with routes to get airport codes
            query = f"""
                SELECT
                    COUNT(*) as flight_count,
                    AVG(EXTRACT(EPOCH FROM f.delay_on_departure) / 60.0) as avg_departure_delay
                FROM lufthansa_flight_history f
                JOIN routes r ON f.route_id = r.id
                WHERE (
                    (r.departure_airport = '{airport_code}' AND f.route_sens = 'A')
                    OR (r.arrival_airport = '{airport_code}' AND f.route_sens = 'R')
                )
                  AND EXTRACT(HOUR FROM f.departure_schedule_time) = {hour}
                  AND EXTRACT(DOW FROM f.departure_schedule_date) = {day_of_week}
                  AND f.departure_schedule_date >= CURRENT_DATE - INTERVAL '90 days'
            """
            df = pd.read_sql(query, self.engine)

            if not df.empty:
                result = {
                    'flight_count': int(df.iloc[0]['flight_count'] or 0),
                    'avg_departure_delay': float(df.iloc[0]['avg_departure_delay'] or 0),
                    'congestion_level': self._calculate_congestion_level(int(df.iloc[0]['flight_count'] or 0)),
                    'has_data': True
                }
            else:
                result = self._get_default_congestion()

            get_feature_cache().set(cache_key, result)
            return result

        except Exception as e:
            print(f"Error fetching airport congestion: {e}")
            return self._get_default_congestion()

    def _calculate_congestion_level(self, flight_count: int) -> str:
        """Calculate congestion level based on flight count"""
        if flight_count >= 20:
            return 'high'
        elif flight_count >= 10:
            return 'medium'
        else:
            return 'low'

    def _get_default_route_performance(self) -> Dict:
        """Default route performance when no data available"""
        return {
            'total_flights': 0,
            'avg_delay_minutes': 0.0,
            'stddev_delay_minutes': 0.0,
            'delay_rate': 0.0,
            'avg_duration_minutes': 0.0,
            'has_data': False
        }

    def _get_default_airline_performance(self) -> Dict:
        """Default airline performance when no data available"""
        return {
            'total_flights': 0,
            'avg_delay_minutes': 0.0,
            'delay_rate': 0.0,
            'has_data': False
        }

    def _get_default_congestion(self) -> Dict:
        """Default congestion data when no data available"""
        return {
            'flight_count': 0,
            'avg_departure_delay': 0.0,
            'congestion_level': 'unknown',
            'has_data': False
        }


@lru_cache(maxsize=256)
def get_airport_metadata(engine, airport_code: str) -> Optional[Dict]:
    """
    Get airport metadata with caching

    Args:
        engine: SQLAlchemy engine
        airport_code: IATA airport code

    Returns:
        Dict with airport metadata or None
    """
    try:
        # Convert engine to string for hashability in lru_cache
        query = f"""
            SELECT
                airport_code,
                iata_code,
                name,
                city_code,
                country_code,
                latitude,
                longitude,
                time_zone_id
            FROM airports
            WHERE iata_code = '{airport_code}'
            LIMIT 1
        """
        df = pd.read_sql(query, engine)

        if not df.empty:
            return {
                'airport_code': df.iloc[0]['airport_code'],
                'iata_code': df.iloc[0]['iata_code'],
                'name': df.iloc[0]['name'],
                'city_code': df.iloc[0]['city_code'],
                'country_code': df.iloc[0]['country_code'],
                'latitude': float(df.iloc[0]['latitude']) if df.iloc[0]['latitude'] else None,
                'longitude': float(df.iloc[0]['longitude']) if df.iloc[0]['longitude'] else None,
                'time_zone_id': df.iloc[0]['time_zone_id']
            }
    except Exception as e:
        print(f"Error fetching airport metadata for {airport_code}: {e}")

    return None


def calculate_time_features(scheduled_dt: datetime) -> Dict:
    """
    Calculate time-based features

    Args:
        scheduled_dt: Scheduled departure datetime

    Returns:
        Dict with time features
    """
    return {
        'hour': scheduled_dt.hour,
        'day_of_week': scheduled_dt.weekday(),
        'month': scheduled_dt.month,
        'day_of_month': scheduled_dt.day,
        'is_weekend': scheduled_dt.weekday() >= 5,
        'is_rush_hour': scheduled_dt.hour in [7, 8, 9, 17, 18, 19],
        'is_early_morning': 5 <= scheduled_dt.hour < 7,
        'is_late_night': scheduled_dt.hour >= 22 or scheduled_dt.hour < 5,
        'quarter': (scheduled_dt.month - 1) // 3 + 1
    }


def enrich_features_with_history(
    base_features: Dict,
    historical_service: HistoricalDataService,
    departure_airport: str,
    arrival_airport: str,
    airline: Optional[str] = None
) -> Dict:
    """
    Enrich base features with historical data

    Args:
        base_features: Base feature dict
        historical_service: HistoricalDataService instance
        departure_airport: Departure airport code
        arrival_airport: Arrival airport code
        airline: Optional airline code

    Returns:
        Enriched feature dict
    """
    # Get route performance
    route_perf = historical_service.get_route_performance(departure_airport, arrival_airport)
    base_features['route_avg_delay'] = route_perf['avg_delay_minutes']
    base_features['route_delay_rate'] = route_perf['delay_rate']
    base_features['route_avg_duration'] = route_perf['avg_duration_minutes']
    base_features['route_has_history'] = route_perf['has_data']

    # Get airline performance
    if airline:
        airline_perf = historical_service.get_airline_performance(airline)
        base_features['airline_avg_delay'] = airline_perf['avg_delay_minutes']
        base_features['airline_delay_rate'] = airline_perf['delay_rate']
        base_features['airline_has_history'] = airline_perf['has_data']
    else:
        base_features['airline_avg_delay'] = 0.0
        base_features['airline_delay_rate'] = 0.0
        base_features['airline_has_history'] = False

    # Get departure airport congestion
    if 'hour' in base_features and 'day_of_week' in base_features:
        congestion = historical_service.get_airport_congestion(
            departure_airport,
            base_features['hour'],
            base_features['day_of_week']
        )
        base_features['departure_congestion_level'] = congestion['congestion_level']
        base_features['departure_flight_count'] = congestion['flight_count']
        base_features['departure_avg_delay'] = congestion['avg_departure_delay']

    return base_features
