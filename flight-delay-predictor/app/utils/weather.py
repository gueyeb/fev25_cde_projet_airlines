"""
Weather API Integration for Flight Delay Prediction
Provides real-time weather data with caching
"""
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
import requests
from functools import lru_cache


class WeatherService:
    """
    Weather service that integrates with OpenWeatherMap API
    Falls back to mock data if API is unavailable
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('OPENWEATHER_API_KEY')
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"
        self.cache = {}
        self.cache_ttl = timedelta(minutes=15)  # Cache weather for 15 minutes

    def _get_cache_key(self, lat: float, lon: float) -> str:
        """Generate cache key for coordinates"""
        return f"{lat:.2f},{lon:.2f}"

    def _is_cache_valid(self, timestamp: datetime) -> bool:
        """Check if cached data is still valid"""
        return datetime.now() - timestamp < self.cache_ttl

    def get_weather_by_coords(self, lat: float, lon: float) -> Dict:
        """
        Get current weather for coordinates with caching

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Dict with weather information
        """
        # Check cache first
        cache_key = self._get_cache_key(lat, lon)
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if self._is_cache_valid(timestamp):
                return cached_data

        # Fetch from API if we have an API key
        if self.api_key:
            try:
                params = {
                    'lat': lat,
                    'lon': lon,
                    'appid': self.api_key,
                    'units': 'metric'
                }
                response = requests.get(self.base_url, params=params, timeout=5)

                if response.status_code == 200:
                    data = response.json()
                    weather_info = self._parse_weather_response(data)
                    # Cache the result
                    self.cache[cache_key] = (weather_info, datetime.now())
                    return weather_info
            except Exception as e:
                print(f"Weather API error: {e}")

        # Fall back to mock data
        return self._get_mock_weather(lat, lon)

    def get_weather_by_airport(self, airport_code: str, airport_coords: Optional[Tuple[float, float]] = None) -> Dict:
        """
        Get weather for an airport

        Args:
            airport_code: IATA airport code
            airport_coords: Optional tuple of (latitude, longitude)

        Returns:
            Dict with weather information
        """
        if airport_coords:
            return self.get_weather_by_coords(airport_coords[0], airport_coords[1])
        else:
            # Return unknown weather if no coordinates provided
            return self._get_unknown_weather()

    def _parse_weather_response(self, data: Dict) -> Dict:
        """Parse OpenWeatherMap API response"""
        weather = data.get('weather', [{}])[0]
        main = data.get('main', {})
        wind = data.get('wind', {})
        visibility = data.get('visibility', 10000)  # meters

        # Categorize weather condition
        condition = self._categorize_weather(
            weather.get('main', 'Clear'),
            main.get('temp', 20),
            wind.get('speed', 0),
            visibility
        )

        return {
            'condition': condition,
            'temperature': main.get('temp', 20),
            'humidity': main.get('humidity', 50),
            'wind_speed': wind.get('speed', 0),
            'visibility': visibility / 1000,  # Convert to km
            'description': weather.get('description', 'clear sky'),
            'raw_condition': weather.get('main', 'Clear')
        }

    def _categorize_weather(self, condition: str, temp: float, wind_speed: float, visibility: int) -> str:
        """
        Categorize weather into simple categories for ML model
        Matches the categories used in training data
        """
        # Check for severe conditions first
        if condition in ['Thunderstorm', 'Tornado', 'Squall']:
            return 'severe'

        if condition in ['Snow', 'Sleet']:
            return 'snow'

        if condition == 'Rain' or condition == 'Drizzle':
            return 'rain'

        if condition == 'Fog' or condition == 'Mist' or visibility < 1000:
            return 'fog'

        if condition == 'Clouds':
            return 'cloudy'

        if wind_speed > 15:  # > 15 m/s is strong wind
            return 'windy'

        if temp < 0:
            return 'freezing'

        return 'clear'

    def _get_mock_weather(self, lat: float, lon: float) -> Dict:
        """
        Generate mock weather data based on location
        Used as fallback when API is unavailable
        """
        # Simple heuristic: colder weather in higher latitudes
        base_temp = 20 - abs(lat) / 3

        return {
            'condition': 'clear',
            'temperature': base_temp,
            'humidity': 50,
            'wind_speed': 5.0,
            'visibility': 10.0,
            'description': 'mock data - api unavailable',
            'raw_condition': 'Clear'
        }

    def _get_unknown_weather(self) -> Dict:
        """Return unknown weather placeholder"""
        return {
            'condition': 'unknown',
            'temperature': None,
            'humidity': None,
            'wind_speed': None,
            'visibility': None,
            'description': 'unknown',
            'raw_condition': 'Unknown'
        }

    def clear_cache(self):
        """Clear the weather cache"""
        self.cache.clear()

    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        valid_entries = sum(
            1 for _, (_, timestamp) in self.cache.items()
            if self._is_cache_valid(timestamp)
        )
        return {
            'total_entries': len(self.cache),
            'valid_entries': valid_entries,
            'cache_ttl_minutes': self.cache_ttl.total_seconds() / 60
        }


# Global weather service instance
_weather_service = None

def get_weather_service() -> WeatherService:
    """Get or create global weather service instance"""
    global _weather_service
    if _weather_service is None:
        _weather_service = WeatherService()
    return _weather_service


@lru_cache(maxsize=128)
def get_airport_coordinates(engine, airport_code: str) -> Optional[Tuple[float, float]]:
    """
    Get airport coordinates from database with caching

    Args:
        engine: SQLAlchemy engine
        airport_code: IATA airport code

    Returns:
        Tuple of (latitude, longitude) or None
    """
    try:
        import pandas as pd
        query = f"""
            SELECT latitude, longitude
            FROM airports
            WHERE iata_code = '{airport_code}'
            LIMIT 1
        """
        df = pd.read_sql(query, engine)
        if not df.empty:
            return (float(df.iloc[0]['latitude']), float(df.iloc[0]['longitude']))
    except Exception as e:
        print(f"Error fetching airport coordinates for {airport_code}: {e}")
    return None
