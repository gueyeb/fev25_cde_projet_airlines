# DST Airlines - Supabase Setup Guide

## Overview

A self-hosted Supabase instance was set up for the DST Airlines project, providing PostgreSQL database with additional features like REST API, real-time subscriptions, and storage.

**⚠️ Note (2026-08): this project's containers have been shut down. The credentials below were redacted after this repo went public — they are no longer valid for a running instance. If this environment is ever revived, generate fresh credentials rather than reusing anything that was previously documented here.**

## Access Information

### Supabase Studio (Web Interface)
- **URL**: https://dst-airlines-studio.srv869578.hstgr.cloud
- **Username**: `supabase`
- **Password**: `<REDACTED>`

The Studio provides a web interface for:
- Database management (tables, views, functions)
- SQL editor
- API documentation
- Real-time logs
- Storage file browser

### API Endpoints
- **REST API**: https://dst-airlines-api.srv869578.hstgr.cloud/rest/v1
- **Auth API**: https://dst-airlines-api.srv869578.hstgr.cloud/auth/v1
- **Storage API**: https://dst-airlines-api.srv869578.hstgr.cloud/storage/v1
- **Realtime**: wss://dst-airlines-api.srv869578.hstgr.cloud/realtime/v1

## Database Connection

### Direct PostgreSQL Connection (Recommended for external tools)
```
Host: srv869578.hstgr.cloud
Port: 5435
Database: postgres
User: postgres
Password: <REDACTED>
```

**Connection String**:
```
postgresql://postgres:<REDACTED>@srv869578.hstgr.cloud:5435/postgres
```

### Pooled Connection (via Supavisor) - Internal use only
For internal services within Docker network:
```
Host: srv869578.hstgr.cloud
Port: 5433 (session mode) or 6544 (transaction mode)
User: postgres.dst-airlines-tenant
Password: <REDACTED>
```

**Note**: Pooled connections require the tenant ID suffix in the username.

## API Keys

### Anonymous Key (Public)
For client-side applications:
```
<REDACTED>
```

### Service Role Key (Secret)
For server-side applications (has admin privileges):
```
<REDACTED>
```

**⚠️ Warning**: Never expose the Service Role Key in client-side code!

## Connecting from Your Application

### Python (using psycopg2)
```python
import psycopg2

conn = psycopg2.connect(
host="srv869578.hstgr.cloud",
port=5435,
database="postgres",
user="postgres",
password="<REDACTED>"
)
```

### Python (using Supabase Client)
```python
from supabase import create_client, Client

url = "https://dst-airlines-api.srv869578.hstgr.cloud"
key = "<REDACTED>"
supabase: Client = create_client(url, key)

# Query data
response = supabase.table('your_table').select('*').execute()
```

### Update Existing Project Configuration

Update your `/srv/fev25_cde_projet_airlines/config/.env` file:

```bash
# PostgreSQL (Supabase)
PG_HOST=srv869578.hstgr.cloud
PG_PORT=5435
PG_DB=postgres
PG_USER=postgres
PG_PASSWORD=<REDACTED>

# Supabase API (optional - for using Supabase client features)
SUPABASE_URL=https://dst-airlines-api.srv869578.hstgr.cloud
SUPABASE_KEY=<REDACTED>
```

## Database Schema Migration

To migrate your existing database schema to Supabase:

```bash
cd /srv/fev25_cde_projet_airlines

# Execute the migration SQL
psql -h srv869578.hstgr.cloud -p 5435 -U postgres -d postgres -f database/migrations/1_create_tables.sql
```

## Managing the Supabase Instance

### Start all services
```bash
cd /srv/fev25_cde_projet_airlines/supabase
docker compose up -d
```

### Stop all services
```bash
cd /srv/fev25_cde_projet_airlines/supabase
docker compose down
```

### View logs
```bash
cd /srv/fev25_cde_projet_airlines/supabase
docker compose logs -f [service_name]
```

Available services:
- `db` - PostgreSQL database
- `studio` - Supabase Studio UI
- `kong` - API Gateway
- `rest` - PostgREST (auto-generated REST API)
- `realtime` - Real-time subscriptions
- `storage` - File storage
- `analytics` - Logs and analytics
- `pooler` - Connection pooler
- `meta` - Database metadata service

### Check service status
```bash
docker ps --filter "name=dst-airlines-supabase"
```

## Services Status

This instance has been shut down (containers stopped) since the project concluded.

## Features Available

### 1. REST API
Automatically generated REST API for all your database tables:
```bash
# Get all records from a table
curl -X GET 'https://dst-airlines-api.srv869578.hstgr.cloud/rest/v1/airlines' \
-H "apikey: YOUR_ANON_KEY" \
-H "Authorization: Bearer YOUR_ANON_KEY"
```

### 2. Real-time Subscriptions
Subscribe to database changes in real-time (useful for live updates).

### 3. File Storage
Store and serve files (images, documents, etc.) with built-in CDN and image transformations.

### 4. Database Management
Use Supabase Studio to:
- Create and modify tables
- Run SQL queries
- View database schema
- Manage users and permissions
- Monitor API usage

## Security Best Practices

1. **Never commit credentials to Git** - The `.env` file should be in `.gitignore`
2. **Use connection pooling** (port 6544) for production applications
3. **Use Row Level Security (RLS)** policies to secure your data
4. **Rotate keys periodically** - Can be done by updating JWT_SECRET and regenerating keys
5. **Use the anon key** for client-side apps, service key only for server-side

## Backup and Maintenance

### Manual Backup
```bash
# Create backup
pg_dump -h srv869578.hstgr.cloud -p 5435 -U postgres -d postgres > backup_$(date +%Y%m%d).sql

# Restore from backup
psql -h srv869578.hstgr.cloud -p 5435 -U postgres -d postgres < backup_20251123.sql
```

### Automated Backups
Consider setting up a cron job for regular backups:
```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /path/to/backup_script.sh
```

## Troubleshooting

### Connection Issues
```bash
# Test database connection
psql -h srv869578.hstgr.cloud -p 5435 -U postgres -d postgres -c "SELECT version();"

# Check if services are running
docker ps --filter "name=dst-airlines-supabase"

# View service logs
docker logs dst-airlines-supabase-db
```

### Restart Services
```bash
cd /srv/fev25_cde_projet_airlines/supabase
docker compose restart [service_name]
```

## Support

For issues or questions about:
- **Supabase features**: https://supabase.com/docs
- **PostgreSQL**: https://www.postgresql.org/docs/
- **PostgREST API**: https://postgrest.org/en/stable/

## Next Steps

This project has concluded; the instance is offline. These steps are kept for reference only.

1. Access Supabase Studio and verify the connection
2. Run the database migration script to create your tables
3. Update your application's `.env` file with the new connection details
4. Test the connection from your application
5. Share the Studio credentials with your colleagues via a password manager (never via this file)

---

**Created**: November 23, 2025
**Location**: `/srv/fev25_cde_projet_airlines/supabase/`
**Configuration**: `/srv/fev25_cde_projet_airlines/supabase/.env`
