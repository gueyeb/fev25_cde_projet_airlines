#!/bin/bash

# DST Airlines - Database Initialization Script
# This script creates all tables in the correct order (handling dependencies)

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration (can be overridden by environment variables)
DB_CONTAINER=${DB_CONTAINER:-postgres_dst}
PG_USER=${PG_USER:-dst_user}
PG_DB=${PG_DB:-dst_airlines}

log_info "=========================================================="
log_info "  DST Airlines - Database Initialization"
log_info "  Container: $DB_CONTAINER"
log_info "  Database:  $PG_DB"
log_info "=========================================================="

# Run the schema initialization SQL file
log_info "Creating database schema..."
# Check if container exists
if ! docker ps | grep -q "$DB_CONTAINER"; then
    log_error "Container $DB_CONTAINER not found or not running."
    exit 1
fi

if docker exec -i "$DB_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" < database/schema_init.sql > /dev/null 2>&1; then
    log_success "Database schema created successfully"
else
    log_error "Failed to create database schema. Check logs."
    exit 1
fi

# Verify tables
log_info "Verifying tables..."
TABLE_COUNT=$(docker exec "$DB_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -t -c "
    SELECT COUNT(*) FROM information_schema.tables
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
" | tr -d ' ')

log_success "Database initialized successfully!"
log_success "Total tables created: $TABLE_COUNT"

log_info "=========================================================="
log_info "Listing all tables:"
docker exec "$DB_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -c "
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    ORDER BY table_name;
"

log_info "=========================================================="
log_success "✅ Database is ready for use!"
log_info "=========================================================="
