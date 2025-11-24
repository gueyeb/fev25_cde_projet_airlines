#!/bin/bash

###############################################################################
# DST Airlines Deployment Script
#
# This script deploys the DST Airlines application with:
# - Prefect Server for workflow orchestration
# - Prefect Agent for executing workflows
# - FastAPI Web Application for flight delay predictions
# - Connection to external Supabase database (no local postgres/mongo)
#
# Usage:
#   ./deploy-dst-airlines.sh [command]
#
# Commands:
#   start       - Start all services
#   stop        - Stop all services
#   restart     - Restart all services
#   logs        - Follow logs from all services
#   logs-api    - Follow logs from API service only
#   logs-prefect - Follow logs from Prefect services only
#   status      - Show status of all services
#   deploy-flows - Deploy Prefect workflows
#   health      - Check health of all services
#   rebuild     - Rebuild and restart all services
#   clean       - Stop and remove all containers and volumes
#   help        - Show this help message
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
PROJECT_NAME="dst-airlines"

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

    # Check Supabase connectivity
    if docker exec dst-airlines-prefect-agent \
        python -c "import psycopg2; conn = psycopg2.connect('postgresql://postgres:d0e6de882220c43de3d3ef5abf0c31c7c87145f936918938e9a6120458e94977@srv869578.hstgr.cloud:5433/postgres'); conn.close(); print('OK')" 2>&1 | grep -q "OK"; then
        log_success "Supabase database connection is healthy"
    else
        log_error "Cannot connect to Supabase database"
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

# Show help
show_help() {
    cat << EOF
DST Airlines Deployment Script

Usage:
  ./deploy-dst-airlines.sh [command]

Commands:
  start         Start all services
  stop          Stop all services
  restart       Restart all services
  logs          Follow logs from all services
  logs-api      Follow logs from API service only
  logs-prefect  Follow logs from Prefect services only
  status        Show status of all services
  deploy-flows  Deploy Prefect workflows
  health        Check health of all services
  rebuild       Rebuild and restart all services
  clean         Stop and remove all containers and volumes
  help          Show this help message

Examples:
  ./deploy-dst-airlines.sh start
  ./deploy-dst-airlines.sh logs
  ./deploy-dst-airlines.sh deploy-flows
  ./deploy-dst-airlines.sh health

Environment:
  Configuration is loaded from config/.env
  Make sure to set your API keys before starting:
    - LH_CLIENT_ID (Lufthansa API)
    - LH_CLIENT_SECRET (Lufthansa API)
    - OWM_API_KEY (OpenWeatherMap API)

Access URLs:
  - Prefect UI: https://dst-prefect.srv869578.hstgr.cloud
  - Web App: https://dst-airlines.srv869578.hstgr.cloud
  - Supabase Studio: https://dst-airlines-studio.srv869578.hstgr.cloud

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
