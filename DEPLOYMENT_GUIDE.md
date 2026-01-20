# DST Airlines - Deployment Guide

## Deployment Summary

Your DST Airlines project has been successfully deployed with Prefect server integration! The deployment uses your existing Supabase database without requiring local PostgreSQL or MongoDB containers.

## Architecture Overview

### Services Deployed

1. **Prefect Server** (Workflow Orchestration)
   - Container: `dst-airlines-prefect-server`
   - Port: 4201
   - Database: SQLite (local to container)
   - Status: Running ✓

2. **Prefect Worker** (Workflow Execution)
   - Container: `dst-airlines-prefect-agent`
   - Work Pool: `default`
   - Status: Running ✓

3. **FastAPI Web Application** (Flight Delay Predictor)
   - Container: `dst-airlines-web`
   - Port: 8001
   - Status: Running ✓

### Database Configuration

- **Application Database**: Supabase PostgreSQL (external, no local container)
  - Host: `host.docker.internal:5433`
  - Database: `postgres`
  - Connection: Direct from containers via `host.docker.internal`

- **Prefect Metadata**: SQLite (embedded in Prefect server container)
  - Path: `/root/.prefect/prefect.db`
  - Volume: `dst-airlines_prefect_data`

## Access URLs

### Local Access

- **Prefect UI**: http://localhost:4201
- **Web Application**: http://localhost:8001
- **Prefect API**: http://localhost:4201/api
- **Web App API Docs**: http://localhost:8001/docs

### Public Access (via Traefik) ✅ ACTIVE

- **Prefect UI**: https://dst-prefect.srv869578.hstgr.cloud ✅
- **Web Application**: https://dst-airlines.srv869578.hstgr.cloud ✅
- **Web App API Docs**: https://dst-airlines.srv869578.hstgr.cloud/docs
- **Supabase Studio**: https://dst-airlines-studio.srv869578.hstgr.cloud
- **Supabase API**: https://dst-airlines-api.srv869578.hstgr.cloud

## Deployment Commands

### Using the Deployment Script

The project includes a convenient deployment script at `/srv/fev25_cde_projet_airlines/deploy-dst-airlines.sh` with the following commands:

```bash
cd /srv/fev25_cde_projet_airlines

# Start all services
./deploy-dst-airlines.sh start

# Stop all services
./deploy-dst-airlines.sh stop

# Restart all services
./deploy-dst-airlines.sh restart

# View logs from all services
./deploy-dst-airlines.sh logs

# View logs from API only
./deploy-dst-airlines.sh logs-api

# View logs from Prefect services only
./deploy-dst-airlines.sh logs-prefect

# Check service status
./deploy-dst-airlines.sh status

# Check health of all services
./deploy-dst-airlines.sh health

# Deploy Prefect workflows
./deploy-dst-airlines.sh deploy-flows

# Rebuild and restart services
./deploy-dst-airlines.sh rebuild

# Clean up (remove containers and volumes)
./deploy-dst-airlines.sh clean
```

### Manual Docker Compose Commands

```bash
cd /srv/fev25_cde_projet_airlines

# Start services
docker compose -f docker-compose.supabase.yml -p dst-airlines up -d

# Stop services
docker compose -f docker-compose.supabase.yml -p dst-airlines down

# View logs
docker compose -f docker-compose.supabase.yml -p dst-airlines logs -f

# Check status
docker compose -f docker-compose.supabase.yml -p dst-airlines ps
```

## Configuration Files

### Main Configuration

- **Docker Compose**: `/srv/fev25_cde_projet_airlines/docker-compose.supabase.yml`
- **Environment File**: `/srv/fev25_cde_projet_airlines/config/.env`
- **Deployment Script**: `/srv/fev25_cde_projet_airlines/deploy-dst-airlines.sh`

### Environment Variables

The `.env` file contains:
- PostgreSQL/Supabase connection details
- API keys (Lufthansa, OpenWeatherMap)
- Supabase API keys
- Application configuration

**Important**: Make sure to update the following API keys in `config/.env`:
```bash
LH_CLIENT_ID=your_lufthansa_client_id_here
LH_CLIENT_SECRET=your_lufthansa_client_secret_here
OWM_API_KEY=your_openweathermap_api_key_here
```

## Next Steps

### 1. Configure API Keys

Before running workflows, update your API keys in `/srv/fev25_cde_projet_airlines/config/.env`:

```bash
# Edit the file
nano /srv/fev25_cde_projet_airlines/config/.env

# Or use vi
vi /srv/fev25_cde_projet_airlines/config/.env
```

### 2. Initialize Database Schema

Run the database migrations to create the required tables:

```bash
cd /srv/fev25_cde_projet_airlines

# Connect to Supabase database and run migrations
docker exec dst-airlines-supabase-db psql -U postgres -d postgres -f /docker-entrypoint-initdb.d/1_create_tables.sql

# Or from the host (if you have psql installed)
PGPASSWORD=d0e6de882220c43de3d3ef5abf0c31c7c87145f936918938e9a6120458e94977 \
psql -h localhost -p 5433 -U postgres -d postgres \
-f database/migrations/1_create_tables.sql
```

### 3. Deploy Prefect Workflows

Deploy the Prefect workflows to start monitoring flows:

```bash
./deploy-dst-airlines.sh deploy-flows
```

This will deploy:
- **Reference Data Flow** - Weekly sync of static reference data (Saturdays 1:00 AM UTC)
- **Daily Flight Data Flow** - Daily flight schedules + weather (Daily 2:00 AM UTC)
- **Update Actuals Flow** - Real-time flight status updates (Every 4h from 6AM-10PM UTC)
- **ML Training Flow** - Retrain prediction models (Sundays 3:00 AM UTC)

### 4. Run Initial Data Load (Optional)

To populate your database with initial data:

```bash
# Enter the prefect-agent container
docker exec -it dst-airlines-prefect-agent bash

# Run initial data sync jobs
python -m src.jobs.sync_countries
python -m src.jobs.sync_cities
python -m src.jobs.sync_airlines
python -m src.jobs.sync_airports
python -m src.jobs.sync_aircrafts
python -m src.jobs.create_routes

# Exit container
exit
```

### 5. Train Machine Learning Models

After populating data, train the ML models:

```bash
docker exec -it dst-airlines-prefect-agent bash

# Run ML training
python -m src.ml.ml_classification
python -m src.ml.ml_regression

exit
```

### 6. Monitor Workflows

Access the Prefect UI at http://localhost:4201 to:
- View deployed workflows
- Monitor flow runs
- Check logs and execution history
- Trigger manual workflow runs

### 7. Access the Web Application

Visit http://localhost:8001 to:
- Use the flight delay prediction interface
- View API documentation at http://localhost:8001/docs
- Access reference data endpoints

## Troubleshooting

### Services Not Starting

Check logs:
```bash
./deploy-dst-airlines.sh logs
```

Check specific service:
```bash
docker logs dst-airlines-prefect-server
docker logs dst-airlines-prefect-agent
docker logs dst-airlines-web
```

### Health Check Issues

The Prefect server may show as "unhealthy" in Docker status but is actually working. Test manually:
```bash
curl http://localhost:4201/api/health
```

Should return: `true`

### Database Connection Issues

Verify Supabase database is running:
```bash
docker ps | grep supabase-db
```

Test connection from container:
```bash
docker exec dst-airlines-prefect-agent \
  python -c "import psycopg2; conn = psycopg2.connect('postgresql://postgres:d0e6de882220c43de3d3ef5abf0c31c7c87145f936918938e9a6120458e94977@host.docker.internal:5433/postgres'); print('Connected!')"
```

### Prefect Worker Issues

Check worker status:
```bash
docker logs dst-airlines-prefect-agent --tail 50
```

Worker should show:
```
Worker 'ProcessWorker <uuid>' started!
```

### Web App Module Errors

If you see "ModuleNotFoundError" for `src` or `config`:
- Ensure volume mounts are correct in `docker-compose.supabase.yml`
- Recreate the container: `./deploy-dst-airlines.sh rebuild`

## Monitoring and Maintenance

### View Running Services

```bash
./deploy-dst-airlines.sh status
```

### Check System Resources

```bash
docker stats dst-airlines-prefect-server dst-airlines-prefect-agent dst-airlines-web
```

### Backup Prefect Metadata

```bash
# Backup Prefect SQLite database
docker cp dst-airlines-prefect-server:/root/.prefect/prefect.db ./backups/prefect-$(date +%Y%m%d).db
```

### Update Services

```bash
# Pull latest code
cd /srv/fev25_cde_projet_airlines
git pull  # if using git

# Rebuild and restart
./deploy-dst-airlines.sh rebuild
```

## Architecture Decisions

### Why SQLite for Prefect?

- **Simplicity**: No additional database container needed
- **Performance**: Sufficient for single-server deployment
- **Persistence**: Data stored in Docker volume
- **Reliability**: No network dependencies for Prefect metadata

If you need to scale to multiple Prefect servers, you can switch to PostgreSQL by:
1. Creating a dedicated database for Prefect in Supabase
2. Updating `PREFECT_API_DATABASE_CONNECTION_URL` in docker-compose
3. Redeploying the services

### Why host.docker.internal?

Containers need to access the Supabase database running on the host machine. The `host.docker.internal` hostname (with `extra_hosts` configuration) allows containers to reach host services without hardcoding IP addresses.

### Volume Mounts

The web application uses volume mounts for:
- `/app/src` - Project source code
- `/app/config` - Configuration files
- `/app/database` - Database migration scripts

This allows code updates without rebuilding the container.

## Security Notes

1. **API Keys**: The `.env` file contains sensitive credentials. Ensure it's not committed to version control.

2. **Database Passwords**: Production deployments should use strong, unique passwords.

3. **Traefik SSL**: Public URLs use Let's Encrypt SSL certificates via Traefik.

4. **Supabase Access**:
   - Studio: https://dst-airlines-studio.srv869578.hstgr.cloud
   - Username: `supabase`
   - Password: `DSTAirlines2025!Secure`

## Support and Documentation

- **Prefect Documentation**: https://docs.prefect.io/
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **Supabase Documentation**: https://supabase.com/docs
- **Project README**: `/srv/fev25_cde_projet_airlines/README.md`
- **Prefect Guide**: `/srv/fev25_cde_projet_airlines/PREFECT_GUIDE.md`

## Summary

✅ **Deployment Status**: Successfully deployed!

**Services Running**:
- Prefect Server (Workflow Orchestration)
- Prefect Worker (Workflow Execution)
- FastAPI Web Application (Flight Delay Predictor)

**Database**:
- Connected to Supabase PostgreSQL (no local postgres/mongo containers)

**Next Actions**:
1. Update API keys in `config/.env`
2. Initialize database schema
3. Deploy Prefect workflows
4. Load initial reference data
5. Train ML models
6. Access Prefect UI and start monitoring!

---

**Deployment Completed**: 2025-11-24
