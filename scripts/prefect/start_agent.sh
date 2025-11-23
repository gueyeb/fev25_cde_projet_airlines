#!/bin/bash
#
# Start Prefect Agent
# This agent will execute scheduled flow runs
#

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="${PROJECT_DIR}/logs/prefect"

# Create log directory
mkdir -p "${LOG_DIR}"

echo "[INFO] Starting Prefect agent..."
echo "Logs will be written to: ${LOG_DIR}/agent.log"
echo ""

# Change to project directory to ensure proper imports
cd "${PROJECT_DIR}"

# Set Python path
export PYTHONPATH="${PROJECT_DIR}:${PYTHONPATH:-}"

# Load environment variables if they exist
if [ -f "${PROJECT_DIR}/config/.prodenv" ]; then
    set -a
    source "${PROJECT_DIR}/config/.prodenv"
    set +a
    echo "[INFO] Environment variables loaded"
fi

# Start agent
echo "[INFO] Agent starting on work pool: default"
echo "[INFO] Press Ctrl+C to stop"
echo ""

prefect agent start -q default 2>&1 | tee "${LOG_DIR}/agent.log"
