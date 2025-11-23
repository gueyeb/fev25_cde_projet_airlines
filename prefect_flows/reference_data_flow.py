"""
Reference Data Sync Flow
Syncs reference data that changes infrequently (countries, cities, airlines, airports, aircrafts)
Schedule: Weekly or on-demand
"""
from prefect import flow, task
from prefect.task_runners import ConcurrentTaskRunner
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@task(
    name="sync-countries",
    description="Synchronize countries from Lufthansa API",
    retries=2,
    retry_delay_seconds=30,
    log_prints=True
)
def sync_countries_task():
    """Sync countries reference data"""
    from src.jobs.sync_countries import sync_countries
    print("[INFO] Starting countries synchronization...")
    sync_countries()
    print("[SUCCESS] Countries synchronized")


@task(
    name="sync-cities",
    description="Synchronize cities from Lufthansa API",
    retries=2,
    retry_delay_seconds=30,
    log_prints=True
)
def sync_cities_task():
    """Sync cities reference data"""
    from src.jobs.sync_cities import sync_cities
    print("[INFO] Starting cities synchronization...")
    sync_cities()
    print("[SUCCESS] Cities synchronized")


@task(
    name="sync-airlines",
    description="Synchronize airlines from Lufthansa API",
    retries=2,
    retry_delay_seconds=30,
    log_prints=True
)
def sync_airlines_task():
    """Sync airlines reference data"""
    from src.jobs.sync_airlines import sync_airlines
    print("[INFO] Starting airlines synchronization...")
    sync_airlines()
    print("[SUCCESS] Airlines synchronized")


@task(
    name="sync-airports",
    description="Synchronize airports from Lufthansa API",
    retries=2,
    retry_delay_seconds=30,
    log_prints=True
)
def sync_airports_task():
    """Sync airports reference data"""
    from src.jobs.sync_airports import sync_airports
    print("[INFO] Starting airports synchronization...")
    sync_airports()
    print("[SUCCESS] Airports synchronized")


@task(
    name="sync-aircrafts",
    description="Synchronize aircraft types from Lufthansa API",
    retries=2,
    retry_delay_seconds=30,
    log_prints=True
)
def sync_aircrafts_task():
    """Sync aircrafts reference data"""
    from src.jobs.sync_aircrafts import sync_aircrafts
    print("[INFO] Starting aircrafts synchronization...")
    sync_aircrafts()
    print("[SUCCESS] Aircrafts synchronized")


@task(
    name="create-routes",
    description="Create routes with distance calculations",
    retries=1,
    retry_delay_seconds=60,
    log_prints=True
)
def create_routes_task():
    """Create routes based on airports"""
    from src.jobs.create_routes import create_routes
    print("[INFO] Starting routes creation...")
    create_routes()
    print("[SUCCESS] Routes created")


@flow(
    name="reference-data-sync",
    description="Synchronize all reference data (countries, cities, airlines, airports, aircrafts, routes)",
    task_runner=ConcurrentTaskRunner(),
    log_prints=True
)
def reference_data_sync_flow(skip_routes: bool = False):
    """
    Main flow to synchronize all reference data.

    Args:
        skip_routes: If True, skip route creation (useful for partial updates)

    This flow syncs:
    1. Countries, cities, airlines, airports, aircrafts (in parallel where possible)
    2. Routes (depends on airports being synced)

    Schedule: Weekly or on-demand
    """
    print("[FLOW START] Reference Data Synchronization")
    print("=" * 60)

    # Phase 1: Sync foundational data (countries and cities must go first)
    print("[PHASE 1] Syncing countries and cities...")
    sync_countries_task()
    sync_cities_task()

    # Phase 2: Sync other reference data (can run in parallel)
    print("[PHASE 2] Syncing airlines, airports, and aircrafts...")
    sync_airlines_task()
    sync_airports_task()
    sync_aircrafts_task()

    # Phase 3: Create routes (depends on airports)
    if not skip_routes:
        print("[PHASE 3] Creating routes...")
        create_routes_task()
    else:
        print("[SKIP] Route creation skipped")

    print("=" * 60)
    print("[FLOW COMPLETE] Reference data synchronized successfully")


if __name__ == "__main__":
    # For testing: run the flow directly
    reference_data_sync_flow()
