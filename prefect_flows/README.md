# Prefect Flows

This directory contains all Prefect workflow definitions for the Flight Delay Prediction project.

## Quick Start

```bash
# 1. Set up Prefect
./scripts/prefect/setup_prefect.sh

# 2. Start the agent
./scripts/prefect/start_agent.sh
```

## Flow Files

### Production Flows

- **`reference_data_flow.py`** - Weekly sync of reference data (countries, cities, airlines, airports, routes)
- **`flight_data_flow.py`** - Daily sync of flight schedules + weather enrichment
- **`update_actuals_flow.py`** - Periodic updates of real-time flight status
- **`ml_training_flow.py`** - Weekly ML model training

### Configuration

- **`deploy_flows.py`** - Deployment script that registers all flows with schedules

## Flow Organization

```
prefect_flows/
├── reference_data_flow.py    # Weekly: Reference data
├── flight_data_flow.py        # Daily: Flight schedules + weather
├── update_actuals_flow.py     # Every 4h: Real-time updates
├── ml_training_flow.py        # Weekly: Model training
└── deploy_flows.py            # Deployment configuration
```

## Running Flows

### Test Locally (Without Prefect)

```bash
# Test individual flows
python reference_data_flow.py
python flight_data_flow.py
python update_actuals_flow.py
python ml_training_flow.py
```

### Run via Prefect (With Scheduling)

```bash
# Deploy all flows
python deploy_flows.py

# Start agent to execute scheduled runs
prefect agent start -q default

# Trigger a deployment manually
prefect deployment run 'daily-flight-data-pipeline/daily-flight-pipeline'
```

## Schedule Summary

| Flow | Deployment Name | Schedule | Description |
|------|----------------|----------|-------------|
| Reference Data | `weekly-reference-sync` | Sat 1:00 AM | Sync countries, cities, airlines, airports, routes |
| Daily Flight | `daily-flight-pipeline` | Daily 2:00 AM | Sync flight schedules + weather |
| Update Actuals | `hourly-actuals-update` | Every 4h (6-22) | Update real-time flight status |
| ML Training | `weekly-ml-training` | Sun 3:00 AM | Train ML models |

All times are UTC.

## Parameters

### daily_flight_data_flow

- `target_date` (str): Date in YYYY-MM-DD format (default: today)
- `weather_budget` (int): OpenWeatherMap API call budget (default: 900)

### ml_training_flow

- `train_both_models` (bool): Train both classification and regression (default: False)

### reference_data_sync_flow

- `skip_routes` (bool): Skip route creation (default: False)

## Monitoring

- **Prefect UI:** http://localhost:4200 (local) or https://app.prefect.cloud
- **Logs:** `logs/prefect/`
- **Agent status:** `prefect agent ls`
- **Deployment status:** `prefect deployment ls`

## Development

### Adding a New Flow

1. Create a new file: `my_new_flow.py`
2. Define tasks with `@task` decorator
3. Define flow with `@flow` decorator
4. Add deployment in `deploy_flows.py`
5. Re-run deployment script

Example:

```python
from prefect import flow, task

@task(retries=2, log_prints=True)
def my_task():
    print("[INFO] Running my task")
    # Your code here

@flow(name="my-flow", log_prints=True)
def my_flow():
    print("[FLOW START] My Flow")
    my_task()
    print("[FLOW COMPLETE]")
```

### Modifying Existing Flows

1. Edit the flow file
2. Test locally: `python <flow_file>.py`
3. Re-deploy: `python deploy_flows.py`
4. Restart agent if needed

## Best Practices

1. **Always use `log_prints=True`** in decorators for visibility
2. **Add retries** to tasks that call external APIs
3. **Set timeouts** for long-running tasks
4. **Use descriptive names** for tasks and flows
5. **Document parameters** in docstrings
6. **Test locally** before deploying

## Troubleshooting

### Import Errors

Make sure to add project root to path:

```python
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
```

### Database Connection

Ensure environment variables are loaded:

```bash
# Check if .prodenv exists
ls -la config/.prodenv

# Load manually if needed
source config/.prodenv
```

### API Rate Limits

If hitting rate limits:
- Increase `retry_delay_seconds` in task decorators
- Reduce `weather_budget` parameter
- Adjust schedule frequency

## Full Documentation

See [PREFECT_GUIDE.md](../PREFECT_GUIDE.md) for complete documentation.
