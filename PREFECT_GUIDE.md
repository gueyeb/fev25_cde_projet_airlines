# Prefect Workflow Orchestration Guide

## Overview

This project uses **Prefect** for workflow orchestration to manage data pipelines and ML training schedules. Prefect provides:

- **Automated scheduling** - Run pipelines on cron schedules
- **Retry logic** - Automatic retries on failures
- **Monitoring** - Web UI to track pipeline runs
- **Logging** - Centralized logs for all tasks
- **Notifications** - Alerts on failures (configurable)

## Architecture

### Flows Organized by Function

Our pipeline is split into 4 main flows:

1. **Reference Data Flow** (`reference_data_flow.py`)
   - Syncs reference data: countries, cities, airlines, airports, aircrafts, routes
   - Schedule: **Weekly (Saturdays at 1:00 AM UTC)**
   - Why: Reference data rarely changes

2. **Daily Flight Data Flow** (`flight_data_flow.py`)
   - Syncs flight schedules for specific dates
   - Enriches with weather data
   - Schedule: **Daily (2:00 AM UTC)**
   - Why: Lufthansa API provides limited time window for schedules

3. **Update Actuals Flow** (`update_actuals_flow.py`)
   - Updates real-time flight status (delays, actual times)
   - Refreshes weather based on actual times
   - Schedule: **Every 4 hours (6 AM - 10 PM UTC)**
   - Why: Real-time data changes throughout the day

4. **ML Training Flow** (`ml_training_flow.py`)
   - Trains classification model
   - Validates model can be loaded
   - Schedule: **Weekly (Sundays at 3:00 AM UTC)**
   - Why: Model improves as more data accumulates

## Setup

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import prefect; print(f'Prefect {prefect.__version__}')"
```

### Quick Setup

Run the automated setup script:

```bash
./scripts/prefect/setup_prefect.sh
```

This will:
1. Install Prefect
2. Start Prefect server (or connect to Prefect Cloud)
3. Create work pool
4. Create storage blocks
5. Deploy all flows with schedules

### Manual Setup

If you prefer manual setup:

```bash
# 1. Start Prefect server (local development)
prefect server start

# OR connect to Prefect Cloud (production)
prefect cloud login

# 2. Create work pool
prefect work-pool create default --type process

# 3. Create storage block
python -c "from prefect.filesystems import LocalFileSystem; LocalFileSystem(basepath='.').save('local-storage', overwrite=True)"

# 4. Deploy flows
cd prefect_flows
python deploy_flows.py
```

## Running the Pipeline

### Starting the Agent

The agent executes scheduled flow runs:

```bash
# Option 1: Interactive mode
prefect agent start -q default

# Option 2: Background mode with logs
./scripts/prefect/start_agent.sh
```

**Important:** Keep the agent running for scheduled flows to execute!

### Manual Execution

Run flows manually (useful for testing):

```bash
# From project root
cd prefect_flows

# Run reference data sync
python reference_data_flow.py

# Run daily pipeline
python flight_data_flow.py

# Update flight actuals
python update_actuals_flow.py

# Train ML model
python ml_training_flow.py
```

### Triggering Deployments

Run a scheduled deployment on-demand:

```bash
# List all deployments
prefect deployment ls

# Run a specific deployment
prefect deployment run 'daily-flight-data-pipeline/daily-flight-pipeline'

# Run with custom parameters
prefect deployment run 'daily-flight-data-pipeline/daily-flight-pipeline' \
  --param target_date='2025-01-15' \
  --param weather_budget=500
```

## Schedule Summary

| Flow | Schedule | Frequency | Purpose |
|------|----------|-----------|---------|
| Reference Data Sync | Sat 1:00 AM | Weekly | Update rarely-changing data |
| Daily Flight Pipeline | Daily 2:00 AM | Daily | Get new flight schedules |
| Update Actuals | 6AM-10PM every 4h | 5x per day | Real-time flight status |
| ML Training | Sun 3:00 AM | Weekly | Retrain models with new data |

**Note:** All times are in UTC. Adjust for your timezone.

## Monitoring

### Prefect UI

Access the web interface:

- **Local Server:** http://localhost:4200
- **Prefect Cloud:** https://app.prefect.cloud

The UI shows:
- Flow run history
- Success/failure rates
- Execution logs
- Task-level details
- Scheduled runs

### Logs

Prefect writes logs to:
- **Agent logs:** `logs/prefect/agent.log`
- **Server logs:** `logs/prefect-server.log` (local server only)
- **Flow logs:** Visible in Prefect UI

## Common Operations

### Pause a Deployment

```bash
prefect deployment pause 'daily-flight-data-pipeline/daily-flight-pipeline'
```

### Resume a Deployment

```bash
prefect deployment resume 'daily-flight-data-pipeline/daily-flight-pipeline'
```

### Backfill Historical Data

Use the backfill flow to load historical data:

```python
from prefect_flows.flight_data_flow import backfill_flight_data_flow

# Backfill last 30 days
backfill_flight_data_flow(
    start_date="2024-12-01",
    end_date="2024-12-31",
    weather_budget=900
)
```

**Warning:** Be mindful of API rate limits when backfilling!

### Update a Deployment

After modifying a flow:

```bash
cd prefect_flows
python deploy_flows.py  # Re-deploys all flows
```

## Troubleshooting

### Agent Not Picking Up Runs

**Symptoms:** Scheduled runs stay in "Scheduled" state

**Solutions:**
1. Check agent is running: `prefect agent ls`
2. Verify work pool: `prefect work-pool ls`
3. Restart agent: `./scripts/prefect/start_agent.sh`

### Import Errors

**Symptoms:** `ModuleNotFoundError` in flow execution

**Solutions:**
1. Ensure agent is started from project root
2. Check `PYTHONPATH` includes project directory
3. Verify virtual environment is activated

### API Rate Limits

**Symptoms:** HTTP 429 errors from Lufthansa/OpenWeatherMap APIs

**Solutions:**
1. Reduce `weather_budget` parameter
2. Increase retry delay in task decorators
3. Adjust schedule frequency

### Database Connection Errors

**Symptoms:** `psycopg2` connection errors

**Solutions:**
1. Verify database is running
2. Check environment variables in `.prodenv`
3. Ensure agent has access to config files

## Best Practices

### Development Workflow

1. **Test flows locally** before deploying
   ```bash
   python prefect_flows/flight_data_flow.py
   ```

2. **Use small date ranges** for testing
   ```python
   daily_flight_data_flow(target_date="2025-01-15")
   ```

3. **Monitor first few runs** in Prefect UI

### Production Deployment

1. **Use Prefect Cloud** for reliability
2. **Set up notifications** for failures
3. **Monitor API budgets** regularly
4. **Review logs** weekly
5. **Backup database** before large backfills

### Scaling Up

When you need more:

1. **More workers:** Start multiple agents
   ```bash
   prefect agent start -q default --limit 5
   ```

2. **Parallel execution:** Use `ConcurrentTaskRunner` in flows

3. **Remote execution:** Deploy to cloud infrastructure

4. **Advanced features:**
   - Task caching
   - Result persistence
   - Custom blocks
   - Webhooks

## Cost Considerations

### Prefect Cloud Pricing

- **Free tier:** 20,000 task runs/month (sufficient for most cases)
- **Paid tier:** $10/month for 100,000 task runs
- **Enterprise:** Custom pricing

### Our Usage Estimate

With current schedule:
- Daily pipeline: ~10 tasks/day × 30 = 300 tasks/month
- Actuals update: ~5 tasks/day × 5 × 30 = 750 tasks/month
- Reference sync: ~10 tasks/week × 4 = 40 tasks/month
- ML training: ~5 tasks/week × 4 = 20 tasks/month

**Total: ~1,110 tasks/month** (well within free tier)

## Next Steps

1. **Run setup:** `./scripts/prefect/setup_prefect.sh`
2. **Start agent:** `./scripts/prefect/start_agent.sh`
3. **Monitor UI:** http://localhost:4200
4. **Wait for first scheduled run** or trigger manually
5. **Check logs** to verify success

## Additional Resources

- [Prefect Documentation](https://docs.prefect.io)
- [Prefect Community Slack](https://prefect.io/slack)
- [Prefect GitHub](https://github.com/PrefectHQ/prefect)
- [Our Workflow Guide](WORKFLOW_ORCHESTRATION.md)

## Support

If you encounter issues:

1. Check Prefect UI for error details
2. Review agent logs: `tail -f logs/prefect/agent.log`
3. Search Prefect docs
4. Ask in Prefect Community Slack
5. File an issue in project repository
