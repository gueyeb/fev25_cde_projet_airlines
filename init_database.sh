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

log_info "=========================================================="
log_info "  DST Airlines - Database Initialization"
log_info "=========================================================="

# Run the schema initialization SQL file
log_info "Creating database schema..."
if docker exec -i dst-airlines-supabase-db psql -U postgres -d postgres < database/schema_init.sql > /dev/null 2>&1; then
    log_success "Database schema created successfully"
else
    log_error "Failed to create database schema"
    exit 1
fi

# Verify tables
log_info "Verifying tables..."
TABLE_COUNT=$(docker exec dst-airlines-supabase-db psql -U postgres -d postgres -t -c "
    SELECT COUNT(*) FROM information_schema.tables
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
" | tr -d ' ')

log_success "Database initialized successfully!"
log_success "Total tables created: $TABLE_COUNT"

log_info "=========================================================="
log_info "Listing all tables:"
docker exec dst-airlines-supabase-db psql -U postgres -d postgres -c "
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    ORDER BY table_name;
"

log_info "=========================================================="
log_success "✅ Database is ready for use!"
log_info "=========================================================="
