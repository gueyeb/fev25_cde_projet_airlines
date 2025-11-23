#!/bin/bash
#
# Simple Workflow Orchestration Script
# This script orchestrates the daily data pipeline for the flight delay prediction system
#
# Usage: ./scheduler.sh [daily|hourly|update-actuals]
#

set -euo pipefail

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="${PROJECT_DIR}/logs/orchestration"
PYTHON_BIN="${PYTHON_BIN:-python3}"

# Create log directory if it doesn't exist
mkdir -p "${LOG_DIR}"

# Logging functions
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_DIR}/scheduler.log"
}

log_error() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [ERROR] $*" | tee -a "${LOG_DIR}/scheduler.log" >&2
}

log_success() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [SUCCESS] $*" | tee -a "${LOG_DIR}/scheduler.log"
}

# Error handling
handle_error() {
    local exit_code=$?
    local line_number=$1
    log_error "Script failed at line ${line_number} with exit code ${exit_code}"

    # Optional: Send alert email or Slack notification
    # send_alert "Pipeline failed at line ${line_number}"

    exit ${exit_code}
}

trap 'handle_error ${LINENO}' ERR

# Change to project directory
cd "${PROJECT_DIR}"

# Set Python path
export PYTHONPATH="${PROJECT_DIR}:${PYTHONPATH:-}"

# Load environment variables
if [ -f "${PROJECT_DIR}/config/.prodenv" ]; then
    set -a
    source "${PROJECT_DIR}/config/.prodenv"
    set +a
    log "Environment variables loaded from config/.prodenv"
fi

# Task execution wrapper
run_task() {
    local task_name="$1"
    local module_name="$2"
    shift 2
    local args="$@"

    log "[TASK START] ${task_name}"
    local start_time=$(date +%s)

    if ${PYTHON_BIN} -m "${module_name}" ${args} >> "${LOG_DIR}/${task_name}.log" 2>&1; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log_success "[TASK COMPLETE] ${task_name} (${duration}s)"
        return 0
    else
        log_error "[TASK FAILED] ${task_name}"
        return 1
    fi
}

# Daily Pipeline: Full data sync
daily_pipeline() {
    log "========================================="
    log "Starting Daily Pipeline"
    log "========================================="

    local TARGET_DATE="${1:-$(date +%Y-%m-%d)}"

    # Reference data sync (only if needed)
    log "[STEP 1/7] Syncing reference data..."
    run_task "sync_countries" "src.jobs.sync_countries" || true
    run_task "sync_cities" "src.jobs.sync_cities" || true
    run_task "sync_airlines" "src.jobs.sync_airlines" || true
    run_task "sync_airports" "src.jobs.sync_airports" || true
    run_task "sync_aircrafts" "src.jobs.sync_aircrafts" || true

    log "[STEP 2/7] Creating routes..."
    run_task "create_routes" "src.jobs.create_routes" || true

    log "[STEP 3/7] Syncing flight history for ${TARGET_DATE}..."
    run_task "sync_flight_history" "src.jobs.sync_flight_history" --date "${TARGET_DATE}"

    log "[STEP 4/7] Enriching weather data..."
    run_task "enrich_weather" "src.jobs.enrich_weather" --date "${TARGET_DATE}"

    log_success "Daily pipeline completed successfully"
}

# Hourly Pipeline: Update flight actuals
hourly_update_actuals() {
    log "========================================="
    log "Starting Hourly Actuals Update"
    log "========================================="

    run_task "update_flight_actuals" "src.jobs.update_flight_history"

    log_success "Hourly actuals update completed"
}

# ML Model Training Pipeline
train_model() {
    log "========================================="
    log "Starting ML Model Training"
    log "========================================="

    run_task "train_classification_model" "src.ml.ml_classification"

    log_success "ML model training completed"
}

# Health check
health_check() {
    log "Performing health check..."

    # Check database connectivity
    if ${PYTHON_BIN} -c "from src.utils.pg_functions import engine; engine.connect()" 2>/dev/null; then
        log_success "Database connection OK"
    else
        log_error "Database connection FAILED"
        return 1
    fi

    # Check API credentials
    if [ -n "${LH_CLIENT_ID:-}" ] && [ -n "${LH_CLIENT_SECRET:-}" ]; then
        log_success "API credentials configured"
    else
        log_error "API credentials missing"
        return 1
    fi

    log_success "Health check passed"
}

# Main execution
main() {
    local command="${1:-daily}"

    # Run health check first
    health_check || exit 1

    case "${command}" in
        daily)
            daily_pipeline "${2:-}"
            ;;
        hourly|update-actuals)
            hourly_update_actuals
            ;;
        train-model)
            train_model
            ;;
        health)
            log_success "System is healthy"
            ;;
        *)
            log_error "Unknown command: ${command}"
            echo "Usage: $0 [daily|hourly|train-model|health]"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
