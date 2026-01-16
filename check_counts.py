import sys
from pathlib import Path
from sqlalchemy import text

# Add parent directory to path to import project modules
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.pg_functions import engine

with engine.connect() as conn:
    lh_count = conn.execute(text("SELECT COUNT(*) FROM lufthansa_flight_history")).scalar()
    lh_with_delay = conn.execute(text("SELECT COUNT(*) FROM lufthansa_flight_history WHERE delay_on_arrival IS NOT NULL")).scalar()
    bts_count = conn.execute(text("SELECT COUNT(*) FROM bts_flight_history")).scalar()
    print(f"Lufthansa History Count: {lh_count}")
    print(f"Lufthansa with Delay Data: {lh_with_delay}")
    print(f"BTS History Count: {bts_count}")
