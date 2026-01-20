# DST Airlines - Flow Testing & Execution Guide

## Quick Start

### Available Flows

1. **reference_data_sync_flow** - Syncs countries, cities, airlines, airports, aircraft, routes
2. **daily_flight_data_flow** - Fetches flight schedules and weather data
3. **update_flight_actuals_flow** - Updates flight status and actuals
4. **ml_training_flow** - Trains machine learning models

---

## Method 1: Interactive Test Script (Easiest)

```bash
cd /srv/fev25_cde_projet_airlines
./test_flow.sh
```

Choose a flow number (1-4) and it will execute immediately!

---

## Method 2: Direct Python Execution

### Test Reference Data Flow
```bash
docker exec dst-airlines-prefect-agent python -c "
import sys
sys.path.insert(0, '/app/prefect_flows')
from reference_data_flow import reference_data_sync_flow
reference_data_sync_flow(skip_routes=True)
"
```

### Test Flight Data Flow
```bash
docker exec dst-airlines-prefect-agent python -c "
import sys
sys.path.insert(0, '/app/prefect_flows')
from flight_data_flow import daily_flight_data_flow
daily_flight_data_flow()
"
```

### Test Update Actuals Flow
```bash
docker exec dst-airlines-prefect-agent python -c "
import sys
sys.path.insert(0, '/app/prefect_flows')
from update_actuals_flow import update_flight_actuals_flow
update_flight_actuals_flow()
"
```

### Test ML Training Flow
```bash
docker exec dst-airlines-prefect-agent python -c "
import sys
sys.path.insert(0, '/app/prefect_flows')
from ml_training_flow import ml_training_flow
ml_training_flow(train_both_models=True)
"
```

---

## Method 3: Prefect UI (After Deployment)

### Step 1: Deploy Flows
```bash
./deploy-dst-airlines.sh deploy-flows
```

### Step 2: Access Prefect UI
- URL: https://dst-prefect.srv869578.hstgr.cloud
- Local: http://localhost:4201

### Step 3: Run Flow
1. Click **"Deployments"** in left sidebar
2. Select a deployment (e.g., "weekly-reference-sync")
3. Click **"Run"** button (top right)
4. Optionally add parameters
5. Click **"Run"** to execute
6. View progress in **"Flow Runs"** page

---

## Method 4: Prefect CLI

### List All Deployments
```bash
docker exec dst-airlines-prefect-agent prefect deployment ls
```

### Run a Deployment
```bash
# Reference data sync
docker exec dst-airlines-prefect-agent \
  prefect deployment run 'reference_data_sync_flow/weekly-reference-sync'

# Flight data sync
docker exec dst-airlines-prefect-agent \
  prefect deployment run 'daily_flight_data_flow/daily-flight-pipeline'

# Update actuals
docker exec dst-airlines-prefect-agent \
  prefect deployment run 'update_flight_actuals_flow/hourly-actuals-update'

# ML training
docker exec dst-airlines-prefect-agent \
  prefect deployment run 'ml_training_flow/weekly-ml-training'
```

### Run with Parameters
```bash
docker exec dst-airlines-prefect-agent \
  prefect deployment run 'reference_data_sync_flow/weekly-reference-sync' \
  --param skip_routes=true
```

### Check Flow Runs
```bash
# List all flow runs
docker exec dst-airlines-prefect-agent prefect flow-run ls

# List recent flow runs
docker exec dst-airlines-prefect-agent prefect flow-run ls --limit 10

# Get details of specific run
docker exec dst-airlines-prefect-agent prefect flow-run inspect <flow-run-id>
```

---

## Monitoring & Logs

### Watch Live Logs
```bash
# Follow all Prefect agent logs
docker logs -f dst-airlines-prefect-agent

# Follow with timestamp
docker logs -f --timestamps dst-airlines-prefect-agent

# Last 100 lines
docker logs --tail 100 dst-airlines-prefect-agent
```

### Check Flow Execution
```bash
# View deployment status
docker exec dst-airlines-prefect-agent prefect deployment ls

# View work pool
docker exec dst-airlines-prefect-agent prefect work-pool ls

# View worker status
docker exec dst-airlines-prefect-agent prefect worker ls
```

---

## Testing Individual Jobs (Without Prefect)

If you want to test the underlying Python jobs directly:

### Sync Countries
```bash
docker exec dst-airlines-prefect-agent python -m src.jobs.sync_countries
```

### Sync Cities
```bash
docker exec dst-airlines-prefect-agent python -m src.jobs.sync_cities
```

### Sync Airlines
```bash
docker exec dst-airlines-prefect-agent python -m src.jobs.sync_airlines
```

### Sync Airports
```bash
docker exec dst-airlines-prefect-agent python -m src.jobs.sync_airports
```

### Sync Aircraft
```bash
docker exec dst-airlines-prefect-agent python -m src.jobs.sync_aircrafts
```

### Create Routes
```bash
docker exec dst-airlines-prefect-agent python -m src.jobs.create_routes
```

### Train ML Models
```bash
# Classification model
docker exec dst-airlines-prefect-agent python -m src.ml.ml_classification

# Regression model
docker exec dst-airlines-prefect-agent python -m src.ml.ml_regression
```

---

## Scheduled Execution

Once deployed with `./deploy-dst-airlines.sh deploy-flows`, flows will run automatically:

| Flow | Schedule | Frequency |
|------|----------|-----------|
| Reference Data Sync | Saturdays 1:00 AM UTC | Weekly |
| Daily Flight Pipeline | Daily 2:00 AM UTC | Daily |
| Actuals Update | 6AM, 10AM, 2PM, 6PM, 10PM UTC | 5x daily |
| ML Training | Sundays 3:00 AM UTC | Weekly |

---

## Troubleshooting

### Flow Not Found
```bash
# Check if flow file exists
docker exec dst-airlines-prefect-agent ls -la /app/prefect_flows/

# Check Python path
docker exec dst-airlines-prefect-agent python -c "import sys; print('\n'.join(sys.path))"
```

### Import Errors
```bash
# Test imports
docker exec dst-airlines-prefect-agent python -c "
import sys
sys.path.insert(0, '/app/prefect_flows')
from reference_data_flow import reference_data_sync_flow
print('✅ Import successful!')
"
```

### Database Connection Issues
```bash
# Test database connection
docker exec dst-airlines-prefect-agent python -c "
from config.env_loader import load_env
load_env()
import psycopg2, os
conn = psycopg2.connect(
    host=os.getenv('PG_HOST'),
    port=os.getenv('PG_PORT'),
    database=os.getenv('PG_DB'),
    user=os.getenv('PG_USER'),
    password=os.getenv('PG_PASSWORD')
)
print('✅ Database connection successful!')
conn.close()
"
```

### Check API Keys
```bash
docker exec dst-airlines-prefect-agent python -c "
from config.env_loader import load_env
load_env()
import os
print(f'Lufthansa Client ID: {os.getenv(\"LH_CLIENT_ID\")}')
print(f'OpenWeatherMap Key: {os.getenv(\"OWM_API_KEY\")[:10]}...')
"
```

---

## Quick Reference Commands

```bash
# Deploy flows
./deploy-dst-airlines.sh deploy-flows

# Test a flow interactively
./test_flow.sh

# View Prefect UI
open https://dst-prefect.srv869578.hstgr.cloud

# Check service status
./deploy-dst-airlines.sh status

# View logs
./deploy-dst-airlines.sh logs-prefect

# Restart services
./deploy-dst-airlines.sh restart
```

---

## Example: Complete First-Time Setup

```bash
# 1. Ensure services are running
./deploy-dst-airlines.sh status

# 2. Test database connection
docker exec dst-airlines-prefect-agent python -c "
from config.env_loader import load_env
load_env()
import psycopg2, os
conn = psycopg2.connect(host=os.getenv('PG_HOST'), port=os.getenv('PG_PORT'),
                       database=os.getenv('PG_DB'), user=os.getenv('PG_USER'),
                       password=os.getenv('PG_PASSWORD'))
print('✅ Connected!'); conn.close()
"

# 3. Run initial data load (test with one flow first)
./test_flow.sh
# Choose option 1 (Reference Data Flow)

# 4. Check Prefect UI
open https://dst-prefect.srv869578.hstgr.cloud

# 5. Deploy all flows for scheduled execution
./deploy-dst-airlines.sh deploy-flows

# 6. Monitor logs
docker logs -f dst-airlines-prefect-agent
```

---

**Need Help?**
- Check logs: `docker logs dst-airlines-prefect-agent`
- View deployment guide: `/srv/fev25_cde_projet_airlines/DEPLOYMENT_GUIDE.md`
- Access Prefect UI: https://dst-prefect.srv869578.hstgr.cloud
