# app.py (FastAPI Backend)
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
import pandas as pd
from datetime import datetime
import requests
import os

app = FastAPI(title="Flight Delay Prediction API")

# Load the trained model
model = joblib.load("models/flight_delay_model.pkl")

class FlightInfo(BaseModel):
    flight_number: str
    departure_airport: str
    arrival_airport: str
    scheduled_departure: datetime
    aircraft_type: str = None
    airline: str = None

class PredictionResponse(BaseModel):
    flight_number: str
    prediction: float
    delay_probability: float
    confidence: float
    factors: dict

@app.post("/predict/", response_model=PredictionResponse)
async def predict_delay(flight_info: FlightInfo):
    try:
        # Get weather data from OpenWeatherMap API
        weather_data = fetch_weather_data(flight_info.departure_airport)
        
        # Prepare features for model
        features = prepare_features(flight_info, weather_data)
        
        # Make prediction
        prediction = model.predict(features)[0]
        probability = model.predict_proba(features)[0][1]
        
        # Identify influential factors (if using explainable AI)
        factors = explain_prediction(model, features)
        
        return {
            "flight_number": flight_info.flight_number,
            "prediction": float(prediction),
            "delay_probability": float(probability),
            "confidence": calculate_confidence(probability),
            "factors": factors
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def fetch_weather_data(airport_code):
    # Fetch weather data from OpenWeatherMap API
    api_key = os.environ.get("OPENWEATHER_API_KEY")
    # Get airport coordinates from database or another service
    lat, lon = get_airport_coordinates(airport_code)
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}"
    response = requests.get(url)
    return response.json()

def prepare_features(flight_info, weather_data):
    # Convert flight info and weather data into model features
    # This will depend on your specific model
    # ...
    return features

def explain_prediction(model, features):
    # Use explainable AI techniques (SHAP, LIME) to identify
    # factors contributing to the prediction
    # ...
    return factors

def calculate_confidence(probability):
    # Calculate confidence score based on probability
    # ...
    return confidence_score