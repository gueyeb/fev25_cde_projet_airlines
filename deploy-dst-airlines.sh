#!/bin/bash

###############################################################################
# DST Airlines Deployment Script
#
# Supports two modes:
#   - Production: VPS with external Supabase (docker-compose.supabase.yml)
#   - Local: Laptop testing with local PostgreSQL (docker-compose.local.yml)
#
# Usage:
#   ./deploy-dst-airlines.sh [command]
#
# Production:  start, stop, restart, rebuild, clean, deploy-flows, health
# Local:       start-local, stop-local, rebuild-local, clean-local
# Common:      logs, status, help
###############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.supabase.yml"
COMPOSE_FILE_LOCAL="docker-compose.local.yml"
PROJECT_NAME="dst-airlines"
PROJECT_NAME_LOCAL="dst-airlines-local"

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if docker-compose is installed
check_dependencies() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
}

# Check if .env file exists
check_env_file() {
    if [ ! -f "config/.env" ]; then
        log_warning ".env file not found in config/ directory"
        log_info "Creating .env file from .env.example..."

        if [ -f "config/.env.example" ]; then
            cp config/.env.example config/.env
            log_warning "Please update config/.env with your API keys before starting services"
            log_warning "Required: LH_CLIENT_ID, LH_CLIENT_SECRET, OWM_API_KEY"
            exit 1
        else
            log_error ".env.example not found. Cannot create .env file."
            exit 1
        fi
    fi
}

# Start services
start_services() {
    log_info "Starting DST Airlines services..."
    docker compose -f $COMPOSE_FILE -p $PROJECT_NAME up -d
    log_success "Services started successfully!"
    log_info "Access URLs:"
    log_info "  - Prefect UI: https://dst-prefect.srv869578.hstgr.cloud or http://localhost:4201"
    log_info "  - Web App: https://dst-airlines.srv869578.hstgr.cloud or http://localhost:8001"
    log_info "  - Supabase Studio: https://dst-airlines-studio.srv869578.hstgr.cloud"
}

# Stop services
stop_services() {
    log_info "Stopping DST Airlines services..."
    docker compose -f $COMPOSE_FILE -p $PROJECT_NAME down
    log_success "Services stopped successfully!"
}

# Restart services
restart_services() {
    log_info "Restarting DST Airlines services..."
    docker compose -f $COMPOSE_FILE -p $PROJECT_NAME restart
    log_success "Services restarted successfully!"
}

# Show logs
show_logs() {
    log_info "Following logs from all services (Ctrl+C to exit)..."
    docker compose -f $COMPOSE_FILE -p $PROJECT_NAME logs -f
}

# Show API logs
show_api_logs() {
    log_info "Following logs from API service (Ctrl+C to exit)..."
    docker compose -f $COMPOSE_FILE -p $PROJECT_NAME logs -f web-app
}

# Show Prefect logs
show_prefect_logs() {
    log_info "Following logs from Prefect services (Ctrl+C to exit)..."
    docker compose -f $COMPOSE_FILE -p $PROJECT_NAME logs -f prefect-server prefect-agent
}

# Show status
show_status() {
    log_info "DST Airlines services status:"
    docker compose -f $COMPOSE_FILE -p $PROJECT_NAME ps
}

# Deploy Prefect flows
deploy_flows() {
    log_info "Deploying Prefect workflows..."

    # Wait for Prefect server to be ready
    log_info "Waiting for Prefect server to be ready..."
    sleep 10

    # Deploy flows using the agent container
    docker compose -f $COMPOSE_FILE -p $PROJECT_NAME exec -T prefect-agent \
        python -m prefect_flows.deploy_flows

    log_success "Prefect workflows deployed successfully!"
    log_info "View deployments at: https://dst-prefect.srv869578.hstgr.cloud"
}

# Check health
check_health() {
    log_info "Checking health of services..."

    # Check Prefect Server
    if curl -sf http://localhost:4201/api/health > /dev/null 2>&1; then
        log_success "Prefect Server is healthy"
    else
        log_error "Prefect Server is not responding"
    fi

    # Check Web App
    if curl -sf http://localhost:8001/api/health > /dev/null 2>&1; then
        log_success "Web App is healthy"
    else
        log_warning "Web App is not responding (may still be starting)"
    fi

    # Check Supabase connectivity (uses container's env vars)
    if docker exec dst-airlines-prefect-agent \
        python -c "import os; import psycopg2; conn = psycopg2.connect(host=os.environ['PG_HOST'], port=os.environ['PG_PORT'], dbname=os.environ['PG_DB'], user=os.environ['PG_USER'], password=os.environ['PG_PASSWORD']); conn.close(); print('OK')" 2>&1 | grep -q "OK"; then
        log_success "Database connection is healthy"
    else
        log_error "Cannot connect to database"
    fi
}

# Rebuild services
rebuild_services() {
    log_info "Rebuilding DST Airlines services..."
    docker compose -f $COMPOSE_FILE -p $PROJECT_NAME up -d --build
    log_success "Services rebuilt and started successfully!"
}

# Clean up
clean_services() {
    log_warning "This will stop and remove all DST Airlines containers and volumes!"
    read -p "Are you sure? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Cleaning up DST Airlines services..."
        docker compose -f $COMPOSE_FILE -p $PROJECT_NAME down -v
        log_success "Cleanup completed!"
    else
        log_info "Cleanup cancelled."
    fi
}

###############################################################################
# LOCAL DEVELOPMENT COMMANDS
###############################################################################

# Start local services
start_local() {
    log_info "Starting DST Airlines LOCAL services..."
    docker compose -f $COMPOSE_FILE_LOCAL -p $PROJECT_NAME_LOCAL up -d
    log_success "Local services started!"
    log_info "Access URLs:"
    log_info "  - Prefect UI: http://localhost:4201"
    log_info "  - Web App: http://localhost:8001"
    log_info "  - PostgreSQL: localhost:5432"
}

# Stop local services
stop_local() {
    log_info "Stopping DST Airlines LOCAL services..."
    docker compose -f $COMPOSE_FILE_LOCAL -p $PROJECT_NAME_LOCAL down
    log_success "Local services stopped!"
}

# Rebuild local services
rebuild_local() {
    log_info "Rebuilding DST Airlines LOCAL services..."
    docker compose -f $COMPOSE_FILE_LOCAL -p $PROJECT_NAME_LOCAL up -d --build
    log_success "Local services rebuilt!"
}

# Clean local services
clean_local() {
    log_warning "This will stop and remove all LOCAL containers and volumes!"
    read -p "Are you sure? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Cleaning up LOCAL services..."
        docker compose -f $COMPOSE_FILE_LOCAL -p $PROJECT_NAME_LOCAL down -v
        log_success "Local cleanup completed!"
    else
        log_info "Cleanup cancelled."
    fi
}

# Show local status
status_local() {
    log_info "DST Airlines LOCAL services status:"
    docker compose -f $COMPOSE_FILE_LOCAL -p $PROJECT_NAME_LOCAL ps
}

# Show local logs
logs_local() {
    log_info "Following LOCAL logs (Ctrl+C to exit)..."
    docker compose -f $COMPOSE_FILE_LOCAL -p $PROJECT_NAME_LOCAL logs -f
}

# Show help
show_help() {
    cat << EOF
DST Airlines Deployment Script

Usage:
  ./deploy-dst-airlines.sh [command]

Production Commands (VPS with Supabase):
  start         Start all services
  stop          Stop all services
  restart       Restart all services
  rebuild       Rebuild and restart all services
  clean         Stop and remove all containers and volumes
  deploy-flows  Deploy Prefect workflows
  logs          Follow logs from all services
  logs-api      Follow logs from API service only
  logs-prefect  Follow logs from Prefect services only
  status        Show status of all services
  health        Check health of all services

Local Development Commands:
  start-local   Start local services (with local PostgreSQL)
  stop-local    Stop local services
  rebuild-local Rebuild local services
  clean-local   Remove local containers and volumes
  status-local  Show local services status
  logs-local    Follow local logs

  help          Show this help message

Examples:
  ./deploy-dst-airlines.sh start          # Production (VPS)
  ./deploy-dst-airlines.sh start-local    # Local laptop testing

Environment:
  config/.env - API keys (LH_CLIENT_ID, LH_CLIENT_SECRET, OWM_API_KEY)

  Local mode uses defaults: postgres/localdev on localhost:5432
  Override with env vars: PG_HOST, PG_PORT, PG_USER, PG_PASSWORD, PG_DB

Access URLs (Production):
  - Prefect UI: https://dst-prefect.srv869578.hstgr.cloud
  - Web App: https://dst-airlines.srv869578.hstgr.cloud

Access URLs (Local):
  - Prefect UI: http://localhost:4201
  - Web App: http://localhost:8001

EOF
}

# Main script logic
main() {
    check_dependencies

    # Change to script directory
    cd "$(dirname "$0")"

    case "${1:-help}" in
        start)
            check_env_file
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        logs)
            show_logs
            ;;
        logs-api)
            show_api_logs
            ;;
        logs-prefect)
            show_prefect_logs
            ;;
        status)
            show_status
            ;;
        deploy-flows)
            deploy_flows
            ;;
        health)
            check_health
            ;;
        rebuild)
            check_env_file
            rebuild_services
            ;;
        clean)
            clean_services
            ;;
        start-local)
            check_env_file
            start_local
            ;;
        stop-local)
            stop_local
            ;;
        rebuild-local)
            check_env_file
            rebuild_local
            ;;
        clean-local)
            clean_local
            ;;
        status-local)
            status_local
            ;;
        logs-local)
            logs_local
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
