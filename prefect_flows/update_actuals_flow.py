"""
Update Flight Actuals Flow
Updates real-time flight status information (delays, actual times, etc.)
Schedule: Every 4 hours during business hours
"""
from prefect import flow, task
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@task(
    name="update-flight-actuals",
    description="Update actual flight times and delays from Lufthansa API",
    retries=3,
    retry_delay_seconds=60,
    log_prints=True
)
def update_flight_actuals_task():
    """
    Update actual flight information for flights scheduled today.

    This task:
    - Fetches real-time flight status from Lufthansa API
    - Updates actual departure/arrival times
    - Records delays
    - Refreshes weather data based on actual times
    """
    from src.jobs.update_flight_history import update_lufthansa_flight_history

    print("[INFO] Updating flight actuals...")
    update_lufthansa_flight_history()
    print("[SUCCESS] Flight actuals updated")


@flow(
    name="update-flight-actuals",
    description="Update real-time flight status information",
    log_prints=True
)
def update_flight_actuals_flow():
    """
    Flow to update actual flight times and status.

    This flow updates:
    - Actual departure/arrival times
    - Flight delays
    - Weather conditions at actual times

    Schedule: Every 4 hours from 6:00 AM to 10:00 PM
    """
    print("[FLOW START] Update Flight Actuals")
    print("=" * 60)

    update_flight_actuals_task()

    print("=" * 60)
    print("[FLOW COMPLETE] Flight actuals updated successfully")


if __name__ == "__main__":
    # For testing: run the update
    update_flight_actuals_flow()
