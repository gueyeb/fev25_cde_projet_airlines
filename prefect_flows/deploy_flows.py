"""
Prefect Deployment Configuration
This script creates and registers all flow deployments with their schedules
"""
from prefect.deployments import Deployment
from prefect.server.schemas.schedules import CronSchedule
from prefect.filesystems import LocalFileSystem
import sys
from pathlib import Path

# Import all flows
from reference_data_flow import reference_data_sync_flow
from flight_data_flow import daily_flight_data_flow
from update_actuals_flow import update_flight_actuals_flow
from ml_training_flow import ml_training_flow


def create_deployments():
    """Create all Prefect deployments with their schedules"""

    print("[INFO] Creating Prefect deployments...")
    print("=" * 60)

    # Storage configuration
    storage = LocalFileSystem.load("local-storage")

    # 1. Reference Data Sync - Weekly on Saturdays at 1:00 AM
    ref_data_deployment = Deployment.build_from_flow(
        flow=reference_data_sync_flow,
        name="weekly-reference-sync",
        version="1.0",
        description="Weekly synchronization of reference data (countries, cities, airlines, airports, routes)",
        schedule=CronSchedule(cron="0 1 * * 6", timezone="UTC"),  # Saturday 1 AM UTC
        work_pool_name="default",
        tags=["reference-data", "weekly", "low-priority"],
        parameters={"skip_routes": False}
    )
    ref_data_id = ref_data_deployment.apply()
    print(f"[SUCCESS] Created deployment: weekly-reference-sync (ID: {ref_data_id})")

    # 2. Daily Flight Data Pipeline - Daily at 2:00 AM
    daily_flight_deployment = Deployment.build_from_flow(
        flow=daily_flight_data_flow,
        name="daily-flight-pipeline",
        version="1.0",
        description="Daily pipeline to sync flight schedules and enrich with weather data",
        schedule=CronSchedule(cron="0 2 * * *", timezone="UTC"),  # Daily 2 AM UTC
        work_pool_name="default",
        tags=["flight-data", "daily", "high-priority"],
        parameters={
            "target_date": None,  # Will use today
            "weather_budget": 900
        }
    )
    daily_flight_id = daily_flight_deployment.apply()
    print(f"[SUCCESS] Created deployment: daily-flight-pipeline (ID: {daily_flight_id})")

    # 3. Update Flight Actuals - Every 4 hours from 6 AM to 10 PM
    update_actuals_deployment = Deployment.build_from_flow(
        flow=update_flight_actuals_flow,
        name="hourly-actuals-update",
        version="1.0",
        description="Update real-time flight status every 4 hours",
        schedule=CronSchedule(cron="0 6,10,14,18,22 * * *", timezone="UTC"),  # 6 AM, 10 AM, 2 PM, 6 PM, 10 PM UTC
        work_pool_name="default",
        tags=["actuals", "periodic", "medium-priority"]
    )
    actuals_id = update_actuals_deployment.apply()
    print(f"[SUCCESS] Created deployment: hourly-actuals-update (ID: {actuals_id})")

    # 4. ML Model Training - Weekly on Sundays at 3:00 AM
    ml_training_deployment = Deployment.build_from_flow(
        flow=ml_training_flow,
        name="weekly-ml-training",
        version="1.0",
        description="Weekly ML model training and validation",
        schedule=CronSchedule(cron="0 3 * * 0", timezone="UTC"),  # Sunday 3 AM UTC
        work_pool_name="default",
        tags=["ml-training", "weekly", "low-priority"],
        parameters={"train_both_models": False}
    )
    ml_id = ml_training_deployment.apply()
    print(f"[SUCCESS] Created deployment: weekly-ml-training (ID: {ml_id})")

    print("=" * 60)
    print("[COMPLETE] All deployments created successfully!")
    print("")
    print("Deployment Schedule Summary:")
    print("  1. Reference Data Sync:  Every Saturday at 1:00 AM UTC")
    print("  2. Daily Flight Pipeline: Every day at 2:00 AM UTC")
    print("  3. Actuals Update:       Every 4 hours (6 AM - 10 PM UTC)")
    print("  4. ML Training:          Every Sunday at 3:00 AM UTC")
    print("")
    print("To start the scheduler:")
    print("  prefect agent start -q default")


if __name__ == "__main__":
    create_deployments()
