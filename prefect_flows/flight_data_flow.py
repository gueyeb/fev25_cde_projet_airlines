"""
Flight Data Pipeline Flow
Syncs flight schedules and enriches with weather data
Schedule: Daily (for new schedules)
"""
from prefect import flow, task
from datetime import date, timedelta
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@task(
    name="sync-flight-history",
    description="Synchronize flight schedules from Lufthansa API",
    retries=3,
    retry_delay_seconds=60,
    log_prints=True
)
def sync_flight_history_task(target_date: str = None):
    """
    Sync flight schedules for a specific date.

    Args:
        target_date: Date in YYYY-MM-DD format. If None, uses today.
    """
    from src.jobs.sync_flight_history import sync_lufthansa_flight_history

    if target_date is None:
        target_date = date.today().isoformat()

    print(f"[INFO] Syncing flight history for {target_date}...")
    sync_lufthansa_flight_history(run_date=target_date)
    print(f"[SUCCESS] Flight history synced for {target_date}")


@task(
    name="enrich-weather",
    description="Enrich flight data with weather information",
    retries=2,
    retry_delay_seconds=120,
    log_prints=True
)
def enrich_weather_task(target_date: str = None, budget: int = 900):
    """
    Enrich flight data with weather information.

    Args:
        target_date: Date in YYYY-MM-DD format. If None, uses today.
        budget: Daily API call budget for OpenWeatherMap
    """
    from src.jobs.enrich_weather import enrich_weather_for_flights

    if target_date is None:
        target_date = date.today().isoformat()

    print(f"[INFO] Enriching weather data for {target_date} (budget: {budget})...")
    enrich_weather_for_flights(target_date=target_date, daily_budget=budget)
    print(f"[SUCCESS] Weather data enriched for {target_date}")


@flow(
    name="daily-flight-data-pipeline",
    description="Daily pipeline to sync flight schedules and enrich with weather data",
    log_prints=True
)
def daily_flight_data_flow(target_date: str = None, weather_budget: int = 900):
    """
    Daily flow to sync flight schedules and enrich with weather.

    Args:
        target_date: Date in YYYY-MM-DD format. If None, uses today.
        weather_budget: Daily API call budget for OpenWeatherMap

    This flow:
    1. Syncs flight schedules from Lufthansa API for the target date
    2. Enriches flight data with weather information

    Schedule: Daily at 2:00 AM
    """
    if target_date is None:
        target_date = date.today().isoformat()

    print(f"[FLOW START] Daily Flight Data Pipeline for {target_date}")
    print("=" * 60)

    # Step 1: Sync flight schedules
    print("[STEP 1/2] Syncing flight schedules...")
    sync_flight_history_task(target_date=target_date)

    # Step 2: Enrich with weather data
    print("[STEP 2/2] Enriching with weather data...")
    enrich_weather_task(target_date=target_date, budget=weather_budget)

    print("=" * 60)
    print(f"[FLOW COMPLETE] Daily pipeline completed for {target_date}")


@flow(
    name="backfill-flight-data",
    description="Backfill flight data for a date range",
    log_prints=True
)
def backfill_flight_data_flow(start_date: str, end_date: str, weather_budget: int = 900):
    """
    Backfill flight data for a range of dates.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        weather_budget: Daily API call budget for OpenWeatherMap per day

    This is useful for:
    - Initial data load
    - Recovering from outages
    - Historical data analysis

    WARNING: Be mindful of API rate limits!
    """
    from datetime import datetime

    start = datetime.fromisoformat(start_date).date()
    end = datetime.fromisoformat(end_date).date()

    print(f"[FLOW START] Backfill from {start_date} to {end_date}")
    print("=" * 60)

    current = start
    day_count = 0

    while current <= end:
        day_count += 1
        date_str = current.isoformat()

        print(f"\n[DAY {day_count}] Processing {date_str}...")

        # Run daily pipeline for this date
        try:
            sync_flight_history_task(target_date=date_str)
            enrich_weather_task(target_date=date_str, budget=weather_budget)
            print(f"[SUCCESS] Completed {date_str}")
        except Exception as e:
            print(f"[ERROR] Failed to process {date_str}: {e}")
            # Continue with next date even if one fails

        current += timedelta(days=1)

    print("=" * 60)
    print(f"[FLOW COMPLETE] Backfill completed: {day_count} days processed")


if __name__ == "__main__":
    # For testing: run today's pipeline
    daily_flight_data_flow()
