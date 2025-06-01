import os
import requests
import psycopg2
import pymongo
from datetime import datetime, timedelta

from config.env_loader import load_env

load_env()

# --- CONFIGURATION ---
BASE_URL=os.getenv("OPENWEATHERMAP_BASE_URL")
OWM_API_KEY = os.getenv("OWM_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")
PG_CONN_INFO = {
    "host": os.getenv("PG_HOST"),
    "port": int(os.getenv("PG_PORT")),
    "dbname": os.getenv("PG_DB"),
    "user": os.getenv("PG_USER"),
    "password": os.getenv("PG_PASSWORD")
}
TTL_MINUTES = 90  # Durée de validité en minutes

# --- RECUPERATION DES AEROPORTS ---
def get_airports_from_postgres():
    conn = psycopg2.connect(**PG_CONN_INFO)
    cur = conn.cursor()
    cur.execute("SELECT iata_code, latitude, longitude FROM airports WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"iata_code": r[0], "lat": r[1], "lon": r[2]} for r in rows]

# --- APPEL API OPENWEATHERMAP ---
def fetch_weather(lat, lon):
    url = f"{BASE_URL}?lat={lat}&lon={lon}&appid={OWM_API_KEY}&units=metric"
    resp = requests.get(url)
    if resp.status_code == 200:
        data = resp.json()
        return {
            "temperature": data["main"]["temp"],
            "wind_speed": data["wind"]["speed"],
            "visibility": data.get("visibility", 0),
            "conditions": [w["main"] for w in data["weather"]]
        }
    else:
        print(f"Erreur météo : {resp.status_code}")
        return None

# --- INSERTION MONGODB ---
def insert_weather(airport_code, weather_data):
    client = pymongo.MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    now = datetime.utcnow()
    document = {
        "airport": airport_code,
        "timestamp": now,
        "valid_until": now + timedelta(minutes=TTL_MINUTES),
        "weather": weather_data
    }
    db.weather.insert_one(document)
    print(f"Météo insérée pour {airport_code}")


if __name__ == "__main__":
    airports = get_airports_from_postgres()
    for airport in airports:
        weather = fetch_weather(airport["lat"], airport["lon"])
        if weather:
            insert_weather(airport["iata_code"], weather)