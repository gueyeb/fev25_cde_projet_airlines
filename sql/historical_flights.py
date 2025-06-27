import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from functions.pg_functions import build_historical_flights_from_bts

if __name__ == "__main__":
    build_historical_flights_from_bts()