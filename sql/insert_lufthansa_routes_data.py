import requests
from sqlalchemy import create_engine
from datetime import datetime, timedelta
import pandas as pd
import os
import sys
# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from functions.pg_functions import getAirPorts, insert_dataframe
from config.env_loader import load_env

load_env()

BASE_URL = os.getenv("LUFTHANSA_BASE_URL")
ACCESS_TOKEN = os.getenv("LUFTHANSA_ACCESS_TOKEN")


iata_codes = getAirPorts()
routes = [(origin, dest) for origin in iata_codes for dest in iata_codes if origin != dest]

start_date = datetime(2025, 5, 28)
end_date = start_date + timedelta(days=7)

def insert_routes_data():
    insert_data = []
    for date in (start_date + timedelta(n) for n in range((end_date - start_date).days)):
        date_str = date.strftime('%Y-%m-%d')
        for origin, dest in routes:
            url = f"{BASE_URL}/{origin}/{dest}/{date_str}"
            response = requests.get(url, headers={'Authorization': ACCESS_TOKEN})
            if response.status_code == 200:
                schedules = response.json().get('ScheduleResource', {}).get('Schedule', [])
                for s in schedules:
                    flight = s['Flight']
                    flight_number = flight['MarketingCarrier']['FlightNumber']
                    airline_code = flight['MarketingCarrier']['AirlineID']
                    operating_days = s.get('OperatingDays', {}).get('DaysOfOperation', '1111111')

                    insert_data.append({
                        'flight_number': flight_number,
                        'airline_code': airline_code,
                        'departure_airport': origin,
                        'arrival_airport': dest,
                        'operating_days': operating_days
                    })
    df = pd.DataFrame(insert_data)
    insert_data(df, "routes")


if __name__ == "__main__":
    insert_routes_data()