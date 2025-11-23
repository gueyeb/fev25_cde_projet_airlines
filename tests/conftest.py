"""
Configuration pytest pour les tests
"""
import pytest
import sys
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def project_root():
    """Retourne le chemin racine du projet"""
    return PROJECT_ROOT


@pytest.fixture
def sample_flight_data():
    """Données de vol exemple pour les tests"""
    return {
        "marketing_carrier_airline_id": "LH",
        "marketing_carrier_flight_number": "400",
        "departure_airport": "FRA",
        "arrival_airport": "JFK",
        "departure_schedule_date": "2025-01-20",
        "departure_schedule_time": "10:00:00"
    }


@pytest.fixture
def sample_weather_data():
    """Données météo exemple pour les tests"""
    return {
        "temp": 15.5,
        "feels_like": 14.2,
        "pressure": 1013,
        "humidity": 65,
        "wind_speed": 5.2,
        "clouds": 20,
        "weather_main": "Clear",
        "weather_description": "clear sky"
    }
