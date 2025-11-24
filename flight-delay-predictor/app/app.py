"""
DST Airlines Flight Delay Predictor - FastAPI Backend
"""

import os
import sys
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

# Initialize FastAPI app
app = FastAPI(title="DST Airlines Flight Delay Predictor", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
APP_DIR = Path(__file__).parent
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


class AirportInfo(BaseModel):
    code: str
    name: str
    city: Optional[str] = None
    country: Optional[str] = None


# Load ML model (placeholder - we'll load actual model later)
MODEL_PATH = Path(__file__).parent / "models" / "flight_delay_model.pkl"


def load_model():
    """Load the trained ML model"""
    if MODEL_PATH.exists():
        try:
            return joblib.load(MODEL_PATH)
        except Exception as e:
            print(f"Error loading model: {e}")
            return None
    return None


model = load_model()

# Store the feature columns that the model was trained on
model_feature_columns = None


def prepare_features_for_model(flight_data: FlightPredictionRequest, scheduled_dt: datetime) -> pd.DataFrame:
    """
    Prepare features in the same format as the ML training pipeline.
    This function creates a feature set that matches the training data preprocessing.
    """
    # Create basic features that we can extract from the request
    features_dict = {
        'total_journey_duration': 0,  # We don't have this information at prediction time
        'delay_on_departure': 0,  # We don't have this information at prediction time
        'departure_day_of_week': scheduled_dt.weekday(),
        'departure_hour': scheduled_dt.hour,
        'departure_terminal': 'unknown',  # Would need to query from database
        'arrival_terminal': 'unknown',  # Would need to query from database
        'marketing_carrier_airline_id': flight_data.airline or 'unknown',
        'equipment_aircraft_code': 'unknown',  # Would need to query from database
        'departure_airport_meteo': 'unknown',  # Would need weather API
        'arrival_airport_meteo': 'unknown',  # Would need weather API
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

    # Convert durations to minutes
    df['total_journey_duration'] = df['total_journey_duration'] / 60.0
    df['delay_on_departure'] = df['delay_on_departure'] / 60.0

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


@app.post("/api/predict", response_model=FlightPredictionResponse)
async def predict_delay(flight_data: FlightPredictionRequest):
    """
    Predict flight delay based on flight information
    """
    try:
        # Parse the scheduled departure datetime
        scheduled_dt = datetime.fromisoformat(flight_data.scheduled_departure)

        using_mock = model is None
        warning_message = None

        if model is not None:
            # Use actual ML model for prediction
            try:
                # Prepare features in the same format as training
                features_df = prepare_features_for_model(flight_data, scheduled_dt)

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
                print(f"Error using ML model: {e}")
                import traceback
                traceback.print_exc()
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

        return FlightPredictionResponse(
            prediction=float(predicted_delay),
            delay_probability=float(delay_probability),
            factors=factors,
            message=message,
            using_mock_data=using_mock,
            warning=warning_message,
        )

    except ValueError as e:
        print(f"❌ ValueError in /api/predict: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Invalid datetime format: {str(e)}")
    except Exception as e:
        print(f"❌ Exception in /api/predict: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "database_connected": check_db_connection(),
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
                r.route_id,
                r.origin_airport_code,
                ao.name as origin_airport_name,
                r.destination_airport_code,
                ad.name as destination_airport_name,
                r.distance_km,
                r.created_at
            FROM routes r
            LEFT JOIN airports ao ON r.origin_airport_code = ao.airport_code
            LEFT JOIN airports ad ON r.destination_airport_code = ad.airport_code
            ORDER BY r.route_id
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
