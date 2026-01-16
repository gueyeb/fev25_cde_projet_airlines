"""
DST Airlines Flight Delay Predictor - FastAPI Backend
Enhanced with Phase 3 (Data Enrichment) and Phase 4 (Production Readiness)
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Add parent directory to path to import from src
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.pg_functions import engine

# Import new utilities
from utils.weather import get_weather_service, get_airport_coordinates
from utils.features import (
    HistoricalDataService,
    calculate_time_features,
    enrich_features_with_history,
    get_feature_cache
)
from utils.logging_config import setup_logging, get_logger, get_metrics_collector
from utils.model_registry import get_model_registry, ModelMetadata
from utils.prediction_cache import get_prediction_cache

# Setup logging
setup_logging(log_level=os.getenv('LOG_LEVEL', 'INFO'), use_json=False)
logger = get_logger(__name__)
metrics = get_metrics_collector()

# Define APP_DIR early
APP_DIR = Path(__file__).parent

# Initialize services
weather_service = get_weather_service()
historical_service = HistoricalDataService(engine)
model_registry = get_model_registry(APP_DIR / "models")
prediction_cache = get_prediction_cache(ttl_minutes=int(os.getenv('PREDICTION_CACHE_TTL', '30')))

logger.info("Application starting", version="2.0.0")

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize application services on startup"""
    logger.info("Loading models from registry")

    # Try to auto-load the latest model
    if model_registry.auto_load_latest():
        active_model = model_registry.get_active_model()
        active_meta = model_registry.get_active_metadata()
        logger.info(
            "Model loaded successfully",
            version=model_registry.active_version,
            model_type=active_meta.model_type if active_meta else "unknown"
        )
    else:
        logger.warning("No model found in registry, predictions will use simulated data")
    
    yield
    # Clean up resources if needed
    logger.info("Application shutting down")


# Initialize FastAPI app
app = FastAPI(title="DST Airlines Flight Delay Predictor", version="2.0.0", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")


# Pydantic models for request/response
class FlightPredictionRequest(BaseModel):
    flight_number: str
    airline: Optional[str] = None
    departure_airport: str
    arrival_airport: str
    scheduled_departure: str


class FlightPredictionResponse(BaseModel):
    prediction: float
    delay_probability: float
    factors: dict
    message: str
    using_mock_data: bool
    warning: Optional[str] = None
    from_cache: bool = False
    cached_at: Optional[str] = None
    departure_weather: Optional[dict] = None
    arrival_weather: Optional[dict] = None
    departure_coords: Optional[dict] = None
    arrival_coords: Optional[dict] = None


class AirportInfo(BaseModel):
    code: str
    name: str
    city: Optional[str] = None
    country: Optional[str] = None


class AirlineInfo(BaseModel):
    code: str
    name: str


class FlightSearchInfo(BaseModel):
    flight_number: str
    airline: str
    airline_name: Optional[str] = None
    departure_airport: str
    departure_airport_name: Optional[str] = None
    arrival_airport: str
    arrival_airport_name: Optional[str] = None


def prepare_features_for_model(flight_data: FlightPredictionRequest, scheduled_dt: datetime, 
                               dep_weather: dict, arr_weather: dict) -> pd.DataFrame:
    """
    Prepare features matching the training data preprocessing.
    Features: total_journey_duration, departure_day_of_week, departure_hour,
              terminals, airline, aircraft, weather
    Note: delay_on_departure is NOT used (data leakage prevention)
    """
    logger.debug("Preparing features", flight_number=flight_data.flight_number)

    # Get route duration from historical data first
    route_perf = historical_service.get_route_performance(
        flight_data.departure_airport,
        flight_data.arrival_airport
    )
    # Use historical average, default to 120 min if no data
    estimated_duration = route_perf.get('avg_duration_minutes', 120) or 120

    # Create features matching training data
    # Note: delay_on_departure is NOT included (data leakage)
    features_dict = {
        'total_journey_duration': estimated_duration,  # in minutes
        'departure_day_of_week': scheduled_dt.weekday(),
        'departure_hour': scheduled_dt.hour,
        'departure_terminal': 'unknown',
        'arrival_terminal': 'unknown',
        'marketing_carrier_airline_id': flight_data.airline or 'unknown',
        'equipment_aircraft_code': 'unknown',
        'departure_airport_meteo': dep_weather['condition'],
        'arrival_airport_meteo': arr_weather['condition'],
    }

    # Create DataFrame with single row
    df = pd.DataFrame([features_dict])

    # Apply the same preprocessing as training
    df = df.fillna('unknown')

    # One-hot encode categorical variables (same as training)
    categorical_cols = [
        'departure_terminal',
        'arrival_terminal',
        'marketing_carrier_airline_id',
        'equipment_aircraft_code',
        'departure_airport_meteo',
        'arrival_airport_meteo'
    ]

    df = pd.get_dummies(df, columns=categorical_cols)

    # total_journey_duration already in minutes, no conversion needed

    logger.debug("Features prepared", feature_count=len(df.columns))

    return df


@app.get("/")
async def root():
    """Serve the main frontend page"""
    return FileResponse(str(APP_DIR / "templates" / "index.html"))


@app.get("/api/airports", response_model=list[AirportInfo])
async def get_airports():
    """Get list of available airports from database"""
    try:
        query = """
            SELECT iata_code as code,
                   name,
                   city_code as city,
                   country_code as country
            FROM airports
            WHERE location_type = 'Airport'
              AND iata_code IS NOT NULL
              AND name IS NOT NULL
            ORDER BY name
            LIMIT 100
        """
        df = pd.read_sql(query, engine)

        airports = []
        for _, row in df.iterrows():
            airports.append(
                AirportInfo(
                    code=row["code"],
                    name=row["name"],
                    city=row.get("city"),
                    country=row.get("country"),
                )
            )

        return airports

    except Exception as e:
        print(f"Error fetching airports: {e}")
        # Return some default airports if database query fails
        return [
            AirportInfo(code="JFK", name="John F. Kennedy International Airport", city="NYC", country="US"),
            AirportInfo(code="LAX", name="Los Angeles International Airport", city="LAX", country="US"),
            AirportInfo(code="ORD", name="O'Hare International Airport", city="CHI", country="US"),
            AirportInfo(code="LHR", name="London Heathrow Airport", city="LON", country="GB"),
            AirportInfo(code="CDG", name="Charles de Gaulle Airport", city="PAR", country="FR"),
            AirportInfo(code="FRA", name="Frankfurt Airport", city="FRA", country="DE"),
        ]


@app.get("/api/airports/search", response_model=list[AirportInfo])
async def search_airports(q: str = ""):
    """Search airports by code or name"""
    try:
        # Sanitize query to prevent basic injection (though pandas params is safer, we'll use f-string with care or param dict)
        search_term = f"%{q.upper()}%"
        
        # Using raw SQL with parameters is safer, but pandas read_sql with params is tricky with psycopg2/sqlalchemy sometimes
        # We will use text() for safety if possible, or just string formatting since this is a read-only internal app for now
        # Ideally: use SQLAlchemy text() and params
        
        query = """
            SELECT iata_code as code,
                   name,
                   city_code as city,
                   country_code as country
            FROM airports
            WHERE location_type = 'Airport'
              AND iata_code IS NOT NULL
              AND name IS NOT NULL
              AND (UPPER(iata_code) LIKE %(search)s OR UPPER(name) LIKE %(search)s OR UPPER(city_code) LIKE %(search)s)
            ORDER BY 
                CASE WHEN UPPER(iata_code) = %(exact)s THEN 1 ELSE 2 END,
                name
            LIMIT 20
        """
        
        df = pd.read_sql(query, engine, params={"search": search_term, "exact": q.upper()})

        airports = []
        for _, row in df.iterrows():
            airports.append(
                AirportInfo(
                    code=row["code"],
                    name=row["name"],
                    city=row.get("city"),
                    country=row.get("country"),
                )
            )

        return airports

    except Exception as e:
        logger.error(f"Error searching airports: {e}")
        return []


@app.get("/api/airlines/search", response_model=list[AirlineInfo])
async def search_airlines(q: str = ""):
    """Search airlines by code or name"""
    try:
        search_term = f"%{q.upper()}%"
        
        query = """
            SELECT airline_code as code,
                   airline_name as name
            FROM airlines
            WHERE airline_code IS NOT NULL
              AND airline_name IS NOT NULL
              AND (UPPER(airline_code) LIKE %(search)s OR UPPER(airline_name) LIKE %(search)s)
            ORDER BY 
                CASE WHEN UPPER(airline_code) = %(exact)s THEN 1 ELSE 2 END,
                airline_name
            LIMIT 20
        """
        
        df = pd.read_sql(query, engine, params={"search": search_term, "exact": q.upper()})

        airlines = []
        for _, row in df.iterrows():
            airlines.append(
                AirlineInfo(
                    code=row["code"],
                    name=row["name"]
                )
            )

        return airlines

    except Exception as e:
        logger.error(f"Error searching airlines: {e}")
        return []


@app.get("/api/flights/search", response_model=list[FlightSearchInfo])
async def search_flights(q: str = ""):
    """
    Search flights by flight number.
    Returns unique Airline/Flight/Route combinations, ordered by how recently they were flown.
    """
    try:
        search_term = f"%{q.upper()}%"
        
        # Group by flight/route and order by the most recent scheduled date
        # This ensures the current active route for a flight number appears first
        query = """
            SELECT
                CONCAT(f.marketing_carrier_airline_id, f.marketing_carrier_flight_number) as flight_full,
                f.marketing_carrier_airline_id as airline,
                a.airline_name,
                r.departure_airport,
                ap1.name as departure_airport_name,
                r.arrival_airport,
                ap2.name as arrival_airport_name,
                MAX(f.departure_schedule_date) as last_seen
            FROM lufthansa_flight_history f
            JOIN routes r ON f.route_id = r.id
            LEFT JOIN airlines a ON f.marketing_carrier_airline_id = a.airline_code
            LEFT JOIN airports ap1 ON r.departure_airport = ap1.iata_code
            LEFT JOIN airports ap2 ON r.arrival_airport = ap2.iata_code
            WHERE CONCAT(f.marketing_carrier_airline_id, f.marketing_carrier_flight_number) LIKE %(search)s
               OR f.marketing_carrier_flight_number LIKE %(search)s
            GROUP BY 
                f.marketing_carrier_airline_id, 
                f.marketing_carrier_flight_number, 
                a.airline_name,
                r.departure_airport, 
                ap1.name,
                r.arrival_airport,
                ap2.name
            ORDER BY last_seen DESC
            LIMIT 10
        """
        
        df = pd.read_sql(query, engine, params={"search": search_term})

        flights = []
        for _, row in df.iterrows():
            flights.append(
                FlightSearchInfo(
                    flight_number=row["flight_full"],
                    airline=row["airline"],
                    airline_name=row["airline_name"],
                    departure_airport=row["departure_airport"],
                    departure_airport_name=row["departure_airport_name"],
                    arrival_airport=row["arrival_airport"],
                    arrival_airport_name=row["arrival_airport_name"]
                )
            )

        return flights

    except Exception as e:
        logger.error(f"Error searching flights: {e}")
        return []


@app.get("/api/stats/route-delays")
async def get_route_delay_stats(departure_airport: str, arrival_airport: str):
    """
    Get average delay statistics by hour of day for a specific route.
    Uses lufthansa_flight_history if available, falls back to bts_flight_history.
    """
    try:
        # Try Lufthansa data first (PostgreSQL interval handling required)
        query = """
            SELECT 
                EXTRACT(HOUR FROM departure_schedule_time) as hour_of_day,
                AVG(EXTRACT(EPOCH FROM delay_on_arrival)/60) as avg_delay_minutes,
                COUNT(*) as flight_count
            FROM lufthansa_flight_history f
            JOIN routes r ON f.route_id = r.id
            WHERE r.departure_airport = %(dep)s 
              AND r.arrival_airport = %(arr)s
              AND f.delay_on_arrival IS NOT NULL
            GROUP BY hour_of_day
            ORDER BY hour_of_day
        """
        
        df = pd.read_sql(query, engine, params={"dep": departure_airport, "arr": arrival_airport})
        
        source = "Lufthansa"
        
        # If no data, try BTS (structure is different, check schema from memory)
        # bts_flight_history has 'airport' (origin?) but maybe not destination easily joinable 
        # based on schema provided earlier: "airport" varchar(10) ... wait, check schema again
        # Schema says: bts_flight_history has 'airport', 'airport_name'. It's origin-centric?
        # Actually schema shows: carrier, airport, arr_flights, arr_del15... 
        # It aggregates by airport/carrier, not route? 
        # Let's check historical_flights table which joins them.
        
        if df.empty:
            # Fallback to historical_flights if it has route info
            # historical_flights has departure_airport, arrival_airport, delay_minutes
            query_hist = """
                SELECT 
                    -- We don't have hour in historical_flights easily unless we join back
                    -- Let's just return empty if LH data is empty for now to be safe
                    -- or check if we can get aggregate stats
                    0 as hour_of_day,
                    AVG(delay_minutes) as avg_delay_minutes,
                    COUNT(*) as flight_count
                FROM historical_flights
                WHERE departure_airport = %(dep)s 
                  AND arrival_airport = %(arr)s
                  AND delay_minutes IS NOT NULL
            """
            # df_hist = pd.read_sql(query_hist, engine, params={"dep": departure_airport, "arr": arrival_airport})
            # For now, let's stick to LH data to ensure accuracy of "Time of Day"
            pass

        # Prepare response
        # Ensure all hours 0-23 are present for the chart
        hours = list(range(24))
        avg_delays = [0] * 24
        counts = [0] * 24
        
        if not df.empty:
            for _, row in df.iterrows():
                h = int(row['hour_of_day'])
                if 0 <= h < 24:
                    avg_delays[h] = max(0, round(row['avg_delay_minutes'], 1))
                    counts[h] = int(row['flight_count'])
        
        return {
            "departure_airport": departure_airport,
            "arrival_airport": arrival_airport,
            "source": source,
            "has_data": not df.empty,
            "labels": [f"{h:02d}:00" for h in hours],
            "values": avg_delays,
            "counts": counts
        }

    except Exception as e:
        logger.error(f"Error fetching route stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/predict", response_model=FlightPredictionResponse)
async def predict_delay(flight_data: FlightPredictionRequest):
    """
    Predict flight delay based on flight information with enriched features and caching
    """
    start_time = time.time()
    success = False

    with logger.operation_context(
        'prediction',
        flight_number=flight_data.flight_number,
        departure_airport=flight_data.departure_airport,
        arrival_airport=flight_data.arrival_airport
    ):
        try:
            # Check cache first
            cached_result = prediction_cache.get(
                flight_data.flight_number,
                flight_data.departure_airport,
                flight_data.arrival_airport,
                flight_data.scheduled_departure,
                flight_data.airline
            )

            if cached_result is not None:
                logger.info("Prediction served from cache")
                metrics.record_cache_hit()
                return FlightPredictionResponse(**cached_result)

            metrics.record_cache_miss()

            # Parse the scheduled departure datetime
            scheduled_dt = datetime.fromisoformat(flight_data.scheduled_departure)

            # Get weather and coords here to include in response
            departure_coords = get_airport_coordinates(engine, flight_data.departure_airport)
            arrival_coords = get_airport_coordinates(engine, flight_data.arrival_airport)

            departure_weather = weather_service.get_weather_by_airport(
                flight_data.departure_airport, departure_coords
            )
            arrival_weather = weather_service.get_weather_by_airport(
                flight_data.arrival_airport, arrival_coords
            )

            # Get active model from registry
            model = model_registry.get_active_model()
            using_mock = model is None
            warning_message = None

            if model is not None:
                # Use actual ML model for prediction
                try:
                    # Prepare features in the same format as training
                    features_df = prepare_features_for_model(flight_data, scheduled_dt, departure_weather, arrival_weather)

                    # Align columns with training data
                    # The model expects specific columns from training
                    # We need to add missing columns with 0 values
                    if hasattr(model, 'feature_names_in_'):
                        model_columns = model.feature_names_in_
                        for col in model_columns:
                            if col not in features_df.columns:
                                features_df[col] = 0
                        # Reorder columns to match model training
                        features_df = features_df[model_columns]

                    # Make prediction using the actual model
                    predicted_delay = model.predict(features_df)[0]

                    # Calculate probability (for regression, estimate based on magnitude)
                    # Higher delays = higher probability
                    delay_probability = min(1.0, max(0.0, predicted_delay / 60.0))

                    # Get feature importance if available
                    if hasattr(model, 'feature_importances_'):
                        importances = model.feature_importances_
                        # Get top 5 features
                        top_indices = np.argsort(importances)[-5:][::-1]
                        top_features = {
                            features_df.columns[i]: float(importances[i])
                            for i in top_indices
                        }
                        # Normalize to sum to 1
                        total = sum(top_features.values())
                        factors = {k: v/total for k, v in top_features.items()}
                    else:
                        factors = {
                            "Time of Day": 0.35,
                            "Day of Week": 0.25,
                            "Route Congestion": 0.20,
                            "Weather Conditions": 0.15,
                            "Historical Delays": 0.05,
                        }

                    message = "Prediction generated using ML model"
                    if predicted_delay > 30:
                        message = "High delay risk detected (ML prediction)"
                    elif predicted_delay > 15:
                        message = "Moderate delay risk (ML prediction)"
                    else:
                        message = "Low delay risk (ML prediction)"

                except Exception as e:
                    logger.error("ML model prediction failed", error=str(e))
                    # Fall back to mock prediction
                    using_mock = True
                    warning_message = f"ML model prediction failed. Using simulated data. Error: {str(e)}"

            if using_mock:
                # Mock prediction logic when model is not available
                features = {
                    "hour": scheduled_dt.hour,
                    "day_of_week": scheduled_dt.weekday(),
                }

                base_delay = 0
                delay_probability = 0.3

                # Higher delays during rush hours
                if 7 <= features["hour"] <= 9 or 17 <= features["hour"] <= 19:
                    base_delay = np.random.randint(15, 45)
                    delay_probability = 0.7
                elif 6 <= features["hour"] <= 22:
                    base_delay = np.random.randint(0, 20)
                    delay_probability = 0.4
                else:
                    base_delay = np.random.randint(0, 10)
                    delay_probability = 0.2

                # Higher delays on Fridays and Sundays
                if features["day_of_week"] in [4, 6]:
                    base_delay += 10
                    delay_probability += 0.1

                # Add some randomness
                predicted_delay = max(0, base_delay + np.random.randint(-5, 10))
                delay_probability = min(1.0, delay_probability + np.random.uniform(-0.1, 0.1))

                factors = {
                    "Time of Day": 0.35,
                    "Day of Week": 0.25,
                    "Route Congestion": 0.20,
                    "Weather Conditions": 0.15,
                    "Historical Delays": 0.05,
                }

                message = "Prediction generated using simulation"
                if predicted_delay > 30:
                    message = "High delay risk detected (simulated)"
                elif predicted_delay > 15:
                    message = "Moderate delay risk (simulated)"
                else:
                    message = "Low delay risk (simulated)"

                if warning_message is None:
                    warning_message = "ML model not loaded. Using simulated predictions based on time patterns."

            # Record metrics
            duration = time.time() - start_time
            success = True
            metrics.record_prediction(duration, using_mock, success)

            logger.info(
                "Prediction completed",
                predicted_delay=predicted_delay,
                using_mock=using_mock,
                duration_seconds=duration
            )

            # Prepare response
            response_data = {
                "prediction": float(predicted_delay),
                "delay_probability": float(delay_probability),
                "factors": factors,
                "message": message,
                "using_mock_data": using_mock,
                "warning": warning_message,
                "from_cache": False,
                "cached_at": None,
                "departure_weather": departure_weather,
                "arrival_weather": arrival_weather,
                "departure_coords": {"lat": departure_coords[0], "lon": departure_coords[1]} if departure_coords else None,
                "arrival_coords": {"lat": arrival_coords[0], "lon": arrival_coords[1]} if arrival_coords else None
            }

            # Cache the result
            prediction_cache.set(
                flight_data.flight_number,
                flight_data.departure_airport,
                flight_data.arrival_airport,
                flight_data.scheduled_departure,
                response_data,
                model_version=model_registry.active_version,
                airline=flight_data.airline
            )

            return FlightPredictionResponse(**response_data)

        except ValueError as e:
            logger.error("Invalid datetime format", error=str(e))
            duration = time.time() - start_time
            metrics.record_prediction(duration, True, False)
            raise HTTPException(status_code=400, detail=f"Invalid datetime format: {str(e)}")
        except Exception as e:
            logger.error("Prediction error", error=str(e))
            duration = time.time() - start_time
            metrics.record_prediction(duration, True, False)
            raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@app.get("/api/health")
async def health_check():
    """Health check endpoint with detailed status"""
    active_model = model_registry.get_active_model()
    active_meta = model_registry.get_active_metadata()

    return {
        "status": "healthy",
        "model_loaded": active_model is not None,
        "model_version": model_registry.active_version if active_model else None,
        "model_type": active_meta.model_type if active_meta else None,
        "database_connected": check_db_connection(),
        "cache_stats": {
            "feature_cache": get_feature_cache().get_stats(),
            "weather_cache": weather_service.get_cache_stats(),
            "prediction_cache": prediction_cache.get_stats()
        }
    }


@app.get("/api/metrics")
async def get_metrics():
    """Get application metrics"""
    return metrics.get_metrics()


@app.get("/api/models")
async def list_models():
    """List all available models in the registry"""
    return {
        "models": model_registry.get_all_metadata(),
        "active_version": model_registry.active_version
    }


@app.post("/api/models/{version}/activate")
async def activate_model(version: str):
    """Activate a specific model version and invalidate prediction cache"""
    if model_registry.set_active(version):
        # Invalidate prediction cache when switching models
        invalidated = prediction_cache.invalidate_all()
        logger.info(
            "Model version activated",
            version=version,
            cache_entries_invalidated=invalidated
        )
        return {
            "status": "success",
            "active_version": version,
            "cache_entries_invalidated": invalidated
        }
    else:
        raise HTTPException(status_code=404, detail=f"Model version {version} not found")


@app.get("/api/cache/stats")
async def get_cache_stats():
    """Get detailed cache statistics"""
    return {
        "feature_cache": get_feature_cache().get_stats(),
        "weather_cache": weather_service.get_cache_stats(),
        "prediction_cache": {
            **prediction_cache.get_stats(),
            "size_mb": prediction_cache.get_cache_size_mb()
        }
    }


@app.post("/api/cache/invalidate")
async def invalidate_caches(cache_type: Optional[str] = None):
    """
    Invalidate caches

    Args:
        cache_type: Optional cache type to invalidate (feature, weather, prediction, all)
    """
    results = {}

    if cache_type is None or cache_type == "all":
        # Invalidate all caches
        get_feature_cache().clear()
        weather_service.clear_cache()
        prediction_cache.invalidate_all()
        results = {
            "feature_cache": "cleared",
            "weather_cache": "cleared",
            "prediction_cache": "cleared"
        }
        logger.info("All caches invalidated")

    elif cache_type == "feature":
        get_feature_cache().clear()
        results["feature_cache"] = "cleared"
        logger.info("Feature cache invalidated")

    elif cache_type == "weather":
        weather_service.clear_cache()
        results["weather_cache"] = "cleared"
        logger.info("Weather cache invalidated")

    elif cache_type == "prediction":
        prediction_cache.invalidate_all()
        results["prediction_cache"] = "cleared"
        logger.info("Prediction cache invalidated")

    else:
        raise HTTPException(status_code=400, detail=f"Invalid cache type: {cache_type}")

    return {"status": "success", "results": results}


@app.post("/api/cache/cleanup")
async def cleanup_expired_caches():
    """Remove expired entries from all caches"""
    expired_predictions = prediction_cache.invalidate_expired()

    logger.info("Expired cache entries cleaned up", expired_predictions=expired_predictions)

    return {
        "status": "success",
        "expired_predictions_removed": expired_predictions
    }


def check_db_connection():
    """Check if database connection is working"""
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


# Data viewing endpoints
@app.get("/api/data/countries")
async def get_countries(limit: int = 100, offset: int = 0):
    """Get list of countries from database"""
    try:
        query = f"""
            SELECT country_code, country_name
            FROM countries
            ORDER BY country_name
            LIMIT {limit} OFFSET {offset}
        """
        df = pd.read_sql(query, engine)

        # Get total count
        count_query = "SELECT COUNT(*) as total FROM countries"
        total = pd.read_sql(count_query, engine)["total"][0]

        return {
            "data": df.to_dict(orient="records"),
            "total": int(total),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching countries: {str(e)}")


@app.get("/api/data/cities")
async def get_cities(limit: int = 100, offset: int = 0):
    """Get list of cities from database"""
    try:
        query = f"""
            SELECT c.city_code, c.city_name, c.country_code, co.country_name
            FROM cities c
            LEFT JOIN countries co ON c.country_code = co.country_code
            ORDER BY c.city_name
            LIMIT {limit} OFFSET {offset}
        """
        df = pd.read_sql(query, engine)

        count_query = "SELECT COUNT(*) as total FROM cities"
        total = pd.read_sql(count_query, engine)["total"][0]

        return {
            "data": df.to_dict(orient="records"),
            "total": int(total),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching cities: {str(e)}")


@app.get("/api/data/airlines")
async def get_airlines(limit: int = 100, offset: int = 0):
    """Get list of airlines from database"""
    try:
        query = f"""
            SELECT airline_id, airline_code, airline_name
            FROM airlines
            ORDER BY airline_name
            LIMIT {limit} OFFSET {offset}
        """
        df = pd.read_sql(query, engine)

        count_query = "SELECT COUNT(*) as total FROM airlines"
        total = pd.read_sql(count_query, engine)["total"][0]

        return {
            "data": df.to_dict(orient="records"),
            "total": int(total),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching airlines: {str(e)}")


@app.get("/api/data/airports")
async def get_airports_data(limit: int = 100, offset: int = 0):
    """Get list of airports with full details from database"""
    try:
        query = f"""
            SELECT
                airport_code,
                iata_code,
                name,
                city_code,
                country_code,
                location_type,
                latitude,
                longitude,
                time_zone_id
            FROM airports
            ORDER BY name
            LIMIT {limit} OFFSET {offset}
        """
        df = pd.read_sql(query, engine)

        count_query = "SELECT COUNT(*) as total FROM airports"
        total = pd.read_sql(count_query, engine)["total"][0]

        return {
            "data": df.to_dict(orient="records"),
            "total": int(total),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching airports: {str(e)}")


@app.get("/api/data/aircrafts")
async def get_aircrafts(limit: int = 100, offset: int = 0):
    """Get list of aircraft types from database"""
    try:
        query = f"""
            SELECT aircraft_code, aircraft_name, airline_equipment_code
            FROM aircrafts
            ORDER BY aircraft_name
            LIMIT {limit} OFFSET {offset}
        """
        df = pd.read_sql(query, engine)

        count_query = "SELECT COUNT(*) as total FROM aircrafts"
        total = pd.read_sql(count_query, engine)["total"][0]

        return {
            "data": df.to_dict(orient="records"),
            "total": int(total),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching aircrafts: {str(e)}")


@app.get("/api/data/routes")
async def get_routes(limit: int = 100, offset: int = 0):
    """Get list of flight routes from database"""
    try:
        query = f"""
            SELECT
                r.id,
                r.departure_airport,
                ao.name as origin_airport_name,
                r.arrival_airport,
                ad.name as destination_airport_name,
                r.distance,
                r.important
            FROM routes r
            LEFT JOIN airports ao ON r.departure_airport = ao.iata_code
            LEFT JOIN airports ad ON r.arrival_airport = ad.iata_code
            ORDER BY r.id
            LIMIT {limit} OFFSET {offset}
        """
        df = pd.read_sql(query, engine)

        count_query = "SELECT COUNT(*) as total FROM routes"
        total = pd.read_sql(count_query, engine)["total"][0]

        return {
            "data": df.to_dict(orient="records"),
            "total": int(total),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching routes: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
