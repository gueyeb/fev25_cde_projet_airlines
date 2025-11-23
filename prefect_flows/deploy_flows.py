"""
Prefect Deployment Configuration
This script creates and serves all flows with their schedules using serve()
For local development with Prefect server
"""
from prefect import serve
from prefect.schedules import Cron
import sys
from pathlib import Path

# Import all flows
from reference_data_flow import reference_data_sync_flow
from flight_data_flow import daily_flight_data_flow
from update_actuals_flow import update_flight_actuals_flow
from ml_training_flow import ml_training_flow


def create_deployments():
    """Serve all Prefect flows with their schedules"""

    print("[INFO] Serving Prefect flows with schedules...")
    print("=" * 60)
    print("[INFO] Starting flow server...")

    # Serve all flows together with individual schedules
    serve(
        reference_data_sync_flow.to_deployment(
            name="weekly-reference-sync",
            schedules=[Cron("0 1 * * 6", timezone="UTC")],  # Saturday 1 AM UTC
            tags=["reference-data", "weekly", "low-priority"],
            parameters={"skip_routes": False}
        ),
        daily_flight_data_flow.to_deployment(
            name="daily-flight-pipeline",
            schedules=[Cron("0 2 * * *", timezone="UTC")],  # Daily 2 AM UTC
            tags=["flight-data", "daily", "high-priority"]
        ),
        update_flight_actuals_flow.to_deployment(
            name="hourly-actuals-update",
            schedules=[Cron("0 6,10,14,18,22 * * *", timezone="UTC")],  # Every 4 hours
            tags=["actuals", "periodic", "medium-priority"]
        ),
        ml_training_flow.to_deployment(
            name="weekly-ml-training",
            schedules=[Cron("0 3 * * 0", timezone="UTC")],  # Sunday 3 AM UTC
            tags=["ml-training", "weekly", "low-priority"],
            parameters={"train_both_models": False}
        )
    )

    print("=" * 60)
    print("[COMPLETE] All flows are now being served!")
    print("")
    print("Deployment Schedule Summary:")
    print("  1. Reference Data Sync:  Every Saturday at 1:00 AM UTC")
    print("  2. Daily Flight Pipeline: Every day at 2:00 AM UTC")
    print("  3. Actuals Update:       Every 4 hours (6 AM - 10 PM UTC)")
    print("  4. ML Training:          Every Sunday at 3:00 AM UTC")
    print("")
    print("The flows are now running and will execute on schedule.")
    print("View the dashboard at: http://127.0.0.1:4200")
    print("Press Ctrl+C to stop serving flows.")


if __name__ == "__main__":
    create_deployments()
