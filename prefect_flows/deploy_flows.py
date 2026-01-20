"""
Prefect Deployment Configuration
This script creates deployments for all flows with their schedules.
Works with both serve() for development and deploy() for production workers.
"""
import sys
import os
from pathlib import Path

# Add prefect_flows to path for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from prefect import serve
from prefect.client.schemas.schedules import CronSchedule

# Import all flows
from reference_data_flow import reference_data_sync_flow
from flight_data_flow import daily_flight_data_flow
from update_actuals_flow import update_flight_actuals_flow
from ml_training_flow import ml_training_flow


def create_deployments_serve():
    """Serve all Prefect flows with their schedules (development mode)"""
    print("[INFO] Serving Prefect flows with schedules (serve mode)...")
    print("=" * 60)

    # Serve all flows together with individual schedules
    serve(
        reference_data_sync_flow.to_deployment(
            name="weekly-reference-sync",
            cron="0 1 * * 6",  # Saturday 1 AM UTC
            tags=["reference-data", "weekly", "low-priority"],
            parameters={"skip_routes": False}
        ),
        daily_flight_data_flow.to_deployment(
            name="daily-flight-pipeline",
            cron="0 2 * * *",  # Daily 2 AM UTC
            tags=["flight-data", "daily", "high-priority"]
        ),
        update_flight_actuals_flow.to_deployment(
            name="hourly-actuals-update",
            cron="0 6,10,14,18,22 * * *",  # Every 4 hours
            tags=["actuals", "periodic", "medium-priority"]
        ),
        ml_training_flow.to_deployment(
            name="weekly-ml-training",
            cron="0 3 * * 0",  # Sunday 3 AM UTC
            tags=["ml-training", "weekly", "low-priority"],
            parameters={"train_both_models": False}
        )
    )


def create_deployments_worker():
    """Create deployments for worker-based execution (production mode)"""
    print("[INFO] Creating Prefect deployments for worker pool...")
    print("=" * 60)

    work_pool_name = os.environ.get("PREFECT_WORK_POOL", "default")

    deployments = []

    # Reference Data Sync - Weekly on Saturday
    print("[1/4] Creating reference-data-sync deployment...")
    ref_deploy = reference_data_sync_flow.deploy(
        name="weekly-reference-sync",
        work_pool_name=work_pool_name,
        cron="0 1 * * 6",  # Saturday 1 AM UTC
        tags=["reference-data", "weekly", "low-priority"],
        parameters={"skip_routes": False},
        description="Weekly sync of reference data (countries, cities, airports, airlines, aircrafts, routes)"
    )
    deployments.append(("Reference Data Sync", ref_deploy))
    print("   ✓ weekly-reference-sync created")

    # Daily Flight Pipeline
    print("[2/4] Creating daily-flight-pipeline deployment...")
    flight_deploy = daily_flight_data_flow.deploy(
        name="daily-flight-pipeline",
        work_pool_name=work_pool_name,
        cron="0 2 * * *",  # Daily 2 AM UTC
        tags=["flight-data", "daily", "high-priority"],
        description="Daily sync of flight schedules and weather enrichment"
    )
    deployments.append(("Daily Flight Pipeline", flight_deploy))
    print("   ✓ daily-flight-pipeline created")

    # Hourly Actuals Update
    print("[3/4] Creating hourly-actuals-update deployment...")
    actuals_deploy = update_flight_actuals_flow.deploy(
        name="hourly-actuals-update",
        work_pool_name=work_pool_name,
        cron="0 6,10,14,18,22 * * *",  # Every 4 hours during the day
        tags=["actuals", "periodic", "medium-priority"],
        description="Update flight actuals (delays, cancellations) from API"
    )
    deployments.append(("Actuals Update", actuals_deploy))
    print("   ✓ hourly-actuals-update created")

    # Weekly ML Training
    print("[4/4] Creating weekly-ml-training deployment...")
    ml_deploy = ml_training_flow.deploy(
        name="weekly-ml-training",
        work_pool_name=work_pool_name,
        cron="0 3 * * 0",  # Sunday 3 AM UTC
        tags=["ml-training", "weekly", "low-priority"],
        parameters={"train_both_models": False},
        description="Weekly ML model training for delay prediction"
    )
    deployments.append(("ML Training", ml_deploy))
    print("   ✓ weekly-ml-training created")

    print("=" * 60)
    print("[SUCCESS] All deployments created!")
    print("")
    print("Deployment Schedule Summary:")
    print("  1. Reference Data Sync:  Every Saturday at 1:00 AM UTC")
    print("  2. Daily Flight Pipeline: Every day at 2:00 AM UTC")
    print("  3. Actuals Update:       6 AM, 10 AM, 2 PM, 6 PM, 10 PM UTC")
    print("  4. ML Training:          Every Sunday at 3:00 AM UTC")
    print("")
    print(f"Work Pool: {work_pool_name}")
    print("")

    return deployments


def run_flow_now(flow_name: str):
    """Run a specific flow immediately"""
    flows = {
        "reference": reference_data_sync_flow,
        "flight": daily_flight_data_flow,
        "actuals": update_flight_actuals_flow,
        "ml": ml_training_flow
    }

    if flow_name not in flows:
        print(f"[ERROR] Unknown flow: {flow_name}")
        print(f"Available flows: {', '.join(flows.keys())}")
        return

    print(f"[INFO] Running {flow_name} flow...")
    flows[flow_name]()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Deploy Prefect flows")
    parser.add_argument(
        "--mode",
        choices=["serve", "deploy", "run"],
        default="deploy",
        help="Mode: 'serve' for development, 'deploy' for worker-based production, 'run' to execute a flow immediately"
    )
    parser.add_argument(
        "--flow",
        choices=["reference", "flight", "actuals", "ml"],
        help="Flow to run (only used with --mode=run)"
    )

    args = parser.parse_args()

    if args.mode == "serve":
        create_deployments_serve()
    elif args.mode == "deploy":
        create_deployments_worker()
    elif args.mode == "run":
        if not args.flow:
            print("[ERROR] --flow is required when using --mode=run")
            sys.exit(1)
        run_flow_now(args.flow)
